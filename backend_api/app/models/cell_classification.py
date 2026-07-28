from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ClassificationRunStatus(StrEnum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class CellPredictionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class CellExplanationStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    GENERATED = "generated"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class ClassificationReviewDecision(StrEnum):
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    NEEDS_ATTENTION = "needs_attention"
    COMMENT_ONLY = "comment_only"


class CanonicalCellLabel(StrEnum):
    UNINFECTED = "uninfected"
    PARASITIZED = "parasitized"


class SmearAnalysisOutcome(StrEnum):
    SUSPICIOUS_CELLS_DETECTED = "suspicious_cells_detected"
    NO_SUSPICIOUS_CELLS_DETECTED = "no_suspicious_cells_detected"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class FrozenClassificationInput:
    id: UUID
    classification_run_id: UUID
    detection_run_id: UUID
    cell_detection_id: UUID
    microscopy_image_id: UUID
    crop_id: UUID | None
    input_order: int
    image_sequence_number: int
    cell_index: int
    cell_code: str
    detector_key: str
    detector_version: str
    detector_algorithm_version: str
    crop_sha256: str | None
    crop_width_px: int | None
    crop_height_px: int | None
    detection_review_status_at_creation: str | None
    eligible: bool
    exclusion_reason: str | None


@dataclass(frozen=True)
class ClassificationCounts:
    processed_count: int
    parasitized_count: int
    uninfected_count: int
    near_threshold_count: int
    failed_count: int
