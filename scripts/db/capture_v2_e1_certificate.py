"""Issue an ACL-only baseline certificate; explicitly cannot certify Gate E."""
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'docs/audits/e10_10_5e1_evidence/route_a'
sys.path.insert(0,str(ROOT))
os.environ['PGV2_EVIDENCE_DIR']=str(E)
os.environ['PGPASSFILE']=json.loads((E/'private_paths.json').read_text())['pgpass']
from verify_v2_route_a import connect,guard
from v2_catalog_probe import snapshot

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name): return json.loads((E/name).read_text())
def main():
 t=guard()
 installed=read('installed_catalog.json')
 with connect(t) as c: assert snapshot(c)==installed
 oldpath=ROOT/'docs/audits/e10_10_5d4_evidence/route_a'
 old=json.loads((oldpath/'installed_catalog.json').read_text())
 expected=copy.deepcopy(old)
 relation=next(r for r in expected['relations'] if r['name']=='alembic_version')
 relation['relacl']='{capstone_v2_migrator=arwdDxtm/capstone_v2_migrator,capstone_v2_runtime=r/capstone_v2_migrator}'
 privilege=next(r for r in expected['runtime_privileges'] if r['relation']=='alembic_version' and r['privilege']=='SELECT')
 assert privilege['allowed'] is False
 privilege['allowed']=True
 assert expected==installed, 'Unexpected catalog or scientific contract drift'
 for path in (E.parent/'previous_baseline').glob('*.sql'):
  if path.name!='10_privileges.sql': assert path.read_bytes()==(ROOT/'alembic_v2/baseline'/path.name).read_bytes()
 suites={}
 for name in ['server_tests.json','d03_server_tests.json','d05_server_tests.json']:
  rows=read(name); assert rows and all(r['passed'] for r in rows); suites[name]=len(rows)
 for name in ['rollback_result.json','idempotence_result.json','restore_result.json','runtime_acl_revision.json']:
  assert read(name)['passed'] is True
 assert read('legacy_revision.json')['revision']=='20260922_01'
 history={}
 for name in subprocess.check_output(['git','ls-files','docs/audits/e10_10_5d4_evidence'],cwd=ROOT,text=True).splitlines():
  original=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
  assert original==(ROOT/name).read_bytes(), name
  history[name]=sha(ROOT/name)
 (E.parent/'d4_preservation.json').write_text(json.dumps(history,indent=2)+'\n')
 manifest=sha(ROOT/'alembic_v2/baseline/catalog_manifest.json')
 catalog=hashlib.sha256(json.dumps(installed,sort_keys=True,default=str).encode()).hexdigest()
 from adoption_v2.core import MANIFEST_HASH,CATALOG_HASH
 assert (manifest,catalog)==(MANIFEST_HASH,CATALOG_HASH)
 evidence={p.name:sha(p) for p in E.glob('*.json') if p.name not in ['certificate.json','private_paths.json']}
 result=dict(stage='E10.10.5E.1',decision='E-01 approved',scope='ACL-only baseline recertification; NOT Gate E integration approval',passed=True,
             manifest_sha256=manifest,catalog_sha256=catalog,previous_certificate=json.loads((oldpath/'certificate.json').read_text()),
             only_catalog_change='runtime SELECT on public.alembic_version',scientific_D01_D06_unchanged=True,
             postgres_system_identifier=t['postgres_system_identifier'],postgres_version='17.9',server_tests=suites,
             evidence_sha256=evidence,gate_e='BLOCKED_E02',pending='TRAIN local/Docker, provenance producers, VALIDATION, recovery/concurrency, publication/lineage, API/React, history/ensemble/XAI producers')
 (E/'certificate.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['passed','manifest_sha256','catalog_sha256','server_tests','gate_e']},indent=2))
if __name__=='__main__': main()
