"""Read-only audit behavior against captured real inputs, with negative controls."""
from __future__ import annotations

import copy
import gzip
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('s1_2_audit', Path(__file__).with_name('audit.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


@pytest.fixture
def snapshot() -> dict:
    with gzip.open(audit.OUT / 'db_before.json.gz', 'rt') as f:
        return json.load(f)


def test_actual_inputs_mapping_distribution_and_no_mutation(snapshot: dict) -> None:
    original = copy.deepcopy(snapshot)
    hashes = {p: audit.sha(p) for p in audit.MAPPINGS}
    summary, rows = audit.calculate(snapshot)
    assert summary['source_ids'] == summary['canonical_ids'] == 193
    assert summary['polygon_ids'] == summary['polygon_cell_matches'] == 33
    assert summary['cell_canonical_ids'] == 201
    assert summary['intersection'] == 193
    assert summary['full_only'] == []
    assert len(summary['cell_only']) == 8
    assert sum(v['patients'] for v in summary['polygon'].values()) == 33
    assert sum(v['images'] for v in summary['polygon'].values()) == 165
    assert snapshot == original
    assert hashes == {p: audit.sha(p) for p in audit.MAPPINGS}
    assert len(rows) == 193


def test_stops_on_protected_counts(snapshot: dict) -> None:
    snapshot['dataset_split_assignments'] = [r for r in snapshot['dataset_split_assignments'] if r['dataset_version_id'] != audit.VERSION]
    with pytest.raises(ValueError, match='STOP: protected assignment counts'):
        audit.calculate(snapshot)


def test_stops_on_identity_mismatch(snapshot: dict) -> None:
    source_ids = {r['dataset_id'] for r in snapshot['dataset_version_sources'] if r['dataset_version_id'] == audit.VERSION}
    next(r for r in snapshot['clinical_identities'] if r['dataset_id'] in source_ids)['source_identifier'] = 'unexpected'
    with pytest.raises(ValueError, match='STOP: Cell identities'):
        audit.calculate(snapshot)


def test_stops_on_collisions(snapshot: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, 'canonical_nlm_full_smear_patient_key', lambda value: 'C92P53ThinF')
    with pytest.raises(ValueError, match='STOP: Full Smear cardinality/collision'):
        audit.calculate(snapshot)


def test_stops_on_unexpected_full_only(snapshot: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    normalizer = audit.canonical_nlm_full_smear_patient_key
    monkeypatch.setattr(audit, 'canonical_nlm_full_smear_patient_key', lambda value: normalizer(value) + '_unknown')
    with pytest.raises(ValueError, match='STOP: Full-only'):
        audit.calculate(snapshot)
