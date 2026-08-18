import hashlib
from pathlib import Path
from uuid import UUID

from malaria_split.persistence.materialization import (
    MaterializationEntry,
    MaterializationPlan,
    reconcile_materialization,
)


def _plan(tmp_path: Path):
    entries = []
    for index, (split, cls) in enumerate((
        ("train", "parasitized"), ("train", "uninfected"),
        ("val", "parasitized"), ("val", "uninfected"),
        ("test", "parasitized"), ("test", "uninfected"),
    ), 1):
        source = tmp_path / "source" / f"{index}.png"
        source.parent.mkdir(exist_ok=True)
        payload = f"byte-exact-{index}".encode()
        source.write_bytes(payload)
        entries.append(MaterializationEntry(
            UUID(int=index), UUID(int=100 + index), split, cls, source,
            Path(split) / cls / source.name, hashlib.sha256(payload).hexdigest(),
        ))
    return MaterializationPlan(UUID(int=999), tuple(entries), "p" * 64, "r" * 64, 0,
                               "PRESERVE_SOURCE_FILENAME")


def _copy(plan, root):
    for entry in plan.entries:
        target = root / entry.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(entry.source_path.read_bytes())


def test_successful_small_materialization_plan(tmp_path):
    plan = _plan(tmp_path)
    root = tmp_path / "final"
    _copy(plan, root)
    result = reconcile_materialization(plan, root)
    assert result.passed
    assert result.files_found == result.sha_match == 6
    assert result.sha_mismatch == result.missing_files == result.unexpected_files == 0


def test_wrong_count_and_wrong_path_fail(tmp_path):
    plan = _plan(tmp_path)
    root = tmp_path / "final"
    _copy(plan, root)
    expected = root / plan.entries[0].relative_path
    wrong = root / "val" / "parasitized" / expected.name
    wrong.parent.mkdir(parents=True, exist_ok=True)
    expected.rename(wrong)
    result = reconcile_materialization(plan, root)
    assert not result.passed
    assert result.missing_files == 1
    assert result.unexpected_files == 1


def test_wrong_sha_fails(tmp_path):
    plan = _plan(tmp_path)
    root = tmp_path / "final"
    _copy(plan, root)
    (root / plan.entries[0].relative_path).write_bytes(b"corrupted")
    result = reconcile_materialization(plan, root)
    assert not result.passed
    assert result.sha_mismatch == 1
