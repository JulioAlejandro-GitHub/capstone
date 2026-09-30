# DBV2.4 — User certification (non-sensitive)

- roles: source total 5; authorized subset per DBV2.3 plan (roles referenced by user_roles) 1; destination 1
- users: source 1 / destination 1
- user_roles: source 1 / destination 1

- preserved user = YES
- user ID preserved = YES
- identity preserved = YES
- status preserved = YES (active)
- password_hash_match = TRUE
- roles preserved = YES

Password hash compared by in-memory/SQL equality only; it is excluded from transfer hashes and never written to any output. No passwords, tokens or secrets recorded. Login/JWT/HTTP are out of scope (SW-V2).
