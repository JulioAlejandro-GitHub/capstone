BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '30s';
SET LOCAL lock_timeout = '2s';
SELECT format('SELECT json_build_object(''table'', %L, ''count'', count(*)) FROM %I.%I;',tablename,schemaname,tablename) FROM pg_tables WHERE schemaname='public' ORDER BY tablename
\gexec
SELECT json_build_object('migration_id', migration_id, 'checksum',checksum) FROM schema_migrations ORDER BY migration_id;
SELECT json_build_object('other_client_sessions',count(*),'active_other_clients',count(*) FILTER (WHERE state='active')) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND backend_type='client backend';
ROLLBACK;
