"""Audit-only probe: current production metadata/files, no DB or image writes.
Run through the existing backend with stdin, never change DATABASE_URL.
"""
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from malaria_split.persistence.split_generation import V1_ID, prepare_split_generation
from malaria_split.splitting.patient_profiles import load_patient_profiles
from malaria_split.splitting.optimizer import optimize_patient_split

engine = create_engine(os.environ['DATABASE_URL'])
output = {}
with engine.connect() as c:
    with c.begin():
        c.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
        output['database'] = c.execute(text('SELECT current_database()')).scalar_one()
        assert output['database'] == 'malaria_experiments'
        assert c.execute(text('SHOW transaction_read_only')).scalar_one() == 'on'
        output['tables'] = {}
        for table in ('datasets', 'clinical_identities', 'dataset_source_records', 'identity_evidence',
                      'dataset_versions', 'dataset_version_sources', 'dataset_split_assignments',
                      'dataset_split_validation_checks', 'dataset_split_statistics', 'dataset_materializations',
                      'dataset_materialization_activations'):
            # Closed internal list; sorted JSON rows include all columns, not just counts.
            rows = c.execute(text(f'SELECT to_jsonb(t)::text FROM {table} t ORDER BY to_jsonb(t)::text')).scalars()
            h = hashlib.sha256(); count = 0
            for row in rows:
                h.update(row.encode()); h.update(b'\n'); count += 1
            output['tables'][table] = {'rows': count, 'sha256': h.hexdigest()}
        output['versions'] = [dict(r) for r in c.execute(text(
            'SELECT id,name,status,source_record_count FROM dataset_versions ORDER BY id')).mappings()]
        materialization = dict(c.execute(text('SELECT id,relative_root,status,reconciliation_status FROM '
            'dataset_materializations WHERE dataset_version_id=:v'), dict(v=V1_ID)).mappings().one())
        output['materialization'] = materialization
        try:
            prepare_split_generation(c)
        except RuntimeError as exc:
            assert str(exc) == 'Split generation requires DRAFT or matching GENERATED state'
            output['default_generation_result'] = str(exc)
        else:
            raise AssertionError('Expected frozen reference to reject regeneration')
        profiles = load_patient_profiles(c, V1_ID)
        first = optimize_patient_split(profiles, 42)
        second = optimize_patient_split(profiles, 43)
        assert first.winner.evaluation.valid and second.winner.evaluation.valid
        assert set(first.winner.assignments) == set(second.winner.assignments)
        assert first.winner.assignments != second.winner.assignments
        output['in_memory_optimizer'] = {
            'patients': len(profiles), 'records': sum(p.total_records for p in profiles),
            'seed42_digest': first.winner.evaluation.canonical_assignment_digest,
            'seed43_digest': second.winner.evaluation.canonical_assignment_digest,
            'changed_patient_assignments': sum(first.winner.assignments[k] != second.winner.assignments[k]
                                               for k in first.winner.assignments),
            'seed42_violations': first.winner.evaluation.hard_constraint_violations,
            'seed43_violations': second.winner.evaluation.hard_constraint_violations,
            'persisted': False,
        }
root = Path('/app/malaria_dl_local_project/data') / materialization['relative_root']
h = hashlib.sha256(); count = 0; byte_count = 0
for path in sorted(p for p in root.rglob('*') if p.is_file()):
    content = path.read_bytes()
    h.update((path.relative_to(root).as_posix() + '\0' + hashlib.sha256(content).hexdigest() + '\n').encode())
    count += 1; byte_count += len(content)
output['reference_files'] = dict(count=count, bytes=byte_count, sha256_inventory=h.hexdigest())
engine.dispose()
print(json.dumps(output, indent=2, default=str))
