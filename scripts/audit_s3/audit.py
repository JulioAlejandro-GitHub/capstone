"""S3 orchestration: compare S2 evidence, run Docker lifecycle, retain minimal artifacts."""
from __future__ import annotations

import gzip
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'malaria_dataset_split_project/src'))
from evidence import inventory, protected_state
from malaria_split.sources.thin_blood_smears_pf import file_sha256
from malaria_split.governance.freeze import _canonical_digest
from malaria_split.persistence.formal_validation import _canonical_json

OUT = ROOT / 'docs/audits/s3'
S2 = ROOT / 'docs/audits/s2'
RAW = ROOT / 'malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf'
CELL = ROOT / 'malaria_dl_local_project/data/malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2'


def dump(name: str, value: Any) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + '\n')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError('STOP: ' + message)


def input_inventory() -> dict[str, Any]:
    baseline = json.loads((S2 / 'integrity_after.json').read_text())
    current = dict(raw=inventory(RAW), cell=inventory(CELL),
                   mappings={path: file_sha256(ROOT / path) for path in baseline['mappings']})
    require(all(current[key] == baseline[key] for key in current), 'physical inputs differ from S2')
    return current


def inventory_summary(current: dict[str, Any], database: dict[str, Any]) -> dict[str, Any]:
    return dict(inventory_reference='docs/audits/s2/integrity_after.json; exact per-file equality checked',
                files={key:dict(count=len(values),sha256=_canonical_digest([(k,v) for k,v in sorted(values.items())])) for key,values in current.items()},
                protected_database=database)


def worker(mode: str, payload: dict[str, Any]) -> dict[str, Any]:
    command = ['docker','compose','exec','-T','-e','PYTHONDONTWRITEBYTECODE=1',
               '-e','PYTHONPATH=/app/malaria_dataset_split_project/src','backend',
               'python','/scripts/audit_s3/worker.py',mode]
    result = subprocess.run(command,input=json.dumps(payload),capture_output=True,text=True,cwd=ROOT)
    if result.returncode:
        (OUT / 'worker_error.log').write_text(result.stderr)
        raise RuntimeError('Docker worker failed; see worker_error.log (transaction rolled back if active)')
    return json.loads(result.stdout)


def main() -> None:
    require(sys.argv[1:] in ([], ['--apply']), 'only --apply is supported')
    OUT.mkdir(exist_ok=True,parents=True)
    inputs = input_inventory()
    with gzip.open(S2/'db_after.json.gz','rt') as handle:
        protected = protected_state(json.load(handle))
    s2_persistence = json.loads((S2/'persistence.json').read_text())
    payload = dict(raw=inputs['raw'],cell=inputs['cell'],protected_database=protected,
                   s2_version=json.loads((S2/'postgresql_final.json').read_text())['version'],
                   expected_assignments={k:s2_persistence[k] for k in ('patient_digest','record_digest')})
    before = inventory_summary(inputs,protected)
    dump('integrity_before.json',before)
    preflight = worker('--preflight',payload)
    dump('preflight.json',{k:v for k,v in preflight.items() if k != 'manifest'})
    (OUT / 'source_manifest.json').write_text(_canonical_json(preflight['manifest']) + '\n')
    require(file_sha256(OUT / 'source_manifest.json') == preflight['manifest_fingerprint'], 'manifest file fingerprint differs')
    if '--apply' not in sys.argv:
        dump('integrity_after.json',inventory_summary(input_inventory(),preflight['protected_after']))
        print(json.dumps(dict(result='PREFLIGHT_PASS',fingerprint=preflight['manifest_fingerprint'],statistics=preflight['validation']['statistics']),indent=2))
        return
    applied = worker('--apply',payload)
    require(applied['manifest'] == preflight['manifest'] and applied['manifest_fingerprint'] == preflight['manifest_fingerprint'], 'manifest changed between preflight and freeze')
    dump('freeze.json',{k:v for k,v in applied.items() if k != 'manifest'})
    repeated = worker('--apply',payload)
    require(repeated['outcome']['result'] == 'ALREADY_FROZEN_MATCH_NO_OP', 'freeze not idempotent')
    require(repeated['before'] == repeated['after'] == applied['after'], 'idempotent version changed')
    require(repeated['persisted_checks'] == applied['persisted_checks'] and repeated['persisted_statistics'] == applied['persisted_statistics'], 'idempotent validation changed')
    require(repeated['manifest'] == applied['manifest'], 'manifest not reproducible')
    dump('idempotency.json',{k:v for k,v in repeated.items() if k != 'manifest'})
    after = inventory_summary(input_inventory(),repeated['protected_after'])
    dump('integrity_after.json',after)
    require(before == after,'protected Cell/RAW/S2 data changed')
    changes = {key:dict(before=applied['before'][key],after=applied['after'][key]) for key in applied['before'] if applied['before'][key] != applied['after'][key]}
    require(set(changes) <= {'status','validated_at','frozen_at','methodology_json'},'unexpected Dataset Version mutation')
    dump('database_changes.json',dict(dataset_version_id=applied['after']['id'],changed_fields=changes,
         statistics_inserted=len(applied['persisted_statistics'])-len(applied['statistics_before']),
         checks_inserted=len(applied['persisted_checks'])-len(applied['checks_before']),
         protected_database_unchanged=True,new_dataset_versions=0,assignments_changed=0,materializations_created=0))
    dump('summary.json',dict(status='APPROVED',dataset_version_id=applied['after']['id'],
         lifecycle_before=applied['before']['status'],lifecycle_after=applied['after']['status'],
         statistics=applied['validation']['statistics'],fingerprint=applied['manifest_fingerprint'],
         fingerprint_contract='canonical SHA-256 of governed_source_assignments_v1 source manifest',
         reproducible=True,cell_changed=False,raw_changed=False,s2_assignments_changed=False,
         s4_authorized=True,trainability=applied['trainability']))
    print((OUT/'summary.json').read_text())


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        dump('STOP.json',dict(status='STOPPED',reason=str(error)))
        raise
