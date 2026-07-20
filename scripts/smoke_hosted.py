#!/usr/bin/env python3
"""Exercise the real cross-surface loop against a hosted Codex Aware service."""
from __future__ import annotations

import argparse
import asyncio
import json

import httpx
import websockets
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

INCIDENT = ["command:team-todo:delete_task", "command:neon-battleship:fire_at"]


async def run(api: str, reset: bool) -> None:
    workspace = "default"
    async with httpx.AsyncClient(timeout=25) as http:
        if reset:
            response = await http.post(f"{api}/api/workspaces/{workspace}/reset")
            response.raise_for_status()
        response = await http.post(
            f"{api}/api/workspaces/{workspace}/selection",
            json={"node_ids": INCIDENT},
        )
        response.raise_for_status()

        websocket_url = api.replace("https://", "wss://").replace("http://", "ws://")
        async with websockets.connect(f"{websocket_url}/ws/{workspace}") as socket:
            await socket.send("ready")
            async with streamable_http_client(f"{api}/chatgpt/mcp") as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("aware_reveal_blast_radius", {})
                    if result.isError:
                        raise RuntimeError(result.content[0].text)
                    tool_receipt = json.loads(result.content[0].text)

            directive = None
            for _ in range(20):
                await socket.send("poll")
                event = json.loads(await asyncio.wait_for(socket.recv(), timeout=5))
                if event["kind"] == "directive.issued":
                    directive = event["payload"]
                    break
            if not directive:
                raise RuntimeError("No semantic directive reached the browser consumer")

            response = await http.post(
                f"{api}/api/workspaces/{workspace}/effects",
                json={
                    "receipt_id": directive["receipt_id"],
                    "directive_id": directive["id"],
                    "observed": {
                        "target_count": len(directive["target_ids"]),
                        "target_ids": directive["target_ids"],
                    },
                },
            )
            response.raise_for_status()
            final = response.json()
            if final["status"] != "executed" or "observed_effect" not in final["payload"]:
                raise RuntimeError("Receipt was not finalized by the observation")
            print(
                json.dumps(
                    {
                        "status": "passed",
                        "mcp_receipt": tool_receipt["id"],
                        "final_receipt": final["id"],
                        "effect": final["payload"]["observed_effect"]["kind"],
                        "target_count": final["payload"]["observed_effect"]["target_count"],
                    },
                    indent=2,
                )
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--reset", action="store_true")
    arguments = parser.parse_args()
    asyncio.run(run(arguments.api.rstrip("/"), arguments.reset))

