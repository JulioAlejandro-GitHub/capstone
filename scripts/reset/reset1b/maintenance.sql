-- Template instantiated only by rehearsal.py after validating the disposable cluster.
-- Values @@...@@ are quoted/validated by Python, never accepted from an app session.
CREATE TEMP TABLE reset1b_context (
 operation uuid PRIMARY KEY, xid xid8 NOT NULL, backend_pid integer NOT NULL
) ON COMMIT DROP;
INSERT INTO reset1b_context VALUES ('@@OPERATION@@',pg_current_xact_id(),pg_backend_pid());
CREATE TEMP TABLE reset1b_allowed (
 relation oid NOT NULL, row_hash bytea NOT NULL, row_key jsonb NOT NULL,
 PRIMARY KEY (relation,row_hash)
) ON COMMIT DROP;
CREATE FUNCTION @@SCHEMA@@._reset1b_allowed(rel oid, value jsonb)
RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $gate$
 SELECT current_database()='reset1b_rehearsal'
 AND session_user='@@ROLE@@' AND current_setting('role')='none'
 AND (SELECT system_identifier::text FROM pg_control_system())='@@CLUSTER@@'
 AND current_setting('reset1b.operation',true)='@@OPERATION@@'
 AND EXISTS (SELECT 1 FROM pg_temp.reset1b_context
   WHERE operation='@@OPERATION@@'::uuid AND xid=pg_current_xact_id()
     AND backend_pid=pg_backend_pid())
 AND EXISTS (SELECT 1 FROM pg_temp.reset1b_allowed
   WHERE relation=rel AND row_hash=sha256(convert_to(value::text,'UTF8')));
$gate$;
REVOKE ALL ON FUNCTION @@SCHEMA@@._reset1b_allowed(oid,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION @@SCHEMA@@._reset1b_allowed(oid,jsonb) TO julio;
CREATE FUNCTION @@SCHEMA@@._reset1b_delete_scope()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $scope$
BEGIN
 IF TG_TABLE_SCHEMA <> '@@SCHEMA_NAME@@' OR NOT @@SCHEMA@@._reset1b_allowed(TG_RELID,to_jsonb(OLD))
 THEN RAISE EXCEPTION 'RESET1B_DELETE_NOT_IN_APPROVED_MANIFEST'; END IF;
 RETURN OLD;
END $scope$;
REVOKE ALL ON FUNCTION @@SCHEMA@@._reset1b_delete_scope() FROM PUBLIC;
