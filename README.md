# Codex Aware

> **Point at your running software. Codex already knows what you mean.**

Codex Aware gives external intelligence a durable semantic connection to a running application. A person can select an application entity and refer to “this” or “these”; an attached actor receives stable identities, bounded relationships, declared actions, current authority, and causal history.

The core loop is:

**Observe → Ground → Resolve → Propose → Gate → Apply → Verify → Receipt**

## Try the live product

- Graph workspace: https://codex-aware-web-jchnbap7ea-zf.a.run.app
- ChatGPT App MCP: `https://codex-aware-jchnbap7ea-zf.a.run.app/chatgpt/mcp`
- Service health: https://codex-aware-jchnbap7ea-zf.a.run.app/health

The graph and remote MCP surface share one PostgreSQL-backed continuity log.

## What changes

An IDE can tell Codex which text is selected. A browser controller can tell it which element was clicked. Codex Aware lets the application say that the selected thing is `delete_task`, where it is declared, what handler and shared state it reaches, whether it is trusted, what the user was doing when it became relevant, and which actions the application will accept.

Context does not grant authority. A dispatched action is not a successful effect. Those distinctions are enforced by application-owned gates and observed-effect receipts.

## Product walkthrough

The included workspace contains four connected applications. Its active incident contrasts:

- Team Todo’s destructive `delete_task`, imported without a neutral safety policy.
- Neon Battleship’s `fire_at`, protected by explicit phase and turn guards.

Select both nodes and ask attached Codex: **“What is happening here?”**

Codex can resolve the exact cross-project context, request a safe blast-radius reveal, propose a bounded policy classification, stop for browser-human approval, patch the adapter, run its conformance test, refresh the sanitized graph, and inspect the resulting receipt.

No task is deleted and no shot is fired.

## Run locally

Requirements: Python 3.12+, Node 22+, npm.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cd apps/web && npm install && cd ../..
make api
```

In a second terminal:

```bash
make web
```

Open `http://localhost:3000`, choose **Pair Codex**, then install or point Codex at `plugins/codex-aware`. The plugin’s local MCP bridge defaults to `http://localhost:8000`; set `AWARE_API_URL` for a hosted service.

## ChatGPT on Android

`/chatgpt/mcp` is a standards-compliant remote MCP surface for ChatGPT Apps. It exposes the same bounded context, graph, safe reveal, human-gated proposal, and receipts without granting the phone local filesystem access.

Run it locally with `make chatgpt`, or deploy it publicly and add its `/mcp` URL as a ChatGPT developer-mode app. The public mobile surface is intentionally read-mostly: durable changes still require the browser-human gate and local Codex performs any authorized source edit.

See [ChatGPT mobile integration](docs/chatgpt-mobile.md) and the
[end-to-end dogfood guide](docs/dogfood.md).

For a deterministic cross-surface verification:

```bash
python scripts/smoke_hosted.py \
  --api https://codex-aware-jchnbap7ea-zf.a.run.app \
  --reset
```

## Repository map

- `apps/web`: responsive graph-first product.
- `services/api`: continuity API, event log, policy engine, receipts, scanner, MCP surfaces.
- `plugins/codex-aware`: installable Codex plugin and dependency-free local bridge.
- `examples`: application-owned semantic adapters.
- `docs`: architecture, security, protocol, and product integration.

## Trust boundaries

- Manifests describe semantics; they never inject executable code.
- Hosted snapshots contain structural metadata and hashes, not raw source.
- Unknown commands fail closed.
- Durable proposals are bound to an exact hash and approved once.
- Receipts become successful only after an effect is observed.
- Tokens are single-use-paired, scoped, hashed, and revocable.

Apache-2.0. See `NOTICE` for research lineage and provenance.
