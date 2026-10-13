from dataclasses import FrozenInstanceError
from pathlib import Path
from uuid import uuid4

import pytest

from src.malaria_dl.data.governed_dataset import (
    GovernedDatasetError, GovernedDatasetSnapshot,
    assert_run_dataset_snapshot_unchanged,
)


def _snapshot():
    return GovernedDatasetSnapshot(
        uuid4(), uuid4(), Path("/tmp/version"), "patient", "record",
        "source", "identity", {"train": 1, "val": 1, "test": 1},
    )


def test_snapshot_is_immutable_and_change_is_rejected():
    original = _snapshot()
    with pytest.raises(FrozenInstanceError):
        original.dataset_root = Path("/tmp/other")
    with pytest.raises(GovernedDatasetError, match="RUN_DATASET_SNAPSHOT_IMMUTABLE"):
        assert_run_dataset_snapshot_unchanged(_snapshot(), original)
