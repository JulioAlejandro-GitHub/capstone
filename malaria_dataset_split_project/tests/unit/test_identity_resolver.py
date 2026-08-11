import tempfile
import unittest
from pathlib import Path

from PIL import Image

from malaria_split.identity import EvidenceType, IdentityStatus, SourceIdentityRecord, decoded_pixel_key, resolve_one


class IdentityResolverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "cell.png"
        Image.new("RGB", (2, 2), (10, 20, 30)).save(self.path)
        self.key = decoded_pixel_key(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def source(self, patient="PAT-A", record="source.png", evidence=EvidenceType.OFFICIAL_METADATA):
        return SourceIdentityRecord(record, record, "parasitized", patient, evidence, "official.csv", self.key)

    def resolve(self, index):
        return resolve_one(
            tfds_index=0, physical_path=self.path, physical_relative_path="train/parasitized/one.png",
            historical_split="train", class_name="parasitized", label=1, source_index=index,
        )

    def test_verified_direct_mapping(self):
        result = self.resolve({self.key: [self.source()]})
        self.assertEqual(result.identity_status, IdentityStatus.VERIFIED)
        self.assertEqual(result.patient_id, "PAT-A")

    def test_no_match_is_unresolved(self):
        self.assertEqual(self.resolve({}).identity_status, IdentityStatus.UNRESOLVED)

    def test_ambiguous_source_mapping_is_conflict(self):
        result = self.resolve({self.key: [self.source(record="a.png"), self.source(record="b.png")]})
        self.assertEqual(result.identity_status, IdentityStatus.CONFLICT)

    def test_multiple_patient_mapping_is_conflict(self):
        result = self.resolve({self.key: [self.source("PAT-A"), self.source("PAT-B")]})
        self.assertEqual(result.identity_status, IdentityStatus.CONFLICT)

    def test_official_metadata_has_precedence(self):
        derived = self.source("DERIVED", evidence=EvidenceType.DECODED_PIXEL_HASH)
        official = self.source("OFFICIAL", evidence=EvidenceType.OFFICIAL_METADATA)
        result = self.resolve({self.key: [derived, official]})
        self.assertEqual(result.patient_id, "OFFICIAL")

    def test_filename_without_evidence_does_not_verify(self):
        record = self.source(None, record="PAT-A_cell.png", evidence=EvidenceType.NONE)
        result = self.resolve({self.key: [record]})
        self.assertNotEqual(result.identity_status, IdentityStatus.VERIFIED)

    def test_decoded_pixel_hash_unique_is_deterministic(self):
        self.assertEqual(decoded_pixel_key(self.path), decoded_pixel_key(self.path))
        self.assertEqual(self.resolve({self.key: [self.source()]}).mapping_method, "decoded_pixel_hash_to_official_metadata")


if __name__ == "__main__":
    unittest.main()

