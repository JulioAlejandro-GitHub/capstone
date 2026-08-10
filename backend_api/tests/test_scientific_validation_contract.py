from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.scientific import (
    ScientificValidationAnnotationCreate,
    ScientificValidationAnnotationUpdate,
    ScientificValidationCreate,
    ScientificValidationUpdate,
)
from app.security import Permission, ROLE_PERMISSIONS


def valid_payload():
    return {
        "name": "Validación externa 2026",
        "datasource": "malaria",
        "image_ids": [uuid4()],
        "detection_run_ids": [],
        "classification_run_ids": [],
        "matching_iou_threshold": 0.5,
        "protocol_key": "two-expert-consensus",
        "protocol_version": "1.0",
    }


def test_validation_create_contract_rejects_client_snapshot_and_duplicate_images():
    payload = valid_payload()
    with pytest.raises(ValidationError):
        ScientificValidationCreate(**payload, initial_snapshot={})
    payload["image_ids"] = [payload["image_ids"][0], payload["image_ids"][0]]
    with pytest.raises(ValidationError):
        ScientificValidationCreate(**payload)


def test_validation_contract_bounds_iou_and_limits_mutable_fields():
    with pytest.raises(ValidationError):
        ScientificValidationCreate(**{**valid_payload(), "matching_iou_threshold": 0})
    with pytest.raises(ValidationError):
        ScientificValidationUpdate(image_ids=[uuid4()])


def test_validation_rbac_is_explicit():
    assert Permission.SCIENTIFIC_VALIDATION_READ in ROLE_PERMISSIONS["read_only"]
    assert Permission.SCIENTIFIC_VALIDATION_CREATE in ROLE_PERMISSIONS["researcher"]
    assert Permission.SCIENTIFIC_VALIDATION_ARCHIVE not in ROLE_PERMISSIONS["operator"]
    assert Permission.SCIENTIFIC_VALIDATION_ANNOTATE in ROLE_PERMISSIONS["reviewer"]
    assert Permission.SCIENTIFIC_VALIDATION_ANNOTATE not in ROLE_PERMISSIONS["read_only"]


def test_annotation_contract_enforces_exact_target_and_server_owned_actor():
    cell_id = uuid4()
    valid = ScientificValidationAnnotationCreate(
        target_type="cell", cell_id=cell_id, category="quality", content="note"
    )
    assert valid.cell_id == cell_id
    with pytest.raises(ValidationError):
        ScientificValidationAnnotationCreate(
            target_type="cell", cell_id=cell_id, analysis_run_id=uuid4(),
            category="quality", content="note",
        )
    with pytest.raises(ValidationError):
        ScientificValidationAnnotationCreate(
            target_type="analysis", category="quality", content="note"
        )
    with pytest.raises(ValidationError):
        ScientificValidationAnnotationCreate(
            target_type="cell", cell_id=cell_id, category="quality", content="note",
            created_by=uuid4(),
        )


def test_annotation_update_requires_version_and_real_change():
    assert ScientificValidationAnnotationUpdate(version=1, content="updated").version == 1
    with pytest.raises(ValidationError):
        ScientificValidationAnnotationUpdate(content="updated")
    with pytest.raises(ValidationError):
        ScientificValidationAnnotationUpdate(version=1)
    with pytest.raises(ValidationError):
        ScientificValidationAnnotationUpdate(version=1, content=None)
