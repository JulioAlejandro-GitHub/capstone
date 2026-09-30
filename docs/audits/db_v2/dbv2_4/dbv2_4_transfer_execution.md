# DBV2.4 — Transfer execution

- Executor: `scripts/db/dbv24_transfer.py transfer` as `capstone_v2_migrator` (NOSUPERUSER, cannot disable triggers or set session_replication_role).
- Executed the 39 approved statements of `dbv2_4_transfer_plan.sql` verbatim in one destination transaction (BEGIN … COMMIT).
- Transport boundary: for each of the 16 tables, the approved SELECT ran on SOURCE as `COPY (SELECT …) TO STDOUT` (text format) and streamed into `pg_temp.dbv24_src_<table>` via `COPY FROM STDIN`. Identical session formatting on both sides (UTC, ISO DateStyle, extra_float_digits=1). No files, no Python value conversion.
- Insert order (plan/DBV2.3, parents before children): dataset_versions → datasets → roles → users → clinical_identities → dataset_materializations → dataset_split_statistics → dataset_split_validation_checks → dataset_splits → dataset_version_sources → user_roles → dataset_materialization_activations → dataset_source_records → dataset_split_images → dataset_split_assignments → identity_evidence.
- All INSERTs use explicit columns; no `SELECT *`, no `ON CONFLICT`, no TRUNCATE/DELETE, no trigger disabling.
- FROZEN technical handling = APPLIED AS APPROVED: `dataset_versions` inserted with status FROZEN→VALIDATED (so FROZEN child-protection triggers accept dependent rows), then restored to FROZEN before COMMIT by the plan UPDATE; lifecycle trigger keeps the stored `frozen_at` (COALESCE) and plan preflight forbids NULL `frozen_at`. Final row is byte-identical to SOURCE → semantic transformations = 0.
- Before COMMIT: plan `$verify$` block (bidirectional EXCEPT ALL vs staging, split counts, 201 patients, 55,116 / 2 roots) + script validations (per-table transfer hashes and exact row equality vs SOURCE, scientific snapshot, 992 FK/CHECK/UNIQUE/PK checks, absence) → all PASS → COMMIT.
- Rows transferred: dataset 138,009; roles 1; users 1; user_roles 1.

## Isolated rollback test (disposable cluster, port 56441)

- Fresh disposable PostgreSQL 17.9 cluster built with the same `pg_v2_baseline` (container `capstone_v2_isolated_fafc32d0d3a3`).
- Partial insert proven: dataset_versions = 1, datasets = 2; deterministic failure `SELECT 1/0` (SQLSTATE 22012) → ROLLBACK → all 16 authorized tables = 0 and structural manifest unchanged.
- Subsequent complete transfer on the same disposable cluster: validated and COMMITTED → PASS. Disposable container stopped afterwards (not the persistent one).
- Result: PASS.

## Superseded attempt (transparency)

- `superseded_attempt_1/`: first disposable run. Failure/rollback half PASSED; recovery half failed validation-before-COMMIT with SQLSTATE 42601 caused by a bug in the script-generated UNIQUE check (`GROUP BY (true)` for the partial unique index on a constant in `assessment_attempts`). ROLLBACK executed; disposable cluster only; persistent DB untouched. Fixed (aliased GROUP BY keys) and the rollback test re-run from a fresh disposable cluster.
- Preflight fixes before any write (checker-only, plan unchanged): column regex now accepts digits (`*_sha256` columns); SOURCE catalog comparison uses the DBV2.3 json_agg representation and default search_path; stored-fingerprint locator matches `fingerprint|digest|sha256` keys.

Event log: `execution_events.jsonl`.
