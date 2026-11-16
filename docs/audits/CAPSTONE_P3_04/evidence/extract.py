from pathlib import Path
import subprocess,json,datetime
B=Path(__file__).resolve().parents[1]
PS=['docker','exec','-i','capstone_db','sh','-lc','PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=60000" psql -X -qAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
def query(name,sql):
 s='BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;\n'+sql+'\nCOMMIT;\n'
 (B/'sql'/f'{name}.sql').write_text(s)
 r=subprocess.run(PS,input=s,text=True,capture_output=True,check=True)
 v=json.loads(r.stdout) if r.stdout.strip() else None;(B/'evidence'/f'{name}.json').write_text(json.dumps(v,indent=2));return v
cols=query('schema',"SELECT json_agg(t) FROM (SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position)t;")
query('constraints',"SELECT json_agg(t) FROM (SELECT c.conrelid::regclass::text AS table_name,c.conname,pg_get_constraintdef(c.oid) definition FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' ORDER BY 1,2)t;")
u='00b8d407-c672-4b68-9814-53c092d034ba'
query('principal_identity',f"SELECT json_build_object('database',current_database(),'user',current_user,'captured_at',now(),'read_only',current_setting('transaction_read_only'),'runs',(SELECT json_agg(r) FROM runs r WHERE id='{u}'),'identities',(SELECT json_agg(i) FROM assessment_identities i WHERE id='{u}' OR training_run_id='{u}'),'attempts',(SELECT json_agg(a) FROM assessment_attempts a WHERE id='{u}'));")
query('runs',"SELECT json_agg(t) FROM (SELECT r.*,to_jsonb(m) model FROM runs r LEFT JOIN models m ON m.id=r.model_id ORDER BY r.created_at)t;")
query('assessments',"SELECT json_agg(t) FROM (SELECT i.id identity_id,i.training_run_id,i.kind,i.identity-'samples' identity,jsonb_array_length(i.identity->'samples') sample_count,a.* FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id=i.id ORDER BY i.training_run_id,a.started_at)t;")
query('artifacts',"SELECT json_agg(t) FROM (SELECT * FROM artifacts ORDER BY run_id,id)t;")
query('assessment_artifacts',"SELECT json_agg(t) FROM (SELECT * FROM assessment_artifacts ORDER BY attempt_id,role)t;")
for table in ['run_configurations','run_clinical_metrics','evaluations','run_checkpoint_policy','run_threshold_calibration','model_versions','experimental_campaigns','dataset_versions','dataset_materializations']:
 query(table,f'SELECT json_agg(t) FROM (SELECT * FROM {table})t;')
query('record_counts',"SELECT json_agg(t) FROM (SELECT run_id,kind,count(*) FROM train_execution_records GROUP BY run_id,kind ORDER BY run_id,kind)t;")
query('epochs',"SELECT json_agg(t) FROM (SELECT * FROM train_execution_records WHERE kind IN ('epoch','selection','architecture') ORDER BY run_id,event_sequence)t;")
query('table_counts',"SELECT json_build_object('training_history',(SELECT count(*) FROM training_history),'predictions',(SELECT count(*) FROM predictions),'xai_evidence',(SELECT count(*) FROM xai_evidence),'assessment_results',(SELECT count(*) FROM assessment_results));")
print('Extraction complete',datetime.datetime.now(datetime.timezone.utc).isoformat())
