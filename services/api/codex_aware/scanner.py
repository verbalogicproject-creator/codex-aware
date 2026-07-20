from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

EXCLUDED_PARTS = {"node_modules", ".git", "dist", "build", ".next", "__pycache__", ".venv"}
SECRET_NAMES = {".env", ".env.local", ".env.production", "credentials.json", "service-account.json"}
COMMAND_PATTERN = re.compile(r'name:\s*["\']([a-zA-Z][a-zA-Z0-9_-]{1,80})["\']')


def allowed(path: Path) -> bool:
    return not any(part in EXCLUDED_PARTS for part in path.parts) and path.name not in SECRET_NAMES and not path.name.startswith(".env")


def scan_project(root: Path, logical_name: str) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []
    hasher = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not allowed(path):
            continue
        relative = path.relative_to(root).as_posix()
        if path.suffix not in {".ts", ".tsx", ".py", ".json", ".yaml", ".yml"}:
            continue
        raw = path.read_bytes()
        file_hash = hashlib.sha256(raw).hexdigest()
        hasher.update(relative.encode())
        hasher.update(file_hash.encode())
        files.append({"uri": f"repo://{logical_name}/{relative}", "kind": path.suffix.lstrip("."), "sha256": file_hash, "bytes": len(raw)})
        if path.name == "commands.ts":
            text = raw.decode("utf-8", errors="replace")
            for name in COMMAND_PATTERN.findall(text):
                commands.append({"id": f"command:{logical_name}:{name}", "name": name, "uri": f"repo://{logical_name}/{relative}#{name}"})
    return {"schema_version": 1, "project": logical_name, "snapshot_hash": hasher.hexdigest(), "files": files, "commands": commands}


def load_policy(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text()) or {}
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a sanitized Codex Aware project snapshot")
    parser.add_argument("root", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--policy", type=Path)
    args = parser.parse_args()
    snapshot = scan_project(args.root.resolve(), args.name)
    if args.policy:
        snapshot["policy"] = load_policy(args.policy)
    print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    main()

