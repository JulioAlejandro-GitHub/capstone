import hashlib
import shutil

import pytest
from PIL import Image

from malaria_split.persistence.smear_source_ingest import prepare_smear_rows
from malaria_split.sources.thin_blood_smears_pf import (
    cell_images_candidate_identifier,
    inspect_thin_blood_smears_pf,
)
from tests.smear_fixtures import HEIGHT, WIDTH, build_tree, write_smear


def _codes(inspection):
    return sorted(issue.code for issue in inspection.issues)


def test_discovers_patients_images_and_annotations(tmp_path):
    inspection = inspect_thin_blood_smears_pf(build_tree(tmp_path))
    report = inspection.report()
    assert inspection.contract_passed and report["contract_status"] == "PASS"
    assert inspection.patients == ("201C1P1ThinF", "202C2NThinF")
    assert (report["patients_found"], report["images_found"], report["annotations_found"]) == (
        2, 5, 5
    )
    assert report["ignored_files"] == 2  # Thumbs.db never becomes a record
    assert report["polygons"] == {
        "total": 15, "rbc": 10, "wbc": 5,
        "by_label": {"Parasitized": 5, "Uninfected": 5, "White_Blood_Cell": 5},
    }
    assert report["dataset_family"] == "smear_segmentation"


def test_records_pair_image_with_gt_using_relative_paths(tmp_path):
    inspection = inspect_thin_blood_smears_pf(build_tree(tmp_path))
    record = inspection.records[0]
    assert record.image_relative_path == "Polygon Set/201C1P1ThinF/Img/IMG_00.jpg"
    assert record.annotation_relative_path == "Polygon Set/201C1P1ThinF/GT/IMG_00.txt"
    assert record.source_record_key == (
        "nih_nlm_thin_blood_smears_pf:polygon_set/201C1P1ThinF/IMG_00.jpg"
    )
    image_bytes = (tmp_path / record.image_relative_path).read_bytes()
    gt_bytes = (tmp_path / record.annotation_relative_path).read_bytes()
    assert record.image_sha256 == hashlib.sha256(image_bytes).hexdigest()
    assert record.annotation_sha256 == hashlib.sha256(gt_bytes).hexdigest()
    assert (record.image_width, record.image_height) == (WIDTH, HEIGHT)
    assert record.image_size_bytes == len(image_bytes)
    assert not any(str(tmp_path) in path for item in inspection.records
                   for path in (item.image_relative_path, item.annotation_relative_path))


def test_same_patient_shares_identity_and_different_patients_do_not(tmp_path):
    rows = prepare_smear_rows(inspect_thin_blood_smears_pf(build_tree(tmp_path)))
    by_patient = {}
    for record in rows["records"]:
        patient = record["source_record_key"].split("/")[1]
        by_patient.setdefault(patient, set()).add(record["clinical_identity_id"])
    assert {patient: len(ids) for patient, ids in by_patient.items()} == {
        "201C1P1ThinF": 1, "202C2NThinF": 1
    }
    assert by_patient["201C1P1ThinF"] != by_patient["202C2NThinF"]
    assert len(rows["identities"]) == 2
    assert {row["evidence_type"] for row in rows["evidence"]} == {"OFFICIAL_DIRECTORY_CONVENTION"}


def test_representation_is_reproducible_and_independent_of_root_location(tmp_path):
    first_root = build_tree(tmp_path / "a")
    second_root = tmp_path / "elsewhere" / "copy"
    shutil.copytree(first_root, second_root)
    first = inspect_thin_blood_smears_pf(first_root)
    again = inspect_thin_blood_smears_pf(first_root)
    moved = inspect_thin_blood_smears_pf(second_root)
    assert first.population_fingerprint == again.population_fingerprint
    assert first.population_fingerprint == moved.population_fingerprint
    assert prepare_smear_rows(first) == prepare_smear_rows(moved)


def test_missing_and_orphan_annotations_fail_contract(tmp_path):
    root = build_tree(tmp_path)
    (root / "Polygon Set/201C1P1ThinF/GT/IMG_00.txt").unlink()
    (root / "Polygon Set/202C2NThinF/GT/IMG_99.txt").write_text("0,64,48", encoding="utf-8")
    inspection = inspect_thin_blood_smears_pf(root)
    report = inspection.report()
    assert not inspection.contract_passed
    assert report["images_without_annotation"] == 1
    assert report["annotations_without_image"] == 1
    assert report["valid_source_records"] == 4


def test_invalid_annotation_is_reported_not_persisted(tmp_path):
    root = build_tree(tmp_path)
    (root / "Polygon Set/202C2NThinF/GT/IMG_01.txt").write_text(
        "1,64,48\n1-1,Uninfected,No_comment,Polygon,3,1,1,99,1,5,5", encoding="utf-8"
    )
    inspection = inspect_thin_blood_smears_pf(root)
    assert _codes(inspection) == ["INVALID_ANNOTATION"]
    assert "COORDINATE_OUT_OF_BOUNDS" in inspection.issues[0].detail
    assert len(inspection.records) == 4


def test_duplicate_images_are_detected(tmp_path):
    root = build_tree(tmp_path)
    shutil.copy(root / "Polygon Set/201C1P1ThinF/Img/IMG_00.jpg",
                root / "Polygon Set/202C2NThinF/Img/IMG_01.jpg")
    report = inspect_thin_blood_smears_pf(root).report()
    assert report["duplicate_images"] == 1 and report["contract_status"] == "FAIL"


def test_ambiguous_image_gt_association(tmp_path):
    root = build_tree(tmp_path)
    shutil.copy(root / "Polygon Set/201C1P1ThinF/Img/IMG_00.jpg",
                root / "Polygon Set/201C1P1ThinF/Img/IMG_00.jpeg")
    report = inspect_thin_blood_smears_pf(root).report()
    assert report["ambiguous_associations"] == 1 and report["contract_status"] == "FAIL"


def test_case_insensitive_patient_collision_is_ambiguous(tmp_path):
    root = build_tree(tmp_path, {"201C1P1ThinF": 1, "201c1p1thinf": 1})
    if len(list((root / "Polygon Set").iterdir())) < 2:
        pytest.skip("case-insensitive filesystem cannot represent the collision")
    assert inspect_thin_blood_smears_pf(root).report()["ambiguous_patient_ids"] == 2


def test_structure_and_unexpected_files(tmp_path):
    root = build_tree(tmp_path)
    (root / "Polygon Set/notes.csv").write_text("x", encoding="utf-8")
    shutil.rmtree(root / "Polygon Set/202C2NThinF/GT")
    report = inspect_thin_blood_smears_pf(root).report()
    assert report["unexpected_files"] == 1 and report["structure_issues"] == 1
    assert inspect_thin_blood_smears_pf(tmp_path / "nowhere").report()["structure_issues"] == 1


def test_exif_rotation_blocks_ambiguous_coordinates(tmp_path):
    root = build_tree(tmp_path)
    path = root / "Polygon Set/201C1P1ThinF/Img/IMG_01.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (WIDTH, HEIGHT), (1, 2, 3)).save(path, exif=exif)
    assert _codes(inspect_thin_blood_smears_pf(root)) == ["EXIF_ORIENTATION_PRESENT"]


def test_lowercase_img_directory_from_readme_is_accepted(tmp_path):
    write_smear(tmp_path, "203C3P2ThinF", "IMG_00", seed=50, image_dir="img")
    assert inspect_thin_blood_smears_pf(tmp_path).contract_passed


def test_cross_source_hint_is_only_a_prefix_strip():
    assert cell_images_candidate_identifier("228C86P47ThinF") == "C86P47ThinF"
    assert cell_images_candidate_identifier("212C71P32_ThinF") == "C71P32_ThinF"
