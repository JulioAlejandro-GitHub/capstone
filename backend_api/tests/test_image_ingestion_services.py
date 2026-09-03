from __future__ import annotations

import asyncio
import hashlib
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import UploadFile
from PIL import Image

from app.config import get_settings, reset_settings_cache
from app.services.image_validation import ImageValidationError, validate_image
from app.services.local_storage import LocalStorage, StorageError, sanitize_filename


def image_bytes(fmt: str, *, frames: int = 1) -> bytes:
    output = BytesIO()
    images = [Image.new("RGB", (12, 8), (index * 10, 20, 30)) for index in range(frames)]
    images[0].save(output, format=fmt, save_all=frames > 1, append_images=images[1:])
    return output.getvalue()


@pytest.fixture
def storage(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("MAX_UPLOAD_SIZE_BYTES", "1024")
    monkeypatch.setenv("UPLOAD_CHUNK_SIZE_BYTES", "7")
    reset_settings_cache()
    local = LocalStorage(get_settings())
    local.ensure_writable_layout()
    yield local
    reset_settings_cache()


@pytest.mark.parametrize(
    ("fmt", "detected", "mime"),
    [("JPEG", "JPEG", "image/jpeg"), ("PNG", "PNG", "image/png"), ("TIFF", "TIFF", "image/tiff")],
)
def test_detects_and_fully_decodes_supported_images(storage, fmt, detected, mime):
    path = storage.staging / f"image-{fmt}"
    payload = image_bytes(fmt)
    path.write_bytes(payload)
    metadata = validate_image(path)
    assert (metadata.detected_format, metadata.mime_type) == (detected, mime)
    assert (metadata.width_px, metadata.height_px) == (12, 8)
    assert path.read_bytes() == payload


def test_rejects_corrupt_and_multipage_tiff(storage):
    corrupt = storage.staging / "corrupt"
    corrupt.write_bytes(b"not an image")
    with pytest.raises(ImageValidationError):
        validate_image(corrupt)
    multipage = storage.staging / "multipage"
    multipage.write_bytes(image_bytes("TIFF", frames=2))
    with pytest.raises(ImageValidationError, match="frame"):
        validate_image(multipage)


def test_streaming_sha_path_containment_and_no_overwrite(storage):
    payload = image_bytes("PNG")
    upload = UploadFile(filename="../../patient.png", file=BytesIO(payload))
    staged = asyncio.run(storage.stage(upload))
    assert staged.original_filename == "patient.png"
    assert staged.sha256 == hashlib.sha256(payload).hexdigest()
    ids = [uuid4() for _ in range(4)]
    key = storage.build_key(*ids, staged.sha256, "png")
    assert not key.startswith("/") and ".." not in key
    final = storage.promote(
        staged.path,
        key,
        expected_size_bytes=staged.size,
        expected_sha256=staged.sha256,
    )
    assert final.read_bytes() == payload
    second = asyncio.run(
        storage.stage(UploadFile(filename="patient.png", file=BytesIO(payload)))
    )
    with pytest.raises(StorageError, match="sobrescribe"):
        storage.promote(
            second.path,
            key,
            expected_size_bytes=second.size,
            expected_sha256=second.sha256,
        )
    with pytest.raises(StorageError):
        storage.resolve("../escape")
    with pytest.raises(StorageError):
        storage.resolve("/absolute")


def test_rejects_symlink_and_sanitizes_control_characters(storage):
    outside = storage.root.parent / "outside"
    outside.write_bytes(b"x")
    link = storage.root / "link"
    link.symlink_to(outside)
    with pytest.raises(StorageError, match="symlink"):
        storage.resolve("link", must_exist=True)
    assert sanitize_filename("folder\\bad\x01 name.png") == "bad name.png"


def test_rejects_symlink_configured_as_storage_root(tmp_path, monkeypatch):
    real_root = tmp_path / "real-storage"
    real_root.mkdir()
    linked_root = tmp_path / "linked-storage"
    linked_root.symlink_to(real_root, target_is_directory=True)
    monkeypatch.setenv("STORAGE_ROOT", str(linked_root))
    reset_settings_cache()
    try:
        with pytest.raises(StorageError, match="STORAGE_ROOT"):
            LocalStorage(get_settings())
    finally:
        reset_settings_cache()
