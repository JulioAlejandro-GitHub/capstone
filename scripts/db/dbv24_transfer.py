"""DBV2.4: guarded exact approved-plan execution; source SELECT-only, no secret logs."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import psycopg
from psycopg.rows import dict_row
import dbv23_destination as persistent
from dbv23_source import DATASET, USER, OFFICIAL, DOCKER, metadata
from v2_catalog_probe import QUERIES, snapshot
from alembic_v2.safety import IDENTITY_SQL, ROLES_SQL, inspect_isolation, validate_server_snapshot

E = ROOT / 'docs/audits/db_v2/dbv2_4'
OLD = ROOT / 'docs/audits/db_v2/dbv2_3'
TABLES = DATASET + USER
PLAN = OLD / 'dbv2_4_transfer_plan.sql'
EXPECTED = json.loads((OLD / 'source_table_counts.json').read_text())
EXPECTED['roles'] = 1
TARGET = json.loads((OLD / 'persistent_target.json').read_text())
CURRENT_STEP = 'initialization'
# Identical text-format settings on SOURCE and DESTINATION so COPY text is lossless.
SETTINGS = dict(timezone='UTC', datestyle='ISO, MDY', intervalstyle='postgres', extra_float_digits='1', bytea_output='hex')
FORMAT = ' '.join('-c '+k+'='+v.replace(', ',',').replace(' ','\\ ') for k,v in SETTINGS.items())


def session(c):
    for k,v in SETTINGS.items(): c.execute('SELECT set_config(%s,%s,false)',(k,v))


def save(name, obj):
    (E / name).write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str)+'\n')


def event(step, **details):
    global CURRENT_STEP
    CURRENT_STEP = step
    with (E / 'execution_events.jsonl').open('a') as f:
        f.write(json.dumps(dict(time=datetime.now(timezone.utc).isoformat(),step=step,**details))+'\n')
    print(step, flush=True)


def scalar(c, q, args=None):
    return next(iter(c.execute(q, args).fetchone().values()))


def qid(x):
    return '"'+x.replace('"','""')+'"'


@contextmanager
def source():
    m = metadata()
    old = json.loads((OLD / 'source_identity.json').read_text())
    assert m == old['environment'], 'SOURCE_IDENTITY_DRIFT'
    # Read only the credential in memory; never put it in argv, evidence or exceptions.
    proc = subprocess.run(DOCKER+['inspect',m['container_id']],capture_output=True,text=True,check=True)
    env = dict(s.split('=',1) for s in json.loads(proc.stdout)[0]['Config']['Env'])
    c = psycopg.connect(host='127.0.0.1',port=m['host_port'],dbname=m['database'],user=m['role'],password=env.get('POSTGRES_PASSWORD'),autocommit=True,row_factory=dict_row,options='-c default_transaction_read_only=on '+FORMAT,application_name='DBV2.4_SOURCE_READ_ONLY')
    del env, proc
    try:
        c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        ident = c.execute("SELECT current_database() AS database,current_setting('server_version_num') AS version,system_identifier::text AS system_identifier,current_setting('transaction_read_only') AS transaction_read_only,current_setting('default_transaction_read_only') AS default_transaction_read_only,pg_current_snapshot()::text AS snapshot FROM pg_control_system()").fetchone()
        assert ident['database']==old['server']['database'] and ident['system_identifier']==old['server']['system_identifier']
        assert ident['version']=='170009' and ident['transaction_read_only']==ident['default_transaction_read_only']=='on'
        event('SOURCE_READ_ONLY_SNAPSHOT',identity=ident,source_write_statements=0)
        yield c
    finally:
        c.execute('ROLLBACK')
        c.close()


def guard(t, connector):
    persistent.verify_baseline()
    inspect_isolation(t)
    with connector(t) as c:
        i=c.execute(IDENTITY_SQL).fetchone()
        validate_server_snapshot(t,i,c.execute(ROLES_SQL).fetchall())
        assert i['system_identifier']==t['postgres_system_identifier']
        assert scalar(c,'SELECT oid::int FROM pg_database WHERE datname=current_database()')==t['database_oid']
        assert scalar(c,'SELECT version_num FROM alembic_version')=='pg_v2_baseline'
    s=metadata()
    assert t['container_id']!=s['container_id'] and t['database']!=s['database'] and t['host_port']!=s['host_port'] and t['volume']!=s['volume']
    assert t['postgres_system_identifier']!=json.loads((OLD/'source_identity.json').read_text())['server']['system_identifier']
    if t.get('persistent'):
        assert t==TARGET and t['database']=='capstone_v2_isolated_persistent' and t['host_port']==56440
    return dict(destination=t,server=i,source=s,source_ne_destination=True,same_host_different_ports=True)


def catalog(c, label):
    obj=snapshot(c)
    digest=hashlib.sha256((json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode()).hexdigest()
    assert digest==persistent.EXPECTED_MANIFEST, 'STRUCTURAL_MANIFEST_DRIFT'
    save('catalog_'+label+'.json',obj)
    return digest


def columns(c,t):
    return c.execute("SELECT a.attname AS name,format_type(a.atttypid,a.atttypmod) AS type FROM pg_attribute a WHERE a.attrelid=%s::regclass AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum",('public.'+t,)).fetchall()


def pk(c,t):
    return [x['name'] for x in c.execute("SELECT a.attname AS name FROM pg_constraint k CROSS JOIN LATERAL unnest(k.conkey) WITH ORDINALITY z(n,i) JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=z.n WHERE k.conrelid=%s::regclass AND k.contype='p' ORDER BY z.i",('public.'+t,)).fetchall()]


def approved(c,s):
    plan=json.loads((E/'approved_plan_statements.json').read_text())
    assert hashlib.sha256(PLAN.read_bytes()).hexdigest()==plan['plan_sha256'],'TRANSFER_PLAN_DRIFT'
    queries={m.group(2):m.group(1) for m in re.finditer(r'^-- (SELECT .+ FROM public\."([a-z_]+)";)$',PLAN.read_text(),re.M)}
    assert set(queries)==set(TABLES)
    for t,q in queries.items():
        names=re.findall(r'"([a-z0-9_]+)"',q.split(' FROM ')[0])
        assert names==[v['name'] for v in columns(c,t)]==[v['name'] for v in columns(s,t)],'TRANSFER_PLAN_DRIFT'
    # Full source catalog still identical to DBV2.3 (DDL, constraints, trigger bodies included).
    old=json.loads((OLD/'source_catalog.json').read_text())
    for key,expected in old.items():
        # Same json_agg representation DBV2.3 used when capturing source_catalog.json.
        actual=scalar(s,"SELECT coalesce(json_agg(q),'[]'::json) FROM ("+QUERIES[key]+") q")
        assert actual==expected,'SOURCE_CATALOG_DRIFT:'+key
    return plan,queries


def all_counts(c):
    names=[r['relname'] for r in c.execute("SELECT relname FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' ORDER BY relname")]
    return {t:scalar(c,'SELECT count(*) FROM public.'+qid(t)) for t in names}


def absence(c):
    counts=all_counts(c)
    outside={t:n for t,n in counts.items() if t not in TABLES}
    assert outside.pop('alembic_version')==1
    assert outside.pop('experiment_execution_gate')==1
    assert not any(outside.values()),'UNAUTHORIZED_ROWS'
    return dict(unauthorized_transferred_rows=0,baseline_empty_tables=outside,technical_rows={'alembic_version':1,'experiment_execution_gate':1})


def science(c):
    v=c.execute('SELECT id::text,status,frozen_at IS NOT NULL AS frozen_at_present FROM dataset_versions').fetchall()
    assert v==[dict(id=OFFICIAL,status='FROZEN',frozen_at_present=True)]
    split={r['split_name']:r['n'] for r in c.execute('SELECT split_name,count(*) AS n FROM dataset_split_assignments WHERE dataset_version_id=%s GROUP BY split_name',(OFFICIAL,))}
    assert split==dict(train=22180,val=2693,test=2685)
    patients=scalar(c,'SELECT count(DISTINCT clinical_identity_id) FROM dataset_split_assignments WHERE dataset_version_id=%s',(OFFICIAL,))
    assert patients==201
    overlaps={}
    for a,b in [('train','val'),('train','test'),('val','test')]:
        n=scalar(c,'SELECT count(*) FROM (SELECT clinical_identity_id FROM dataset_split_assignments WHERE dataset_version_id=%s AND split_name=%s INTERSECT SELECT clinical_identity_id FROM dataset_split_assignments WHERE dataset_version_id=%s AND split_name=%s) q',(OFFICIAL,a,OFFICIAL,b))
        assert n==0
        overlaps[a+'/'+b]=n
    roots=c.execute('SELECT dataset_dir,dataset_version_id,count(*) AS records FROM dataset_split_images GROUP BY dataset_dir,dataset_version_id ORDER BY dataset_dir').fetchall()
    assert len(roots)==2 and all(r['records']==27558 and r['dataset_version_id'] is None for r in roots)
    # Only return already stored fingerprint/hash metadata, never recompute scientific evidence.
    fingerprints=[]
    def walk(x,path):
        if isinstance(x,dict):
            for k,v in x.items():
                if re.search('fingerprint|digest|sha256',path+'.'+k,re.I) and isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v):
                    fingerprints.append({'path':path+'.'+k,'stored_value':v})
                elif isinstance(v,(dict,list)):
                    walk(v,path+'.'+k)
        elif isinstance(x,list):
            for i,v in enumerate(x): walk(v,path+f'[{i}]')
    for t in ['datasets','dataset_versions','dataset_split_statistics','dataset_materializations']:
        for i,r in enumerate(c.execute('SELECT to_jsonb(t) AS v FROM '+qid(t)+' t ORDER BY '+','.join(map(qid,pk(c,t))))): walk(r['v'],t+f'[{i}]')
    assert fingerprints,'STORED_FINGERPRINT_NOT_IDENTIFIED'
    return dict(dataset_version_id=OFFICIAL,train=22180,validation=2693,test=2685,total=27558,patients=patients,overlaps=overlaps,dataset_split_images=55116,physical_roots=roots,stored_fingerprints=fingerprints,status='FROZEN')


def readrows(c,t,selected=True):
    where=' WHERE id IN (SELECT role_id FROM public.user_roles)' if t=='roles' and selected else ''
    return c.execute('SELECT '+','.join(qid(r['name']) for r in columns(c,t))+' FROM public.'+qid(t)+where+' ORDER BY '+','.join(map(qid,pk(c,t)))).fetchall()


def hashes(c,t):
    keys=pk(c,t)
    where=' WHERE id IN (SELECT role_id FROM public.user_roles)' if t=='roles' else ''
    body="(to_jsonb(t)-'password_hash')" if t=='users' else 'to_jsonb(t)'
    q='SELECT '+body+'::text AS body,jsonb_build_array('+','.join('t.'+qid(k) for k in keys)+')::text AS pk FROM public.'+qid(t)+' t'+where+' ORDER BY '+','.join('t.'+qid(k) for k in keys)
    rh,ph=hashlib.sha256(),hashlib.sha256()
    n=0
    for r in c.execute(q):
        for h,v in [(rh,r['body']),(ph,r['pk'])]:
            b=v.encode();h.update(len(b).to_bytes(8,'big'));h.update(b)
        n+=1
    return dict(count=n,transfer_hash=rh.hexdigest(),pk_hash=ph.hexdigest())


def compare(s,c):
    results=[]
    for t in TABLES:
        a,b=hashes(s,t),hashes(c,t)
        assert a==b and a['count']==EXPECTED[t],'ROW_CONTENT_CONFLICT:'+t
        # Independent exact equality including password, NULLs, timestamps and stored hashes.
        assert readrows(s,t)==readrows(c,t),'EXACT_ROW_CONFLICT:'+t
        results.append(dict(table=t,source_count=a['count'],destination_count=b['count'],transferred_count=b['count'],primary_key_match=True,transfer_hash_match=True,transfer_hash=a['transfer_hash'],pk_hash=a['pk_hash'],fk_status='PASS',semantic_transformations=0,result='PRESERVED_EMPTY' if not a['count'] else 'PASS'))
    auth=dict(roles_source_total=scalar(s,'SELECT count(*) FROM roles'),roles_source_selected=1,roles_count=1,users_count=1,user_roles_count=1,preserved_user_count=1,user_id_preserved=True,identity_preserved=True,status_preserved=True,roles_preserved=True,password_hash_match=readrows(s,'users')[0]['password_hash']==readrows(c,'users')[0]['password_hash'])
    assert auth['password_hash_match'] and scalar(c,"SELECT count(*) FROM users WHERE status='active'")==1
    return results,auth


def integrity(c):
    checks=[]
    # Explicit FK anti-joins, supporting composite keys and MATCH SIMPLE/FULL.
    fks=c.execute("SELECT k.conname,k.conrelid::regclass::text AS child,k.confrelid::regclass::text AS parent,k.confmatchtype,ARRAY(SELECT attname FROM unnest(k.conkey) WITH ORDINALITY z(n,i) JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=z.n ORDER BY i) AS ck,ARRAY(SELECT attname FROM unnest(k.confkey) WITH ORDINALITY z(n,i) JOIN pg_attribute a ON a.attrelid=k.confrelid AND a.attnum=z.n ORDER BY i) AS pk FROM pg_constraint k WHERE k.connamespace='public'::regnamespace AND k.contype='f' ORDER BY 2,1").fetchall()
    for r in fks:
        nonnull=' AND '.join('c.'+qid(k)+' IS NOT NULL' for k in r['ck'])
        eq=' AND '.join('c.'+qid(a)+'=p.'+qid(b) for a,b in zip(r['ck'],r['pk']))
        condition='('+nonnull+') AND NOT EXISTS (SELECT 1 FROM '+r['parent']+' p WHERE '+eq+')'
        if r['confmatchtype']=='f':
            condition='('+condition+') OR (('+ ' OR '.join('c.'+qid(k)+' IS NULL' for k in r['ck'])+') AND ('+' OR '.join('c.'+qid(k)+' IS NOT NULL' for k in r['ck'])+'))'
        q='SELECT count(*) FROM '+r['child']+' c WHERE '+condition
        n=scalar(c,q); assert n==0,'FK_VIOLATION'
        checks.append(dict(kind='FK',name=r['conname'],table=r['child'],violations=n,query=q))
    for r in c.execute("SELECT conname,conrelid::regclass::text AS tbl,pg_get_expr(conbin,conrelid) AS expr FROM pg_constraint WHERE connamespace='public'::regnamespace AND contype='c' ORDER BY 2,1").fetchall():
        q='SELECT count(*) FROM '+r['tbl']+' WHERE ('+r['expr']+') IS FALSE'
        n=scalar(c,q);assert n==0,'CHECK_VIOLATION'
        checks.append(dict(kind='CHECK',name=r['conname'],table=r['tbl'],violations=n,query=q))
    indexes=c.execute("SELECT i.indexrelid::regclass::text AS name,i.indrelid::regclass::text AS tbl,i.indisprimary,i.indnullsnotdistinct,pg_get_expr(i.indpred,i.indrelid) AS pred,ARRAY(SELECT pg_get_indexdef(i.indexrelid,n,true) FROM generate_series(1,i.indnkeyatts) n) AS exprs FROM pg_index i JOIN pg_class t ON t.oid=i.indrelid WHERE t.relnamespace='public'::regnamespace AND i.indisunique ORDER BY 2,1").fetchall()
    for r in indexes:
        exprs=r['exprs']; filters=[r['pred']] if r['pred'] else []
        if not r['indnullsnotdistinct']: filters += ['('+x+') IS NOT NULL' for x in exprs]
        # Alias keys so constant-expression indexes (e.g. partial UNIQUE on (true)) group correctly.
        keys=['k'+str(i) for i in range(len(exprs))]
        q='SELECT count(*) FROM (SELECT 1 FROM (SELECT '+','.join('('+x+') AS '+k for x,k in zip(exprs,keys))+' FROM '+r['tbl']+(' WHERE '+' AND '.join('('+f+')' for f in filters) if filters else '')+') s GROUP BY '+','.join(keys)+' HAVING count(*)>1) q'
        n=scalar(c,q);assert n==0,'UNIQUE_VIOLATION'
        checks.append(dict(kind='PK' if r['indisprimary'] else 'UNIQUE',name=r['name'],table=r['tbl'],violations=n,query=q))
    return dict(orphan_fk=0,duplicate_pk=0,unique_violations=0,check_violations=0,queries=checks)


def preflight(s,c,t,label,clean):
    plan,queries=approved(c,s)
    structure=catalog(c,label)
    counts=all_counts(c)
    if clean: assert all(counts[x]==0 for x in TABLES),'DESTINATION NOT CLEAN FOR FIRST TRANSFER'
    absent=absence(c)
    scientific=science(s)
    actual={x:hashes(s,x)['count'] for x in TABLES}
    assert actual==EXPECTED,'SOURCE_COUNT_DRIFT'
    save('preflight_'+label+'.json',dict(structural_manifest_sha256=structure,root_revision_sha256=persistent.EXPECTED_REVISION,plan_sha256=plan['plan_sha256'],destination=t,counts=counts,source_selected_counts=actual,scientific_snapshot=scientific,absence=absent,source_writes=0,columns_compared=177))
    return plan,queries


def transfer(t,connector,label,inject=False):
    event('PREFLIGHT_'+label)
    identity=guard(t,connector); save('identity_'+label+'.json',identity)
    with source() as s,connector(t) as c:
        session(c)
        plan,queries=preflight(s,c,t,label,True)
        try:
            for index,stmt in enumerate(plan['statements']):
                kind=stmt['kind']
                if kind=='LockStmt':
                    for table,query in queries.items():
                        names=[r['name'] for r in columns(c,table)]
                        # Source runs only the approved SELECT (COPY TO is read-only); PostgreSQL text
                        # format streams byte-exact values into staging, never through Python types or files.
                        with s.cursor().copy('COPY ('+query.rstrip(';')+') TO STDOUT') as out, c.cursor().copy('COPY pg_temp.'+qid('dbv24_src_'+table)+' ('+','.join(map(qid,names))+') FROM STDIN') as inp:
                            for block in out: inp.write(block)
                    event('STAGING_LOADED_'+label)
                if index==len(plan['statements'])-1:
                    tables,auth=compare(s,c)
                    scientific=science(c); assert scientific==science(s)
                    integ=integrity(c); absent=absence(c)
                    save('validation_before_commit_'+label+'.json',dict(tables=tables,authentication=auth,scientific_snapshot=scientific,integrity=integ,absence=absent))
                    event('VALIDATED_BEFORE_COMMIT_'+label)
                c.execute(stmt['sql'])
                if kind=='InsertStmt':
                    table=re.search(r'INSERT INTO public\."([a-z_]+)"',stmt['sql']).group(1)
                    event('INSERT_'+label,table=table)
                    if inject and table=='datasets':
                        partial={x:scalar(c,'SELECT count(*) FROM '+qid(x)) for x in TABLES}
                        assert partial['datasets']==2 and partial['dataset_versions']==1
                        save('rollback_partial.json',partial)
                        c.execute('SELECT 1/0')
            event('COMMITTED_'+label)
        except Exception as error:
            c.execute('ROLLBACK')
            event('ROLLED_BACK_'+label,error_type=type(error).__name__,sqlstate=getattr(error,'sqlstate',None))
            if inject and getattr(error,'sqlstate',None)=='22012':
                counts=all_counts(c)
                assert all(counts[x]==0 for x in TABLES)
                catalog(c,'rollback_empty')
                save('rollback_result.json',dict(status='PASS',deterministic_error='division_by_zero',sqlstate='22012',partial_insert_proven=True,authorized_counts_after_rollback={x:counts[x] for x in TABLES},source_writes=0))
                return
            raise
        assert not inject
        catalog(c,'after_commit_'+label)


def verify(label):
    guard(TARGET,persistent.connect)
    with source() as s,persistent.connect(TARGET) as c:
        session(c)
        c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        try:
            approved(c,s)
            tables,auth=compare(s,c)
            scientific=science(c);assert scientific==science(s)
            structure=catalog(c,label)
            result=dict(mode='VERIFY_ALREADY_TRANSFERRED',result='ALREADY_TRANSFERRED_EXACTLY',destination_database=TARGET['database'],destination_revision='pg_v2_baseline',structural_manifest_sha256=structure,dataset_version_id=OFFICIAL,tables=tables,dataset=[r for r in tables if r['table'] in DATASET],scientific_snapshot=scientific,authentication=auth,unauthorized_transfer=0,absence=absence(c),integrity=integrity(c),semantic_transformations=0,source_writes=0,destination_writes=0,transfer_hash_label='TRANSFER VERIFICATION HASH; PostgreSQL JSONB text, length-prefixed UTF-8 rows ordered by PK; users excludes password_hash, separately checked by exact boolean equality')
            save('verification_'+label+'.json',result)
            event('ALREADY_TRANSFERRED_EXACTLY_'+label)
            return result
        finally: c.execute('ROLLBACK')


def main():
    action=argparse.ArgumentParser();action.add_argument('action',choices=['preflight','rollback','transfer','verify','restart']);a=action.parse_args()
    if a.action=='preflight':
        save('identity_initial.json',guard(TARGET,persistent.connect))
        with source() as s,persistent.connect(TARGET) as c: preflight(s,c,TARGET,'initial',True)
        event('PREFLIGHT_PASS')
    elif a.action=='rollback':
        os.environ['DBV22_EVIDENCE_DIR']=str(E/'disposable');os.environ['DBV22_PORT']='56441'
        import certify_dbv22 as disposable
        assert not disposable.TARGET.exists(),'REFUSE_TO_RECREATE_DISPOSABLE'
        disposable.provision();disposable.upgrade()
        t=json.loads(disposable.TARGET.read_text())
        transfer(t,disposable.connect,'disposable_failure',True)
        transfer(t,disposable.connect,'disposable_recovery')
        save('rollback_recovery.json',dict(status='PASS',subsequent_complete_transfer=True,target=t))
        # Stop separate test cluster; preserve its evidence and never touch persistent/source storage.
        subprocess.run(DOCKER+['stop','--time','30',t['container_id']],capture_output=True,check=True)
        event('ROLLBACK_AND_RECOVERY_PASS')
    elif a.action=='transfer':
        assert json.loads((E/'rollback_recovery.json').read_text())['status']=='PASS'
        transfer(TARGET,persistent.connect,'persistent')
        verify('post_commit')
    elif a.action=='verify': verify('repeat')
    elif a.action=='restart':
        before=verify('before_restart')
        t=TARGET
        subprocess.run(DOCKER+['stop','--time','30',t['container_id']],capture_output=True,check=True)
        subprocess.run(DOCKER+['start',t['container_id']],capture_output=True,check=True)
        for _ in range(60):
            if subprocess.run(DOCKER+['exec',t['container_id'],'pg_isready','-U','postgres'],capture_output=True).returncode==0: break
            time.sleep(1)
        after=verify('after_restart');assert before==after
        save('persistence_result.json',dict(status='PASS',same_container=True,same_volume=True,same_database_oid=True,same_system_identifier=True,identical_before_after=True,persistent=True,target=t))
        event('PERSISTENCE_PASS')


if __name__=='__main__':
    try: main()
    except Exception as error:
        # Never serialize PostgreSQL DETAIL, query parameters or source user rows.
        safe=dict(status='BLOCKED',step=CURRENT_STEP,error_type=type(error).__name__,sqlstate=getattr(error,'sqlstate',None))
        if isinstance(error,AssertionError) and error.args and isinstance(error.args[0],str): safe['invariant']=error.args[0]
        save('blocked.json',safe);print(json.dumps(safe));sys.exit(1)
