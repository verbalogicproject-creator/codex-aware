from __future__ import annotations

import json
import secrets
import threading
import uuid
from typing import Any

from .models import GraphNode
from .seed import seed_graph
from .store import digest, now_ms


class PostgresStore:
    """PostgreSQL parity store using namespaced tables in the existing Cloud SQL DB."""

    def __init__(self, url: str):
        import psycopg
        from psycopg.rows import dict_row

        normalized = url.replace("postgresql+psycopg://", "postgresql://", 1)
        self.db = psycopg.connect(normalized, row_factory=dict_row, autocommit=False)
        self._lock = threading.RLock()
        self.migrate()
        self.ensure_workspace("default")

    def migrate(self) -> None:
        statements = [
            """CREATE TABLE IF NOT EXISTS aware_workspaces (
                id TEXT PRIMARY KEY, created_at BIGINT NOT NULL, snapshot_hash TEXT)""",
            """CREATE TABLE IF NOT EXISTS aware_nodes (
                workspace_id TEXT NOT NULL, id TEXT NOT NULL, payload JSONB NOT NULL,
                PRIMARY KEY(workspace_id,id))""",
            """CREATE TABLE IF NOT EXISTS aware_edges (
                workspace_id TEXT NOT NULL, id TEXT NOT NULL, payload JSONB NOT NULL,
                PRIMARY KEY(workspace_id,id))""",
            """CREATE TABLE IF NOT EXISTS aware_events (
                sequence BIGSERIAL PRIMARY KEY, id TEXT UNIQUE NOT NULL,
                workspace_id TEXT NOT NULL, kind TEXT NOT NULL, actor TEXT NOT NULL,
                trace_id TEXT NOT NULL, causation_id TEXT, schema_version INTEGER NOT NULL,
                payload JSONB NOT NULL, created_at BIGINT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS aware_pair_codes (
                code_hash TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
                expires_at BIGINT NOT NULL, consumed_at BIGINT)""",
            """CREATE TABLE IF NOT EXISTS aware_actor_tokens (
                token_hash TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
                actor_name TEXT NOT NULL, scopes JSONB NOT NULL,
                created_at BIGINT NOT NULL, revoked_at BIGINT)""",
            """CREATE TABLE IF NOT EXISTS aware_proposals (
                id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, proposal_hash TEXT NOT NULL,
                payload JSONB NOT NULL, status TEXT NOT NULL, created_at BIGINT NOT NULL,
                decided_at BIGINT)""",
            """CREATE TABLE IF NOT EXISTS aware_receipts (
                id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, trace_id TEXT NOT NULL,
                command TEXT NOT NULL, status TEXT NOT NULL, payload JSONB NOT NULL,
                created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL)""",
            "CREATE INDEX IF NOT EXISTS aware_events_workspace_sequence ON aware_events(workspace_id,sequence)",
            "CREATE INDEX IF NOT EXISTS aware_receipts_workspace_created ON aware_receipts(workspace_id,created_at DESC)",
        ]
        with self.db.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        self.db.commit()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, separators=(",", ":"))

    @staticmethod
    def _payload(value: Any) -> Any:
        if isinstance(value, str):
            return json.loads(value)
        return value

    def ensure_workspace(self, workspace_id: str) -> None:
        with self._lock, self.db.cursor() as cursor:
            cursor.execute("SELECT id FROM aware_workspaces WHERE id=%s", (workspace_id,))
            if cursor.fetchone():
                return
            cursor.execute("INSERT INTO aware_workspaces(id,created_at) VALUES (%s,%s)", (workspace_id, now_ms()))
            nodes, edges = seed_graph()
            cursor.executemany(
                "INSERT INTO aware_nodes VALUES (%s,%s,%s::jsonb)",
                [(workspace_id, node.id, node.model_dump_json()) for node in nodes],
            )
            cursor.executemany(
                "INSERT INTO aware_edges VALUES (%s,%s,%s::jsonb)",
                [(workspace_id, edge.id, edge.model_dump_json()) for edge in edges],
            )
            self.db.commit()
        self.event(workspace_id, "workspace.seeded", "system", {"node_count": len(nodes)})

    def reset(self, workspace_id: str) -> None:
        with self._lock, self.db.cursor() as cursor:
            for table in ("aware_nodes", "aware_edges", "aware_events", "aware_proposals", "aware_receipts", "aware_actor_tokens", "aware_pair_codes"):
                cursor.execute(f"DELETE FROM {table} WHERE workspace_id=%s", (workspace_id,))
            cursor.execute("DELETE FROM aware_workspaces WHERE id=%s", (workspace_id,))
            self.db.commit()
        self.ensure_workspace(workspace_id)

    def graph(self, workspace_id: str) -> dict[str, Any]:
        with self.db.cursor() as cursor:
            cursor.execute("SELECT payload FROM aware_nodes WHERE workspace_id=%s", (workspace_id,))
            nodes = [self._payload(row["payload"]) for row in cursor.fetchall()]
            cursor.execute("SELECT payload FROM aware_edges WHERE workspace_id=%s", (workspace_id,))
            edges = [self._payload(row["payload"]) for row in cursor.fetchall()]
            cursor.execute("SELECT snapshot_hash FROM aware_workspaces WHERE id=%s", (workspace_id,))
            snapshot = cursor.fetchone()
        return {"nodes": nodes, "edges": edges, "snapshot_hash": snapshot["snapshot_hash"] if snapshot else None}

    def node(self, workspace_id: str, node_id: str) -> dict[str, Any] | None:
        with self.db.cursor() as cursor:
            cursor.execute("SELECT payload FROM aware_nodes WHERE workspace_id=%s AND id=%s", (workspace_id, node_id))
            row = cursor.fetchone()
        return self._payload(row["payload"]) if row else None

    def put_node(self, workspace_id: str, node: GraphNode) -> None:
        with self.db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO aware_nodes VALUES (%s,%s,%s::jsonb)
                   ON CONFLICT(workspace_id,id) DO UPDATE SET payload=EXCLUDED.payload""",
                (workspace_id, node.id, node.model_dump_json()),
            )
        self.db.commit()

    def set_snapshot_hash(self, workspace_id: str, snapshot_hash: str) -> None:
        with self.db.cursor() as cursor:
            cursor.execute("UPDATE aware_workspaces SET snapshot_hash=%s WHERE id=%s", (snapshot_hash, workspace_id))
        self.db.commit()

    def event(self, workspace_id: str, kind: str, actor: str, payload: dict[str, Any], trace_id: str | None = None, causation_id: str | None = None) -> dict[str, Any]:
        event_id = str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())
        created = now_ms()
        with self.db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO aware_events(id,workspace_id,kind,actor,trace_id,causation_id,schema_version,payload,created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,1,%s::jsonb,%s) RETURNING sequence""",
                (event_id, workspace_id, kind, actor, trace_id, causation_id, self._json(payload), created),
            )
            sequence = cursor.fetchone()["sequence"]
        self.db.commit()
        return {"sequence": sequence, "id": event_id, "workspace_id": workspace_id, "kind": kind, "actor": actor, "trace_id": trace_id, "causation_id": causation_id, "schema_version": 1, "payload": payload, "created_at": created}

    def events(self, workspace_id: str, after: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        with self.db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM aware_events WHERE workspace_id=%s AND sequence>%s ORDER BY sequence LIMIT %s",
                (workspace_id, after, min(limit, 200)),
            )
            rows = cursor.fetchall()
        return [{**row, "payload": self._payload(row["payload"])} for row in rows]

    def latest_sequence(self, workspace_id: str) -> int:
        with self.db.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS sequence FROM aware_events WHERE workspace_id=%s",
                (workspace_id,),
            )
            row = cursor.fetchone()
        return int(row["sequence"])

    def latest_event(self, workspace_id: str, kind: str) -> dict[str, Any] | None:
        with self.db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM aware_events WHERE workspace_id=%s AND kind=%s ORDER BY sequence DESC LIMIT 1",
                (workspace_id, kind),
            )
            row = cursor.fetchone()
        return {**row, "payload": self._payload(row["payload"])} if row else None

    def create_pair_code(self, workspace_id: str) -> str:
        code = f"{secrets.randbelow(1_000_000):06d}"
        with self.db.cursor() as cursor:
            cursor.execute("DELETE FROM aware_pair_codes WHERE workspace_id=%s", (workspace_id,))
            cursor.execute("INSERT INTO aware_pair_codes VALUES (%s,%s,%s,NULL)", (digest(code), workspace_id, now_ms() + 300_000))
        self.db.commit()
        self.event(workspace_id, "pairing.code_created", "browser", {"expires_in_seconds": 300})
        return code

    def attach(self, code: str, actor_name: str) -> tuple[str, str] | None:
        with self.db.cursor() as cursor:
            cursor.execute("SELECT * FROM aware_pair_codes WHERE code_hash=%s FOR UPDATE", (digest(code),))
            row = cursor.fetchone()
            if not row or row["consumed_at"] or row["expires_at"] < now_ms():
                self.db.rollback()
                return None
            token = secrets.token_urlsafe(32)
            scopes = ["context:read", "graph:read", "action:request", "receipt:read", "snapshot:write"]
            cursor.execute("UPDATE aware_pair_codes SET consumed_at=%s WHERE code_hash=%s", (now_ms(), digest(code)))
            cursor.execute(
                "INSERT INTO aware_actor_tokens VALUES (%s,%s,%s,%s::jsonb,%s,NULL)",
                (digest(token), row["workspace_id"], actor_name, self._json(scopes), now_ms()),
            )
        self.db.commit()
        self.event(row["workspace_id"], "actor.attached", actor_name, {"scopes": scopes})
        return token, row["workspace_id"]

    def authenticate(self, token: str) -> dict[str, Any] | None:
        with self.db.cursor() as cursor:
            cursor.execute("SELECT * FROM aware_actor_tokens WHERE token_hash=%s AND revoked_at IS NULL", (digest(token),))
            return cursor.fetchone()

    def create_receipt(self, workspace_id: str, command: str, status: str, payload: dict[str, Any], trace_id: str | None = None) -> dict[str, Any]:
        receipt_id = str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())
        created = now_ms()
        with self.db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO aware_receipts VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s)",
                (receipt_id, workspace_id, trace_id, command, status, self._json(payload), created, created),
            )
        self.db.commit()
        return self.receipt(workspace_id, receipt_id)

    def receipt(self, workspace_id: str, receipt_id: str) -> dict[str, Any] | None:
        with self.db.cursor() as cursor:
            cursor.execute("SELECT * FROM aware_receipts WHERE workspace_id=%s AND id=%s", (workspace_id, receipt_id))
            row = cursor.fetchone()
        return {**row, "payload": self._payload(row["payload"])} if row else None

    def receipts(self, workspace_id: str) -> list[dict[str, Any]]:
        with self.db.cursor() as cursor:
            cursor.execute("SELECT * FROM aware_receipts WHERE workspace_id=%s ORDER BY created_at DESC LIMIT 50", (workspace_id,))
            rows = cursor.fetchall()
        return [{**row, "payload": self._payload(row["payload"])} for row in rows]

    def update_receipt(self, workspace_id: str, receipt_id: str, status: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        current = self.receipt(workspace_id, receipt_id)
        if not current:
            return None
        payload = {**current["payload"], **patch}
        with self.db.cursor() as cursor:
            cursor.execute(
                "UPDATE aware_receipts SET status=%s,payload=%s::jsonb,updated_at=%s WHERE workspace_id=%s AND id=%s",
                (status, self._json(payload), now_ms(), workspace_id, receipt_id),
            )
        self.db.commit()
        return self.receipt(workspace_id, receipt_id)

    def create_proposal(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        proposal_id = str(uuid.uuid4())
        proposal_hash = digest(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        created = now_ms()
        with self.db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO aware_proposals VALUES (%s,%s,%s,%s::jsonb,%s,%s,NULL)",
                (proposal_id, workspace_id, proposal_hash, self._json(payload), "pending", created),
            )
        self.db.commit()
        return {"id": proposal_id, "workspace_id": workspace_id, "proposal_hash": proposal_hash, "payload": payload, "status": "pending", "created_at": created}

    def proposal(self, workspace_id: str, proposal_id: str) -> dict[str, Any] | None:
        with self.db.cursor() as cursor:
            cursor.execute("SELECT * FROM aware_proposals WHERE workspace_id=%s AND id=%s", (workspace_id, proposal_id))
            row = cursor.fetchone()
        return {**row, "payload": self._payload(row["payload"])} if row else None

    def decide_proposal(self, workspace_id: str, proposal_id: str, proposal_hash: str, decision: str) -> dict[str, Any] | None:
        proposal = self.proposal(workspace_id, proposal_id)
        if not proposal or proposal["status"] != "pending" or not secrets.compare_digest(proposal["proposal_hash"], proposal_hash):
            return None
        status = "approved" if decision == "approved" else "rejected"
        with self.db.cursor() as cursor:
            cursor.execute("UPDATE aware_proposals SET status=%s,decided_at=%s WHERE id=%s", (status, now_ms(), proposal_id))
        self.db.commit()
        return self.proposal(workspace_id, proposal_id)
