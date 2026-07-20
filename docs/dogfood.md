# Dogfood Guide

## Browser-only orientation

Open https://codex-aware-web-jchnbap7ea-zf.a.run.app.

Expected:

- Four application clusters are visible.
- Team Todo `delete_task` is amber and unclassified.
- Battleship `fire_at` is green and protected.
- Selecting a node creates a stable shared-context card.
- Selecting the active incident selects both commands.
- Reveal blast radius highlights eight related entities.
- The receipt changes from awaiting consumer to executed only after the graph responds.

## Local Codex

1. Install or load `plugins/codex-aware`.
2. In the browser choose **Pair Codex**.
3. Call `aware_attach` with the six-digit code.
4. Ask “What am I pointing at?”
5. Request `reveal_blast_radius`.
6. Inspect the receipt.

Expected:

- The code can be used once only.
- Context contains logical `repo://` URIs, never absolute paths.
- Selection identity arrives without repository search.
- A safe visual action reaches the browser.

## ChatGPT Android

1. On ChatGPT web enable **Settings → Security and login → Developer mode**.
2. Open **Settings → Plugins**, choose **+**, and create:
   - Name: `Codex Aware`
   - MCP URL: `https://codex-aware-jchnbap7ea-zf.a.run.app/chatgpt/mcp`
3. Confirm the five tools.
4. Open a new Android chat and add Codex Aware through **+ → More**.
5. Ask:
   - “What is currently selected?”
   - “Explain the capability-safety drift.”
   - “Reveal the blast radius.”
   - “Show what was requested versus what was observed.”

Expected:

- Android and web see the same live application context.
- The phone receives no local filesystem authority.
- Safe visual requests can affect the connected graph.
- Durable policy proposals still require a human in the browser.

## Human-gated patch

1. Select `delete_task`.
2. Request the safe-boundary proposal.
3. Inspect its exact target, scope, and proposal hash.
4. Reject once and verify nothing changes.
5. Request again and approve once.
6. Change only:

```yaml
policy:
  safety_class: protected
  confirmation_policy: human_approval
```

7. Run:

```bash
python scripts/check_policy.py examples/team-todo/aware.yaml --require-protected
```

8. Call `aware_refresh` with the passing result and sanitized policy hash.

Expected:

- A bad or stale proposal hash fails.
- Approval does not itself edit the file.
- Refresh fails without an approval and attached actor.
- After refresh, the graph becomes green and the receipt links approval, test, source, snapshot, and effect.

## Failure checks

- Disconnect the browser before a reveal: receipt remains awaiting consumer.
- Reuse a pairing code: attach fails.
- Request an undeclared command: receipt is denied.
- Send an approval with a changed hash: approval fails.
- Scan a fixture containing `.env.local`: no secret or source body appears in the snapshot.

