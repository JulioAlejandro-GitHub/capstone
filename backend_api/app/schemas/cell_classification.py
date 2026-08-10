from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CanonicalLabel = Literal["parasitized", "uninfected"]
ReviewDecision = Literal[
    "confirmed", "corrected", "needs_attention", "comment_only"
]


class CellClassificationRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detection_run_id: UUID


class CellExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retry: bool = False


class CellClassificationReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision
    reviewed_label: CanonicalLabel | None = None
    comment: str | None = Field(default=None, max_length=4000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_decision_payload(self):
        if self.decision == "corrected":
            if self.reviewed_label is None:
                raise ValueError("corrected requiere reviewed_label.")
            if self.comment is None:
                raise ValueError("corrected requiere comentario.")
        elif self.decision in {"needs_attention", "comment_only"}:
            if self.reviewed_label is not None:
                raise ValueError(
                    f"{self.decision} no admite reviewed_label."
                )
            if self.comment is None:
                raise ValueError(f"{self.decision} requiere comentario.")
        return self


class HumanCellClassificationSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: CanonicalLabel
    comment: str | None = Field(default=None, max_length=4000)

    @field_validator("comment")
    @classmethod
    def normalize_human_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
