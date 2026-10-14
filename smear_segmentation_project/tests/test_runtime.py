from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from smear_segmentation.inference import (Box, Detection, DetectionResponse, InferenceOptions,
                                          consolidate, global_detection)
from smear_segmentation.runtime_api import RuntimeSettings, create_app, decode_image
from smear_segmentation.tiling import tiles_for_image

TOKEN = "unit-test-token-" * 3


class FakeRuntime:
    checkpoint_sha256 = "a" * 64

    def __init__(self, checkpoint: Path) -> None:
        self.checkpoint = checkpoint

    def detect(self, image: Image.Image, options: InferenceOptions) -> DetectionResponse:
        return DetectionResponse(model_checkpoint=str(self.checkpoint), checkpoint_sha256=self.checkpoint_sha256,
                                 image_width=image.width, image_height=image.height, options=options,
                                 detections=[], raw_detection_count=0, final_detection_count=0,
                                 invalid_detection_count=0, consolidated_detection_count=0, warnings=["NO_DETECTIONS"])


def png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (20, 10)).save(output, format="PNG")
    return output.getvalue()


def test_http_contract_and_authentication() -> None:
    with TestClient(create_app(RuntimeSettings(token=TOKEN), FakeRuntime)) as client:
        assert client.get("/health").json()["device"] == "mps"
        assert client.post("/v1/detect", content=png()).status_code == 401
        headers = {"Authorization": f"Bearer {TOKEN}"}
        response = client.post("/v1/detect?confidence=0.4", content=png(), headers=headers)
        assert response.status_code == 200
        assert response.json()["image_width"] == 20
        assert response.json()["options"]["confidence"] == 0.4
        assert response.json()["checkpoint_sha256"] == "a" * 64
        for query in ("confidence=nan", "nms_iou=0", "device=cpu"):
            assert client.post(f"/v1/detect?{query}", content=png(), headers=headers).status_code == 422
        assert client.post("/v1/detect", content=b"invalid", headers=headers).status_code == 422


def test_limits_and_explicit_failure() -> None:
    headers = {"Authorization": f"Bearer {TOKEN}"}
    with TestClient(create_app(RuntimeSettings(token=TOKEN, max_upload_bytes=5), FakeRuntime)) as client:
        assert client.post("/v1/detect", content=png(), headers=headers).status_code == 413
    with TestClient(create_app(RuntimeSettings(token=TOKEN, max_image_pixels=5), FakeRuntime)) as client:
        assert client.post("/v1/detect", content=png(), headers=headers).status_code == 413

    class FailedRuntime(FakeRuntime):
        def detect(self, image: Image.Image, options: InferenceOptions) -> DetectionResponse:
            raise RuntimeError("sensitive details")

    with TestClient(create_app(RuntimeSettings(token=TOKEN), FailedRuntime)) as client:
        response = client.post("/v1/detect", content=png(), headers=headers)
        assert response.status_code == 503
        assert "sensitive" not in response.text


def test_exif_is_preserved_for_inference() -> None:
    image = Image.new("RGB", (20, 10))
    exif = image.getexif()
    exif[274] = 6
    output = io.BytesIO()
    image.save(output, format="JPEG", exif=exif)
    from PIL import ImageOps
    assert ImageOps.exif_transpose(decode_image(output.getvalue(), 1000)).size == (10, 20)


def test_global_geometry_and_clipping() -> None:
    polygon = np.array([[0, 0], [20, 0], [20, 10], [0, 10]])
    result = global_detection([-2, -1, 22, 12], .9, polygon, (768, 50), (20, 10), "tile")
    assert result is not None
    assert result.bbox == Box(x=768, y=50, width=20, height=10)
    assert result.centroid_x == 778
    assert result.centroid_y == 55
    assert result.area_px == 200
    assert result.mask_polygon == [(768, 50), (788, 50), (788, 60), (768, 60)]
    assert global_detection([0, 0, float("nan"), 4], .9, None, (0, 0), (20, 10), "t") is None
    assert global_detection([21, 0, 22, 4], .9, None, (0, 0), (20, 10), "t") is None


def test_nms_deterministic_and_nearby_cells_survive() -> None:
    def cell(x: int, score: float, tile: str) -> Detection:
        return Detection(bbox=Box(x=x, y=0, width=10, height=10), confidence=score,
                         centroid_x=x+5, centroid_y=5, area_px=100, geometry_source="bbox", tile_id=tile)
    first, duplicate, neighbor = cell(0, .9, "a"), cell(1, .8, "b"), cell(8, .9, "c")
    assert consolidate([duplicate, neighbor, first], .7) == [first, neighbor]
    assert consolidate([first, neighbor, duplicate], .7) == [first, neighbor]
    assert [(t.x, t.y) for t in tiles_for_image(1800, 1024)] == [(0, 0), (768, 0), (776, 0)]


def test_runtime_refuses_cpu_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from smear_segmentation.inference import YoloRuntime
    monkeypatch.setenv("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    with pytest.raises(RuntimeError, match="fallback"):
        YoloRuntime()


def test_tiled_inference_translates_and_consolidates() -> None:
    from threading import Lock
    from types import SimpleNamespace
    from smear_segmentation.inference import YoloRuntime

    class Tensor:
        def __init__(self, values: list) -> None:
            self.values = values

        def cpu(self) -> Tensor:
            return self

        def tolist(self) -> list:
            return self.values

    class Model:
        calls = 0

        def predict(self, **kwargs: object) -> list:
            assert kwargs["device"] == "mps"
            assert kwargs["save"] is False
            x = 800 if self.calls == 0 else 32
            self.calls += 1
            return [SimpleNamespace(boxes=SimpleNamespace(xyxy=Tensor([[x, 20, x+20, 40]]),
                                                          conf=Tensor([.9])), masks=None)]

    runtime = object.__new__(YoloRuntime)
    runtime.model = Model()
    runtime.lock = Lock()
    runtime.checkpoint = "fixture.pt"
    runtime.checkpoint_sha256 = "a" * 64
    result = runtime.detect(Image.new("RGB", (1792, 1024)), InferenceOptions())
    assert runtime.model.calls == 2
    assert result.raw_detection_count == 2
    assert result.final_detection_count == 1
    assert result.consolidated_detection_count == 1
    assert result.detections[0].bbox.x == 800
    assert "MASK_UNAVAILABLE_BBOX_GEOMETRY" in result.warnings


@pytest.mark.parametrize("run", ["yolo26n_rbc_1024_v1", "123e4567-e89b-42d3-a456-426614174000"])
def test_checkpoint_selection_is_shared_and_independent_of_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, run: str) -> None:
    from smear_segmentation.checkpoints import checkpoint_reference, resolve_checkpoint
    from smear_segmentation.inference import selected_checkpoint
    monkeypatch.setenv("YOLO_RUN_UUID", run)
    monkeypatch.setenv("YOLO_RUNS_ROOT", "smear_segmentation_project/runs/yolo26_seg")
    monkeypatch.setenv("YOLO_RUNTIME_CHECKPOINT", "/ignored/weights/best.pt")
    monkeypatch.setenv("YOLO_RUNTIME_TOKEN", TOKEN)
    monkeypatch.chdir(tmp_path)
    import os
    root = Path(__file__).resolve().parents[2]
    expected = resolve_checkpoint(checkpoint_reference(os.environ), root)
    assert selected_checkpoint() == RuntimeSettings.from_env().checkpoint == expected
    assert expected == root / "smear_segmentation_project/runs/yolo26_seg" / run / "weights/best.pt"


@pytest.mark.parametrize("run", ["", " ", ".", "..", "../other", "/tmp/run", "a/b", "a\\b", "C:run"])
def test_unsafe_run_is_rejected(monkeypatch: pytest.MonkeyPatch, run: str) -> None:
    monkeypatch.setenv("YOLO_RUN_UUID", run)
    monkeypatch.setenv("YOLO_RUNTIME_TOKEN", TOKEN)
    with pytest.raises(ValueError, match="YOLO_RUN_UUID"):
        RuntimeSettings.from_env()


def test_dotenv_precedence_and_legacy_checkpoint(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from smear_segmentation.inference import selected_checkpoint
    monkeypatch.delenv("YOLO_RUN_UUID", raising=False)
    monkeypatch.delenv("YOLO_RUNS_ROOT", raising=False)
    monkeypatch.setenv("YOLO_RUNTIME_CHECKPOINT", str(tmp_path / "legacy.pt"))
    monkeypatch.setattr("dotenv.dotenv_values", lambda _: {"YOLO_RUN_UUID": "file-run", "YOLO_RUNS_ROOT": str(tmp_path)})
    assert selected_checkpoint() == tmp_path / "file-run/weights/best.pt"
    monkeypatch.setenv("YOLO_RUN_UUID", "process-run")
    assert selected_checkpoint() == tmp_path / "process-run/weights/best.pt"
    monkeypatch.delenv("YOLO_RUN_UUID")
    monkeypatch.setattr("dotenv.dotenv_values", lambda _: {})
    assert selected_checkpoint() == tmp_path / "legacy.pt"


def test_checkpoint_symlink_cannot_escape_root(tmp_path: Path) -> None:
    from smear_segmentation.checkpoints import resolve_checkpoint
    root = tmp_path / "runs"
    root.mkdir()
    (root / "run").symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="escapes"):
        resolve_checkpoint(root / "run/weights/best.pt", tmp_path)
