#!/bin/sh
set -eu

exec /data/data/com.termux/files/home/.npm-global/bin/codex mcp add codex-aware \
  --env AWARE_API_URL=https://codex-aware-jchnbap7ea-zf.a.run.app \
  -- python3 /data/data/com.termux/files/home/openai/codex-aware/plugins/codex-aware/scripts/mcp_server.py
