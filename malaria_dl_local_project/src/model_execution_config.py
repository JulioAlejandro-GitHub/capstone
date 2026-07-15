"""Serializable configuration for a model execution."""

from dataclasses import asdict, dataclass

from src.execution_types import validate_execution_type


@dataclass
class ModelExecutionConfig:
    model_name: str
    execution_type: str
    img_size: int
    batch_size: int
    epochs: int
    fine_tune_epochs: int | None
    learning_rate: float | None
    fine_tune_learning_rate: float | None
    preprocessing: str
    checkpoint_policy: str | None
    checkpoint_metric: str | None
    min_recall: float | None
    target_recall: float | None
    threshold: str | float | None
    positive_label: str
    seed: int
    output_dir: str
    track_db: bool

    def __post_init__(self) -> None:
        self.execution_type = validate_execution_type(self.execution_type)

    def to_dict(self) -> dict:
        """Return the complete configuration as a JSON/JSONB-compatible mapping."""
        return asdict(self)
