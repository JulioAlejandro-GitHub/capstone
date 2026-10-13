"""Technical identity contracts; no database connection or dataset mutation."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from malaria_split.identity.nlm import (
    canonical_nlm_cell_patient_key,
    canonical_nlm_full_smear_patient_key,
)
from malaria_split.identity.source_identity_index import load_official_patient_mapping
from malaria_split.sources.thin_blood_smears_pf import cell_images_candidate_identifier

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('patient', ['C101P62ThinF', 'C33P1thinF', 'C1_thinF', 'C47P8thin_Original_Motic', 'C47P8thinOriginalOlympusCX21'])
def test_cell_preserves_official_key(patient: str) -> None:
    official = frozenset({patient})
    assert canonical_nlm_cell_patient_key(patient, official_patient_ids=official) == patient
    assert official == frozenset({patient})


@pytest.mark.parametrize('patient', ['', 'unknown', ' C101P62ThinF', 'c101p62thinf'])
def test_cell_rejects_nonofficial_keys(patient: str) -> None:
    with pytest.raises(ValueError, match='Unknown official'):
        canonical_nlm_cell_patient_key(patient, official_patient_ids={'C101P62ThinF'})


@pytest.mark.parametrize(('source', 'expected'), [
    ('234C92P53ThinF', 'C92P53ThinF'),
    ('146C47P8thin_Original_Motic', 'C47P8thin_Original_Motic'),
    ('148C47P8thinOriginalOlympusCX21', 'C47P8thinOriginalOlympusCX21'),
    ('152C51AP12thinF', 'C51AP12thinF'),
    ('352C167P128ReThinF', 'C167P128ReThinF'),
])
def test_full_key_and_compatibility_alias(source: str, expected: str) -> None:
    assert canonical_nlm_full_smear_patient_key(source) == expected
    assert canonical_nlm_full_smear_patient_key(source) == expected
    assert cell_images_candidate_identifier(source) == expected


@pytest.mark.parametrize('source', [
    '', '234garbage', 'C92P53ThinF', '234C92P53ThinF_extra',
    '234C92P53ThinF\n', ' 234C92P53ThinF', '234C92P53ThinF/Img',
    '２３４C92P53ThinF', '0234C92P53ThinF', '234C0P53ThinF',
    '234C92P53thinOriginalOlympusCX22', '234C92P53THINF',
])
def test_full_key_fails_closed(source: str) -> None:
    with pytest.raises(ValueError, match='Invalid NLM Full Smear'):
        canonical_nlm_full_smear_patient_key(source)


def test_all_real_s1_1_identifiers_and_polygon() -> None:
    with (ROOT / 'docs/audits/s1_1/full_smear_candidates.csv').open() as f:
        rows = list(csv.DictReader(f))
    keys = [canonical_nlm_full_smear_patient_key(r['full_patient_id']) for r in rows]
    assert len(keys) == len(set(keys)) == 193
    assert keys == [r['cell_candidate'] for r in rows]
    assert len({key for key, row in zip(keys, rows) if row['set'] == 'Polygon Set'}) == 33
    mapping, errors = load_official_patient_mapping([
        ROOT / 'docs/audits/s1_1' / f'official_{label}.csv'
        for label in ('parasitized', 'uninfected')
    ])
    assert not errors
    official = set().union(*mapping.values())
    assert len(official) == 201
    assert len(official & set(keys)) == 193
    assert not set(keys) - official
    assert len(official - set(keys)) == 8
