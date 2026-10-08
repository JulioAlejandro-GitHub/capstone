from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CellActivationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    replace_existing: bool = False
    reason: str = 'Activación para clasificación celular'


class CellActivationResult(BaseModel):
    training_run_id: UUID
    model_version_id: UUID
    deployment_id: UUID
    available_for_inference: bool
    idempotent: bool
