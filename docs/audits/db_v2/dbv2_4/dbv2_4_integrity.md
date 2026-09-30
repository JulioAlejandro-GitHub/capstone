# DBV2.4 — Integrity

Explicit queries over the whole public schema after COMMIT and after restart: FK 251, CHECK 518, UNIQUE 118, PK 105.

- orphan FK = 0
- duplicate PK = 0
- UNIQUE violations = 0
- CHECK violations = 0

- SOURCE PK set == DESTINATION PK set for every authorized table (roles: the authorized subset).
- Structural manifest after COMMIT and after restart: `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` (unchanged).
- Query texts and per-constraint results: `verification_after_restart.json` → integrity.queries.
