-- Rehearsal approval is not authorization to reset or migrate operational PostgreSQL.
\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;
DO $$ BEGIN RAISE EXCEPTION 'RESET1B_PRODUCTION_NOT_AUTHORIZED'; END $$;
ROLLBACK;
