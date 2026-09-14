import json,datetime
from sqlalchemy import text
from src.malaria_dl.data.governed_dataset import dataset_read_connection
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
with dataset_read_connection() as c:
 def rows(q,**p):return [dict(x) for x in c.execute(text(q),p).mappings()]
 out['columns']=rows("select table_name,column_name,is_nullable from information_schema.columns where table_schema='public' and (column_name='campaign_id' or table_name in ('runs','artifacts','model_versions','run_lineage')) order by table_name,ordinal_position")
 out['foreign_keys']=rows("select conrelid::regclass::text source,confrelid::regclass::text target,conname,pg_get_constraintdef(oid) definition,convalidated from pg_constraint where contype='f' and connamespace='public'::regnamespace and (conrelid in ('public.runs'::regclass,'public.campaign_attempts'::regclass,'public.campaign_members'::regclass,'public.train_execution_sessions'::regclass,'public.model_versions'::regclass,'public.run_lineage'::regclass) or confrelid='public.experimental_campaigns'::regclass)")
 out['campaign_counts']=rows("select c.id,c.state,m.state member_state,count(*) count from experimental_campaigns c join campaign_members m on m.campaign_id=c.id group by c.id,c.state,m.state")
 checks={
 'members_without_campaign':'select count(*) from campaign_members m left join experimental_campaigns c on c.id=m.campaign_id where c.id is null',
 'attempts_without_member':'select count(*) from campaign_attempts a left join campaign_members m on m.id=a.member_id where m.id is null',
 'attempts_missing_train':'select count(*) from campaign_attempts a left join runs r on r.id=a.training_run_id where a.training_run_id is not null and r.id is null',
 'session_without_run':'select count(*) from train_execution_sessions s left join runs r on r.id=s.run_id where r.id is null',
 'session_attempt_mismatch':'select count(*) from train_execution_sessions s left join campaign_attempts a on a.id=s.attempt_id where s.attempt_id is not null and (a.id is null or a.training_run_id is distinct from s.run_id)',
 'versions_without_train':'select count(*) from model_versions v left join runs r on r.id=v.training_run_id where v.training_run_id is not null and r.id is null',
 'versions_without_checkpoint':'select count(*) from model_versions v left join artifacts a on a.id=v.checkpoint_artifact_id where v.checkpoint_artifact_id is not null and a.id is null',
 'lineage_missing_parent_or_child':'select count(*) from run_lineage l left join runs p on p.id=l.parent_run_id left join runs ch on ch.id=l.child_run_id where p.id is null or ch.id is null',
 'train_multiple_campaigns':'select count(*) from (select a.training_run_id from campaign_attempts a join campaign_members m on m.id=a.member_id where a.training_run_id is not null group by a.training_run_id having count(distinct m.campaign_id)>1) q'}
 out['checks']={k:c.execute(text(q)).scalar_one() for k,q in checks.items()}
 out['unassociated_runs']=rows("select r.run_type,r.status,count(*) count from runs r where not exists(select 1 from campaign_attempts a where a.training_run_id=r.id) group by r.run_type,r.status")
 out['unassociated_fingerprint']=rows("select count(*) count,encode(sha256(convert_to(coalesce(string_agg(to_jsonb(r)::text,E'\\n' order by r.id),''),'UTF8')),'hex') sha256 from runs r where not exists(select 1 from campaign_attempts a where a.training_run_id=r.id)")
 # Verify every direct campaign FK/catalogued column, including any legacy table.
 out['campaign_columns_orphans']={}
 quote=c.dialect.identifier_preparer.quote
 for r in out['columns']:
  if r['column_name']=='campaign_id':
   table=quote(r['table_name'])
   out['campaign_columns_orphans'][r['table_name']]=c.execute(text(f'SELECT count(*) FROM public.{table} t LEFT JOIN public.experimental_campaigns c ON c.id=t.campaign_id WHERE t.campaign_id IS NOT NULL AND c.id IS NULL')).scalar_one()
print(json.dumps(out,default=str,indent=2))
