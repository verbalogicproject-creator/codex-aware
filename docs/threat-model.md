# Threat Model

Codex Aware assumes model output and imported metadata may be wrong or adversarial.

## Defenses

- Imported commands begin unclassified.
- Database and adapter values cannot select arbitrary executable code.
- Pairing codes expire, are single-use, and are stored only as hashes.
- Actor tokens are scoped, revocable, and stored only as hashes.
- Workspace IDs are checked on authenticated writes.
- Durable approvals are bound to canonical proposal hashes.
- Reuse, mismatch, and stale proposals fail closed.
- Hosted scanning excludes environment files, secrets, databases, dependencies, caches, and source bodies.
- Logical URIs prevent hosted disclosure of absolute local paths.
- Browser effects require explicit acknowledgement.

## Non-goals

- Bypassing application authentication.
- Inferring trust from model confidence.
- Uploading unrestricted repositories.
- Executing destructive example commands.
- Using browser clicks or DOM coordinates as semantic command execution.

