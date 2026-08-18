from dataclasses import FrozenInstanceError
from pathlib import Path
from uuid import uuid4

import pytest

from run_train_all_models import build_train_command
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


def test_orchestrator_propagates_only_dataset_version_selection():
    version = str(uuid4())
    command = build_train_command("custom_cnn", "adam", 1, 32, 2, 42,
                                  version, .98, 2)
    assert command[command.index("--dataset-version-id") + 1] == version
    assert "--dataset-dir" not in command
