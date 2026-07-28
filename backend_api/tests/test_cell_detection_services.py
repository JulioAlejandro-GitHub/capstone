from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageOps

from app.main import app
from app.models.cell_detection import ComponentStatus
from app.security import Permission, ROLE_PERMISSIONS
from app.services.cell_analysis import CellAnalysisError, CellAnalysisService
from app.services.cell_crop_storage import CellCropStorage
from app.services.detectors.connected_components_v1 import (
    ALGORITHM_VERSION,
    DETECTOR_KEY,
    DETECTOR_VERSION,
    DetectorInputError,
    detect_image,
    detect_path,
    profile_snapshot,
)
from app.services.local_storage import LocalStorage, StorageError


GEOMETRY = {
    "blur_kernel": 1,
    "morphology_iterations": 0,
    "minimum_component_area_px": 10,
    "maximum_component_area_px": 10_000,
    "minimum_width_px": 2,
    "minimum_height_px": 2,
    "minimum_circularity": 0.01,
    "minimum_solidity": 0.01,
}


def circles(size: tuple[int, int], boxes: list[tuple[int, int, int, int]]) -> Image.Image:
    image = Image.new("L", size, 255)
    drawing = ImageDraw.Draw(image)
    for box in boxes:
        drawing.ellipse(box, fill=0)
    return image


def test_detector_profile_is_versioned_copied_and_semantically_fixed():
    snapshot = profile_snapshot()
    assert snapshot["detector_key"] == DETECTOR_KEY == "connected_components_v1"
    assert snapshot["detector_version"] == DETECTOR_VERSION == "1.0.0"
    assert snapshot["algorithm_version"] == ALGORITHM_VERSION
    assert snapshot["orientation_policy"] == "exif_transpose"
    assert snapshot["maximum_components_per_image"] == 500
    snapshot["minimum_width_px"] = 999
    assert profile_snapshot()["minimum_width_px"] != 999
    with pytest.raises(ValueError):
        profile_snapshot({"threshold_method": "manual"})
    with pytest.raises(ValueError):
        profile_snapshot({"coordinate_space": "resized_pixels"})
    with pytest.raises(ValueError):
        profile_snapshot({"orientation_policy": "ignore_exif"})


def test_isolated_circle_creates_bounded_candidate_and_matching_crop():
    source = circles((80, 80), [(20, 20, 40, 40)])
    before = source.tobytes()
    result = detect_image(source, GEOMETRY)
    assert source.tobytes() == before
    assert len(result.components) == len(result.crops) == 1
    component = result.components[0]
    crop = result.crops[0]
    assert component.component_status == ComponentStatus.ACCEPTED
    assert component.bbox.is_within(80, 80)
    assert crop.bbox.is_within(80, 80)
    with Image.open(__import__("io").BytesIO(crop.png_bytes)) as crop_image:
        assert crop_image.mode == "L"
        expected = ImageOps.exif_transpose(source).crop(
            (crop.bbox.x, crop.bbox.y, crop.bbox.right, crop.bbox.bottom)
        )
        assert crop_image.size == expected.size
        assert crop_image.tobytes() == expected.tobytes()


def test_multiple_components_have_stable_raster_order():
    source = circles((100, 80), [(60, 45, 75, 60), (10, 10, 25, 25), (60, 10, 75, 25)])
    first = detect_image(source, GEOMETRY)
    second = detect_image(source, GEOMETRY)
    boxes = [(item.bbox.x, item.bbox.y) for item in first.components]
    assert boxes == [(10, 10), (60, 10), (60, 45)]
    assert first.components == second.components
    assert [item.component_index for item in first.components] == [1, 2, 3]


def test_touching_circles_remain_one_documented_connected_component():
    source = circles((80, 60), [(15, 15, 40, 40), (35, 15, 60, 40)])
    result = detect_image(source, GEOMETRY)
    assert len(result.components) == 1
    assert result.components[0].bbox.x == 15
    assert result.components[0].bbox.right == 61


def test_tiny_large_and_border_components_are_persistable_rejections():
    source = circles(
        (100, 100),
        [(20, 20, 22, 22), (45, 45, 75, 75), (-6, 65, 10, 82)],
    )
    result = detect_image(
        source,
        {
            **GEOMETRY,
            "minimum_component_area_px": 20,
            "maximum_component_area_px": 300,
        },
    )
    codes = {component.rejection_code for component in result.components}
    assert "COMPONENT_AREA_BELOW_MINIMUM" in codes
    assert "COMPONENT_AREA_ABOVE_MAXIMUM" in codes
    assert "BORDER_COMPONENT" in codes
    assert all(
        component.component_status == ComponentStatus.REJECTED_BY_FILTER
        for component in result.components
    )
    assert not result.crops


def test_empty_image_has_no_components_and_explicit_warning():
    result = detect_image(Image.new("RGB", (64, 64), "white"), GEOMETRY)
    assert result.threshold_value is None
    assert result.components == ()
    assert result.crops == ()
    assert result.warnings == ("NO_ACCEPTED_COMPONENTS",)


def test_hundreds_of_components_are_deterministic_and_capped():
    source = Image.new("L", (180, 180), 255)
    drawing = ImageDraw.Draw(source)
    for row in range(20):
        for column in range(20):
            x, y = 5 + column * 8, 5 + row * 8
            drawing.rectangle((x, y, x + 3, y + 3), fill=0)
    profile = {
        **GEOMETRY,
        "minimum_component_area_px": 4,
        "minimum_width_px": 2,
        "minimum_height_px": 2,
        "maximum_components_per_image": 500,
    }
    result = detect_image(source, profile)
    assert len(result.components) == len(result.crops) == 400
    capped = detect_image(source, {**profile, "maximum_components_per_image": 250})
    assert len(capped.components) == 400
    assert len(capped.crops) == 250
    assert capped.warnings == ("MAXIMUM_COMPONENTS_REACHED",)
    assert sum(
        item.rejection_code == "MAXIMUM_COMPONENTS_EXCEEDED"
        for item in capped.components
    ) == 150


def test_corrupt_and_checksum_modified_inputs_fail_safely(tmp_path: Path):
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(b"not-an-image")
    digest = hashlib.sha256(corrupt.read_bytes()).hexdigest()
    with pytest.raises(DetectorInputError) as corrupt_error:
        detect_path(
            corrupt,
            expected_sha256=digest,
            expected_width_px=10,
            expected_height_px=10,
            expected_file_size_bytes=corrupt.stat().st_size,
            profile=GEOMETRY,
        )
    assert corrupt_error.value.code == "SOURCE_DECODE_FAILED"

    valid = tmp_path / "valid.png"
    circles((40, 40), [(10, 10, 25, 25)]).save(valid)
    original = valid.read_bytes()
    modified = bytearray(original)
    modified[-1] ^= 1
    valid.write_bytes(modified)
    with pytest.raises(DetectorInputError) as checksum_error:
        detect_path(
            valid,
            expected_sha256=hashlib.sha256(original).hexdigest(),
            expected_width_px=40,
            expected_height_px=40,
            expected_file_size_bytes=len(original),
            profile=GEOMETRY,
        )
    assert checksum_error.value.code == "CHECKSUM_MISMATCH"


@pytest.mark.parametrize("orientation", [6, 8])
def test_exif_orientation_is_applied_without_resampling(tmp_path: Path, orientation: int):
    source = Image.new("RGB", (60, 40), "white")
    ImageDraw.Draw(source).ellipse((10, 10, 28, 28), fill="black")
    exif = source.getexif()
    exif[274] = orientation
    path = tmp_path / f"oriented-{orientation}.jpg"
    source.save(path, format="JPEG", quality=100, exif=exif)
    payload = path.read_bytes()
    result = detect_path(
        path,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        expected_width_px=60,
        expected_height_px=40,
        expected_file_size_bytes=len(payload),
        profile=GEOMETRY,
    )
    assert (result.raw_width_px, result.raw_height_px) == (60, 40)
    assert (result.oriented_width_px, result.oriented_height_px) == (40, 60)
    assert all(
        component.bbox.is_within(
            result.oriented_width_px, result.oriented_height_px
        )
        for component in result.components
    )


def _storage(tmp_path: Path) -> CellCropStorage:
    settings = SimpleNamespace(
        storage_provider="local",
        storage_root=tmp_path / "storage",
        max_upload_size_bytes=10_000_000,
        upload_chunk_size_bytes=1024,
    )
    return CellCropStorage(LocalStorage(settings))


def test_crop_storage_stages_validates_promotes_and_hashes(tmp_path: Path):
    storage = _storage(tmp_path)
    image = Image.new("L", (12, 10), 17)
    output = __import__("io").BytesIO()
    image.save(output, format="PNG")
    values = [uuid4() for _ in range(4)]
    staged = storage.stage(
        analysis_run_id=values[0],
        detection_run_id=values[1],
        microscopy_image_id=values[2],
        cell_detection_id=values[3],
        png_bytes=output.getvalue(),
        expected_width_px=12,
        expected_height_px=10,
        padding_px=4,
    )
    assert staged.sha256 == hashlib.sha256(output.getvalue()).hexdigest()
    assert staged.relative_storage_key == (
        f"cell-crops/{values[0]}/{values[1]}/{values[2]}/{values[3]}/crop.png"
    )
    final = storage.promote(staged)
    assert final.read_bytes() == output.getvalue()
    assert not staged.path.exists()
    storage.cleanup([final])
    assert not final.exists()


def test_crop_storage_rejects_substituted_symlink_and_cleanup_unlinks_it(tmp_path: Path):
    storage = _storage(tmp_path)
    image = Image.new("RGB", (8, 8), "red")
    output = __import__("io").BytesIO()
    image.save(output, format="PNG")
    ids = [uuid4() for _ in range(4)]
    staged = storage.stage(
        analysis_run_id=ids[0],
        detection_run_id=ids[1],
        microscopy_image_id=ids[2],
        cell_detection_id=ids[3],
        png_bytes=output.getvalue(),
        expected_width_px=8,
        expected_height_px=8,
        padding_px=1,
    )
    outside = tmp_path / "outside.png"
    outside.write_bytes(output.getvalue())
    staged.path.unlink()
    staged.path.symlink_to(outside)
    with pytest.raises(StorageError):
        storage.promote(staged)
    storage.cleanup([staged.path])
    assert not staged.path.exists()
    assert outside.exists()


def test_crop_storage_rejects_symlinked_staging_parent(tmp_path: Path):
    root = tmp_path / "storage"
    outside = tmp_path / "outside-staging"
    root.mkdir()
    outside.mkdir()
    (root / ".staging").symlink_to(outside, target_is_directory=True)
    settings = SimpleNamespace(
        storage_provider="local",
        storage_root=root,
        max_upload_size_bytes=10_000_000,
        upload_chunk_size_bytes=1024,
    )
    with pytest.raises(StorageError):
        LocalStorage(settings)
    assert not (outside / "cell-detection").exists()


def test_crop_resolve_rejects_traversal(tmp_path: Path):
    storage = _storage(tmp_path)
    with pytest.raises(StorageError):
        storage.resolve("../outside.png")
    with pytest.raises(StorageError):
        storage.resolve("/absolute/crop.png")


def test_review_validation_and_rbac_contract():
    service = CellAnalysisService(engine=object())
    with pytest.raises(CellAnalysisError) as rejected:
        service.create_review(
            cell_detection_id=str(uuid4()),
            decision="rejected",
            comment=" ",
            principal=SimpleNamespace(user_id=str(uuid4())),
            request=SimpleNamespace(),
        )
    assert rejected.value.code == "REVIEW_COMMENT_REQUIRED"

    read = Permission.SCIENTIFIC_CELL_DETECTION_READ
    execute = Permission.SCIENTIFIC_CELL_DETECTION_EXECUTE
    review = Permission.SCIENTIFIC_CELL_DETECTION_REVIEW
    for role in ROLE_PERMISSIONS:
        assert read in ROLE_PERMISSIONS[role]
    assert execute in ROLE_PERMISSIONS["administrator"]
    assert execute in ROLE_PERMISSIONS["researcher"]
    assert execute in ROLE_PERMISSIONS["operator"]
    assert execute not in ROLE_PERMISSIONS["reviewer"]
    assert review in ROLE_PERMISSIONS["administrator"]
    assert review in ROLE_PERMISSIONS["researcher"]
    assert review in ROLE_PERMISSIONS["reviewer"]
    assert review not in ROLE_PERMISSIONS["operator"]
    assert {execute, review}.isdisjoint(ROLE_PERMISSIONS["read_only"])


def test_crop_and_original_content_endpoints_require_authentication():
    client = TestClient(app, raise_server_exceptions=False)
    crop = client.get(f"/api/v1/cell-analysis/crops/{uuid4()}/content")
    original = client.get(
        f"/api/v1/cell-analysis/detection-runs/{uuid4()}/images/{uuid4()}/content"
    )
    assert crop.status_code == 401
    assert original.status_code == 401


def test_migration_declares_six_tables_composite_links_and_append_only_guards():
    project_root = Path(__file__).resolve().parents[2]
    source = (
        project_root
        / "alembic/versions/20260727_05_cell_detection_and_review.py"
    ).read_text(encoding="utf-8")
    for table in (
        "cell_detection_runs",
        "image_connected_components",
        "cell_detections",
        "cell_crops",
        "cell_detection_events",
        "scientific_reviews",
    ):
        assert f"CREATE TABLE {table}" in source
    assert "uq_cell_detection_runs_equivalent_active" in source
    assert "fk_components_frozen_image" in source
    assert "fk_cell_detections_component" in source
    assert "trg_scientific_reviews_append_only" in source
    assert "trg_cell_detection_events_append_only" in source
    assert "terminal cell_detection_runs are immutable" in source
    assert "relative_storage_key ~" in source
