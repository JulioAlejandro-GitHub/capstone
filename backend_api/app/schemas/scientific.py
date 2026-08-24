from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


PII_KEYS = {
    "name", "first_name", "last_name", "full_name", "rut", "national_id",
    "document_id", "address", "phone", "email", "birth_date", "date_of_birth",
    "contact", "diagnosis",
}


def _assert_no_pii(value: Any) -> Any:
    if not isinstance(value, dict):
        raise PydanticCustomError("metadata_object", "metadata_json debe ser un objeto")
    pending = [value]
    while pending:
        current = pending.pop()
        for key, nested in current.items():
            if str(key).lower() in PII_KEYS:
                raise PydanticCustomError(
                    "metadata_pii",
                    "metadata_json no admite información identificable: {key}",
                    {"key": str(key)},
                )
            if isinstance(nested, dict):
                pending.append(nested)
            elif isinstance(nested, list):
                pending.extend(item for item in nested if isinstance(item, dict))
    return value


class ScientificSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class MetadataSchema(ScientificSchema):
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata_json")
    @classmethod
    def metadata_has_no_pii(cls, value: dict[str, Any]):
        return _assert_no_pii(value)


class SubjectCreate(MetadataSchema):
    subject_code: str = Field(min_length=1, max_length=120)
    study_reference: str | None = Field(None, max_length=200)
    age_group: str | None = Field(None, max_length=80)
    biological_sex: str | None = Field(None, max_length=80)


class SubjectUpdate(MetadataSchema):
    subject_code: str | None = Field(None, min_length=1, max_length=120)
    study_reference: str | None = Field(None, max_length=200)
    age_group: str | None = Field(None, max_length=80)
    biological_sex: str | None = Field(None, max_length=80)
    status: Literal["active"] | None = None


class CaseCreate(MetadataSchema):
    case_code: str = Field(min_length=1, max_length=120)
    subject_id: UUID | None = None
    title: str | None = Field(None, max_length=240)
    description: str | None = None
    source_type: Literal["physical_microscope", "imported_image", "research_dataset", "synthetic"]
    status: Literal["draft", "registered", "ready"] = "draft"
    priority: Literal["low", "normal", "high"] = "normal"


class CaseUpdate(MetadataSchema):
    subject_id: UUID | None = None
    title: str | None = Field(None, max_length=240)
    description: str | None = None
    source_type: Literal["physical_microscope", "imported_image", "research_dataset", "synthetic"] | None = None
    status: Literal["draft", "registered", "ready"] | None = None
    priority: Literal["low", "normal", "high"] | None = None


class SampleCreate(MetadataSchema):
    sample_code: str = Field(min_length=1, max_length=120)
    specimen_type: str = Field("peripheral_blood", min_length=1, max_length=80)
    collection_method: str | None = Field(None, max_length=120)
    anticoagulant: str | None = Field(None, max_length=120)
    collected_at: datetime | None = None
    received_at: datetime | None = None
    status: Literal["registered", "received", "prepared"] = "registered"
    notes: str | None = None


class SampleUpdate(MetadataSchema):
    specimen_type: str | None = Field(None, min_length=1, max_length=80)
    collection_method: str | None = Field(None, max_length=120)
    anticoagulant: str | None = Field(None, max_length=120)
    collected_at: datetime | None = None
    received_at: datetime | None = None
    status: Literal["registered", "received", "prepared"] | None = None
    notes: str | None = None


class SlideCreate(MetadataSchema):
    slide_code: str = Field(min_length=1, max_length=120)
    smear_type: Literal["thin", "thick", "combined", "unknown"]
    stain_type: str | None = Field(None, max_length=120)
    preparation_method: str | None = Field(None, max_length=160)
    prepared_at: datetime | None = None
    status: Literal["registered", "prepared", "ready_for_capture"] = "registered"
    notes: str | None = None


class SlideUpdate(MetadataSchema):
    smear_type: Literal["thin", "thick", "combined", "unknown"] | None = None
    stain_type: str | None = Field(None, max_length=120)
    preparation_method: str | None = Field(None, max_length=160)
    prepared_at: datetime | None = None
    status: Literal["registered", "prepared", "ready_for_capture"] | None = None
    notes: str | None = None


class ImageCreate(MetadataSchema):
    image_code: str = Field(min_length=1, max_length=120)
    storage_provider: str = Field("local", min_length=1, max_length=40)
    storage_key: str = Field(min_length=1)
    original_filename: str | None = None
    mime_type: str = Field(min_length=1, max_length=120)
    file_size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)
    bit_depth: int | None = Field(None, gt=0)
    magnification: float | None = Field(None, gt=0)
    objective_lens: str | None = Field(None, max_length=120)
    microscope_reference: str | None = Field(None, max_length=160)
    camera_reference: str | None = Field(None, max_length=160)
    captured_at: datetime | None = None
    status: Literal["registered", "available", "unavailable", "rejected"] = "registered"


class ImageUpdate(MetadataSchema):
    storage_provider: str | None = Field(None, min_length=1, max_length=40)
    storage_key: str | None = Field(None, min_length=1)
    original_filename: str | None = None
    mime_type: str | None = Field(None, min_length=1, max_length=120)
    file_size_bytes: int | None = Field(None, gt=0)
    sha256: str | None = Field(None, pattern=r"^[0-9a-fA-F]{64}$")
    width_px: int | None = Field(None, gt=0)
    height_px: int | None = Field(None, gt=0)
    bit_depth: int | None = Field(None, gt=0)
    magnification: float | None = Field(None, gt=0)
    objective_lens: str | None = Field(None, max_length=120)
    microscope_reference: str | None = Field(None, max_length=160)
    camera_reference: str | None = Field(None, max_length=160)
    captured_at: datetime | None = None
    status: Literal["registered", "available", "unavailable", "rejected"] | None = None


class ArchiveRequest(ScientificSchema):
    reason: str | None = Field(None, max_length=500)


ValidationStatus = Literal[
    "draft", "annotation_in_progress", "ready_for_analysis", "completed", "archived"
]


class ScientificValidationCreate(ScientificSchema):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(None, max_length=4000)
    datasource: Literal["malaria"] = "malaria"
    image_ids: list[UUID] = Field(min_length=1, max_length=10000)
    detection_run_ids: list[UUID] = Field(default_factory=list, max_length=1000)
    classification_run_ids: list[UUID] = Field(default_factory=list, max_length=1000)
    matching_iou_threshold: float = Field(gt=0, le=1)
    protocol_key: str = Field(min_length=1, max_length=120)
    protocol_version: str = Field(min_length=1, max_length=80)

    @field_validator("image_ids", "detection_run_ids", "classification_run_ids")
    @classmethod
    def identifiers_are_unique(cls, value: list[UUID]):
        if len(value) != len(set(value)):
            raise ValueError("Los identificadores no pueden repetirse.")
        return value


class ScientificValidationUpdate(ScientificSchema):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=4000)
    status: ValidationStatus | None = None


class ScientificValidationAnnotationCreate(ScientificSchema):
    target_type: Literal["cell", "analysis", "sample"]
    cell_id: UUID | None = None
    analysis_run_id: UUID | None = None
    sample_id: UUID | None = None
    category: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=10000)

    @field_validator("content", "category")
    @classmethod
    def annotation_text_is_not_blank(cls, value: str):
        if not value.strip():
            raise ValueError("El texto no puede estar vacío.")
        return value

    @model_validator(mode="after")
    def validate_target(self):
        valid = (
            self.target_type == "cell" and self.cell_id is not None
            and self.analysis_run_id is None and self.sample_id is None
        ) or (
            self.target_type == "analysis" and self.analysis_run_id is not None
            and self.cell_id is None and self.sample_id is None
        ) or (
            self.target_type == "sample" and self.sample_id is not None
            and self.cell_id is None and self.analysis_run_id is None
        )
        if not valid:
            raise PydanticCustomError(
                "annotation_target",
                "Debe especificarse exactamente el target correspondiente.",
            )
        return self


class ScientificValidationAnnotationUpdate(ScientificSchema):
    category: str | None = Field(None, min_length=1, max_length=120)
    content: str | None = Field(None, min_length=1, max_length=10000)
    version: int = Field(gt=0)

    @field_validator("content", "category")
    @classmethod
    def updated_annotation_text_is_not_blank(cls, value: str | None):
        if value is not None and not value.strip():
            raise ValueError("El texto no puede estar vacío.")
        return value

    @model_validator(mode="after")
    def contains_change(self):
        changed = self.model_fields_set.intersection({"category", "content"})
        if not changed:
            raise PydanticCustomError(
                "annotation_change", "Debe enviarse al menos un campo editable."
            )
        if any(getattr(self, field) is None for field in changed):
            raise PydanticCustomError(
                "annotation_null", "Los campos editables no admiten null."
            )
        return self
