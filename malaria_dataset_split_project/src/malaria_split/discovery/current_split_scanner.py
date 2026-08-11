from pathlib import Path

from malaria_split.domain import (
    ClassDistribution,
    CurrentPhysicalSplit,
    SplitPartitionSummary,
)

DEFAULT_SPLITS = ("train", "val", "test")
DEFAULT_CLASSES = ("parasitized", "uninfected")
DEFAULT_EXTENSIONS = (".png", ".jpg", ".jpeg")
KNOWN_AUXILIARY_FILES = ("metadata.json", "split_summary.csv", "files_manifest.csv")


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def scan_current_physical_split(
    root: Path | str,
    expected_splits: tuple[str, ...] = DEFAULT_SPLITS,
    expected_classes: tuple[str, ...] = DEFAULT_CLASSES,
    expected_extensions: tuple[str, ...] = DEFAULT_EXTENSIONS,
) -> CurrentPhysicalSplit:
    """Inspect a physical split without opening or mutating image files."""
    root = Path(root).expanduser().resolve()
    errors: list[str] = []
    unexpected: list[str] = []
    zero_bytes: list[str] = []
    hidden: list[str] = []
    extensions: set[str] = set()
    auxiliary: list[str] = []
    partitions: list[SplitPartitionSummary] = []

    if not root.exists():
        return CurrentPhysicalSplit((), ("split_root_missing",))
    if not root.is_dir():
        return CurrentPhysicalSplit((), ("split_root_not_directory",))

    for child in sorted(root.iterdir(), key=lambda item: item.name):
        rel = _relative(child, root)
        if child.name.startswith("."):
            hidden.append(rel)
        if child.is_file():
            if child.name in KNOWN_AUXILIARY_FILES:
                auxiliary.append(rel)
            else:
                unexpected.append(rel)
            if child.stat().st_size == 0:
                zero_bytes.append(rel)
        elif child.is_dir() and child.name not in expected_splits:
            errors.append(f"unexpected_split_directory:{rel}")

    for split_name in expected_splits:
        split_dir = root / split_name
        class_summaries: list[ClassDistribution] = []
        if not split_dir.is_dir():
            errors.append(f"missing_split_directory:{split_name}")
            continue
        for child in sorted(split_dir.iterdir(), key=lambda item: item.name):
            rel = _relative(child, root)
            if child.name.startswith("."):
                hidden.append(rel)
            if child.is_file():
                unexpected.append(rel)
                if child.stat().st_size == 0:
                    zero_bytes.append(rel)
            elif child.name not in expected_classes:
                errors.append(f"unexpected_class_directory:{rel}")
        for class_name in expected_classes:
            class_dir = split_dir / class_name
            count = 0
            class_exts: set[str] = set()
            if not class_dir.is_dir():
                errors.append(f"missing_class_directory:{split_name}/{class_name}")
                continue
            for path in sorted(class_dir.rglob("*")):
                rel = _relative(path, root)
                if path.name.startswith("."):
                    hidden.append(rel)
                if path.is_dir():
                    errors.append(f"unexpected_nested_directory:{rel}")
                    continue
                suffix = path.suffix.lower()
                if suffix not in expected_extensions:
                    unexpected.append(rel)
                else:
                    count += 1
                    extensions.add(suffix)
                    class_exts.add(suffix)
                if path.stat().st_size == 0:
                    zero_bytes.append(rel)
            class_summaries.append(
                ClassDistribution(class_name, count, tuple(sorted(class_exts)))
            )
        partitions.append(
            SplitPartitionSummary(split_name, split_name, tuple(class_summaries))
        )

    return CurrentPhysicalSplit(
        tuple(partitions),
        tuple(sorted(set(errors))),
        tuple(sorted(set(unexpected))),
        tuple(sorted(set(zero_bytes))),
        tuple(sorted(set(hidden))),
        tuple(sorted(extensions)),
        tuple(sorted(auxiliary)),
    )

