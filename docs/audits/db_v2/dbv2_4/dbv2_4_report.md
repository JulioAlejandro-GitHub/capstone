# DBV2.4 — TRANSFERENCIA MÍNIMA CERTIFICADA

- Destination `capstone_v2_isolated_persistent` · PostgreSQL 17.9 · volume `capstone_v2_isolated_persistent_data` · revision `pg_v2_baseline`
- Structural manifest before/after: `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` / `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb`
- Dataset version `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`; TRAIN 22,180 · VAL 2,693 · TEST 2,685 · TOTAL 27,558 · patients 201 · overlap 0 · dataset_split_images 55,116
- Dataset tables 13 (11 with rows, 2 PRESERVED_EMPTY); dataset rows 138,009
- Roles 1 · Users 1 · User roles 1 · preserved users 1 · password_hash_match true
- FROZEN technical handling: APPLIED AS APPROVED · semantic transformations 0
- FK/CHECK/UNIQUE: PASS · unauthorized rows 0 · audit_events 0 · XAI 0 · E10 0
- Restart persistence PASS · VERIFY_ALREADY_TRANSFERRED = ALREADY_TRANSFERRED_EXACTLY · isolated rollback test PASS
- Source writes 0 · Cutover NO · not FINAL FREEZE / not PRODUCTION READY

Transfer manifest SHA-256: `295ad3737e92d0e64333062f459a527026a4eacf6e9d36179ce31fbb89c33cf9`

Evidence: dbv2_4_preflight.md, dbv2_4_transfer_execution.md, dbv2_4_dataset_certification.md, dbv2_4_user_certification.md, dbv2_4_integrity.md, dbv2_4_absence_checks.md, dbv2_4_persistence.md, dbv2_4_transfer_manifest.json, dbv2_4_hashes.sha256.

Awaiting GATE DBV2.4.
