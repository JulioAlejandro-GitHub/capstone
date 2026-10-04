"""Source-family preparation for the existing formal validation and freeze lifecycle.

Reads S2 assignments and real source inspections. Never ingests, repairs or splits.
"""
from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, text

from malaria_split.governance.freeze import compute_final_fingerprints, _canonical_digest
from malaria_split.governance.trainability import SMEAR_LOGICAL_VALIDATION_CHECKS
from malaria_split.sources.thin_blood_smears_pf import SmearSourceInspection
from .formal_validation import FormalValidationError, FormalValidationPreparation, _canonical_json, _check
from .repositories import DatasetVersionRepository, ScientificBootstrapRepository
from .same_split import VERSION_ID, V1_ID, STRATEGY, preflight, _definition
from .smear_source_ingest import dataset_source_id, prepare_smear_rows, _dataset_metadata, source_name
from .split_generation import audit_persisted_assignments


@dataclass(frozen=True, slots=True)
class SmearValidationPreparation:
    formal: FormalValidationPreparation
    fingerprints: dict[str, str]
    manifest: dict[str, Any]
    manifest_fingerprint: str


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FormalValidationError('STOP: ' + message)


def _verify_source_rows(connection: Connection, inspection: SmearSourceInspection) -> dict[UUID, dict[str, Any]]:
    """Use S1's row serialization and repository, with SELECT-only comparisons."""
    source_id = dataset_source_id(inspection.annotation_set)
    source = connection.execute(text('SELECT * FROM datasets WHERE id=:id'), {'id': source_id}).mappings().one()
    _require(source['name'] == source_name(inspection.annotation_set)
             and source['metadata'] == _dataset_metadata(inspection)
             and source['total_images'] == len(inspection.records)
             and source['checksum'] == inspection.population_fingerprint, 'source provenance conflict')
    expected = prepare_smear_rows(inspection)
    repository = ScientificBootstrapRepository(connection)
    for group, table, key in (('identities', 'clinical_identities', 'source_identifier'),
                              ('records', 'dataset_source_records', 'source_record_key'),
                              ('evidence', 'identity_evidence', 'source_record_id')):
        rows = expected[group]
        actual = repository.rows_by_key(table, ','.join(rows[0]), key, dataset_id=source_id)
        _require(set(actual) == {row[key] for row in rows}, table + ' population conflict')
        _require(all(dict(actual[row[key]]) == row for row in rows), table + ' content conflict')
    return {row['id']: row for row in expected['records']}


def _verify_definition(connection: Connection, inspections: Sequence[SmearSourceInspection], plan: dict[str, Any], version_id: UUID) -> None:
    version = DatasetVersionRepository(connection).get(version_id)
    _require(version is not None and version['status'] in ('GENERATED', 'VALIDATED', 'FROZEN'), 'invalid S3 lifecycle')
    definition = _definition(inspections, plan)
    definition['id'] = version_id
    for key, expected in definition.items():
        actual = version[key]
        if key in ('class_mapping', 'methodology_json'):
            expected = json.loads(expected)
        if key == 'methodology_json':
            actual = {k: v for k, v in actual.items() if k != 'freeze_contract'}
        elif key.startswith('target_'):
            actual = str(actual.normalize())
        _require(actual == expected, 'S2 definition conflict: ' + key)
    links = set(connection.execute(text('SELECT dataset_id,role FROM dataset_version_sources WHERE dataset_version_id=:id'), {'id': version_id}).tuples())
    _require(links == {(dataset_source_id(s.annotation_set), 'PRIMARY') for s in inspections}, 'version source links conflict')


def prepare_smear_validation(
    connection: Connection, inspections: Sequence[SmearSourceInspection],
    expected_assignments: dict[str, str], dataset_version_id: UUID = VERSION_ID,
) -> SmearValidationPreparation:
    """Reconcile physical provenance, S2 evidence, and every persisted assignment."""
    plan = preflight(connection, inspections)  # S2's read-only reference/identity gates.
    _verify_definition(connection, inspections, plan, dataset_version_id)
    source_records: dict[UUID, dict[str, Any]] = {}
    record_sets: dict[UUID, str] = {}
    for inspection in inspections:
        current = _verify_source_rows(connection, inspection)
        source_records.update(current)
        record_sets.update({key: inspection.annotation_set for key in current})
    assignments = [dict(row) for row in connection.execute(text('''
        SELECT a.*,i.source_identifier FROM dataset_split_assignments a
        JOIN clinical_identities i ON i.id=a.clinical_identity_id
        WHERE a.dataset_version_id=:id ORDER BY a.source_record_id
    '''), {'id': dataset_version_id}).mappings()]
    _require(len(assignments) == len(source_records) and
             {r['source_record_id'] for r in assignments} == source_records.keys(), 'assignment coverage conflict')
    counts = Counter(row['source_identifier'] for row in assignments)
    sets = {s: {plan['canonical_keys'][r['source_identifier']] for r in assignments if r['split_name'] == s}
            for s in ('train', 'val', 'test')}
    mismatch_patients = {r['source_identifier'] for r in assignments
                         if plan['patient_assignments'][r['source_identifier']] != r['split_name']}
    manifest_records = []
    for row in assignments:
        source = source_records[row['source_record_id']]
        patient = row['source_identifier']
        canonical = plan['canonical_keys'][patient]
        annotation_set = record_sets[row['source_record_id']]
        _require(all(row[k] == source[k] for k in ('clinical_identity_id', 'class_index', 'class_name')), 'assignment/source identity conflict')
        _require(row['metadata'] == dict(algorithm=STRATEGY, canonical_patient_id=canonical,
                                        reference_dataset_version_id=str(V1_ID), annotation_set=annotation_set), 'assignment provenance conflict')
        manifest_records.append(dict(
            source_record_id=str(row['source_record_id']), clinical_identity_id=str(row['clinical_identity_id']),
            full_smear_patient_id=patient, canonical_patient_id=canonical,
            split=row['split_name'], annotation_set=annotation_set,
            image_relative_path=source['relative_source_key'], image_sha256=source['source_file_sha256'],
            annotation_relative_path=source['metadata']['annotation']['relative_path'],
            annotation_sha256=source['metadata']['annotation']['sha256']))
    audit = audit_persisted_assignments(connection, dataset_version_id)
    fingerprints = {key + '_sha256': value for key, value in asdict(compute_final_fingerprints(connection, dataset_version_id)).items()}
    repeated = {key + '_sha256': value for key, value in asdict(compute_final_fingerprints(connection, dataset_version_id)).items()}
    populations = {}
    for annotation_set in ('Polygon Set', 'Point Set'):
        rows = [r for r in manifest_records if r['annotation_set'] == annotation_set]
        inspection = next(s for s in inspections if s.annotation_set == annotation_set)
        populations[annotation_set] = dict(
            patients=len({r['canonical_patient_id'] for r in rows}), images=len(rows), gt=inspection.annotations_found,
            splits={split: dict(patients=len({r['canonical_patient_id'] for r in rows if r['split'] == split}),
                                images=sum(r['split'] == split for r in rows)) for split in ('train', 'val', 'test')})
    overlaps = {a + '_' + b: len(sets[a] & sets[b]) for a, b in (('train', 'val'), ('train', 'test'), ('val', 'test'))}
    checks = {
        'identity_coverage': _check(len(counts), 193, len(counts) == 193),
        'identity_conflicts': _check(0, 0, True, evidence='exact S1 identity and evidence row reconciliation'),
        **{'patient_' + name + '_overlap': _check(value, 0, value == 0) for name, value in overlaps.items()},
        'duplicate_cross_split_overlap': _check(audit['duplicate_cross_split_overlap'], 0, audit['duplicate_cross_split_overlap'] == 0),
        'assignment_count': _check(len(assignments), 965, len(assignments) == 965),
        'source_record_count': _check(len(source_records), 965, len(source_records) == 965),
        'split_completeness': _check(audit['split_counts'], {'train': 770, 'val': 95, 'test': 100}, audit['split_counts'] == {'train': 770, 'val': 95, 'test': 100}),
        'patient_count': _check(audit['patient_counts'], {'train': 154, 'val': 19, 'test': 20}, audit['patient_counts'] == {'train': 154, 'val': 19, 'test': 20} and audit['distinct_patients'] == 193),
        'five_images_per_patient': _check(sorted(set(counts.values())), [5], set(counts.values()) == {5}),
        'same_split_cross_family': _check(len(mismatch_patients), 0, not mismatch_patients, matched_patients=len(counts)-len(mismatch_patients)),
        'polygon_population': _check(populations['Polygon Set'], '33 patients / 165 images / 165 GT / 28-2-3',
            populations['Polygon Set']['patients'] == 33 and populations['Polygon Set']['images'] == populations['Polygon Set']['gt'] == 165 and
            {k: v['patients'] for k,v in populations['Polygon Set']['splits'].items()} == {'train': 28, 'val': 2, 'test': 3}),
        'point_population': _check(populations['Point Set'], '160 patients / 800 images / 800 GT', populations['Point Set']['patients'] == 160 and populations['Point Set']['images'] == populations['Point Set']['gt'] == 800),
        'source_provenance': _check('MATCH', 'MATCH', True, source_fingerprints={s.annotation_set: s.population_fingerprint for s in inspections}),
        's2_assignments_unchanged': _check(dict(patient_digest=audit['patient_digest'], record_digest=audit['record_digest']), expected_assignments,
            expected_assignments == dict(patient_digest=audit['patient_digest'], record_digest=audit['record_digest'])),
        'fingerprint_reproducibility': _check(fingerprints, repeated, fingerprints == repeated),
    }
    _require(set(checks) == set(SMEAR_LOGICAL_VALIDATION_CHECKS), 'required check set mismatch')
    failed = [name for name, check in checks.items() if check['status'] != 'PASS']
    _require(not failed, 'validation failed: ' + ', '.join(failed))
    statistics = dict(dataset_family='smear_segmentation', total_patients=len(counts), total_source_records=len(source_records),
                      total_assignments=len(assignments), patients=audit['patient_counts'], records=audit['split_counts'],
                      populations=populations, patient_overlaps=overlaps, no_assignment=len(source_records)-len(assignments),
                      cross_family_mismatches=len(mismatch_patients), fingerprints=fingerprints,
                      scientific_limitations=['Polygon VAL has 2 patients; TEST has 3. Images/tiles are correlated within patient.',
                                              'Technical NLM naming correspondence is not clinically verified biological identity.'])
    manifest = dict(contract='governed_source_assignments_v1', dataset_version_id=str(dataset_version_id),
                    dataset_family='smear_segmentation', strategy=STRATEGY, reference_dataset_version_id=str(V1_ID),
                    identity_rule=json.loads(_definition(inspections, plan)['methodology_json'])['identity_rule'],
                    sources={s.annotation_set: dict(population_fingerprint=s.population_fingerprint, provenance=s.provenance_sha256) for s in inspections},
                    fingerprints=fingerprints, records=manifest_records)
    # Reuse the existing canonical JSON serializer and canonical SHA-256 primitive.
    manifest_fingerprint = _canonical_digest([(_canonical_json(manifest),)])
    formal = FormalValidationPreparation(dataset_version_id, statistics, checks, audit['patient_digest'], audit['record_digest'])
    return SmearValidationPreparation(formal, fingerprints, manifest, manifest_fingerprint)
