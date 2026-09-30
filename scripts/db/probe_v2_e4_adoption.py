"""Route B regression on a fresh child DB, restored only from an archived copy.

Candidate pins are scoped to this test process, not promoted before certification.
Raw archive data stays in a private directory; public evidence is counts/hashes.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4
from probe_v2_e4_contract import E, ROOT, connect, guard
from verify_v2_route_a import new_database
from candidate_v2_e4 import candidate
from psycopg.types.string import TextLoader


def main():
    t=guard()
    child=new_database(t,'_e4b_'+uuid4().hex[:6])
    saved=ROOT/'docs/audits/e10_10_5d2_evidence/route_b'
    old=json.loads((saved/'target.json').read_text())
    backup_ref=json.loads((saved/'isolated_backup.json').read_text())
    backup=Path(backup_ref['path'])
    assert hashlib.sha256(backup.read_bytes()).hexdigest()==backup_ref['sha256']==old['backup_sha256']
    private=Path(tempfile.mkdtemp(prefix='e10_e4_adoption_',dir='/private/tmp'));os.chmod(private,0o700)
    d=['docker','--host','unix:///Users/julio/.docker/run/docker.sock']
    with backup.open('rb') as stream:
        result=subprocess.run(d+['exec','-i',t['container_id'],'pg_restore','-U','postgres',
            '--role=capstone_v2_migrator','--no-owner','--no-acl','--single-transaction','--exit-on-error',
            '-d',child['database']],stdin=stream,capture_output=True)
    (private/'restore.stderr').write_bytes(result.stderr)
    assert result.returncode==0,'Archived copy restore failed; private stderr retained'
    from adoption_v2 import execute
    from adoption_v2.core import digest,decode
    from adoption_v2.planner import build_plan
    from adoption_v2.preflight import preflight,schema_signature
    from adoption_v2.check_catalog import compare
    bindings=dict(documents={},configurations={},evaluations=[],calibrations={},consolidations=[],xai=[],xai_excluded={})
    with candidate():
        with connect(child) as c:
            c.adapters.register_loader('uuid',TextLoader)
            source=execute.capture(c)
            inventory=preflight(source)
            plan=build_plan(source,bindings)
        child.update(authorized_stage='E10.10.5D',gate_c_approved=True,copy_only=True,writers_fenced=True,
            regression_authorization='E-04 approved; isolated Route B regression only',
            migration_role='capstone_v2_migrator',runtime_role='capstone_v2_runtime',
            origin_system_identifier=old['origin_system_identifier'],backup_sha256=backup_ref['sha256'],
            mapping_sha256=digest(bindings),source_inventory_sha256=digest(inventory),
            legacy_schema_sha256=digest(schema_signature(source['catalog'])))
        (E/'route_b_target.json').write_text(json.dumps(child,indent=2)+'\n')
        url=f"postgresql+psycopg://capstone_v2_migrator@127.0.0.1:{child['host_port']}/{child['database']}"
        first=private/'apply';first.mkdir(mode=0o700)
        applied=execute.apply(child,url,bindings,first,backup_path=backup)
        assert applied['status']=='committed'
        completed=decode(json.loads((first/'plan.json').read_text()))
        child['completed_plan_sha256']=completed['plan_sha256']
        second=private/'repeat';second.mkdir(mode=0o700)
        repeated=execute.apply(child,url,bindings,second,backup_path=backup,completed_plan=completed)
        assert repeated['status']=='already_adopted'
        with connect(child) as c:
            c.adapters.register_loader('uuid',TextLoader)
            reconciliation=execute.reconcile(c,completed)
            comparison=compare(c,execute.catalog_snapshot(c),execute.certified_catalog())
            assert not comparison['unjustified']
            head=c.execute('SELECT version_num FROM alembic_version').fetchall()
            assert head==[{'version_num':'pg_v2_baseline'}]
        report=dict(passed=True,scope='Actual controlled Route B on fresh isolated archived copy; candidate pins test-only',
            source_backup_sha256=backup_ref['sha256'],source_inventory_sha256=digest(inventory),
            applied=applied,repeated_status=repeated['status'],reconciliation=reconciliation,
            catalog_comparison=comparison,head=head,private_directory=str(private),
            source_row_counts={k:len(v) for k,v in source['rows'].items()})
        (E/'route_b_regression.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    print('Route B apply, reconciliation and repeat passed; production pins unchanged')


if __name__=='__main__': main()
