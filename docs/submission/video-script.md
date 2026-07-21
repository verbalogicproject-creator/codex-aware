# Codex Aware — Submission Video Screenplay

**Target runtime:** 2:45–2:55

**Hard limit:** 2:59

**Format:** 1080p landscape, readable terminal zoom, captions enabled

**Method:** Record clean picture first. Add the narration afterward.

The product remains unaware that it is in a competition. Build Week is discussed
only in the narration and submission materials.

## Preflight checklist

Complete this before recording any clip:

1. Confirm Codex shows `gpt-5.6-sol high`.
2. Run `/mcp` and confirm the separate `codex-aware` server exposes
   `aware_attach`, `aware_context`, `aware_act`, and `aware_receipt`.
3. Open the deployed application with the latest cache-busting URL.
4. Choose **Reset before pairing**. Never reset after attachment because reset
   revokes the scoped actor token.
5. Select **Veleur Fashion**.
6. Use landscape orientation or desktop mirroring. Make terminal text large
   enough to read in the final 1080p export.
7. Close notifications, unrelated tabs, credentials, and private terminal
   history.
8. Record each numbered scene as a separate clip. Waiting can be cut, but tool
   calls and returned facts must remain genuine and in their original order.

## Exact Codex prompts

Replace `123456` with the fresh one-time code shown by the browser.

### Pair and resolve

```text
Use only the codex-aware MCP server. Attach with code 123456, then read the current context and identify the highlighted node. Do not inspect the repository.
```

### Resolve changed context

```text
Using only codex-aware.aware_context, what is highlighted now?
```

### Reverse the channel

```text
Using only the codex-aware MCP server, reveal the current selection's blast radius. Wait for its observed-effect receipt; do not inspect the repository.
```

### Confirm if needed

```text
Confirm the latest receipt using codex-aware.aware_receipt.
```

## Timed screenplay

### Scene 1 — Cold open and genuine attachment (0:00–0:28)

**Picture**

- Begin directly on the deployed graph with **Veleur Fashion** selected.
- Tap **Pair Codex** and hold the one-time code for roughly two seconds.
- Cut to Codex and enter the **Pair and resolve** prompt.
- Keep `codex-aware.aware_attach` visible long enough to read `attached: true`,
  the workspace, and bounded scopes.
- Show `codex-aware.aware_context` returning **Veleur Fashion**.
- The code is safe to show only because it has now been consumed.

**Narration**

> This is Codex Aware: a semantic continuity layer for running software. The
> browser and Codex are separate processes. A single-use code attaches this
> Codex session with bounded workspace scopes. I selected Veleur Fashion, and
> Codex resolved it as a commerce storefront—without receiving a screenshot,
> DOM tree, coordinate, or copied explanation.

### Scene 2 — Context remains live (0:28–0:48)

**Picture**

- Return to the browser and close the pairing dialog.
- Select **Game engine** in Neon Battleship.
- Return to Codex and enter the **Resolve changed context** prompt.
- Show the answer identifying **Game engine**, its project, and its semantic
  relationship to the guarded `fire_at` command.

**Narration**

> Pairing happened once. I changed focus inside the running application and
> asked again. Codex now resolves the Game engine and its guarded command from
> the application’s current semantic state. The meaning changed without a new
> prompt payload or a new integration.

### Scene 3 — The channel works in reverse (0:48–1:15)

**Picture**

- Enter the **Reverse the channel** prompt.
- Show `codex-aware.aware_act` returning `awaiting_consumer`.
- Immediately return to the browser. Do not reload it.
- Capture the automatic switch to **Incident** and the three highlighted nodes:
  **Game engine**, **fire_at**, and **Phase + turn guard**.
- Return to Codex and show the same receipt become `executed` with
  `graph.reveal.observed` and target count `3`.

**Narration**

> The same channel works in reverse. Codex requests a declared semantic action,
> never a synthetic click. The application decides how to express it. Notice
> that dispatch is only awaiting consumer. Success is recorded only after the
> browser renders the three-node blast radius and acknowledges the observed
> effect against the same trace.

### Scene 4 — Context is not authority (1:15–1:43)

**Picture**

- In the browser choose **Select active incident**.
- Frame the amber Team Todo `delete_task` and green Battleship `fire_at` nodes.
- Tap **Propose safe boundary**.
- Show the hash-bound approval panel with **Reject** and **Approve once**.
- Do not complete the source-edit workflow in this scene. The visible human
  gate is the point.

**Narration**

> Awareness does not grant authority. Battleship declares phase and turn
> guards, while Team Todo’s imported delete command remains unclassified. The
> same contract can produce an exact, hash-bound safety proposal, but Codex
> cannot approve it. Durable authority remains with the human in the browser.

### Scene 5 — Take a step back into the architecture (1:43–2:14)

**Picture**

- In **Continuity receipts**, open the executed blast-radius receipt—not the
  pending classification proposal.
- Show its causal detail, then its architecture graph.
- Slowly frame: **Deictic resolver → Policy gate → Semantic directive → Effect
  observer → Verified receipt**, with the **Continuity log** supporting them.
- Use three short readable cuts to:
  - `services/api/codex_aware/app.py`
  - `services/api/codex_aware/store.py` and `postgres.py`
  - `services/api/tests/test_api.py`

**Narration**

> Take a step back. The receipt explains the system that produced it: stable
> identity enters a deictic resolver, bounded context reaches a policy gate, a
> semantic directive reaches the application controller, and an effect observer
> closes the causal record. The Python API and store persist hashed actors,
> monotonic events, proposals, and receipts in SQLite locally and PostgreSQL in
> production. Tests enforce that dispatch alone can never become success.

### Scene 6 — Codex and GPT-5.6 built the product (2:14–2:37)

**Picture**

- Show brief, readable cuts of:
  - the public GitHub repository;
  - `10 passed` backend tests and `3 passed` frontend tests;
  - the successful GitHub Actions run;
  - the two healthy Cloud Run services.
- Keep `gpt-5.6-sol high` visible in one Codex shot.

**Narration**

> I used Codex with GPT-5.6 to examine four existing applications, recognize
> their shared architectural pattern, formalize the continuity protocol,
> implement the product, generate its tests, and deploy it. During mobile
> dogfooding, Codex traced an Android event storm and a suspended-browser race,
> added regression tests, and shipped both fixes to production.

### Scene 7 — The implication (2:37–2:55)

**Picture**

- Return to the clean portfolio graph.
- End on the live product with a small editor-added lower third:

```text
Codex Aware
Point at your running software. Codex already knows what you mean.
github.com/verbalogicproject-creator/codex-aware
```

**Narration**

> Today, intelligence is usually embedded through bespoke integrations. Codex
> Aware gives running software an application-owned contract for meaning,
> authority, and verified effects. When software can describe itself through
> the same governed surface by which it can be safely controlled, intelligence
> becomes attachable. That changes the relationship between applications and
> AI.

## Recording order

Capture in this order to minimize resets and pairing mistakes:

1. Browser reset, Veleur selection, and pairing-code clip.
2. Codex `aware_attach` and first context result.
3. Browser Game engine selection.
4. Codex second context result and reveal dispatch.
5. Browser automatic blast-radius effect.
6. Codex executed receipt confirmation.
7. Browser active incident and human approval panel.
8. Executed receipt and architecture view.
9. Repository, tests, CI, and Cloud Run proof.
10. Clean closing graph.

## Edit notes

- Record screen footage without live narration. Read the narration afterward in
  a quiet room, then fit cuts to the voice track.
- Use jump cuts for model latency; never reorder tool calls or fabricate a
  result.
- Keep at least one full `aware_attach` call, one `aware_act` result showing
  `awaiting_consumer`, and the matching final `executed` receipt readable.
- Use subtle zooms and hard cuts. Avoid decorative animations or cinematic
  intros that delay the working product.
- Add captions manually or carefully correct automatic captions for `Codex`,
  `deictic`, `SQLite`, `PostgreSQL`, and `semantic`.
- Use quiet background music only if it does not compete with the narration.

## Failure-safe alternatives

- If the browser is background-suspended, return to it immediately after
  `aware_act`; recovery happens automatically without reload.
- If the terminal polls repeatedly, cut the duplicate polls while retaining the
  first `awaiting_consumer` and final `executed` results.
- If a pairing code expires, reset first, create a new code, and restart the
  scene. Never reuse a consumed code.
- If a live step fails, record that complete scene again. Do not narrate around
  a failure in the final edit.

## Safety and disclosure guardrails

- Do not expose bearer tokens, provider credentials, Cloud SQL connection
  strings, environment variables, or private repository content.
- A consumed six-digit pairing code is safe to show. Never show the resulting
  stored token.
- Do not claim that dispatch equals execution. Show the browser ACK.
- Do not describe the product as a POC.
- Say that prior projects informed the architecture; distinguish architectural
  lineage from newly implemented product code.
