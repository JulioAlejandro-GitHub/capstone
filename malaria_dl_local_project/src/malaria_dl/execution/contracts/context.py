"""Immutable identity at the scientific execution boundary."""
from dataclasses import dataclass
from enum import Enum
import re
from uuid import UUID


class ExecutionMode(str, Enum):
    DOCKER = "docker"
    LOCAL_PYTHON = "local_python"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionContext:
    run_id: UUID
    owner: UUID
    execution_mode: ExecutionMode
    dataset_version_id: UUID
    model_id: str
    adapter_version: str
    attempt_id: UUID | None = None
    campaign_id: UUID | None = None
    member_id: UUID | None = None
    configuration_hash: str | None = None
    contract_hash: str | None = None

    def __post_init__(self) -> None:
        for name in ("run_id", "owner", "dataset_version_id"):
            if not isinstance(getattr(self, name), UUID):
                raise TypeError(f"{name} must be UUID")
        for name in ("attempt_id", "campaign_id", "member_id"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, UUID):
                raise TypeError(f"{name} must be UUID or None")
        if not isinstance(self.execution_mode, ExecutionMode):
            raise TypeError("execution_mode must be ExecutionMode")
        for name in ("model_id", "adapter_version"):
            value = getattr(self, name)
            if type(value) is not str or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        for name in ("configuration_hash", "contract_hash"):
            value = getattr(self, name)
            if value is not None and (
                type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None
            ):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest or None")
