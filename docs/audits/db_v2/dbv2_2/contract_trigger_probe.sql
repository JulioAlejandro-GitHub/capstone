-- Minimal reproduction only: NOT installation or execution of the design SQL.
-- Execute only on the identified network-none, tmpfs PostgreSQL 17.9 container.
\set ON_ERROR_STOP on
BEGIN;
DO $$ BEGIN
 IF current_setting('server_version_num') <> '170009' OR inet_server_addr() IS NOT NULL
 THEN RAISE EXCEPTION 'UNSAFE_PROBE_TARGET'; END IF;
END $$;
CREATE SCHEMA dbv22_contract_probe;
CREATE TABLE dbv22_contract_probe.xai_quantitative_evaluations(id uuid);
CREATE TABLE dbv22_contract_probe.xai_evaluation_members(evaluation_id uuid);
CREATE FUNCTION dbv22_contract_probe.probe() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE eid uuid;
BEGIN
 -- Exact expression from DBV2.1 target SQL, line 2834.
 eid:=CASE WHEN TG_TABLE_NAME='xai_quantitative_evaluations' THEN NEW.id ELSE NEW.evaluation_id END;
 RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER probe AFTER INSERT ON dbv22_contract_probe.xai_quantitative_evaluations
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION dbv22_contract_probe.probe();
CREATE CONSTRAINT TRIGGER probe AFTER INSERT ON dbv22_contract_probe.xai_evaluation_members
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION dbv22_contract_probe.probe();
DO $$
DECLARE t text; msg text; state text;
BEGIN
 FOREACH t IN ARRAY ARRAY['xai_quantitative_evaluations','xai_evaluation_members'] LOOP
  BEGIN
   EXECUTE format('INSERT INTO dbv22_contract_probe.%I VALUES (gen_random_uuid())',t);
   SET CONSTRAINTS ALL IMMEDIATE;
   RAISE EXCEPTION 'PROBE_UNEXPECTED_SUCCESS: %',t;
  EXCEPTION WHEN undefined_column THEN
   GET STACKED DIAGNOSTICS msg = MESSAGE_TEXT, state = RETURNED_SQLSTATE;
   RAISE NOTICE 'CONTRACT_CONFLICT table=% SQLSTATE=% error=%',t,state,msg;
  END;
 END LOOP;
END $$;
ROLLBACK;
SELECT count(*) AS remaining_probe_schemas FROM pg_namespace WHERE nspname='dbv22_contract_probe';
