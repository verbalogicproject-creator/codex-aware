# ChatGPT Mobile Integration

Codex Aware exposes two complementary MCP surfaces:

- The local Codex plugin uses one-time pairing and a scoped token. Local Codex may edit the checked-out adapter under its normal filesystem approvals.
- The remote ChatGPT App uses the public Streamable HTTP MCP endpoint. It reads the same live demo workspace and may request safe visual actions or human-gated proposals.

This makes Android ChatGPT another semantic actor, not a privileged remote shell.

## Run

```bash
PYTHONPATH=services/api uvicorn codex_aware.app:app --port 8001
```

The MCP URL is:

```text
https://YOUR-MCP-HOST/chatgpt/mcp
```

Add that URL as a custom app in ChatGPT developer mode, then test from both ChatGPT web and Android.

Suggested prompts:

- “What is selected in Codex Aware?”
- “Compare the authority around these two commands.”
- “Reveal the blast radius.”
- “Propose the missing safety boundary.”
- “Show me what was actually observed.”

The proposal tool never edits source. Approval appears in the connected browser, and local Codex remains responsible for any approved adapter patch and test.

OpenAI’s current Apps SDK guidance recommends the MCP Apps bridge as the core integration surface. The product should add an inline widget only if it improves the mobile experience; the external graph remains authoritative.
