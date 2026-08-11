import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from malaria_split import cli
from malaria_split.persistence.bootstrap import (
    BootstrapConflict,
    expected_methodology,
    is_sha256,
    verify_source_record_compatible,
    verify_version_methodology,
)


class ScientificBootstrapTests(TestCase):
    def test_dry_run_does_not_construct_database_engine(self):
        summary = {
            "total_records": 27558, "patient_verified": 27558,
            "patient_unresolved": 0, "patient_conflict": 0,
            "unique_patients_total": 201, "min_cells_per_patient": 65,
            "max_cells_per_patient": 702, "patients_only_parasitized": 0,
            "patients_only_uninfected": 50, "patients_with_both_classes": 151,
            "class_counts": {"parasitized": 13779, "uninfected": 13779},
        }
        row = {"source_record_key": "key"}
        prepared = SimpleNamespace(
            summary=summary, source_mapping_sha256={},
            records=(row,) * 27558, evidence=(row,) * 27558,
        )
        with patch.object(cli, "_bootstrap_paths", return_value=(None, None, [])), \
             patch.object(cli, "prepare_scientific_population", return_value=prepared), \
             patch.object(cli, "create_postgresql_engine") as engine:
            self.assertEqual(cli.bootstrap_malaria_v1(None, True), 0)
            engine.assert_not_called()

    def test_same_source_record_content_is_idempotent(self):
        identity = uuid4()
        row = {
            "clinical_identity_id": identity, "class_index": 0,
            "class_name": "uninfected", "source_file_sha256": "a" * 64,
            "decoded_pixel_sha256": "b" * 64,
        }
        verify_source_record_compatible(row, dict(row))

    def test_different_patient_is_conflict(self):
        row = {
            "clinical_identity_id": uuid4(), "class_index": 0,
            "class_name": "uninfected", "source_file_sha256": "a" * 64,
            "decoded_pixel_sha256": "b" * 64,
        }
        with self.assertRaises(BootstrapConflict):
            verify_source_record_compatible(row, {**row, "clinical_identity_id": uuid4()})

    def test_different_source_hash_is_conflict(self):
        row = {
            "clinical_identity_id": uuid4(), "class_index": 0,
            "class_name": "uninfected", "source_file_sha256": "a" * 64,
            "decoded_pixel_sha256": "b" * 64,
        }
        with self.assertRaises(BootstrapConflict):
            verify_source_record_compatible(row, {**row, "source_file_sha256": "c" * 64})

    def test_sha256_format_for_source_and_decoded_pixels(self):
        self.assertTrue(is_sha256("a" * 64))
        self.assertTrue(is_sha256("F" * 64))
        self.assertFalse(is_sha256("a" * 63))
        self.assertFalse(is_sha256("z" * 64))

    def test_same_v1_methodology_is_idempotent(self):
        methodology = expected_methodology()
        verify_version_methodology(methodology, json.loads(json.dumps(methodology)))

    def test_different_v1_methodology_is_conflict(self):
        methodology = expected_methodology()
        with self.assertRaises(BootstrapConflict):
            verify_version_methodology(methodology, {**methodology, "seed": 99})
