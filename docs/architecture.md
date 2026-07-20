# Architecture

## Principle

When a running application can semantically describe itself through the same persistent surface by which it can be safely controlled, intelligence becomes attachable rather than embedded.

Codex Aware implements that surface without pretending the model is the source of truth. The application owns identity, state projection, command declarations, authority, effect observation, and continuity. Codex interprets and proposes through those constraints.

## Five kinds of awareness

1. **Repository-aware:** logical URIs and hashes connect application concepts to implementation locations.
2. **Context-aware:** durable selection events resolve “this,” “these,” and “last touched.”
3. **Runtime-aware:** typed state and effect events describe what is happening now.
4. **Authority-aware:** safety classes and human gates define what each actor may request.
5. **History-aware:** append-only causal receipts preserve what was grounded, requested, allowed, and observed.

The system is also recursively inspectable: a receipt can expand into the resolver, policy gate, directive, event log, observer, API, database, source, and tests that produced it.

## Data flow

```text
Browser selection
    │ stable IDs
    ▼
Continuity event log ──► bounded deictic context ──► Codex / ChatGPT
    ▲                                                   │
    │                                                   │ semantic request
    │                                                   ▼
Observed effect ◄── browser controller ◄── directive ◄── policy gate
    │                                                   ▲
    └──────────────────── causal receipt ───────────────┘
```

The browser ACK is load-bearing. A server-dispatched directive remains `awaiting_consumer`; only a bounded observed before/after result may finalize it.

## Adapter boundary

The supporting applications already declare domain commands. Codex Aware adds an application-neutral adapter layer:

- Source declaration: what the application calls the command.
- Semantic identity: stable cross-surface ID and logical source URI.
- Safety class: safe, protected, browser-only, forbidden, or unclassified.
- Confirmation policy: none, human approval, runtime guard, or unavailable.
- Handler key: compile-time allowlisted controller entry.

An adapter cannot provide executable source. Unknown and unclassified commands are legible but not operable.

## Storage

The reference implementation uses SQLite locally and preserves a PostgreSQL-compatible entity model:

- workspaces
- nodes and edges
- actors and hashed tokens
- one-time pairing codes
- append-only events
- proposals
- effect receipts

Events carry a workspace-local monotonic sequence plus globally unique ID, actor, schema version, trace ID, causation ID, bounded payload, and timestamp.

## Actors

- **Browser human:** establishes focus and holds durable approval authority.
- **Local Codex:** can use semantic context and, under normal workspace permissions, edit adapter source.
- **ChatGPT mobile/web:** remote semantic actor; can inspect and request safe application actions without local filesystem authority.
- **Application controller:** the only component that translates a declared directive into a visible application effect.

All actors use the same identities, gates, and receipt vocabulary.

