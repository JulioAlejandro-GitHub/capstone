import unittest

from malaria_split.identity import EvidenceType, IdentityStatus, ResolvedClinicalIdentity, analyze_identities


def identity(patient, split, class_name="parasitized", status=IdentityStatus.VERIFIED):
    return ResolvedClinicalIdentity(
        0, f"{split}/{class_name}/x.png", split, class_name, 1, "source", "x.png",
        patient, None, None, None, status, EvidenceType.OFFICIAL_METADATA,
        "official.csv", "test", 1,
    )


class LeakageAnalysisTests(unittest.TestCase):
    def test_controlled_overlap(self):
        result = analyze_identities([
            identity("PAT-A", "train"), identity("PAT-A", "val"),
            identity("PAT-B", "train"), identity("PAT-C", "test"),
        ])
        self.assertEqual(result["train_val_patient_overlap"], 1)
        self.assertEqual(result["train_test_patient_overlap"], 0)
        self.assertEqual(result["val_test_patient_overlap"], 0)

    def test_patient_in_all_three_splits(self):
        result = analyze_identities([identity("PAT-A", split) for split in ("train", "val", "test")])
        self.assertEqual(result["patients_in_all_three_splits"], 1)

    def test_coverage_is_eighty_percent(self):
        records = [identity(f"PAT-{i}", "train") for i in range(8)]
        records += [identity(None, "train", status=IdentityStatus.UNRESOLVED)]
        records += [identity(None, "train", status=IdentityStatus.CONFLICT)]
        self.assertEqual(analyze_identities(records)["patient_id_coverage_percent"], 80.0)

    def test_patient_distribution(self):
        result = analyze_identities([
            identity("PAT-A", "train", "parasitized"),
            identity("PAT-A", "val", "uninfected"),
        ])
        patient = result["patients"]["PAT-A"]
        self.assertEqual(patient["total_cells"], 2)
        self.assertEqual(patient["parasitized_cells"], 1)
        self.assertEqual(patient["uninfected_cells"], 1)
        self.assertEqual(patient["splits_present"], ["train", "val"])


if __name__ == "__main__":
    unittest.main()
