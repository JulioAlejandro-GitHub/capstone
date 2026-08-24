import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import Permission, Principal, current_principal
from app.services.governed_datasets import (
    governed_dataset_version_detail,
    list_governed_dataset_versions,
)


pytestmark = pytest.mark.requires_local_postgres
V1 = UUID("d8c0cab5-09dd-597f-9de7-7ca01aee2ec2")


@pytest.fixture(autouse=True)
def require_explicit_postgres_gate():
    if os.getenv("TEST_EXECUTION", "").lower() != "true":
        pytest.skip("requiere gate PostgreSQL local explícito")


def test_governed_v1_list_and_detail_contract():
    items = list_governed_dataset_versions("malaria")["items"]
    v1 = next(item for item in items if item["dataset_version_id"] == V1)
    assert (v1["name"], v1["semantic_version"], v1["status"], v1["trainable"]) == (
        "Malaria Patient Split v1", "1.0.0", "FROZEN", True,
    )
    assert (v1["patient_count"], v1["source_record_count"]) == (201, 27558)
    assert (v1["train_records"], v1["val_records"], v1["test_records"]) == (22180, 2693, 2685)
    assert (v1["train_patients"], v1["val_patients"], v1["test_patients"]) == (161, 20, 20)
    assert (v1["validation_pass_count"], v1["validation_required_count"]) == (12, 12)
    assert (v1["materialization_status"], v1["reconciliation_status"]) == ("READY", "PASS")

    detail = governed_dataset_version_detail("malaria", V1)
    assert detail["distribution"]["class_counts"] == {
        "train": {"parasitized": 11137, "uninfected": 11043},
        "val": {"parasitized": 1325, "uninfected": 1368},
        "test": {"parasitized": 1317, "uninfected": 1368},
    }
    assert detail["integrity"] == {
        "patient_disjoint": True, "patient_train_val_overlap": 0,
        "patient_train_test_overlap": 0, "patient_val_test_overlap": 0,
        "duplicate_cross_split_overlap": 0,
    }
    assert (detail["validation"]["pass_count"], detail["validation"]["fail_count"]) == (12, 0)
    assert detail["materialization"]["sha_mismatch"] == 0
    assert detail["materialization"]["sha_files_checked"] == 27558
    assert all(detail["lineage"].values())
    assert detail["runs"]["count"] == len(detail["runs"]["items"])


def test_unknown_version_and_datasource_are_404():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as missing:
        governed_dataset_version_detail("malaria", uuid4())
    assert missing.value.status_code == 404
    with pytest.raises(HTTPException) as datasource:
        list_governed_dataset_versions("unknown")
    assert datasource.value.status_code == 404


def test_dataset_version_endpoints_require_and_accept_dataset_read_permission():
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/api/datasets?datasource=malaria").status_code == 401
        app.dependency_overrides[current_principal] = lambda: Principal(
            "test", "dataset-reader", ("read_only",),
            frozenset({Permission.DATASETS_READ}),
        )
        try:
            response = client.get("/api/datasets?datasource=malaria")
            assert response.status_code == 200
            detail = client.get(f"/api/datasets/{V1}?datasource=malaria")
            assert detail.status_code == 200
            assert detail.json()["dataset"]["trainable"] is True
        finally:
            app.dependency_overrides.clear()
