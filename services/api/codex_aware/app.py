from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .models import ActionRequest, EffectAck, MCPRequest, PairAttach, ProposalDecision, RefreshRequest, SelectionRequest
from .seed import INTERNAL_TRACE_NODES
from .store import Store, digest

DATABASE_PATH = os.getenv("AWARE_DATABASE_PATH", str(Path(__file__).parents[4] / "data" / "aware.db"))
DATABASE_URL = os.getenv("AWARE_DATABASE_URL")
if DATABASE_URL:
    from .postgres import PostgresStore

    store = PostgresStore(DATABASE_URL)
else:
    store = Store(DATABASE_PATH)
app = FastAPI(title="Codex Aware", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in os.getenv("AWARE_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def workspace(value: str = Header("default", alias="X-Aware-Workspace")) -> str:
    store.ensure_workspace(value)
    return value


def actor(authorization: str | None = Header(None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Pair Codex first")
    record = store.authenticate(authorization.removeprefix("Bearer ").strip())
    if not record:
        raise HTTPException(401, "Invalid or revoked actor token")
    return record


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "product": "Codex Aware"}


@app.get("/api/workspaces/{workspace_id}/graph")
def get_graph(workspace_id: str) -> dict[str, Any]:
    store.ensure_workspace(workspace_id)
    return store.graph(workspace_id)


@app.post("/api/workspaces/{workspace_id}/reset")
def reset_workspace(workspace_id: str) -> dict[str, bool]:
    store.reset(workspace_id)
    return {"reset": True}


@app.post("/api/workspaces/{workspace_id}/pair")
def create_pair(workspace_id: str) -> dict[str, Any]:
    store.ensure_workspace(workspace_id)
    return {"code": store.create_pair_code(workspace_id), "expires_in": 300}


@app.post("/api/pair/attach")
def attach(request: PairAttach) -> dict[str, Any]:
    result = store.attach(request.code, request.actor_name)
    if not result:
        raise HTTPException(400, "Pairing code is invalid, expired, or already used")
    token, workspace_id = result
    return {"token": token, "workspace_id": workspace_id, "scopes": ["context:read", "graph:read", "action:request", "receipt:read", "snapshot:write"]}


@app.post("/api/workspaces/{workspace_id}/selection")
def set_selection(workspace_id: str, request: SelectionRequest) -> dict[str, Any]:
    store.ensure_workspace(workspace_id)
    nodes = [store.node(workspace_id, node_id) for node_id in request.node_ids]
    if any(node is None for node in nodes):
        raise HTTPException(404, "One or more graph nodes do not exist")
    if current_selection(workspace_id) == request.node_ids:
        return {"selection": nodes, "event": None, "unchanged": True}
    event = store.event(workspace_id, "context.selection_changed", "browser", {"node_ids": request.node_ids})
    return {"selection": nodes, "event": event, "unchanged": False}


def current_selection(workspace_id: str) -> list[str]:
    event = store.latest_event(workspace_id, "context.selection_changed")
    return event["payload"]["node_ids"] if event else []


def bounded_context(workspace_id: str) -> dict[str, Any]:
    graph = store.graph(workspace_id)
    selected_ids = current_selection(workspace_id)
    selected = [node for node in graph["nodes"] if node["id"] in selected_ids]
    related_ids = set(selected_ids)
    for edge in graph["edges"]:
        if edge["source"] in selected_ids or edge["target"] in selected_ids:
            related_ids.update((edge["source"], edge["target"]))
    related = [node for node in graph["nodes"] if node["id"] in related_ids and node["id"] not in selected_ids]
    gap = any(node.get("safety_class") == "unclassified" for node in selected)
    return {
        "selection": selected,
        "related": related[:12],
        "active_incident": "Capability safety drift" if gap else None,
        "grounding": {
            "source": "application-owned semantic graph",
            "selection_event": True,
            "omitted_nodes": max(0, len(graph["nodes"]) - len(selected) - len(related)),
            "snapshot_hash": graph["snapshot_hash"],
        },
    }


@app.get("/api/workspaces/{workspace_id}/context")
def get_context(workspace_id: str) -> dict[str, Any]:
    return bounded_context(workspace_id)


@app.get("/api/workspaces/{workspace_id}/events")
def get_events(workspace_id: str, after: int = Query(0, ge=0)) -> list[dict[str, Any]]:
    return store.events(workspace_id, after)


@app.get("/api/workspaces/{workspace_id}/receipts")
def get_receipts(workspace_id: str) -> list[dict[str, Any]]:
    return store.receipts(workspace_id)


@app.post("/api/workspaces/{workspace_id}/actions")
def request_action(workspace_id: str, request: ActionRequest, authorization: str | None = Header(None)) -> dict[str, Any]:
    actor_name = "browser"
    if authorization:
        record = actor(authorization)
        if record["workspace_id"] != workspace_id:
            raise HTTPException(403, "Actor is scoped to another workspace")
        actor_name = record["actor_name"]
    trace_id = str(uuid.uuid4())
    context = bounded_context(workspace_id)
    store.event(workspace_id, "action.requested", actor_name, {"command": request.command, "arguments": request.arguments}, trace_id)

    if request.command == "reveal_blast_radius":
        selected = [n["id"] for n in context["selection"]]
        if not selected:
            raise HTTPException(409, "Select one or more graph nodes first")
        graph = store.graph(workspace_id)
        targets = set(selected)
        for edge in graph["edges"]:
            if edge["source"] in targets or edge["target"] in targets:
                targets.update((edge["source"], edge["target"]))
        directive_id = str(uuid.uuid4())
        receipt = store.create_receipt(
            workspace_id, request.command, "awaiting_consumer",
            {"grounding": context, "directive": {"id": directive_id, "kind": "graph.reveal", "target_ids": sorted(targets)}, "evidence": ["selection_event", "graph_edges"]},
            trace_id,
        )
        store.event(workspace_id, "directive.issued", "policy-engine", {"receipt_id": receipt["id"], **receipt["payload"]["directive"]}, trace_id)
        return receipt

    if request.command == "classify_command":
        node_id = str(request.arguments.get("node_id", ""))
        safety_class = str(request.arguments.get("safety_class", ""))
        confirmation_policy = str(request.arguments.get("confirmation_policy", ""))
        if node_id != "command:team-todo:delete_task" or safety_class != "protected" or confirmation_policy != "human_approval":
            return store.create_receipt(workspace_id, request.command, "denied", {"reason": "Only the bounded seeded classification proposal is eligible", "arguments_hash": digest(json.dumps(request.arguments, sort_keys=True))}, trace_id)
        proposal = store.create_proposal(workspace_id, {"node_id": node_id, "safety_class": safety_class, "confirmation_policy": confirmation_policy, "adapter_uri": "repo://codex-aware/examples/team-todo/aware.yaml"})
        receipt = store.create_receipt(workspace_id, request.command, "awaiting_approval", {"grounding": context, "proposal": proposal}, trace_id)
        store.event(workspace_id, "proposal.created", actor_name, {"proposal_id": proposal["id"], "receipt_id": receipt["id"], "proposal_hash": proposal["proposal_hash"]}, trace_id)
        return receipt

    return store.create_receipt(workspace_id, request.command, "denied", {"reason": "Command is not declared by this application"}, trace_id)


@app.post("/api/workspaces/{workspace_id}/effects")
def acknowledge_effect(workspace_id: str, ack: EffectAck) -> dict[str, Any]:
    receipt = store.receipt(workspace_id, ack.receipt_id)
    if not receipt or receipt["payload"].get("directive", {}).get("id") != ack.directive_id:
        raise HTTPException(409, "Receipt and directive do not match")
    observed = {
        "kind": "graph.reveal.observed",
        "target_count": min(int(ack.observed.get("target_count", 0)), 100),
        "view_hash": digest(json.dumps(ack.observed, sort_keys=True)),
    }
    updated = store.update_receipt(workspace_id, ack.receipt_id, "executed", {"observed_effect": observed})
    store.event(workspace_id, "effect.observed", "browser", {"receipt_id": ack.receipt_id, **observed}, receipt["trace_id"])
    store.event(workspace_id, "receipt.finalized", "system", {"receipt_id": ack.receipt_id, "status": "executed"}, receipt["trace_id"])
    return updated


@app.post("/api/workspaces/{workspace_id}/proposals/{proposal_id}")
def decide_proposal(workspace_id: str, proposal_id: str, decision: ProposalDecision) -> dict[str, Any]:
    proposal = store.decide_proposal(workspace_id, proposal_id, decision.proposal_hash, decision.decision)
    if not proposal:
        raise HTTPException(409, "Proposal is stale, mismatched, or already decided")
    event = store.event(workspace_id, f"proposal.{proposal['status']}", "browser-human", {"proposal_id": proposal_id, "proposal_hash": proposal["proposal_hash"]})
    return {"proposal": proposal, "event": event}


@app.post("/api/workspaces/{workspace_id}/refresh")
def refresh(workspace_id: str, request: RefreshRequest, authenticated: dict[str, Any] = Depends(actor)) -> dict[str, Any]:
    if authenticated["workspace_id"] != workspace_id:
        raise HTTPException(403, "Actor is scoped to another workspace")
    policy = request.policies.get("command:team-todo:delete_task")
    if not policy or policy.get("safety_class") != "protected" or policy.get("confirmation_policy") != "human_approval":
        raise HTTPException(422, "Snapshot does not contain the expected approved policy")
    approvals = [e for e in store.events(workspace_id, 0, 200) if e["kind"] == "proposal.approved"]
    if not approvals:
        raise HTTPException(403, "A browser-human approval is required before refresh")
    node_data = store.node(workspace_id, "command:team-todo:delete_task")
    node_data["safety_class"] = "protected"
    node_data["metadata"] = {**node_data.get("metadata", {}), "confirmation_policy": "human_approval", "policy_source": "repo://codex-aware/examples/team-todo/aware.yaml", "test": request.test_result}
    from .models import GraphNode
    store.put_node(workspace_id, GraphNode.model_validate(node_data))
    if hasattr(store, "set_snapshot_hash"):
        store.set_snapshot_hash(workspace_id, request.snapshot_hash)
    else:
        store.db.execute("UPDATE workspaces SET snapshot_hash=? WHERE id=?", (request.snapshot_hash, workspace_id))
        store.db.commit()
    event = store.event(workspace_id, "repository.refreshed", authenticated["actor_name"], {"snapshot_hash": request.snapshot_hash, "changed_nodes": ["command:team-todo:delete_task"], "test_result": request.test_result})
    receipt = store.create_receipt(workspace_id, "aware_refresh", "executed", {"snapshot_hash": request.snapshot_hash, "changed_nodes": ["command:team-todo:delete_task"], "test_result": request.test_result, "approval_event_id": approvals[-1]["id"], "observed_effect": {"kind": "policy.verified"}})
    return {"graph": store.graph(workspace_id), "event": event, "receipt": receipt}


@app.get("/api/workspaces/{workspace_id}/architecture")
def architecture(workspace_id: str) -> dict[str, Any]:
    return {
        "nodes": [node.model_dump(mode="json") for node in INTERNAL_TRACE_NODES],
        "edges": [
            {"id": "a1", "source": "aware:context", "target": "aware:policy", "kind": "grounds"},
            {"id": "a2", "source": "aware:policy", "target": "aware:directive", "kind": "permits"},
            {"id": "a3", "source": "aware:context", "target": "aware:event-log", "kind": "records"},
            {"id": "a4", "source": "aware:directive", "target": "aware:effect", "kind": "observed_by"},
            {"id": "a5", "source": "aware:event-log", "target": "aware:receipt", "kind": "causes"},
            {"id": "a6", "source": "aware:effect", "target": "aware:receipt", "kind": "verifies"},
        ],
    }


TOOLS = [
    {"name": "aware_attach", "description": "Attach Codex to a browser workspace using a one-time code.", "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}, "actor_name": {"type": "string"}}, "required": ["code"]}, "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}},
    {"name": "aware_context", "description": "Resolve the current semantic selection and active incident.", "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "aware_graph", "description": "Read the bounded semantic graph.", "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "aware_act", "description": "Request a declared semantic action through application-owned gates.", "inputSchema": {"type": "object", "properties": {"command": {"type": "string"}, "arguments": {"type": "object"}}, "required": ["command"]}, "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}},
    {"name": "aware_receipt", "description": "Inspect verified and pending action receipts.", "inputSchema": {"type": "object", "properties": {"receipt_id": {"type": "string"}}}, "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "aware_refresh", "description": "Publish an approved sanitized policy snapshot.", "inputSchema": {"type": "object", "properties": {"snapshot_hash": {"type": "string"}, "policies": {"type": "object"}, "test_result": {"type": "object"}}, "required": ["snapshot_hash", "policies"]}, "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
]


@app.post("/mcp")
def mcp(request: MCPRequest, authorization: str | None = Header(None)) -> dict[str, Any]:
    if request.method == "initialize":
        result = {"protocolVersion": "2025-03-26", "serverInfo": {"name": "codex-aware", "version": "0.1.0"}, "capabilities": {"tools": {}}}
    elif request.method == "tools/list":
        result = {"tools": TOOLS}
    elif request.method == "tools/call":
        name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        if name == "aware_attach":
            result = attach(PairAttach(code=arguments["code"], actor_name=arguments.get("actor_name", "Codex")))
        else:
            record = actor(authorization)
            workspace_id = record["workspace_id"]
            if name == "aware_context":
                result = bounded_context(workspace_id)
            elif name == "aware_graph":
                result = store.graph(workspace_id)
            elif name == "aware_act":
                result = request_action(workspace_id, ActionRequest(command=arguments["command"], arguments=arguments.get("arguments", {})), authorization)
            elif name == "aware_receipt":
                result = store.receipt(workspace_id, arguments["receipt_id"]) if arguments.get("receipt_id") else store.receipts(workspace_id)
            elif name == "aware_refresh":
                result = refresh(workspace_id, RefreshRequest.model_validate(arguments), record)
            else:
                raise HTTPException(404, "Unknown tool")
        result = {"content": [{"type": "text", "text": json.dumps(result, separators=(",", ":"))}], "structuredContent": result}
    else:
        raise HTTPException(404, "Unknown MCP method")
    return {"jsonrpc": "2.0", "id": request.id, "result": result}


@app.websocket("/ws/{workspace_id}")
async def events_socket(socket: WebSocket, workspace_id: str):
    await socket.accept()
    # REST hydrates the current graph and receipts. The live channel starts at
    # "now" so a reconnect cannot replay an unbounded historical event stream.
    cursor = store.latest_sequence(workspace_id)
    try:
        while True:
            await socket.receive_text()
            events = store.events(workspace_id, cursor)
            for event in events:
                cursor = event["sequence"]
                await socket.send_json(event)
    except WebSocketDisconnect:
        return


# ChatGPT web/mobile use the standard MCP Apps transport mounted beside the
# browser API, so both surfaces share one event log and one authority boundary.
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

MCP_ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "AWARE_MCP_ALLOWED_HOSTS",
        "127.0.0.1:*,localhost:*,codex-aware-jchnbap7ea-zf.a.run.app,"
        "codex-aware-67134152472.me-west1.run.app",
    ).split(",")
    if host.strip()
]

chatgpt_mcp = FastMCP(
    "Codex Aware",
    instructions=(
        "Resolve the person's current application selection before acting. "
        "Visual reveals are safe. Durable policy changes remain browser-human gated."
    ),
    website_url="https://github.com/verbalogicproject-creator/codex-aware",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/mcp",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=MCP_ALLOWED_HOSTS,
        allowed_origins=["https://chatgpt.com", "https://chat.openai.com", "http://localhost:*"],
    ),
)


@chatgpt_mcp.tool(
    name="aware_context",
    title="Read current application context",
    description="Resolve the current browser selection into stable application-owned identities.",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
)
def chatgpt_aware_context() -> dict[str, Any]:
    return bounded_context("default")


@chatgpt_mcp.tool(
    name="aware_graph",
    title="Inspect the semantic graph",
    description="Read the bounded graph of applications, commands, handlers, policies, and runtime boundaries.",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
)
def chatgpt_aware_graph() -> dict[str, Any]:
    return store.graph("default")


@chatgpt_mcp.tool(
    name="aware_reveal_blast_radius",
    title="Reveal blast radius",
    description="Ask the connected browser to highlight the semantic blast radius of its current selection.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
)
def chatgpt_aware_reveal_blast_radius() -> dict[str, Any]:
    return request_action("default", ActionRequest(command="reveal_blast_radius"), None)


@chatgpt_mcp.tool(
    name="aware_propose_boundary",
    title="Propose a protected command boundary",
    description="Create the bounded Team Todo proposal. A browser human must approve it; this tool cannot edit source.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
)
def chatgpt_aware_propose_boundary() -> dict[str, Any]:
    return request_action(
        "default",
        ActionRequest(
            command="classify_command",
            arguments={
                "node_id": "command:team-todo:delete_task",
                "safety_class": "protected",
                "confirmation_policy": "human_approval",
            },
        ),
        None,
    )


@chatgpt_mcp.tool(
    name="aware_receipts",
    title="Inspect continuity receipts",
    description="Read the latest bounded request, gate, directive, and observed-effect receipts.",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
)
def chatgpt_aware_receipts() -> list[dict[str, Any]]:
    return store.receipts("default")

chatgpt_http_app = chatgpt_mcp.streamable_http_app()


@asynccontextmanager
async def combined_lifespan(_: FastAPI):
    async with chatgpt_mcp.session_manager.run():
        yield


app.router.lifespan_context = combined_lifespan
app.mount("/chatgpt", chatgpt_http_app)
