"""Read-only, module-scoped report requests. Identity contract shared with Preflight."""
from typing import Annotated, Literal

from pydantic import Field, JsonValue

from app.schemas.scientific_preflight import Contract, PreflightRequest


class ScientificReportRequest(PreflightRequest):
    module: Literal['catalog', 'curves', 'metrics', 'consensus', 'questions', 'representations']
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=25, ge=1, le=100)
    category: Literal['all', 'disagreement', 'CONSENSUS_TP', 'CONSENSUS_TN', 'CONSENSUS_FP', 'CONSENSUS_FN', 'high_confidence_error', 'low_confidence'] = 'all'
    # Consensus samples are ordered over the whole filtered population before paging (a page-local sort would lie).
    sort_by: str | None = Field(default=None, pattern=r'^(sample|label|category|run-[0-9])$')
    sort_desc: bool = False
    # Column filters of the samples table, applied to the whole population before sorting and paging.
    sample_query: str | None = Field(default=None, max_length=200)
    label: Literal[0, 1] | None = None
    score_ranges: dict[Annotated[int, Field(ge=0, le=9)], tuple[float | None, float | None]] = Field(default_factory=dict)


class ScientificReportResponse(Contract):
    module: str
    data: JsonValue
    warnings: list[str] = Field(default_factory=list)
