"""SWV2.2 campaign configuration DTOs.

Shape only (strict JSON types, no coercion). Domains, defaults and cross-field rules belong to
the canonical ``src.malaria_dl.campaigns.configuration`` so backend, CLI and UI cannot diverge.
"""
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr

ParameterValue = StrictBool | StrictInt | StrictFloat | StrictStr


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CampaignVariant(_Strict):
    name: StrictStr
    parameters: dict[StrictStr, dict[StrictStr, ParameterValue]]


class EarlyStoppingConfiguration(_Strict):
    enabled: StrictBool
    patience: StrictInt
    min_delta: StrictInt | StrictFloat
    restore_best_weights: StrictBool


class BudgetConfiguration(_Strict):
    max_attempts_per_member: StrictInt


class CampaignProtocolConfiguration(_Strict):
    early_stopping: EarlyStoppingConfiguration
    budget: BudgetConfiguration


class CampaignMatrixConfiguration(_Strict):
    version: StrictStr = "campaign_configuration_v1"
    models: list[StrictStr]
    optimizers: list[StrictStr]
    seeds: list[StrictInt]
    variants: list[CampaignVariant]
    protocol: CampaignProtocolConfiguration


class CampaignCreate(_Strict):
    # Client-generated idempotency key: a retried request with the same decisions returns the
    # stored campaign; different decisions under the same id are rejected.
    campaign_id: UUID
    name: StrictStr = Field(min_length=1, max_length=200)
    purpose: StrictStr = Field(min_length=1, max_length=2000)
    dataset_version_id: UUID
    configuration: CampaignMatrixConfiguration
