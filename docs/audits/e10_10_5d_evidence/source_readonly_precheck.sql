BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SELECT json_build_object('database', current_database(), 'database_oid', (SELECT oid FROM pg_database WHERE datname=current_database()), 'system_identifier', (SELECT system_identifier::text FROM pg_control_system()), 'server_version',current_setting('server_version'), 'server_version_num',current_setting('server_version_num'), 'read_only',current_setting('transaction_read_only'), 'recovery',pg_is_in_recovery(), 'revision',(SELECT json_agg(version_num) FROM alembic_version));
SELECT json_build_object('gate_count',count(*),'singleton_valid',bool_and(singleton),'owner_present',bool_or(owner IS NOT NULL),'db_pid_present',bool_or(db_pid IS NOT NULL),'blocked_reason_present',bool_or(blocked_reason IS NOT NULL),'process_evidence_empty',bool_and(process_evidence = '{}'::jsonb)) FROM experiment_execution_gate;
SELECT json_build_object('table',t,'state',s,'count',n) FROM (
SELECT 'train_execution_sessions' t,state::text s,count(*) n FROM train_execution_sessions GROUP BY state
UNION ALL SELECT 'assessment_attempts',state::text,count(*) FROM assessment_attempts GROUP BY state
UNION ALL SELECT 'campaign_attempts',state::text,count(*) FROM campaign_attempts GROUP BY state
UNION ALL SELECT 'campaign_members',state::text,count(*) FROM campaign_members GROUP BY state
UNION ALL SELECT 'experimental_campaigns',state::text,count(*) FROM experimental_campaigns GROUP BY state
UNION ALL SELECT 'local_execution_jobs',state::text,count(*) FROM local_execution_jobs GROUP BY state
UNION ALL SELECT 'runs',status::text,count(*) FROM runs GROUP BY status
) s ORDER BY t,s;
ROLLBACK;
