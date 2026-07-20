#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def validate(path: Path, require_protected: bool = False) -> dict[str, str]:
    payload = yaml.safe_load(path.read_text())
    policy = payload.get("policy", {})
    safety_class = policy.get("safety_class")
    confirmation = policy.get("confirmation_policy")
    allowed = {"safe", "protected", "browser_only", "forbidden", "unclassified"}
    if safety_class not in allowed:
        raise ValueError(f"unknown safety_class: {safety_class}")
    if safety_class == "protected" and confirmation not in {"human_approval", "runtime_guard"}:
        raise ValueError("protected commands require human_approval or runtime_guard")
    if require_protected and (safety_class, confirmation) != ("protected", "human_approval"):
        raise ValueError("expected protected / human_approval after the approved patch")
    return {"safety_class": safety_class, "confirmation_policy": confirmation}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--require-protected", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"status": "passed", **validate(args.path, args.require_protected)}))

