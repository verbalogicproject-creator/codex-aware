# Continuity Protocol 0.1

## Event vocabulary

- `workspace.seeded`
- `actor.attached`
- `context.selection_changed`
- `action.requested`
- `proposal.created`
- `proposal.approved`
- `proposal.rejected`
- `directive.issued`
- `effect.observed`
- `receipt.finalized`
- `repository.refreshed`

## Action states

- `awaiting_approval`: application requires a browser-human decision.
- `awaiting_consumer`: directive exists but no live surface has observed it.
- `executed`: bounded effect acknowledgement exists.
- `denied`: declaration, actor, scope, policy, or arguments failed.
- `degraded`: delivery or observation failed after a valid request.

## Invariants

1. Stable semantic IDs are not DOM selectors.
2. Context is not authorization.
3. A proposal is not an approval.
4. Dispatch is not effect.
5. Model output is not evidence of execution.
6. Every final receipt identifies its grounding, gate, and observation.
7. Repeated delivery is idempotent.
8. Stored payloads are bounded and secret-free.

