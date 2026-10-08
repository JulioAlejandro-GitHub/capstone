from __future__ import annotations

import io
import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict

import httpx
import pytest
from PIL import Image, ImageOps

from app.config import Settings, validate_yolo_runtime_url
from app.models.cell_detection import ComponentStatus
from app.services.cell_detection import detect_image as detect_and_crop
from app.services.detectors import yolo26_seg_v1 as yolo
from app.services.detectors.resolver import Detector

TOKEN = "test-yolo-token-" * 3


def payload() -> dict:
    return {
        "detector_key": "yolo26_seg_v1", "detector_version": "1.0.0",
        "algorithm_version": "yolo26-seg-tiling-global-nms-1.0.0", "runtime_version": "1.0.0",
        "model_checkpoint": "/host/" + yolo.MODEL_CHECKPOINT,
        "checkpoint_sha256": yolo.CHECKPOINT_SHA256, "device": "mps",
        "image_width": 80, "image_height": 100, "tile_size": 1024, "tile_overlap": 256,
        "coordinate_space": "original_image_pixels", "orientation_policy": "exif_transpose",
        "bbox_format": "xywh", "options": {"confidence": .25, "nms_iou": .7, "max_detections_per_tile": 1000},
        "detections": [{"bbox": {"x": 10, "y": 20, "width": 15, "height": 20},
                        "confidence": .9, "centroid_x": 17.5, "centroid_y": 30.0, "area_px": 299.4,
                        "geometry_source": "mask_polygon", "mask_polygon": [[10.015, 20.], [24.985, 20.], [24.985, 40.], [10.015, 40.]],
                        "tile_id": "image__x0000_y0000"}],
        "raw_detection_count": 2, "invalid_detection_count": 0,
        "consolidated_detection_count": 1, "final_detection_count": 1, "warnings": [],
    }


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> Callable:
    monkeypatch.setenv("YOLO_RUNTIME_TOKEN", TOKEN)
    monkeypatch.setenv("YOLO_RUNTIME_URL", "http://host.docker.internal:8765")
    monkeypatch.setenv("YOLO_RUNTIME_TIMEOUT_SECONDS", "12")
    monkeypatch.setattr(yolo, "get_settings", Settings.from_env)
    real_client = httpx.Client

    def install(handler: Callable[[httpx.Request], httpx.Response]) -> list[httpx.Request]:
        requests: list[httpx.Request] = []

        def capture(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return handler(request)

        def client(**kwargs: object) -> httpx.Client:
            assert kwargs == {"timeout": 12., "follow_redirects": False, "trust_env": False}
            return real_client(transport=httpx.MockTransport(capture), **kwargs)

        monkeypatch.setattr(yolo.httpx, "Client", client)
        return requests
    return install


def detector() -> Detector:
    return Detector(yolo.DETECTOR_KEY, yolo.DETECTOR_VERSION, yolo.ALGORITHM_VERSION,
                    yolo.profile_snapshot, yolo.detect_image)


def source() -> Image.Image:
    image = Image.new("RGB", (100, 80), (11, 22, 33))
    image.getexif()[274] = 6
    return image


def test_auth_exif_conversion_and_original_crop_pixels(transport: Callable) -> None:
    requests = transport(lambda request: httpx.Response(200, json=payload()))
    original = source()
    result = detect_and_crop(original, detector=detector())
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/detect"
    assert request.url.host == "host.docker.internal"
    assert dict(request.url.params) == {"confidence": "0.25", "nms_iou": "0.7", "max_detections_per_tile": "1000"}
    assert request.headers["authorization"] == "Bearer " + TOKEN
    assert request.headers["content-type"] == "application/octet-stream"
    with Image.open(io.BytesIO(request.content)) as sent:
        assert sent.size == (80, 100)
        assert sent.mode == "RGB"
        assert not sent.getexif()
        assert sent.tobytes() == ImageOps.exif_transpose(original).tobytes()
    component = result.components[0]
    assert component.component_status == ComponentStatus.ACCEPTED
    assert component.component_index == 1
    assert component.detector_score == .9
    assert component.area_px == 300
    assert component.centroid_x == 17.5
    assert (component.perimeter_px, component.circularity, component.solidity) == (None, None, None)
    assert component.rejection_codes == ()
    assert result.threshold_value is None
    assert (result.raw_width_px, result.raw_height_px) == (100, 80)
    assert (result.oriented_width_px, result.oriented_height_px) == (80, 100)
    assert len(result.crops) == 1
    crop = result.crops[0]
    with Image.open(io.BytesIO(crop.png_bytes)) as image:
        assert image.tobytes() == ImageOps.exif_transpose(original).crop((6, 16, 29, 44)).tobytes()
    assert "YOLO_GEOMETRIC_METRICS_UNAVAILABLE" in result.warnings
    # Existing persistence JSON consumers can serialize missing metrics without NaN.
    json.dumps(asdict(component), allow_nan=False)


def test_empty_result(transport: Callable) -> None:
    data = payload()
    data.update(detections=[], raw_detection_count=0, final_detection_count=0,
                consolidated_detection_count=0, warnings=["NO_DETECTIONS"])
    transport(lambda request: httpx.Response(200, json=data))
    result = detect_and_crop(source(), detector=detector())
    assert result.components == result.crops == ()
    assert "NO_ACCEPTED_COMPONENTS" in result.warnings


def test_bbox_fallback_metrics_are_missing_not_fabricated(transport: Callable) -> None:
    data = payload()
    data["detections"][0].update(area_px=300., geometry_source="bbox", mask_polygon=None)
    data["warnings"] = ["MASK_UNAVAILABLE_BBOX_GEOMETRY"]
    transport(lambda request: httpx.Response(200, json=data))
    result = yolo.detect_image(source())
    assert result.components[0].solidity is None
    assert "MASK_UNAVAILABLE_BBOX_GEOMETRY" in result.warnings


def test_order_cap_and_border(transport: Callable) -> None:
    data = payload()
    other = deepcopy(data["detections"][0])
    other.update(bbox={"x": 0, "y": 0, "width": 10, "height": 10}, confidence=.8,
                 centroid_x=5., centroid_y=5., area_px=100., geometry_source="bbox", mask_polygon=None)
    data.update(detections=[other, data["detections"][0]], final_detection_count=2, raw_detection_count=3,
                warnings=["MASK_UNAVAILABLE_BBOX_GEOMETRY"])
    transport(lambda request: httpx.Response(200, json=data))
    first = detect_and_crop(source(), {"maximum_components_per_image": 1}, detector=detector())
    data["detections"].reverse()
    second = detect_and_crop(source(), {"maximum_components_per_image": 1}, detector=detector())
    assert first == second
    assert [c.component_index for c in first.components] == [1, 2]
    assert first.components[1].touches_border
    assert first.components[1].component_status == ComponentStatus.REJECTED_BY_FILTER
    assert first.components[1].rejection_code == "MAXIMUM_COMPONENTS_EXCEEDED"
    assert len(first.crops) == 1
    assert "MAXIMUM_COMPONENTS_REACHED" in first.warnings


@pytest.mark.parametrize("status", [301, 302, 401, 413, 422, 500, 503])
def test_http_errors_never_fallback_or_follow_redirects(transport: Callable, status: int) -> None:
    requests = transport(lambda request: httpx.Response(status, text=TOKEN,
                                                        headers={"Location": "https://untrusted.example"}))
    with pytest.raises(yolo.YoloRuntimeError) as error:
        yolo.detect_image(source())
    assert error.value.code == f"YOLO_RUNTIME_HTTP_{status}"
    assert TOKEN not in str(error.value)
    assert len(requests) == 1


@pytest.mark.parametrize("exception,code", [(httpx.ReadTimeout, "YOLO_RUNTIME_TIMEOUT"),
                                           (httpx.ConnectError, "YOLO_RUNTIME_UNAVAILABLE")])
def test_transport_errors_are_sanitized(transport: Callable, exception: type[Exception], code: str) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise exception(TOKEN)
    requests = transport(fail)
    with pytest.raises(yolo.YoloRuntimeError, match=code) as error:
        yolo.detect_image(source())
    assert TOKEN not in str(error.value)
    assert len(requests) == 1


@pytest.mark.parametrize("field,value", [
    ("detector_key", "connected_components_v1"), ("detector_version", "2.0.0"),
    ("algorithm_version", "unknown"), ("runtime_version", "2.0.0"),
    ("device", "cpu"), ("checkpoint_sha256", "0"*64), ("model_checkpoint", "/tmp/best.pt"),
    ("image_width", 79), ("image_height", 99), ("image_width", "80"), ("tile_size", 512),
    ("tile_overlap", 128), ("coordinate_space", "tile_pixels"), ("orientation_policy", "none"),
    ("bbox_format", "xyxy"), ("final_detection_count", 3), ("raw_detection_count", 9),
    ("invalid_detection_count", -1), ("warnings", ["untrusted warning"]),
    ("options", {"confidence": .5, "nms_iou": .7, "max_detections_per_tile": 1000}),
])
def test_rejects_invalid_identity_and_envelope(transport: Callable, field: str, value: object) -> None:
    data = payload()
    data[field] = value
    transport(lambda request: httpx.Response(200, json=data))
    with pytest.raises(yolo.YoloRuntimeError):
        yolo.detect_image(source())


@pytest.mark.parametrize("field,value", [
    ("bbox", {"x": 75, "y": 20, "width": 15, "height": 20}),
    ("bbox", {"x": -1, "y": 20, "width": 15, "height": 20}),
    ("bbox", {"x": 10, "y": 20, "width": 0, "height": 20}),
    ("bbox", {"x": 10.5, "y": 20, "width": 15, "height": 20}),
    ("centroid_x", 100.), ("area_px", 301.), ("area_px", 0.), ("confidence", 1.1),
    ("confidence", .1), ("confidence", "0.9"), ("mask_polygon", None),
    ("mask_polygon", [[10., 20.], [100., 20.], [25., 40.]]),
    ("mask_polygon", [[10., 20.], [10., 20.], [10., 20.]]),
    ("area_px", 100.),
    ("tile_id", "other"), ("geometry_source", "unknown"),
])
def test_rejects_invalid_detection_geometry(transport: Callable, field: str, value: object) -> None:
    data = payload()
    data["detections"][0][field] = value
    transport(lambda request: httpx.Response(200, json=data))
    with pytest.raises(yolo.YoloRuntimeError):
        yolo.detect_image(source())


@pytest.mark.parametrize("body", [b"invalid", b"[]", b"{}", b'{"confidence": NaN}'])
def test_rejects_malformed_responses(transport: Callable, body: bytes) -> None:
    transport(lambda request: httpx.Response(200, content=body))
    with pytest.raises(yolo.YoloRuntimeError, match="YOLO_RUNTIME_INVALID_RESPONSE"):
        yolo.detect_image(source())


@pytest.mark.parametrize("url", ["http://localhost:8765", "http://127.0.0.1:8765", "http://169.254.169.254",
                                 "https://example.com", "http://host.docker.internal.evil:8765",
                                 "http://user:secret@host.docker.internal:8765", "file:///tmp/x",
                                 "http://host.docker.internal:8765/v1", "http://host.docker.internal:8765?x=1",
                                 "http://host.docker.internal:8765#x", "http://host.docker.internal:0",
                                 "http://host.docker.internal:99999", "http://host.docker.internal:8765\n"])
def test_rejects_untrusted_runtime_urls(url: str) -> None:
    with pytest.raises(ValueError, match="YOLO_RUNTIME_URL"):
        validate_yolo_runtime_url(url)


def test_profile_identity_is_fixed_and_secrets_are_absent(transport: Callable) -> None:
    profile = yolo.profile_snapshot()
    assert profile["checkpoint_sha256"] == yolo.CHECKPOINT_SHA256
    assert TOKEN not in json.dumps(profile)
    assert TOKEN not in repr(Settings.from_env())
    profile["crop_padding_px"] = 99
    assert yolo.profile_snapshot()["crop_padding_px"] == 4
    for overrides in ({"checkpoint_sha256": "0"*64}, {"device": "cpu"}, {"confidence": float("nan")},
                      {"maximum_components_per_image": 501}, {"token": TOKEN}):
        with pytest.raises(ValueError, match="Invalid YOLO detector profile"):
            yolo.profile_snapshot(overrides)


@pytest.mark.parametrize("token", ["", "short", "x"*32+"\n", "á"*32])
def test_missing_or_unsafe_token_fails_before_http(transport: Callable, monkeypatch: pytest.MonkeyPatch, token: str) -> None:
    requests = transport(lambda request: pytest.fail("HTTP must not run"))
    monkeypatch.setenv("YOLO_RUNTIME_TOKEN", token)
    with pytest.raises(yolo.YoloRuntimeError, match="YOLO_RUNTIME_TOKEN_INVALID"):
        yolo.detect_image(source())
    assert not requests


def test_configuration_selects_yolo_without_network_at_resolution(
    transport: Callable, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import cell_analysis
    from app.services.detectors.resolver import resolve_detector

    requests = transport(lambda request: httpx.Response(200, json=payload()))
    monkeypatch.setenv("CELL_DETECTOR_KEY", "yolo26_seg_v1")
    monkeypatch.setattr(cell_analysis, "get_settings", Settings.from_env)
    service = cell_analysis.CellAnalysisService(engine=object())
    assert service.detector == resolve_detector("yolo26_seg_v1")
    assert service.crop_strategy.key == "bbox_crop_v1"
    assert not requests
    result = detect_and_crop(source(), detector=service.detector, crop_strategy=service.crop_strategy)
    assert len(result.crops) == 1
    assert len(requests) == 1
    monkeypatch.setenv("CELL_DETECTOR_KEY", "connected_components_v1")
    assert cell_analysis.CellAnalysisService(engine=object()).detector == resolve_detector()
    monkeypatch.delenv("CELL_DETECTOR_KEY")
    assert Settings.from_env().cell_detector_key == "connected_components_v1"


def test_resolved_yolo_never_invokes_connected_components(transport: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.detectors import connected_components_v1
    from app.services.detectors.resolver import resolve_detector

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Silent fallback to connected components")

    monkeypatch.setattr(connected_components_v1, "detect_image", forbidden)
    transport(lambda request: httpx.Response(503))
    with pytest.raises(yolo.YoloRuntimeError, match="YOLO_RUNTIME_HTTP_503"):
        detect_and_crop(source(), detector=resolve_detector("yolo26_seg_v1"))
    with pytest.raises(ValueError, match="Unsupported cell detector"):
        resolve_detector("unknown")


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf"])
def test_invalid_timeout_is_rejected(monkeypatch: pytest.MonkeyPatch, timeout: str) -> None:
    monkeypatch.setenv("YOLO_RUNTIME_TIMEOUT_SECONDS", timeout)
    with pytest.raises(ValueError, match="YOLO_RUNTIME_TIMEOUT_SECONDS"):
        Settings.from_env()


@pytest.mark.parametrize("field", list(payload()))
def test_response_fields_cannot_be_silently_defaulted(transport: Callable, field: str) -> None:
    data = payload()
    del data[field]
    transport(lambda request: httpx.Response(200, json=data))
    with pytest.raises(yolo.YoloRuntimeError, match="YOLO_RUNTIME_INVALID_RESPONSE"):
        yolo.detect_image(source())


@pytest.mark.parametrize("field", ["confidence", "area_px", "centroid_x", "centroid_y"])
@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_geometry_is_rejected(transport: Callable, field: str, value: float) -> None:
    data = payload()
    data["detections"][0][field] = value
    transport(lambda request: httpx.Response(200, content=json.dumps(data).encode()))
    with pytest.raises(yolo.YoloRuntimeError, match="YOLO_RUNTIME_INVALID_RESPONSE"):
        yolo.detect_image(source())
