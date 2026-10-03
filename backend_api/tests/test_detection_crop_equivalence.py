"""Golden results captured before D1/D2 from dfc96215968b25794f98fb69e8f7e462a9827e13."""
from __future__ import annotations

import hashlib
import io
import json
from dataclasses import asdict
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageOps

from app.models.cell_detection import ImageDetectionResult
from app.services.detectors.connected_components_v1 import profile_snapshot
from app.services.cell_detection import detect_image

GOLDEN = Path(__file__).parent / "fixtures/detection_crop/connected_components_v1.json"
CASES = ["default", "empty", "rejections", "cap", "padding", "L", "RGBA", "P", "exif_2", "exif_6", "exif_8"]


def source_case(name: str) -> tuple[Image.Image, dict]:
    source = Image.new("RGB", (100, 80), "white")
    draw = ImageDraw.Draw(source)
    if name != "empty":
        for box in [(12, 12, 30, 30), (60, 45, 80, 65), (0, 40, 10, 55), (45, 12, 46, 13)]:
            draw.ellipse(box, fill=(15, 25, 35))
    overrides = {}
    if name == "rejections":
        overrides = {"maximum_component_area_px": 200}
    if name == "cap":
        overrides = {"maximum_components_per_image": 1}
    if name == "padding":
        overrides = {"reject_border_components": False, "crop_padding_px": 9}
    if name in {"L", "RGBA", "P"}:
        source = source.convert(name)
    if name.startswith("exif_"):
        exif = source.getexif()
        exif[274] = int(name.split("_")[1])
        output = io.BytesIO()
        source.save(output, format="JPEG", quality=95, exif=exif)
        source = Image.open(io.BytesIO(output.getvalue()))
        source.load()
    return source, overrides


def snapshot(result: ImageDetectionResult) -> dict:
    value = asdict(result)
    for crop in value["crops"]:
        payload = crop.pop("png_bytes")
        crop["sha256"] = hashlib.sha256(payload).hexdigest()
        with Image.open(io.BytesIO(payload)) as image:
            crop["pixel_sha256"] = hashlib.sha256(image.tobytes()).hexdigest()
            crop["mode"] = image.mode
            crop["format"] = image.format
    return json.loads(json.dumps(value))


@pytest.mark.parametrize("name", CASES)
def test_detection_and_crop_match_pre_refactor_golden(name: str) -> None:
    golden = json.loads(GOLDEN.read_text())
    source, overrides = source_case(name)
    result = detect_image(source, overrides)
    assert profile_snapshot() == golden["profile_snapshot"]
    assert snapshot(result) == golden["cases"][name]
    accepted = [c.component_index for c in result.components if c.component_status == "accepted"]
    assert [c.component_index for c in result.crops] == accepted
    for crop in result.crops:
        with Image.open(io.BytesIO(crop.png_bytes)) as actual:
            oriented = ImageOps.exif_transpose(source)
            box = crop.bbox
            expected = oriented.crop((box.x, box.y, box.right, box.bottom))
            assert actual.tobytes() == expected.tobytes()
            assert actual.size == expected.size



def test_resolvers_are_deterministic_and_profiles_are_independent() -> None:
    from app.config import Settings
    from app.services.cell_analysis import CellAnalysisService
    from app.services.detectors.resolver import resolve_detector
    from app.services.crops.resolver import resolve_crop_strategy

    settings = Settings.from_env()
    service = CellAnalysisService(engine=object())
    detector = resolve_detector()
    assert service.detector == detector == resolve_detector(settings.cell_detector_key)
    assert detector.key == "connected_components_v1"
    assert service.crop_strategy == resolve_crop_strategy(settings.cell_crop_strategy_key)
    assert service.crop_strategy.key == "bbox_crop_v1"
    changed = detector.profile_snapshot(None)
    changed["crop_padding_px"] = 99
    assert resolve_detector().profile_snapshot(None)["crop_padding_px"] == 4
    assert detector == resolve_detector()


@pytest.mark.parametrize("key", ["yolo_seg", "faster_rcnn", "u_net", "", "unknown"])
def test_unimplemented_detectors_are_rejected(key: str) -> None:
    from app.services.detectors.resolver import resolve_detector

    with pytest.raises(ValueError, match="Unsupported cell detector"):
        resolve_detector(key)


@pytest.mark.parametrize("key", ["segmented_crop", "masked_crop", "", "unknown"])
def test_unimplemented_crops_are_rejected(key: str) -> None:
    from app.services.crops.resolver import resolve_crop_strategy

    with pytest.raises(ValueError, match="Unsupported cell crop strategy"):
        resolve_crop_strategy(key)


def test_detection_needs_no_png_encoder_and_crop_is_separate(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.cell_detection import DetectionResult
    from app.services.detectors.resolver import resolve_detector
    from app.services.crops.resolver import resolve_crop_strategy

    source, profile = source_case("default")

    def unavailable_encoder(*args: object, **kwargs: object) -> None:
        raise RuntimeError("PNG encoder unavailable")

    monkeypatch.setattr(Image.Image, "save", unavailable_encoder)
    result = resolve_detector().detect_image(source, profile)
    assert type(result) is DetectionResult
    assert result.components
    assert not hasattr(result, "crops")
    with pytest.raises(RuntimeError, match="PNG encoder unavailable"):
        resolve_crop_strategy().crop_image(source, result.components, 4)


def test_unsupported_crop_mode_does_not_block_detection() -> None:
    from app.models.cell_detection import DetectorInputError
    from app.services.detectors.resolver import resolve_detector
    from app.services.crops.resolver import resolve_crop_strategy

    source, profile = source_case("default")
    source = source.convert("CMYK")
    result = resolve_detector().detect_image(source, profile)
    assert any(c.component_status == "accepted" for c in result.components)
    with pytest.raises(DetectorInputError) as error:
        resolve_crop_strategy().crop_image(source, result.components, 4)
    assert error.value.code == "UNSUPPORTED_CROP_MODE"
    empty = Image.new("CMYK", (20, 20), (0, 0, 0, 0))
    assert detect_image(empty).crops == ()


def test_orchestration_uses_explicit_resolved_stages_and_profile() -> None:
    from dataclasses import replace
    from app.models.cell_detection import CellCrop, ConnectedComponent, DetectionResult
    from app.services.detectors.resolver import resolve_detector
    from app.services.crops.resolver import resolve_crop_strategy

    detector = resolve_detector()
    strategy = resolve_crop_strategy()
    calls: list[str] = []
    source, _ = source_case("exif_6")
    selected = detector.profile_snapshot({"crop_padding_px": 9})

    def detect(image: Image.Image, profile: dict | None) -> DetectionResult:
        calls.append("detection")
        assert profile == selected
        return detector.detect_image(image, profile)

    def crop(image: Image.Image, components: tuple[ConnectedComponent, ...], padding: int) -> tuple[CellCrop, ...]:
        calls.append("crop")
        assert image.size == (80, 100)
        assert padding == 9
        return strategy.crop_image(image, components, padding)

    result = detect_image(source, selected, detector=replace(detector, detect_image=detect),
                          crop_strategy=replace(strategy, crop_image=crop))
    assert calls == ["detection", "crop"]
    assert result.crops
    assert all(c.padding_px == 9 for c in result.crops)


def test_service_resolves_backend_configuration_without_silent_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import Settings
    from app.services import cell_analysis

    monkeypatch.setenv("CELL_DETECTOR_KEY", "yolo_seg")
    monkeypatch.setenv("CELL_CROP_STRATEGY_KEY", "bbox_crop_v1")
    monkeypatch.setattr(cell_analysis, "get_settings", Settings.from_env)
    with pytest.raises(ValueError, match="Unsupported cell detector: yolo_seg"):
        cell_analysis.CellAnalysisService(engine=object())
    service = cell_analysis.CellAnalysisService(engine=object(), detector_key="connected_components_v1")
    assert service.detector.key == "connected_components_v1"
    monkeypatch.setenv("CELL_DETECTOR_KEY", "connected_components_v1")
    monkeypatch.setenv("CELL_CROP_STRATEGY_KEY", "masked_crop")
    with pytest.raises(ValueError, match="Unsupported cell crop strategy: masked_crop"):
        cell_analysis.CellAnalysisService(engine=object())
