from uuid import UUID, uuid5

import pytest

from malaria_split.families import (
    DatasetFamily,
    get_source,
    resolve_dataset_family,
)
from malaria_split.persistence import bootstrap
from malaria_split.persistence.split_generation import V1_ID


def test_both_families_are_representable():
    assert {item.value for item in DatasetFamily} == {"cell_classification", "smear_segmentation"}
    assert get_source("smear_segmentation", "thin_blood_smears_pf").name == (
        "NIH/NLM ThinBloodSmearsPf"
    )
    assert get_source("cell_classification", "nih_nlm_malaria_cell_images").name == (
        "NIH/NLM Malaria Cell Images"
    )


def test_family_source_mismatch_and_unknowns_are_rejected():
    with pytest.raises(ValueError):
        get_source("cell_classification", "thin_blood_smears_pf")
    with pytest.raises(ValueError):
        get_source("smear_segmentation", "unknown")
    with pytest.raises(ValueError):
        get_source("detection", "thin_blood_smears_pf")


def test_historical_v1_source_is_cell_classification_without_metadata_rewrite():
    # The real v1 datasets row has no dataset_family key; its name alone resolves it.
    assert resolve_dataset_family("NIH/NLM Malaria Cell Images", {"task_type": "x"}) is (
        DatasetFamily.CELL_CLASSIFICATION
    )
    assert resolve_dataset_family("anything", {"dataset_family": "smear_segmentation"}) is (
        DatasetFamily.SMEAR_SEGMENTATION
    )
    assert resolve_dataset_family("malaria_physical_split", {}) is None


def test_frozen_v1_constants_are_unchanged():
    assert bootstrap.SOURCE_NAME == "NIH/NLM Malaria Cell Images"
    assert (bootstrap.EXPECTED_RECORDS, bootstrap.EXPECTED_PATIENTS) == (27_558, 201)
    assert uuid5(bootstrap.ID_NAMESPACE, f"{bootstrap.VERSION_NAME}:{bootstrap.VERSION_SEMVER}") == (
        UUID("d8c0cab5-09dd-597f-9de7-7ca01aee2ec2")
    ) == V1_ID
