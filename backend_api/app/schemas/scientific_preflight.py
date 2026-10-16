"""SCC-PRE.1: explicit selections and independent, scoped scientific verdicts."""
from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from typing_extensions import TypeAliasType

from app.config import get_settings

ScientificState = Literal[
    'COMPARABLE', 'COMPARABLE_CON_ADVERTENCIAS', 'NO_COMPARABLE', 'EVIDENCIA_INSUFICIENTE'
]
Dimension = Literal['A1', 'A2', 'A3', 'A4', 'A5', 'A6']
Module = Literal['curves', 'metrics', 'consensus', 'xai', 'embeddings', 'pca', 'umap', 'cka']
Split = Literal['train', 'val', 'test']
T = TypeVar('T')


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Known(Contract, Generic[T]):
    state: Literal['known'] = 'known'
    value: T
    evidence_ids: list[str]


class Unknown(Contract):
    state: Literal['unknown', 'not_applicable', 'not_checked']
    reason: str
    evidence_ids: list[str]


class QueryError(Contract):
    state: Literal['query_error'] = 'query_error'
    error_ids: list[str]


Observation = TypeAliasType('Observation', Annotated[Known[T] | Unknown | QueryError, Field(discriminator='state')], type_params=(T,))


class AssessmentSelection(Contract):
    source: Literal['assessment']
    identity_id: UUID
    attempt_id: UUID


class HistoricalSelection(Contract):
    source: Literal['evaluations']
    evaluation_id: UUID


EvaluationSelection = Annotated[AssessmentSelection | HistoricalSelection, Field(discriminator='source')]


class RequestedSelection(Contract):
    training_run_id: UUID
    evaluation: EvaluationSelection | None = None
    split: Split | None = None
    checkpoint_artifact_id: UUID | None = None


class PreflightRequest(Contract):
    selections: list[RequestedSelection] = Field(min_length=1)

    @model_validator(mode='after')
    def validate_selection(self):
        ids = [s.training_run_id for s in self.selections]
        if len(ids) != len(set(ids)):
            raise ValueError('Cada TRAIN debe aparecer una sola vez.')
        if len(ids) > get_settings().scc_max_comparison_runs:
            raise ValueError('Selección excede SCC_MAX_COMPARISON_RUNS.')
        return self


class EffectiveSelection(Contract):
    selection_id: str
    training_run_id: UUID
    dataset_version_id: Observation[UUID]
    evaluation: Observation[JsonValue]
    split: Observation[Split]
    checkpoint: Observation[UUID]
    selection_reason: str


class Scope(Contract):
    scope_id: str
    requested_training_run_ids: list[UUID]
    participating_training_run_ids: list[UUID]
    selection_ids: list[str]
    population: Literal['original', 'intersection', 'not_applicable']
    question: str


class Finding(Contract):
    reason_id: str
    code: str
    kind: Literal['difference', 'warning', 'missing', 'incompatibility']
    message: str
    condition: str
    affected_selection_ids: list[str]
    evidence_ids: list[str]


class Verdict(Contract):
    evaluation_status: Literal['evaluated', 'not_evaluated']
    scientific_state: ScientificState | None
    error_ids: list[str]

    @model_validator(mode='after')
    def validate_state(self):
        if self.evaluation_status == 'not_evaluated':
            if self.scientific_state is not None or not self.error_ids:
                raise ValueError('Un dictamen no evaluado requiere error técnico.')
        elif self.scientific_state is None:
            raise ValueError('Un dictamen evaluado requiere estado científico.')
        return self


class DimensionResult(Contract):
    dimension: Dimension
    scope: Scope
    verdict: Verdict
    evidence_ids: list[str]
    findings: list[Finding]


class IndividualData(Contract):
    selection_id: str
    availability: Observation[bool]
    references: list[str]


class AnalysisResult(Contract):
    analysis_id: str
    module_id: Module
    scope: Scope
    verdict: Verdict
    dimension_refs: list[str]
    evidence_ids: list[str]
    findings: list[Finding]
    individual_data: list[IndividualData]
    interpretation_limits: list[str]


class EvidenceRef(Contract):
    evidence_id: str
    source: str
    operation: str
    record_keys: dict[str, str]
    field: str | None
    selection_ids: list[str]
    observed_at: datetime
    verification: Literal['operational', 'not_verified']
    value: Observation[JsonValue]


class PopulationMember(Contract):
    selection_id: str
    expected_unique: Observation[int]
    retrieved_rows: Observation[int]
    retrieved_unique: Observation[int]
    duplicate_count: Observation[int]
    label_conflict_count: Observation[int]
    missing_count: Observation[int]
    exclusive_count: Observation[int]
    numerator: Observation[int]
    denominator: Observation[int]
    ratio: Observation[float]
    evidence_ids: list[str]


class PopulationCoverage(Contract):
    population_id: str
    scope_id: str
    alignment_key: Observation[str]
    complete: Observation[bool]
    per_selection: list[PopulationMember]
    intersection_unique: Observation[int]
    identity_references: list[str]
    subset_rule: str | None


class CheckpointCheck(Contract):
    selection_id: str
    artifact_id: UUID
    registered: Observation[bool]
    lineage: Observation[bool]
    availability: Literal['not_checked']
    integrity: Literal['not_checked']
    checked_at: None
    evidence_ids: list[str]
    error_ids: list[str]


class TechnicalError(Contract):
    error_id: str
    state: Literal['ERROR_DE_CONSULTA']
    code: str
    message: str
    operation: str
    scope_ids: list[str]
    selection_ids: list[str]
    correlation_id: str
    retryable: bool


class Consistency(Contract):
    mode: Literal['repeatable_read', 'partial']
    started_at: datetime
    completed_at: datetime
    limitations: list[str]


class Summary(Contract):
    by_state: dict[ScientificState, int]
    not_evaluated: int
    analysis_count: int
    warning_reason_ids: list[str]
    technical_error_ids: list[str]


class PreflightResponse(Contract):
    contract_version: Literal['scc_pre_1']
    generated_at: datetime
    correlation_id: str
    consistency: Consistency
    selections: list[EffectiveSelection]
    dimensions: list[DimensionResult]
    analyses: list[AnalysisResult]
    evidence: list[EvidenceRef]
    populations: list[PopulationCoverage]
    checkpoints: list[CheckpointCheck]
    technical_errors: list[TechnicalError]
    summary: Summary
