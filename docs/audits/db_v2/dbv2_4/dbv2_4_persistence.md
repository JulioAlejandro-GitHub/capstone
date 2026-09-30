# DBV2.4 — Persistence

- `docker stop` / `docker start` of the SAME container `capstone_db_v2`; volume `capstone_v2_isolated_persistent_data` NOT removed.
- After restart: database `capstone_v2_isolated_persistent` (OID 16386), same system_identifier, head `pg_v2_baseline`, manifest `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb`.
- Dataset, roles, users, user_roles and scientific counts re-verified against SOURCE: ALREADY_TRANSFERRED_EXACTLY; before/after results identical.
- Result: PASS. VERIFY_ALREADY_TRANSFERRED (standalone re-run, read-only, no INSERT): ALREADY_TRANSFERRED_EXACTLY.
- BD-v2 left running and persistent. No DROP DATABASE, no volume deletion, no `down -v`.
