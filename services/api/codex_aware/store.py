from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .models import GraphNode
from .seed import seed_graph


def now_ms() -> int:
    return int(time.time() * 1000)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Store:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.migrate()
        self.ensure_workspace("default")

    def migrate(self) -> None:
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS workspaces (
              id TEXT PRIMARY KEY, created_at INTEGER NOT NULL, snapshot_hash TEXT
            );
            CREATE TABLE IF NOT EXISTS nodes (
              workspace_id TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL,
              PRIMARY KEY(workspace_id, id)
            );
            CREATE TABLE IF NOT EXISTS edges (
              workspace_id TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL,
              PRIMARY KEY(workspace_id, id)
            );
            CREATE TABLE IF NOT EXISTS events (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
              workspace_id TEXT NOT NULL, kind TEXT NOT NULL, actor TEXT NOT NULL,
              trace_id TEXT NOT NULL, causation_id TEXT, schema_version INTEGER NOT NULL,
              payload TEXT NOT NULL, created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pair_codes (
              code_hash TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
              expires_at INTEGER NOT NULL, consumed_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS actor_tokens (
              token_hash TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
              actor_name TEXT NOT NULL, scopes TEXT NOT NULL,
              created_at INTEGER NOT NULL, revoked_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS proposals (
              id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, proposal_hash TEXT NOT NULL,
              payload TEXT NOT NULL, status TEXT NOT NULL, created_at INTEGER NOT NULL,
              decided_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS receipts (
              id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, trace_id TEXT NOT NULL,
              command TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL,
              created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
            );
            """
        )
        self.db.commit()

    def ensure_workspace(self, workspace_id: str) -> None:
        with self._lock:
            row = self.db.execute("SELECT id FROM workspaces WHERE id=?", (workspace_id,)).fetchone()
            if row:
                return
            self.db.execute("INSERT INTO workspaces(id, created_at) VALUES (?,?)", (workspace_id, now_ms()))
            nodes, edges = seed_graph()
            self.db.executemany(
                "INSERT INTO nodes VALUES (?,?,?)",
                [(workspace_id, node.id, node.model_dump_json()) for node in nodes],
            )
            self.db.executemany(
                "INSERT INTO edges VALUES (?,?,?)",
                [(workspace_id, edge.id, edge.model_dump_json()) for edge in edges],
            )
            self.db.commit()
            self.event(workspace_id, "workspace.seeded", "system", {"node_count": len(nodes)})

    def reset(self, workspace_id: str) -> None:
        with self._lock:
            for table in ("nodes", "edges", "events", "proposals", "receipts", "actor_tokens", "pair_codes"):
                self.db.execute(f"DELETE FROM {table} WHERE workspace_id=?", (workspace_id,))
            self.db.execute("DELETE FROM workspaces WHERE id=?", (workspace_id,))
            self.db.commit()
            self.ensure_workspace(workspace_id)

    def graph(self, workspace_id: str) -> dict[str, Any]:
        nodes = [json.loads(r["payload"]) for r in self.db.execute("SELECT payload FROM nodes WHERE workspace_id=?", (workspace_id,))]
        edges = [json.loads(r["payload"]) for r in self.db.execute("SELECT payload FROM edges WHERE workspace_id=?", (workspace_id,))]
        snapshot = self.db.execute("SELECT snapshot_hash FROM workspaces WHERE id=?", (workspace_id,)).fetchone()
        return {"nodes": nodes, "edges": edges, "snapshot_hash": snapshot["snapshot_hash"] if snapshot else None}

    def node(self, workspace_id: str, node_id: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT payload FROM nodes WHERE workspace_id=? AND id=?", (workspace_id, node_id)).fetchone()
        return json.loads(row["payload"]) if row else None

    def put_node(self, workspace_id: str, node: GraphNode) -> None:
        self.db.execute(
            "INSERT INTO nodes VALUES (?,?,?) ON CONFLICT(workspace_id,id) DO UPDATE SET payload=excluded.payload",
            (workspace_id, node.id, node.model_dump_json()),
        )
        self.db.commit()

    def event(self, workspace_id: str, kind: str, actor: str, payload: dict[str, Any], trace_id: str | None = None, causation_id: str | None = None) -> dict[str, Any]:
        event_id = str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())
        created_at = now_ms()
        cursor = self.db.execute(
            "INSERT INTO events(id,workspace_id,kind,actor,trace_id,causation_id,schema_version,payload,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (event_id, workspace_id, kind, actor, trace_id, causation_id, 1, json.dumps(payload, separators=(",", ":")), created_at),
        )
        self.db.commit()
        return {"sequence": cursor.lastrowid, "id": event_id, "workspace_id": workspace_id, "kind": kind, "actor": actor, "trace_id": trace_id, "causation_id": causation_id, "schema_version": 1, "payload": payload, "created_at": created_at}

    def events(self, workspace_id: str, after: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM events WHERE workspace_id=? AND sequence>? ORDER BY sequence LIMIT ?",
            (workspace_id, after, min(limit, 200)),
        )
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def create_pair_code(self, workspace_id: str) -> str:
        code = f"{secrets.randbelow(1_000_000):06d}"
        self.db.execute("DELETE FROM pair_codes WHERE workspace_id=?", (workspace_id,))
        self.db.execute("INSERT INTO pair_codes VALUES (?,?,?,NULL)", (digest(code), workspace_id, now_ms() + 300_000))
        self.db.commit()
        self.event(workspace_id, "pairing.code_created", "browser", {"expires_in_seconds": 300})
        return code

    def attach(self, code: str, actor_name: str) -> tuple[str, str] | None:
        row = self.db.execute("SELECT * FROM pair_codes WHERE code_hash=?", (digest(code),)).fetchone()
        if not row or row["consumed_at"] or row["expires_at"] < now_ms():
            return None
        token = secrets.token_urlsafe(32)
        scopes = ["context:read", "graph:read", "action:request", "receipt:read", "snapshot:write"]
        self.db.execute("UPDATE pair_codes SET consumed_at=? WHERE code_hash=?", (now_ms(), digest(code)))
        self.db.execute(
            "INSERT INTO actor_tokens VALUES (?,?,?,?,?,NULL)",
            (digest(token), row["workspace_id"], actor_name, json.dumps(scopes), now_ms()),
        )
        self.db.commit()
        self.event(row["workspace_id"], "actor.attached", actor_name, {"scopes": scopes})
        return token, row["workspace_id"]

    def authenticate(self, token: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM actor_tokens WHERE token_hash=? AND revoked_at IS NULL", (digest(token),)).fetchone()
        return dict(row) if row else None

    def create_receipt(self, workspace_id: str, command: str, status: str, payload: dict[str, Any], trace_id: str | None = None) -> dict[str, Any]:
        receipt_id = str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())
        created = now_ms()
        self.db.execute("INSERT INTO receipts VALUES (?,?,?,?,?,?,?,?)", (receipt_id, workspace_id, trace_id, command, status, json.dumps(payload), created, created))
        self.db.commit()
        return self.receipt(workspace_id, receipt_id)

    def receipt(self, workspace_id: str, receipt_id: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM receipts WHERE workspace_id=? AND id=?", (workspace_id, receipt_id)).fetchone()
        return {**dict(row), "payload": json.loads(row["payload"])} if row else None

    def receipts(self, workspace_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT * FROM receipts WHERE workspace_id=? ORDER BY created_at DESC LIMIT 50", (workspace_id,))
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def update_receipt(self, workspace_id: str, receipt_id: str, status: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        current = self.receipt(workspace_id, receipt_id)
        if not current:
            return None
        payload = {**current["payload"], **patch}
        self.db.execute("UPDATE receipts SET status=?,payload=?,updated_at=? WHERE workspace_id=? AND id=?", (status, json.dumps(payload), now_ms(), workspace_id, receipt_id))
        self.db.commit()
        return self.receipt(workspace_id, receipt_id)

    def create_proposal(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        proposal_id = str(uuid.uuid4())
        proposal_hash = digest(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        created = now_ms()
        self.db.execute("INSERT INTO proposals VALUES (?,?,?,?,?,?,NULL)", (proposal_id, workspace_id, proposal_hash, json.dumps(payload), "pending", created))
        self.db.commit()
        return {"id": proposal_id, "workspace_id": workspace_id, "proposal_hash": proposal_hash, "payload": payload, "status": "pending", "created_at": created}

    def proposal(self, workspace_id: str, proposal_id: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM proposals WHERE workspace_id=? AND id=?", (workspace_id, proposal_id)).fetchone()
        return {**dict(row), "payload": json.loads(row["payload"])} if row else None

    def decide_proposal(self, workspace_id: str, proposal_id: str, proposal_hash: str, decision: str) -> dict[str, Any] | None:
        proposal = self.proposal(workspace_id, proposal_id)
        if not proposal or proposal["status"] != "pending" or not secrets.compare_digest(proposal["proposal_hash"], proposal_hash):
            return None
        status = "approved" if decision == "approved" else "rejected"
        self.db.execute("UPDATE proposals SET status=?,decided_at=? WHERE id=?", (status, now_ms(), proposal_id))
        self.db.commit()
        return self.proposal(workspace_id, proposal_id)

