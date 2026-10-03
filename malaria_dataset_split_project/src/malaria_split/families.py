"""Dataset Families known to the split subsystem.

A family is recorded in ``datasets.metadata.dataset_family`` for new sources. The
historical cell-classification source predates the concept and is recognised by its
frozen name, so its ``datasets`` row is never rewritten.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from malaria_split.persistence.bootstrap import SOURCE_NAME as CELL_IMAGES_SOURCE_NAME


class DatasetFamily(StrEnum):
    CELL_CLASSIFICATION = "cell_classification"
    SMEAR_SEGMENTATION = "smear_segmentation"


@dataclass(frozen=True, slots=True)
class DatasetSourceSpec:
    family: DatasetFamily
    slug: str
    name: str


THIN_BLOOD_SMEARS_PF_SOURCE_NAME = "NIH/NLM ThinBloodSmearsPf"

SOURCES: tuple[DatasetSourceSpec, ...] = (
    DatasetSourceSpec(
        DatasetFamily.CELL_CLASSIFICATION, "nih_nlm_malaria_cell_images", CELL_IMAGES_SOURCE_NAME
    ),
    DatasetSourceSpec(
        DatasetFamily.SMEAR_SEGMENTATION, "thin_blood_smears_pf", THIN_BLOOD_SMEARS_PF_SOURCE_NAME
    ),
)


def get_source(family: str, slug: str) -> DatasetSourceSpec:
    """Return the registered source, rejecting unknown or mismatched family/source pairs."""
    resolved_family = DatasetFamily(family)
    for spec in SOURCES:
        if spec.slug == slug:
            if spec.family is not resolved_family:
                raise ValueError(f"Source {slug!r} belongs to family {spec.family.value!r}")
            return spec
    raise ValueError(f"Unknown dataset source {slug!r}")


def resolve_dataset_family(
    name: str, metadata: Mapping[str, Any] | None
) -> DatasetFamily | None:
    declared = (metadata or {}).get("dataset_family")
    if declared:
        return DatasetFamily(declared)
    for spec in SOURCES:
        if spec.name == name:
            return spec.family
    return None
