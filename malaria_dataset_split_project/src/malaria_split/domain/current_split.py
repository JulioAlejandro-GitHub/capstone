from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ClassDistribution:
    class_name: str
    count: int
    extensions: tuple[str, ...] = ()


@dataclass(frozen=True)
class SplitPartitionSummary:
    split_name: str
    relative_path: str
    classes: tuple[ClassDistribution, ...]

    @property
    def total_files(self) -> int:
        return sum(item.count for item in self.classes)


@dataclass(frozen=True)
class CurrentPhysicalSplit:
    partitions: tuple[SplitPartitionSummary, ...]
    structural_errors: tuple[str, ...] = ()
    unexpected_files: tuple[str, ...] = ()
    zero_byte_files: tuple[str, ...] = ()
    hidden_files: tuple[str, ...] = ()
    observed_extensions: tuple[str, ...] = ()
    auxiliary_files: tuple[str, ...] = ()

    @property
    def total_image_files(self) -> int:
        return sum(item.total_files for item in self.partitions)

    def to_dict(self) -> dict:
        return asdict(self) | {"total_image_files": self.total_image_files}

