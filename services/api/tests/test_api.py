from __future__ import annotations


def select_incident(client):
    response = client.post(
        "/api/workspaces/default/selection",
        json={"node_ids": ["command:team-todo:delete_task", "command:neon-battleship:fire_at"]},
    )
    assert response.status_code == 200


def attach(client):
    code = client.post("/api/workspaces/default/pair").json()["code"]
    response = client.post("/api/pair/attach", json={"code": code, "actor_name": "Test Codex"})
    assert response.status_code == 200
    return response.json()["token"]


def test_seeded_graph_and_grounded_context(client):
    graph = client.get("/api/workspaces/default/graph").json()
    assert len(graph["nodes"]) == 14
    select_incident(client)
    context = client.get("/api/workspaces/default/context").json()
    assert context["active_incident"] == "Capability safety drift"
    assert {node["label"] for node in context["selection"]} == {"delete_task", "fire_at"}
    assert context["grounding"]["source"] == "application-owned semantic graph"


def test_pair_code_is_single_use(client):
    code = client.post("/api/workspaces/default/pair").json()["code"]
    assert client.post("/api/pair/attach", json={"code": code, "actor_name": "Codex"}).status_code == 200
    assert client.post("/api/pair/attach", json={"code": code, "actor_name": "Replay"}).status_code == 400


def test_dispatch_is_not_success_until_observed(client):
    select_incident(client)
    receipt = client.post(
        "/api/workspaces/default/actions",
        json={"command": "reveal_blast_radius", "arguments": {}},
    ).json()
    assert receipt["status"] == "awaiting_consumer"
    directive = receipt["payload"]["directive"]
    final = client.post(
        "/api/workspaces/default/effects",
        json={
            "receipt_id": receipt["id"],
            "directive_id": directive["id"],
            "observed": {"target_count": len(directive["target_ids"])},
        },
    ).json()
    assert final["status"] == "executed"
    assert final["payload"]["observed_effect"]["kind"] == "graph.reveal.observed"


def test_proposal_hash_and_human_gate(client):
    select_incident(client)
    receipt = client.post(
        "/api/workspaces/default/actions",
        json={
            "command": "classify_command",
            "arguments": {
                "node_id": "command:team-todo:delete_task",
                "safety_class": "protected",
                "confirmation_policy": "human_approval",
            },
        },
    ).json()
    proposal = receipt["payload"]["proposal"]
    assert receipt["status"] == "awaiting_approval"
    bad = client.post(
        f"/api/workspaces/default/proposals/{proposal['id']}",
        json={"proposal_hash": "0" * 64, "decision": "approved"},
    )
    assert bad.status_code == 409
    good = client.post(
        f"/api/workspaces/default/proposals/{proposal['id']}",
        json={"proposal_hash": proposal["proposal_hash"], "decision": "approved"},
    )
    assert good.status_code == 200
    assert good.json()["proposal"]["status"] == "approved"


def test_refresh_requires_actor_approval_and_policy(client):
    select_incident(client)
    token = attach(client)
    denied = client.post(
        "/api/workspaces/default/refresh",
        headers={"authorization": f"Bearer {token}"},
        json={
            "snapshot_hash": "abc",
            "policies": {"command:team-todo:delete_task": {"safety_class": "protected", "confirmation_policy": "human_approval"}},
            "test_result": {"status": "passed"},
        },
    )
    assert denied.status_code == 403
    receipt = client.post(
        "/api/workspaces/default/actions",
        json={
            "command": "classify_command",
            "arguments": {"node_id": "command:team-todo:delete_task", "safety_class": "protected", "confirmation_policy": "human_approval"},
        },
    ).json()
    proposal = receipt["payload"]["proposal"]
    client.post(
        f"/api/workspaces/default/proposals/{proposal['id']}",
        json={"proposal_hash": proposal["proposal_hash"], "decision": "approved"},
    )
    refreshed = client.post(
        "/api/workspaces/default/refresh",
        headers={"authorization": f"Bearer {token}"},
        json={
            "snapshot_hash": "policy-hash",
            "policies": {"command:team-todo:delete_task": {"safety_class": "protected", "confirmation_policy": "human_approval"}},
            "test_result": {"status": "passed", "test": "team-todo-policy"},
        },
    )
    assert refreshed.status_code == 200
    node = next(n for n in refreshed.json()["graph"]["nodes"] if n["id"] == "command:team-todo:delete_task")
    assert node["safety_class"] == "protected"


def test_unknown_command_fails_closed(client):
    receipt = client.post(
        "/api/workspaces/default/actions",
        json={"command": "deploy_everything", "arguments": {}},
    ).json()
    assert receipt["status"] == "denied"

