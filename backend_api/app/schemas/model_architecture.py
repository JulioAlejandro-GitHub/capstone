"""Public contract of one TRAIN's recorded model architecture."""
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel

Origin = Literal['recorded', 'derived', 'reference']


class ArchitectureLayer(BaseModel):
    name: str
    type: str
    block: str
    output_shape: list[int | None] | None
    inputs: list[str]
    parameters: int | None
    trainable_phases: list[str]
    settings: dict[str, Any]


class ArchitectureBlock(BaseModel):
    id: str
    label: str
    kind: Literal['input', 'convolution', 'dense', 'transition', 'encoder', 'head', 'output']
    layers: int
    units: int | None = None
    output_shape: list[int | None] | None
    parameters: int | None
    trainable_phases: list[str]
    origin: Origin


class ArchitectureOutput(BaseModel):
    neurons: int | None
    activation: str | None
    loss: str | None
    from_logits: bool | None
    meaning: str | None
    embedding_features: int | None = None


class ArchitecturePhase(BaseModel):
    phase: str
    trainable_parameters: int | None
    trainable_tensors: int | None = None
    encoder: str | None = None


class ArchitectureCheckpoint(BaseModel):
    artifact_id: str | None
    selected_epoch: int | None
    phase: str | None


class ModelArchitecture(BaseModel):
    training_run_id: UUID
    state: Literal['available', 'missing']
    issues: list[str]
    model_name: str | None
    architecture: str | None
    family: Literal['custom_cnn', 'vgg16', 'densenet121', 'biomedclip', 'generic']
    framework: str | None
    input_shape: list[int | None] | None
    output: ArchitectureOutput | None
    total_parameters: int | None
    checkpoint: ArchitectureCheckpoint
    phases: list[ArchitecturePhase]
    blocks: list[ArchitectureBlock]
    layers: list[ArchitectureLayer]
