from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
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


class ScientificRead(ScientificSchema):
    id: UUID
    status: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
