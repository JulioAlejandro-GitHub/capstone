"""Certify E-04 only after all isolated prerequisites; not a Gate E certificate."""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from probe_v2_e4_contract import E, ROOT, connect, guard
from v2_catalog_probe import snapshot


def sha(data): return hashlib.sha256(data).hexdigest()
def read(name): return json.loads((E/name).read_text())


def main():
    t=guard()
    actual=read('installed_catalog.json')
    with connect(t) as c:
        assert snapshot(c)==actual
        from adoption_v2.function_guard import DEPENDENCY_SQL,dependency_reference
        from adoption_v2.check_catalog import PAIRS,capture,reference
        deps=c.execute(DEPENDENCY_SQL).fetchall()
        historical_deps=dependency_reference()
        historical_keys={(r['name'],r['arguments']) for r in historical_deps}
        assert [r for r in deps if (r['name'],r['arguments']) in historical_keys]==historical_deps
        assert {name:capture(c,(table,name)) for table,name in sorted(PAIRS)}==reference()
    previous=ROOT/'docs/audits/e10_10_5e1_evidence/route_a'
    old=json.loads((previous/'installed_catalog.json').read_text())
    delta={}
    for key in old:
        before=[r for r in old[key] if r not in actual[key]]
        after=[r for r in actual[key] if r not in old[key]]
        if before or after: delta[key]=dict(before=before,after=after)
    assert set(delta)=={'constraints','indexes','functions','triggers'}
    for key in ('indexes','functions','triggers'):
        assert not delta[key]['before'],key
    removed={r['name'] for r in delta['constraints']['before']}
    assert removed=={'v2_evaluations_check_6a2239d39784','v2_evaluations_foreign_93473146c016'}
    assert {r['name'] for r in delta['functions']['after']}=={
        'e04_legacy_admission','e04_assert_calibration','e04_calibration_complete','e04_calibration_immutable'}
    assert all(r['owner']=='capstone_v2_migrator' and not r['prosecdef'] for r in delta['functions']['after'])
    suites={}
    for name in ('server_tests.json','d03_server_tests.json','d05_server_tests.json','e04_atomicity.json','e04_edges.json','e04_runtime_preflight.json'):
        rows=read(name);assert rows and all(r['passed'] for r in rows),name;suites[name]=len(rows)
    contract=read('e04_contract_tests.json')
    assert contract['passed'] and len(contract['results'])==27
    suites['e04_contract_tests.json']=len(contract['results'])
    assert len(read('e04_atomicity.json'))==7
    for name in ('rollback_result.json','idempotence_result.json','restore_result.json','runtime_acl_revision.json','route_b_regression.json'):
        assert read(name)['passed'] is True,name
    projection=read('e10_projection.json')
    for key in ('service_never_updates_legacy_results','ledger_canonical_event_and_typed_atomic',
                'fresh_service_replay_after_discarded_ack','missing_provenance_rejected'):
        assert projection[key] is True,key
    assert projection['typed_sql_failure_rollback']==dict(ledger=1,evaluations=0,metrics=0)
    assert len(projection['check_rejections'])==2
    assert read('legacy_revision.json')['revision']=='20260922_01'
    for name,marker in [('candidate_unit_tests.txt','101 passed'),('legacy_service_tests.txt','50 passed'),
                        ('service_unit_tests.txt','76 passed')]:
        assert marker in (E/name).read_text(),name
    cat=read('catalog_diff.json')
    manifest_hash=sha((ROOT/'alembic_v2/baseline/catalog_manifest.json').read_bytes())
    catalog_hash=sha(json.dumps(actual,sort_keys=True,default=str).encode())
    assert cat['status']=='passed' and cat['manifest_sha256']==manifest_hash
    assert cat['installed_sha256']==cat['expected_sha256']==catalog_hash
    subprocess.run([sys.executable,'scripts/db/build_v2_baseline.py','--check'],cwd=ROOT,check=True,
        env=dict(os.environ,PYTHONPATH='/private/tmp/e10_10_5d_parser312:'+str(ROOT)),capture_output=True)
    history={}
    names=subprocess.check_output(['git','ls-files','docs/audits/e10_10_5d4_evidence',
        'docs/audits/e10_10_5e1_evidence','docs/audits/e10_10_5e2_evidence','docs/audits/e10_10_5e3_evidence',
        'docs/audits/e10_10_4_target_schema.sql'],cwd=ROOT,text=True).splitlines()
    for name in names:
        original=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        assert original==(ROOT/name).read_bytes(),name
        history[name]=sha(original)
    (E.parent/'historical_preservation.json').write_text(json.dumps(history,indent=2)+'\n')
    # Promotion is the final step, after every assertion and historical check.
    core=ROOT/'adoption_v2/core.py'
    source=core.read_text()
    for key,value in [('MANIFEST_HASH',manifest_hash),('CATALOG_HASH',catalog_hash)]:
        source,n=re.subn(r'^'+key+r' = "[0-9a-f]{64}"$',key+' = "'+value+'"',source,flags=re.MULTILINE)
        assert n==1
    core.write_text(source)
    executor=ROOT/'adoption_v2/execute.py'
    source=executor.read_text()
    source,n=re.subn(r'^CERTIFIED_CATALOG_PATH = .+$',
        'CERTIFIED_CATALOG_PATH = ROOT / "docs/audits/e10_10_5e4_evidence/route_a/installed_catalog.json"',source,flags=re.MULTILINE)
    assert n==1
    executor.write_text(source)
    subprocess.run([sys.executable,'-c',
        'from adoption_v2.core import target; from adoption_v2.execute import certified_catalog; target(); certified_catalog()'],
        cwd=ROOT,check=True,env=dict(os.environ,PYTHONPATH='/private/tmp/e10_10_5d_parser312:'+str(ROOT)),capture_output=True)
    runtime_path=ROOT/'malaria_dl_local_project/src/malaria_dl/persistence/v2_runtime_contract.json'
    assert read('runtime_contract_capture.json')['sha256']==sha(runtime_path.read_bytes())
    report=dict(stage='E10.10.5E.4',decision='E-03 and E-04 approved',passed=True,
        scope='Baseline and calibration integrity recertification; NOT full E integration approval',
        manifest_sha256=manifest_hash,catalog_sha256=catalog_hash,postgres_version='17.9',
        postgres_system_identifier=t['postgres_system_identifier'],server_tests=suites,
        D01_D06_preserved=True,d04_historical_function_dependencies_unchanged=True,
        d06_four_exact_check_references=True,exact_catalog_delta=delta,
        runtime_legacy_admission_forbidden=True,route_b_regression=True,
        historical_files_verified=len(history),previous_certificate_sha256=sha((previous/'certificate.json').read_bytes()),
        supersedes_e4_certificate_sha256=sha((E.parent/'certificate_01/certificate.json').read_bytes()),
        e03_candidate_remains_uncertified=True,gate_e='BLOCKED_INTEGRATION_PENDING',
        pending='Real TRAIN/EVALUATE context producer and full E integration matrix',
        evidence_sha256={p.name:sha(p.read_bytes()) for p in E.iterdir() if p.is_file()
            and p.name not in {'certificate.json','private_paths.json'}},
        implementation_sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [
            ROOT/'alembic_v2/e04_contract.sql',ROOT/'scripts/db/build_v2_baseline.py',core,executor,
            ROOT/'adoption_v2/planner.py',ROOT/'adoption_v2/ddl.py',ROOT/'adoption_v2/transforms.py',
            ROOT/'malaria_dl_local_project/src/malaria_dl/persistence/v2_projection.py',
            ROOT/'malaria_dl_local_project/src/malaria_dl/persistence/result_repository.py',
            ROOT/'malaria_dl_local_project/src/malaria_dl/results/service.py',runtime_path,
            ROOT/'malaria_dl_local_project/src/malaria_dl/persistence/schema_contract.py']})
    (E/'certificate.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps({k:report[k] for k in ('passed','manifest_sha256','catalog_sha256','gate_e')},indent=2))


if __name__=='__main__': main()
