import hashlib
from pathlib import Path

from PIL import Image

from app.services.image_quality import _border_and_field, _entropy, _focus, _percentile, assess_image
from app.services.microscopy_analysis import manifest
from app.services.quality_profiles import select_profile, snapshot


class Storage:
    def __init__(self, path): self.path = path
    def resolve(self, *_args, **_kwargs): return self.path


def test_profile_selection_and_snapshot_are_versioned():
    assert select_profile("manual_upload", None)["profile_key"] == "manual_microscopy_v1"
    assert select_profile("research_dataset_import", "NIH-NLM")["profile_key"] == "nih_nlm_v1"
    assert select_profile("external_capture_system", "scope")["profile_key"] == "external_capture_v1"
    first = snapshot("manual_microscopy_v1")
    first["minimum_width"] = 999
    assert snapshot("manual_microscopy_v1")["minimum_width"] != 999


def test_scalar_metrics_are_deterministic():
    values = [0.0, 0.25, 0.5, 0.75, 1.0]
    assert _percentile(values, .5) == .5
    assert _entropy([0.0] * 10) == 0
    assert _focus([0.0] * 25, 5, 5) == (0.0, 0.0)
    border, usable = _border_and_field([0.0] * 16, 4, 4, .02)
    assert border == 1 and usable == 0


def test_manifest_is_order_independent():
    images = [
        {"id": "00000000-0000-4000-8000-000000000002", "sha256": "b"*64, "file_size_bytes": 2,
         "width_px": 2, "height_px": 2, "image_sequence_number": 2},
        {"id": "00000000-0000-4000-8000-000000000001", "sha256": "a"*64, "file_size_bytes": 1,
         "width_px": 1, "height_px": 1, "image_sequence_number": 1},
    ]
    assert manifest(images)[0] == manifest(list(reversed(images)))[0]


def test_uniform_image_fails_without_modifying_original(tmp_path: Path):
    path = tmp_path / "uniform.png"
    Image.new("RGB", (128, 128), (127, 127, 127)).save(path)
    before = path.read_bytes()
    image = {"storage_key": "unused", "file_size_bytes": path.stat().st_size,
             "sha256": hashlib.sha256(before).hexdigest(), "width_px": 128, "height_px": 128,
             "detected_format": "PNG"}
    result = assess_image(image, snapshot("manual_microscopy_v1"), Storage(path))
    assert result["quality_verdict"] == "fail"
    assert "LOW_ENTROPY" in result["failure_codes"]
    assert path.read_bytes() == before


def test_checksum_mismatch_fails(tmp_path: Path):
    path = tmp_path / "detail.png"
    Image.new("RGB", (128, 128), "white").save(path)
    image = {"storage_key": "unused", "file_size_bytes": path.stat().st_size, "sha256": "0"*64,
             "width_px": 128, "height_px": 128, "detected_format": "PNG"}
    result = assess_image(image, snapshot("manual_microscopy_v1"), Storage(path))
    assert result["quality_verdict"] == "fail"
    assert result["failure_codes"] == ["CHECKSUM_MISMATCH"]
