"""Reproducible S1.2: local read-only inputs and Docker SELECT-only snapshots."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'malaria_dataset_split_project/src'), str(ROOT / 'scripts/audit_s1_1')]
from malaria_split.identity.nlm import canonical_nlm_cell_patient_key, canonical_nlm_full_smear_patient_key
from malaria_split.identity.source_identity_index import load_official_patient_mapping
from inspect_smears import workbook_rows

OUT = ROOT / 'docs/audits/s1_2'
RAW = ROOT / 'malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf'
VERSION = 'd8c0cab5-09dd-597f-9de7-7ca01aee2ec2'
CELL = ROOT / 'malaria_dl_local_project/data/malaria_dataset_versions' / VERSION
MAPPINGS = [ROOT / 'malaria_dataset_split_project/var/audit/source' / f'patientid_cellmapping_{c}.csv' for c in ('parasitized', 'uninfected')]


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError('STOP: ' + reason)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def dump(name: str, value: object) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def snapshot(name: str) -> dict:
    base = ROOT / 'scripts/audit_s1_1'
    code = (base / 'guards.py').read_text() + '\n' + (base / 'db_snapshot.py').read_text().replace('from guards import require_read_only_select', '')
    result = subprocess.run(['docker', 'compose', 'exec', '-T', 'backend', 'python', '-'], input=code, text=True, capture_output=True, check=True, cwd=ROOT)
    data = json.loads(result.stdout)
    # Retain complete table digests but only rows needed to reproduce this join.
    for key in ('datasets', 'dataset_source_records', 'identity_evidence', 'dataset_materializations'):
        del data[key]
    data['dataset_split_assignments'] = [r for r in data['dataset_split_assignments'] if r['dataset_version_id'] == VERSION]
    with gzip.open(OUT / name, 'wt') as f:
        json.dump(data, f, sort_keys=True)
    return data


def write_csv(name: str, rows: list[dict]) -> None:
    with (OUT / name).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def calculate(db: dict) -> tuple[dict, list[dict]]:
    mapping, errors = load_official_patient_mapping(MAPPINGS)
    require(not errors and all(len(ids) == 1 for ids in mapping.values()), 'official mapping errors/ambiguity')
    official = set().union(*mapping.values())
    cell_keys = {canonical_nlm_cell_patient_key(p, official_patient_ids=official) for p in official}
    source_ids = {r['dataset_id'] for r in db['dataset_version_sources'] if r['dataset_version_id'] == VERSION}
    identities = {r['id']: r['source_identifier'] for r in db['clinical_identities'] if r['dataset_id'] in source_ids}
    require(set(identities.values()) == cell_keys and len(cell_keys) == 201, 'Cell identities disagree with official mappings')
    assignments = [r for r in db['dataset_split_assignments'] if r['dataset_version_id'] == VERSION]
    require(Counter(r['split_name'].upper() for r in assignments) == {'TRAIN': 22180, 'VAL': 2693, 'TEST': 2685}, 'protected assignment counts')
    splits: dict[str, set[str]] = defaultdict(set)
    for row in assignments:
        splits[identities[row['clinical_identity_id']]].add(row['split_name'].upper())
    require(all(len(s) == 1 for s in splits.values()), 'patient crosses protected splits')
    workbook = workbook_rows(RAW / 'Dataset_statistics.xlsx')
    stats = defaultdict(Counter)
    for sheet, entries in workbook.items():
        for row in entries:
            pid = row[0].split('\\')[2]
            stats[(sheet, pid)].update(images=1, WBC=int(row[1]), parasitized=int(row[2]), uninfected=int(row[3]))
    rows = []
    forms = Counter()
    import re
    for sheet in ('Polygon Set', 'Point Set'):
        for path in sorted((RAW / sheet).iterdir()):
            if not path.is_dir():
                continue
            pid = path.name
            key = canonical_nlm_full_smear_patient_key(pid)
            forms[re.sub('[0-9]+', '#', pid)] += 1
            images = len(list((path / 'Img').glob('*.jpg')))
            gt = len(list((path / 'GT').glob('*.txt')))
            require(images == gt == stats[(sheet, pid)]['images'] == 5, 'physical/workbook image counts: ' + pid)
            rows.append(dict(source_family='smear_segmentation', source_patient_id=pid, canonical_patient_id=key, cell_identity_exists=key in cell_keys, set=sheet.removesuffix(' Set'), status='MATCHED_BY_NLM_NAMING_CONVENTION' if key in cell_keys else 'NO_CELL_IDENTITY_MATCH', existing_cell_split=next(iter(splits[key]), 'NO_ASSIGNMENT'), images=images, **{k: stats[(sheet, pid)][k] for k in ('WBC', 'parasitized', 'uninfected')}))
    keys = {r['canonical_patient_id'] for r in rows}
    polygon = [r for r in rows if r['set'] == 'Polygon']
    require(len(rows) == len(keys) == 193, 'Full Smear cardinality/collision')
    require(keys <= cell_keys, 'Full-only identities')
    require(len(polygon) == len({r['canonical_patient_id'] for r in polygon}) == 33, 'Polygon mapping')
    prior = list(csv.DictReader((ROOT / 'docs/audits/s1_1/full_smear_candidates.csv').open()))
    require({(r['source_patient_id'], r['canonical_patient_id']) for r in rows} == {(r['full_patient_id'], r['cell_candidate']) for r in prior}, 'S1.1 mapping disagreement')
    def distribution(selected: list[dict]) -> dict:
        return {split: dict(patients=sum(r['existing_cell_split'] == split for r in selected), percent=round(100 * sum(r['existing_cell_split'] == split for r in selected) / len(selected), 6), **{field: sum(r[field] for r in selected if r['existing_cell_split'] == split) for field in ('images', 'WBC', 'parasitized', 'uninfected')}) for split in ('TRAIN', 'VAL', 'TEST', 'NO_ASSIGNMENT')}
    return dict(source_ids=len(rows), parsed_successfully=len(rows), parse_failures=0, canonical_ids=len(keys), duplicate_canonical_ids=len(rows)-len(keys), cell_canonical_ids=len(cell_keys), intersection=len(keys & cell_keys), full_only=sorted(keys-cell_keys), cell_only=sorted(cell_keys-keys), polygon_ids=len(polygon), polygon_cell_matches=sum(r['cell_identity_exists'] for r in polygon), polygon=distribution(polygon), full_smear=distribution(rows), observed_forms=dict(forms), s1_1_mapping_equal=True, c47p8=[r for r in rows if r['canonical_patient_id'].startswith('C47P8')]), rows


def main() -> None:
    OUT.mkdir(exist_ok=True, parents=True)
    dump('git_at_execution.json', {key: subprocess.check_output(['git', *args], text=True, cwd=ROOT).strip() for key, args in {'branch':['branch','--show-current'], 'HEAD':['rev-parse','HEAD'], 'parent':['rev-parse','HEAD^'], 'status':['status','--short']}.items()})
    before = {'raw': inventory(RAW), 'cell': inventory(CELL), 'mapping': {str(p.relative_to(ROOT)): sha(p) for p in MAPPINGS}}
    dump('input_hashes_before.json', before)
    db = snapshot('db_before.json.gz')
    summary, rows = calculate(db)
    after_db = snapshot('db_after.json.gz')
    after = {'raw': inventory(RAW), 'cell': inventory(CELL), 'mapping': {str(p.relative_to(ROOT)): sha(p) for p in MAPPINGS}}
    dump('input_hashes_after.json', after)
    require(before == after, 'physical inputs changed')
    require(db == after_db, 'database snapshots changed')
    summary.update(status='PASS', timestamp=datetime.now(timezone.utc).isoformat(), protected_dataset_version_id=VERSION, postgresql_writes=0, db_snapshots_equal=True, inputs_equal=True, input_counts={k:len(v) for k,v in before.items()}, freeze_matches=db['freeze_matches'], annotation_count_source='Official local Dataset_statistics.xlsx; no GT polygon validation', protected_cell_dataset_version_changed=False, cell_assignments_changed=0, full_smear_raw_files_changed=0, dataset_versions_created=0, full_smear_assignments_created=0, yolo_datasets_created=0, tiles_created=0)
    write_csv('full_smear_identity_mapping.csv', [{k:r[k] for k in ('source_family','source_patient_id','canonical_patient_id','cell_identity_exists','set','status')} for r in rows])
    write_csv('full_smear_existing_split.csv', rows)
    write_csv('polygon_existing_split.csv', [dict(full_smear_patient_id=r['source_patient_id'], canonical_patient_id=r['canonical_patient_id'], cell_identity_exists=r['cell_identity_exists'], existing_cell_split=r['existing_cell_split']) for r in rows if r['set']=='Polygon'])
    dump('canonical_identity_summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as error:
        dump('STOP.json', {'status':'STOP', 'reason':str(error)})
        raise
