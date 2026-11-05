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


class LearningRateGroup(BaseModel):
    group: str | None
    learning_rate: float | None
    parameters: int | None = None


class ArchitecturePhase(BaseModel):
    phase: str
    trainable_parameters: int | None
    trainable_tensors: int | None = None
    encoder: str | None = None
    # ViT: recorded trainable set against the one the registered base declares for that encoder setting.
    structure_check: Literal['match', 'mismatch'] | None = None
    learning_rates: list[LearningRateGroup] = []


class ArchitectureStructure(BaseModel):
    origin: Literal['derived']
    base_sha256: str
    vit_blocks: int | None = None
    patch_size: list[int] | None = None
    width: int | None = None
    patches: int | None = None
    tokens: int | None = None


class ArchitectureCheckpoint(BaseModel):
    artifact_id: str | None
    selected_epoch: int | None
    phase: str | None


class ZeroShot(BaseModel):
    """Logical TRAIN: the registered version's frozen protocol; nothing was trained."""
    model_version_id: str
    prompts: list[str]
    class_order: list[str]
    training_performed: bool


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
    structure: ArchitectureStructure | None = None
    zero_shot: ZeroShot | None = None
