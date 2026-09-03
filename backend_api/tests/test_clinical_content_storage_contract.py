from __future__ import annotations

import hashlib
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routes import cell_analysis as cell_analysis_route
from app.routes import scientific as scientific_route
from app.services.cell_analysis import CellAnalysisError, CellAnalysisService
from app.services.local_storage import (
    StorageChecksumMismatchError,
    StorageContentMissingError,
)


class _Engine:
    @contextmanager
    def connect(self):
        yield object()


class _VerifiedStorage:
    def __init__(self, path: Path, error: Exception | None = None):
        self.path = path
        self.error = error
        self.calls: list[tuple[str, int, str]] = []

    def resolve_verified(
        self,
        key: str,
        *,
        expected_size_bytes: int,
        expected_sha256: str,
    ) -> Path:
        self.calls.append((key, expected_size_bytes, expected_sha256))
        if self.error is not None:
            raise self.error
        return self.path


def _image(path: Path) -> dict:
    payload = path.read_bytes()
    checksum = hashlib.sha256(payload).hexdigest()
    return {
        "id": uuid4(),
        "status": "available",
        "storage_key": "microscopy-images/source.png",
        "file_size_bytes": len(payload),
        "sha256": checksum,
        "mime_type": "image/png",
        "original_filename": "source.png",
    }


def _frozen_image(path: Path) -> dict:
    image = _image(path)
    return {
        **image,
        "input_file_size_bytes": image["file_size_bytes"],
        "input_sha256": image["sha256"],
        "current_width_px": 12,
        "current_height_px": 8,
        "input_width_px": 12,
        "input_height_px": 8,
    }


def test_scientific_image_endpoint_uses_canonical_verified_read(
    tmp_path: Path, monkeypatch
):
    path = tmp_path / "source.png"
    path.write_bytes(b"png-content")
    image = _image(path)
    storage = _VerifiedStorage(path)
    monkeypatch.setattr(scientific_route.service, "get", lambda *_args: image)
    monkeypatch.setattr(scientific_route, "LocalStorage", lambda: storage)

    response = scientific_route.image_content(uuid4(), None)

    assert storage.calls == [
        (image["storage_key"], image["file_size_bytes"], image["sha256"])
    ]
    assert Path(response.path) == path
    assert response.media_type == "image/png"
    assert response.headers["etag"] == f'"sha256-{image["sha256"]}"'
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize(
    "error",
    [
        StorageContentMissingError("missing"),
        StorageChecksumMismatchError("corrupt"),
    ],
)
def test_scientific_image_endpoint_maps_unavailable_or_corrupt_content_to_404(
    tmp_path: Path, monkeypatch, error: Exception
):
    path = tmp_path / "source.png"
    path.write_bytes(b"png-content")
    image = _image(path)
    monkeypatch.setattr(scientific_route.service, "get", lambda *_args: image)
    monkeypatch.setattr(
        scientific_route, "LocalStorage", lambda: _VerifiedStorage(path, error)
    )

    with pytest.raises(HTTPException) as raised:
        scientific_route.image_content(uuid4(), None)

    assert raised.value.status_code == 404
    assert "path" not in str(raised.value.detail).lower()


def test_detection_source_reader_uses_same_verification_and_frozen_metadata(
    tmp_path: Path, monkeypatch
):
    path = tmp_path / "source.png"
    path.write_bytes(b"png-content")
    image = _frozen_image(path)
    storage = _VerifiedStorage(path)

    class Repository:
        def __init__(self, _connection):
            pass

        def source_image(self, _run_id, _image_id):
            return image

    monkeypatch.setattr(
        "app.services.cell_analysis.CellAnalysisRepository", Repository
    )
    service = CellAnalysisService(engine=_Engine(), local_storage=storage)

    result, resolved = service.source_image_content(str(uuid4()), str(image["id"]))

    assert result is image
    assert resolved == path
    assert storage.calls == [
        (image["storage_key"], image["input_file_size_bytes"], image["input_sha256"])
    ]


def test_detection_source_reader_preserves_409_for_metadata_or_integrity_conflict(
    tmp_path: Path, monkeypatch
):
    path = tmp_path / "source.png"
    path.write_bytes(b"png-content")
    image = _frozen_image(path)

    class Repository:
        def __init__(self, _connection):
            pass

        def source_image(self, _run_id, _image_id):
            return image

    monkeypatch.setattr(
        "app.services.cell_analysis.CellAnalysisRepository", Repository
    )
    corrupted = CellAnalysisService(
        engine=_Engine(),
        local_storage=_VerifiedStorage(
            path, StorageChecksumMismatchError("corrupt")
        ),
    )
    with pytest.raises(CellAnalysisError) as raised:
        corrupted.source_image_content(str(uuid4()), str(image["id"]))
    assert raised.value.status_code == 409
    assert raised.value.code == "CONTENT_INTEGRITY_MISMATCH"

    image["sha256"] = "0" * 64
    with pytest.raises(CellAnalysisError) as raised:
        corrupted.source_image_content(str(uuid4()), str(image["id"]))
    assert raised.value.status_code == 409
    assert raised.value.code == "SOURCE_METADATA_MISMATCH"


def test_crop_reader_delegates_size_and_checksum_to_crop_storage(
    tmp_path: Path, monkeypatch
):
    path = tmp_path / "crop.png"
    path.write_bytes(b"crop")
    checksum = hashlib.sha256(b"crop").hexdigest()
    crop = {
        "id": uuid4(),
        "relative_storage_key": "cell-crops/run/crop.png",
        "file_size_bytes": 4,
        "sha256": checksum,
    }
    storage = _VerifiedStorage(path)

    class Repository:
        def __init__(self, _connection):
            pass

        def crop(self, _crop_id):
            return crop

    monkeypatch.setattr(
        "app.services.cell_analysis.CellAnalysisRepository", Repository
    )
    service = CellAnalysisService(engine=_Engine(), crop_storage=storage)

    result, resolved = service.crop_content(str(crop["id"]))

    assert result is crop
    assert resolved == path
    assert storage.calls == [
        (crop["relative_storage_key"], crop["file_size_bytes"], checksum)
    ]


def test_content_route_headers_remain_stable(tmp_path: Path, monkeypatch):
    path = tmp_path / "source.png"
    path.write_bytes(b"png-content")
    image = _frozen_image(path)
    monkeypatch.setattr(
        cell_analysis_route.service,
        "source_image_content",
        lambda *_args: (image, path),
    )

    response = cell_analysis_route.source_image_content(uuid4(), uuid4(), None)

    assert response.media_type == "image/png"
    assert response.headers["content-length"] == str(image["input_file_size_bytes"])
    assert response.headers["etag"] == f'"sha256-{image["input_sha256"]}"'
    assert response.headers["x-content-type-options"] == "nosniff"
