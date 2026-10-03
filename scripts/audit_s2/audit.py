"""Host orchestration only: hash local inputs, run PostgreSQL work inside Docker."""
from __future__ import annotations
import csv
import gzip
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/audit_s1_2')]
import audit as previous

OUT = ROOT / 'docs/audits/s2'


def dump(name: str, value: object) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def snapshot(name: str) -> dict:
    base = ROOT / 'scripts/audit_s1_1'
    code = (base / 'guards.py').read_text() + '\n' + (base / 'db_snapshot.py').read_text().replace('from guards import require_read_only_select', '')
    output = subprocess.check_output(['docker', 'compose', 'exec', '-T', 'backend', 'python', '-'], input=code, text=True, cwd=ROOT)
    data = json.loads(output)
    with gzip.open(OUT / name, 'wt') as handle:
        json.dump(data, handle, sort_keys=True)
    return data


def protected(db: dict) -> dict:
    links = [r for r in db['dataset_version_sources'] if r['dataset_version_id'] == previous.VERSION]
    source_ids = {r['dataset_id'] for r in links}
    records = [r for r in db['dataset_source_records'] if r['dataset_id'] in source_ids]
    record_ids = {r['id'] for r in records}
    return dict(version=db['version'], fingerprints=db['fingerprints'], sources=links,
                datasets=[r for r in db['datasets'] if r['id'] in source_ids],
                records=records, identities=[r for r in db['clinical_identities'] if r['dataset_id'] in source_ids],
                evidence=[r for r in db['identity_evidence'] if r['source_record_id'] in record_ids],
                assignments=[r for r in db['dataset_split_assignments'] if r['dataset_version_id'] == previous.VERSION],
                materializations=[r for r in db['dataset_materializations'] if r['dataset_version_id'] == previous.VERSION])


def inventory(db: dict) -> dict:
    return dict(raw=previous.inventory(previous.RAW), cell=previous.inventory(previous.CELL),
                mappings={str(p.relative_to(ROOT)): previous.sha(p) for p in previous.MAPPINGS},
                cell_fingerprints=db['fingerprints'], cell_version=db['version'], freeze_matches=db['freeze_matches'])


def worker(mode: str) -> dict:
    return json.loads(subprocess.check_output([
        'docker', 'compose', 'exec', '-T', '-e', 'PYTHONDONTWRITEBYTECODE=1',
        '-e', 'PYTHONPATH=/app/malaria_dataset_split_project/src', 'backend',
        'python', '/scripts/audit_s2/worker.py', mode], text=True, cwd=ROOT))


def write_csv(name: str, rows: list[dict]) -> None:
    with (OUT / name).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: list[dict]) -> dict:
    result = {}
    for split in ('TRAIN', 'VAL', 'TEST'):
        selected = [r for r in rows if r['existing_cell_split'] == split]
        result[split.lower()] = dict(patients=len(selected), **{key: sum(r[key] for r in selected) for key in ('images', 'parasitized', 'uninfected', 'WBC')})
    return result


def main() -> None:
    if sys.argv[1:] not in ([], ['--apply']):
        raise ValueError('Only --apply is supported; default is preflight only')
    OUT.mkdir(exist_ok=True, parents=True)
    before_db = snapshot('db_before.json.gz')
    before = inventory(before_db)
    dump('integrity_before.json', before)
    _, rows = previous.calculate(before_db)
    plan = worker('--preflight')
    previous.require(all(plan['patient_assignments'][r['source_patient_id']].upper() == r['existing_cell_split'] for r in rows), 'independent workbook/adapter join differs')
    polygon = [r for r in rows if r['set'] == 'Polygon']
    point = [r for r in rows if r['set'] == 'Point']
    for split, counts in plan['polygon_annotations'].items():
        selected = [r for r in polygon if r['existing_cell_split'].lower() == split]
        previous.require(counts == dict(Parasitized=sum(r['parasitized'] for r in selected), Uninfected=sum(r['uninfected'] for r in selected), White_Blood_Cell=sum(r['WBC'] for r in selected)), 'workbook / parsed Polygon mismatch')
    dump('preflight.json', plan)
    result = worker('--apply') if '--apply' in sys.argv else {'result': 'PREFLIGHT_ONLY'}
    dump('persistence.json', result)
    if '--apply' in sys.argv:
        repeat = worker('--apply')
        previous.require(repeat['result'] == 'ALREADY_EXISTS_MATCH', 'idempotency failed')
        dump('idempotency.json', repeat)
    after_db = snapshot('db_after.json.gz')
    after = inventory(after_db)
    dump('integrity_after.json', after)
    previous.require(before == after, 'protected physical inputs or Cell fingerprints changed')
    previous.require(protected(before_db) == protected(after_db), 'protected complete database rows changed')
    write_csv('smear_patient_assignments.csv', [dict(full_smear_patient_id=r['source_patient_id'], canonical_patient_id=r['canonical_patient_id'], set=r['set'], cell_reference_split=r['existing_cell_split'], smear_split=plan['patient_assignments'][r['source_patient_id']].upper(), image_count=r['images']) for r in rows])
    write_csv('polygon_split_summary.csv', [dict(full_smear_patient_id=r['source_patient_id'], canonical_patient_id=r['canonical_patient_id'], split=r['existing_cell_split'], image_count=r['images'], polygon_count=r['parasitized']+r['uninfected']+r['WBC'], rbc_parasitized=r['parasitized'], rbc_uninfected=r['uninfected'], wbc=r['WBC']) for r in polygon])
    write_csv('polygon_positive_concentration.csv', [dict(canonical_patient_id=r['canonical_patient_id'], split=r['existing_cell_split'], rbc_parasitized=r['parasitized'], positive_fraction=r['parasitized']/sum(x['parasitized'] for x in polygon if x['existing_cell_split'] == r['existing_cell_split'])) for r in polygon if r['existing_cell_split'] in ('VAL', 'TEST')])
    summary = dict(strategy='thin_blood_smear_same_split_v1', reference_dataset_version_id=previous.VERSION,
                   dataset_family='smear_segmentation', patients_total=len(rows), images_total=sum(r['images'] for r in rows),
                   **{k: {f:v[f] for f in ('patients','images')} for k,v in aggregate(rows).items()},
                   no_assignment=sum(r['existing_cell_split'] == 'NO_ASSIGNMENT' for r in rows),
                   canonical_collisions=len(rows)-len({r['canonical_patient_id'] for r in rows}),
                   cross_family_mismatches=sum(plan['patient_assignments'][r['source_patient_id']].upper() != r['existing_cell_split'] for r in rows),
                   polygon=dict(patients=len(polygon), images=sum(r['images'] for r in polygon),
                                **{s+'_patients':v['patients'] for s,v in aggregate(polygon).items()},
                                annotations={s:dict(**v, total_polygons=v['parasitized']+v['uninfected']+v['WBC']) for s,v in aggregate(polygon).items()}),
                   point=dict(patients=len(point), images=sum(r['images'] for r in point), splits=aggregate(point), annotation_type='point; not polygon'),
                   persistence={k:v for k,v in result.items() if k not in ('preflight','sources')},
                   integrity=dict(physical_inputs_equal=True, protected_cell_rows_equal=True, raw_files=len(before['raw']), cell_files=len(before['cell'])))
    dump('split_summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        dump('STOP.json', dict(status='STOP', reason=str(error)))
        raise
