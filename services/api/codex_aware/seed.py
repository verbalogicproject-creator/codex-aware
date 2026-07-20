from __future__ import annotations

from .models import GraphEdge, GraphNode, SafetyClass


def seed_graph() -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes = [
        GraphNode(id="project:team-todo", kind="project", label="Team Todo", summary="Collaborative task management", x=80, y=100),
        GraphNode(id="command:team-todo:delete_task", kind="command", label="delete_task", project="Team Todo", uri="repo://team-todo/src/lib/aria/commands.ts#delete_task", safety_class=SafetyClass.UNCLASSIFIED, summary="Deletes a shared task by stable ID", x=280, y=65, metadata={"mutation": True, "runtime_guards": []}),
        GraphNode(id="handler:team-todo:deleteTask", kind="handler", label="deleteTask()", project="Team Todo", uri="repo://team-todo/src/lib/aria/commands.ts#createCommands", summary="Firestore-backed destructive mutation", x=485, y=65),
        GraphNode(id="store:team-todo:firestore", kind="runtime", label="Shared task store", project="Team Todo", summary="Durable multi-user state", x=680, y=65),
        GraphNode(id="project:neon-battleship", kind="project", label="Neon Battleship", summary="Phase-aware strategy game", x=80, y=270),
        GraphNode(id="command:neon-battleship:fire_at", kind="command", label="fire_at", project="Neon Battleship", uri="repo://neon-battleship/src/lib/aria/commands.ts#fire_at", safety_class=SafetyClass.PROTECTED, summary="Fires at an enemy coordinate", x=280, y=235, metadata={"mutation": True, "runtime_guards": ["phase=battle", "isPlayerTurn"]}),
        GraphNode(id="guard:neon-battleship:phase", kind="gate", label="Phase + turn guard", project="Neon Battleship", uri="repo://neon-battleship/src/lib/aria/commands.ts#APPLICABLE_PHASES", summary="Rejects fire outside battle or the player's turn", x=485, y=235),
        GraphNode(id="engine:neon-battleship:shot", kind="runtime", label="Game engine", project="Neon Battleship", summary="Authoritative shot outcome", x=680, y=235),
        GraphNode(id="project:veleur-fashion", kind="project", label="Veleur Fashion", summary="Commerce storefront", x=80, y=440),
        GraphNode(id="command:veleur-fashion:add_to_cart", kind="command", label="add_to_cart", project="Veleur Fashion", uri="repo://veleur-fashion/src/lib/aria/commands.ts#add_to_cart", safety_class=SafetyClass.SAFE, summary="Adds a known catalog item", x=280, y=405),
        GraphNode(id="route:veleur-fashion:checkout", kind="route", label="/checkout", project="Veleur Fashion", summary="Browser-mediated checkout boundary", x=485, y=405),
        GraphNode(id="project:greenleaf-coffee", kind="project", label="Greenleaf Coffee", summary="Informational hospitality site", x=80, y=610),
        GraphNode(id="command:greenleaf-coffee:navigate", kind="command", label="navigate", project="Greenleaf Coffee", uri="repo://greenleaf-coffee/lib/aria/commands.ts#navigate", safety_class=SafetyClass.SAFE, summary="Navigates between public routes", x=280, y=575),
        GraphNode(id="route:greenleaf-coffee:menu", kind="route", label="/menu", project="Greenleaf Coffee", summary="Public menu route", x=485, y=575),
    ]
    edges = [
        GraphEdge(id="e1", source="project:team-todo", target="command:team-todo:delete_task", kind="declares"),
        GraphEdge(id="e2", source="command:team-todo:delete_task", target="handler:team-todo:deleteTask", kind="dispatches"),
        GraphEdge(id="e3", source="handler:team-todo:deleteTask", target="store:team-todo:firestore", kind="mutates"),
        GraphEdge(id="e4", source="project:neon-battleship", target="command:neon-battleship:fire_at", kind="declares"),
        GraphEdge(id="e5", source="command:neon-battleship:fire_at", target="guard:neon-battleship:phase", kind="guarded_by"),
        GraphEdge(id="e6", source="guard:neon-battleship:phase", target="engine:neon-battleship:shot", kind="permits"),
        GraphEdge(id="e7", source="project:veleur-fashion", target="command:veleur-fashion:add_to_cart", kind="declares"),
        GraphEdge(id="e8", source="command:veleur-fashion:add_to_cart", target="route:veleur-fashion:checkout", kind="precedes"),
        GraphEdge(id="e9", source="project:greenleaf-coffee", target="command:greenleaf-coffee:navigate", kind="declares"),
        GraphEdge(id="e10", source="command:greenleaf-coffee:navigate", target="route:greenleaf-coffee:menu", kind="targets"),
    ]
    return nodes, edges


INTERNAL_TRACE_NODES = [
    GraphNode(id="aware:context", kind="internal", label="Deictic resolver", summary="Stable selection → bounded context", x=260, y=150),
    GraphNode(id="aware:policy", kind="internal", label="Policy gate", summary="Application-owned authority check", x=455, y=150),
    GraphNode(id="aware:directive", kind="internal", label="Semantic directive", summary="Command identity, never DOM coordinates", x=650, y=150),
    GraphNode(id="aware:event-log", kind="internal", label="Continuity log", summary="Append-only causal sequence", x=260, y=340),
    GraphNode(id="aware:effect", kind="internal", label="Effect observer", summary="Browser ACK before success", x=455, y=340),
    GraphNode(id="aware:receipt", kind="receipt", label="Verified receipt", summary="Grounding + gate + effect + source", x=650, y=340),
]

