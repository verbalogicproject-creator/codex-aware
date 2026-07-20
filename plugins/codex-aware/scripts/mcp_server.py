#!/usr/bin/env python3
"""Dependency-free stdio MCP bridge for the Codex Aware HTTP API."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API = os.getenv("AWARE_API_URL", "http://localhost:8000").rstrip("/")
STATE = Path(os.getenv("AWARE_STATE_PATH", str(Path.home() / ".codex-aware" / "connection.json")))

TOOLS = [
    {"name": "aware_attach", "description": "Attach to a browser workspace with its one-time code.", "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}, "actor_name": {"type": "string"}}, "required": ["code"]}, "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}},
    {"name": "aware_context", "description": "Resolve the current browser selection into stable semantic identities.", "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "aware_graph", "description": "Read the bounded application semantic graph.", "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "aware_act", "description": "Request a declared semantic action through application-owned gates.", "inputSchema": {"type": "object", "properties": {"command": {"type": "string"}, "arguments": {"type": "object"}}, "required": ["command"]}, "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}},
    {"name": "aware_receipt", "description": "Inspect pending or verified continuity receipts.", "inputSchema": {"type": "object", "properties": {"receipt_id": {"type": "string"}}}, "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "aware_refresh", "description": "Publish a sanitized policy snapshot after exact approval and a passing test.", "inputSchema": {"type": "object", "properties": {"snapshot_hash": {"type": "string"}, "policies": {"type": "object"}, "test_result": {"type": "object"}}, "required": ["snapshot_hash", "policies"]}, "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
]


def load_state() -> dict[str, str]:
    if not STATE.exists():
        return {}
    try:
        return json.loads(STATE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(payload: dict[str, str]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(payload))
    try:
        STATE.chmod(0o600)
    except OSError:
        pass


def http(path: str, method: str = "GET", payload: dict[str, Any] | None = None, auth: bool = True) -> Any:
    state = load_state()
    headers = {"content-type": "application/json"}
    if auth and state.get("token"):
        headers["authorization"] = f"Bearer {state['token']}"
    request = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"Codex Aware returned {error.code}: {detail}") from error


def call(name: str, args: dict[str, Any]) -> Any:
    state = load_state()
    if name == "aware_attach":
        result = http("/api/pair/attach", "POST", {"code": args["code"], "actor_name": args.get("actor_name", "Codex")}, auth=False)
        save_state({"token": result["token"], "workspace_id": result["workspace_id"], "api": API})
        return {"attached": True, "workspace_id": result["workspace_id"], "scopes": result["scopes"]}
    workspace = state.get("workspace_id")
    if not workspace:
        raise RuntimeError("Not attached. Open Codex Aware, choose Pair Codex, then call aware_attach.")
    if name == "aware_context":
        return http(f"/api/workspaces/{workspace}/context")
    if name == "aware_graph":
        return http(f"/api/workspaces/{workspace}/graph")
    if name == "aware_act":
        return http(f"/api/workspaces/{workspace}/actions", "POST", {"command": args["command"], "arguments": args.get("arguments", {})})
    if name == "aware_receipt":
        receipts = http(f"/api/workspaces/{workspace}/receipts")
        receipt_id = args.get("receipt_id")
        return next((item for item in receipts if item["id"] == receipt_id), None) if receipt_id else receipts
    if name == "aware_refresh":
        return http(f"/api/workspaces/{workspace}/refresh", "POST", args)
    raise RuntimeError(f"Unknown tool: {name}")


def respond(request_id: Any, result: Any = None, error: str | None = None) -> None:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error:
        payload["error"] = {"code": -32000, "message": error}
    else:
        payload["result"] = result
    print(json.dumps(payload, separators=(",", ":")), flush=True)


request: dict[str, Any] = {}
for line in sys.stdin:
    try:
        request = json.loads(line)
        method = request.get("method")
        if method == "initialize":
            respond(request.get("id"), {"protocolVersion": "2025-03-26", "serverInfo": {"name": "codex-aware", "version": "0.1.0"}, "capabilities": {"tools": {}}})
        elif method == "tools/list":
            respond(request.get("id"), {"tools": TOOLS})
        elif method == "tools/call":
            value = call(request["params"]["name"], request["params"].get("arguments", {}))
            respond(request.get("id"), {"content": [{"type": "text", "text": json.dumps(value, separators=(",", ":"))}], "structuredContent": value})
        elif method in {"notifications/initialized", "notifications/cancelled"}:
            continue
        elif request.get("id") is not None:
            respond(request.get("id"), error=f"Unsupported method: {method}")
    except Exception as error:
        respond(request.get("id"), error=str(error))
