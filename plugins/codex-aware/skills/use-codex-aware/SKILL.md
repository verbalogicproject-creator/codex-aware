---
name: use-codex-aware
description: Use when a browser is connected to Codex Aware or the user refers to a selected graph node, this, these, blast radius, policy drift, or a continuity receipt.
---

# Use Codex Aware

1. Call `aware_context` before searching the repository when the user refers to a live selection.
2. Treat logical URIs and stable IDs as grounding, not authorization.
3. Use `aware_graph` only for the bounded neighborhood needed by the task.
4. Safe visual actions may use `aware_act`.
5. A protected proposal must remain pending until the browser-human gate is approved.
6. Never describe a dispatched directive as completed until its receipt contains an observed effect.
7. After an approved adapter edit, run the focused policy test before `aware_refresh`.
8. Keep secrets, raw source bodies, absolute paths, and unrestricted tool output out of snapshots.
