# DBV2.4 — Preflight

- Destination: `capstone_v2_isolated_persistent` on `127.0.0.1:56440`, container `capstone_db_v2` (`1dc48428c6b9`), volume `capstone_v2_isolated_persistent_data`
- PostgreSQL server_version_num: `170009` (17.9); system_identifier `7691366089693499436`; database OID `16386` (DBV2.3: `16386`)
- Alembic head: `pg_v2_baseline`; roots = 1; heads = 1; down_revision = None
- Structural manifest SHA-256 (recomputed live): `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` — expected `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` → MATCH
- Root revision SHA-256: `e3aaad12e49e65cff8ad9742fcdd83af075f2e2fcfaa81733a2bec121efef279` → MATCH (file hash verified)
- Transfer plan `dbv2_3/dbv2_4_transfer_plan.sql` SHA-256 `d4ec300f26b44c1261c87a923c336309e2ac56ad939f95090d28191bdad99efb` = DBV2.3 certified hash; 39 statements parsed, identical to plan body; per-table column lists = SOURCE = DESTINATION (177 columns); full SOURCE catalog identical to DBV2.3 capture → NO PLAN DRIFT
- Destination authorized tables: all 16 = 0 rows; only non-zero tables: `alembic_version` = 1, `experiment_execution_gate` = 1 (baseline technical rows) → CLEAN FOR FIRST TRANSFER

## SOURCE READ ONLY

- Connection option `default_transaction_read_only=on` + `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY`; `transaction_read_only = on` asserted; `application_name = DBV2.4_SOURCE_READ_ONLY`.
- Only SELECT / `COPY (SELECT …) TO STDOUT` executed on SOURCE; every session ends with ROLLBACK. SOURCE WRITES = 0.

## SOURCE ≠ DESTINATION

- Source: container `capstone_db` (`2604ff988465`), port 5432, database `malaria_experiments`, volume `capstone-malaria_postgres_data`
- Destination: container `capstone_db_v2`, port 56440, database `capstone_v2_isolated_persistent`, volume `capstone_v2_isolated_persistent_data`
- Different container, port, database, volume and PostgreSQL system_identifier (cluster) → SOURCE != DESTINATION (same physical host).

## Source scientific snapshot (pre-transfer)

TRAIN 22180 · VALIDATION 2693 · TEST 2685 · TOTAL 27558 · PATIENTS 201 · overlaps {'train/test': 0, 'train/val': 0, 'val/test': 0}
