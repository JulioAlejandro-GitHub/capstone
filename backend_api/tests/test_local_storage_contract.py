from __future__ import annotations

import hashlib
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.services.local_storage as local_storage_module
from app.services.local_storage import (
    LocalStorage,
    StorageChecksumMismatchError,
    StorageContentMissingError,
    StorageError,
    StorageFileTypeError,
    StorageSizeMismatchError,
    UnsafeStorageKeyError,
)


def _storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(
        SimpleNamespace(
            storage_provider="local",
            storage_root=tmp_path / "clinical-storage",
            max_upload_size_bytes=10_000_000,
            upload_chunk_size_bytes=1024,
        )
    )


def _write(storage: LocalStorage, key: str, payload: bytes) -> Path:
    path = storage.resolve(key)
    path.parent.mkdir(parents=True, mode=0o700)
    path.write_bytes(payload)
    return path


def test_construction_and_missing_reads_are_strictly_read_only(tmp_path: Path):
    storage = _storage(tmp_path)
    assert not storage.root.exists()
    assert not storage.staging.exists()

    with pytest.raises(StorageContentMissingError):
        storage.resolve("microscopy-images/missing.png", must_exist=True)

    assert not storage.root.exists()
    assert not storage.staging.exists()


def test_valid_verified_read_preserves_content_and_modification_time(tmp_path: Path):
    storage = _storage(tmp_path)
    payload = b"verified-clinical-content"
    path = _write(storage, "microscopy-images/source.bin", payload)
    before = path.stat()

    resolved = storage.resolve_verified(
        "microscopy-images/source.bin",
        expected_size_bytes=len(payload),
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    after = path.stat()
    assert resolved == path
    assert path.read_bytes() == payload
    assert after.st_mtime_ns == before.st_mtime_ns


@pytest.mark.parametrize(
    "key",
    ["", "/absolute.png", "../escape.png", "safe/../../escape.png", "bad\x00key"],
)
def test_unsafe_keys_are_rejected_without_creating_root(tmp_path: Path, key: str):
    storage = _storage(tmp_path)
    with pytest.raises(UnsafeStorageKeyError):
        storage.resolve(key)
    assert not storage.root.exists()


def test_symlinks_and_directories_are_rejected_at_every_boundary(tmp_path: Path):
    real_root = tmp_path / "real"
    real_root.mkdir()
    linked_root = tmp_path / "linked"
    linked_root.symlink_to(real_root, target_is_directory=True)
    settings = SimpleNamespace(
        storage_provider="local",
        storage_root=linked_root,
        max_upload_size_bytes=100,
        upload_chunk_size_bytes=10,
    )
    with pytest.raises(UnsafeStorageKeyError):
        LocalStorage(settings)

    storage = _storage(tmp_path)
    storage.root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (storage.root / "intermediate").symlink_to(outside, target_is_directory=True)
    with pytest.raises(UnsafeStorageKeyError):
        storage.resolve("intermediate/file.png", must_exist=True)

    target = storage.root / "target.png"
    target.write_bytes(b"target")
    (storage.root / "final.png").symlink_to(target)
    with pytest.raises(UnsafeStorageKeyError):
        storage.resolve("final.png", must_exist=True)

    directory = storage.root / "directory"
    directory.mkdir()
    with pytest.raises(StorageFileTypeError):
        storage.resolve("directory", must_exist=True)


def test_integrity_errors_are_differentiated_and_replacement_is_detected(
    tmp_path: Path,
):
    storage = _storage(tmp_path)
    payload = b"original"
    key = "cell-crops/crop.png"
    path = _write(storage, key, payload)
    checksum = hashlib.sha256(payload).hexdigest()

    with pytest.raises(StorageSizeMismatchError):
        storage.resolve_verified(
            key, expected_size_bytes=len(payload) + 1, expected_sha256=checksum
        )
    with pytest.raises(StorageChecksumMismatchError):
        storage.resolve_verified(
            key, expected_size_bytes=len(payload), expected_sha256="0" * 64
        )
    with pytest.raises(StorageChecksumMismatchError):
        storage.resolve_verified(
            key, expected_size_bytes=len(payload), expected_sha256="malformed"
        )
    with pytest.raises(StorageContentMissingError):
        storage.resolve_verified(
            "cell-crops/missing.png",
            expected_size_bytes=1,
            expected_sha256="0" * 64,
        )

    replacement = b"replaced"
    path.write_bytes(replacement)
    with pytest.raises(StorageChecksumMismatchError):
        storage.resolve_verified(
            key,
            expected_size_bytes=len(replacement),
            expected_sha256=checksum,
        )


def test_checksum_is_streamed_in_multiple_blocks(tmp_path: Path, monkeypatch):
    storage = _storage(tmp_path)
    payload = b"x" * (2 * 1024 * 1024 + 17)
    key = "microscopy-images/large.bin"
    _write(storage, key, payload)
    reads: list[int] = []
    original_read = local_storage_module.os.read

    def tracking_read(descriptor: int, size: int) -> bytes:
        reads.append(size)
        return original_read(descriptor, size)

    monkeypatch.setattr(local_storage_module.os, "read", tracking_read)
    storage.resolve_verified(
        key,
        expected_size_bytes=len(payload),
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )
    assert len(reads) >= 3
    assert max(reads) <= 1024 * 1024


def test_staging_promotion_permissions_no_overwrite_and_cleanup_boundaries(
    tmp_path: Path,
):
    storage = _storage(tmp_path)
    payload = b"crop-payload"
    assert not storage.root.exists()

    staged = storage.stage_bytes(
        payload, namespace="cell-detection", suffix=".crop.png"
    )
    assert storage.staging.is_dir()
    assert staged.path.is_file()
    key = "cell-crops/run/image/crop.png"
    final = storage.promote(
        staged.path,
        key,
        expected_size_bytes=staged.size,
        expected_sha256=staged.sha256,
    )
    assert stat.S_IMODE(final.stat().st_mode) == 0o600

    second = storage.stage_bytes(
        payload, namespace="cell-detection", suffix=".crop.png"
    )
    with pytest.raises(StorageError, match="no se sobrescribe"):
        storage.promote(
            second.path,
            key,
            expected_size_bytes=second.size,
            expected_sha256=second.sha256,
        )
    assert final.read_bytes() == payload

    with pytest.raises(UnsafeStorageKeyError, match="Namespace clínico"):
        storage.promote(
            second.path,
            "model-explanations/not-clinical.png",
            expected_size_bytes=second.size,
            expected_sha256=second.sha256,
        )

    original = _write(storage, "microscopy-images/original.bin", b"original")
    explanation = _write(storage, "cell-explanations/explanation.bin", b"xai")
    storage.cleanup(
        [second.path, final, original, explanation, storage.root],
        boundaries=(storage.staging / "cell-detection", storage.root / "cell-crops"),
    )
    assert not second.path.exists()
    assert not final.exists()
    assert original.exists()
    assert explanation.exists()
    assert storage.root.exists()
    assert (storage.root / "cell-crops").exists()

    with pytest.raises(UnsafeStorageKeyError):
        storage.cleanup([original], boundaries=(storage.root,))
