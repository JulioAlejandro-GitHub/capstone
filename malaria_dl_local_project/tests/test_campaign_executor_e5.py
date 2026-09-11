"""Pure E5 process/artifact guard tests; no model construction or PostgreSQL."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from src.malaria_dl.campaigns.contracts import CampaignError, digest
from src.malaria_dl.execution.artifacts import file_identity, verify_session
from src.malaria_dl.execution.campaign import dead_local, parse_args
from test_campaigns_e4 import dataset, expand_matrix, protocol, request


def evidence(tmp_path):
    run = str(uuid4())
    data = dataset()
    cfg = deepcopy(
        next(
            iter(
                expand_matrix(request(), protocol(), frozen=True, dataset=data)[
                    "configurations"
                ].values()
            )
        )["configuration"]
    )
    cfg["resolved"]["execution"]["fine_tune_epochs"] = 0
    p = tmp_path / "epoch_1.keras"
    p.write_bytes(b"synthetic checkpoint")
    selection = {"selected_epoch": 1}
    payloads = {
        ("epoch", "base", "1"): {"epoch": 1},
        ("artifact_prepared", "base", "1"): {"epoch": 1},
        ("artifact", "base", "1"): dict(
            path=str(p), epoch=1, run_id=run, **file_identity(p)
        ),
        ("selection", "base", "1"): selection,
        ("predictions", "base", "1"): {
            "samples": [{"sample": "val/a"}, {"sample": "val/b"}]
        },
        ("phase", "base", "completed"): {"epochs": 1},
        ("runtime", "base", "configuration"): {"synthetic": True},
        ("calibration", "val", "selected"): {"synthetic": True},
    }
    records = [
        {"kind": k[0], "phase": k[1], "record_key": k[2], "payload": v}
        for k, v in sorted(payloads.items())
    ]
    session = {
        "run_id": run,
        "configuration": cfg,
        "dataset": data,
        "artifact_root": str(tmp_path),
        "completion": {
            "epochs": 1,
            "selection": selection,
            "records_hash": digest(records),
        },
    }
    return session, records


def test_valid_checkpoint_requires_loader_and_complete_records(tmp_path):
    s, records = evidence(tmp_path)
    calls = []
    result = verify_session(
        SimpleNamespace(records=lambda _: records), s, lambda p, c: calls.append(p)
    )
    assert result["status"] == "verified" and len(calls) == 1


@pytest.mark.parametrize(
    "kind",
    [
        "epoch",
        "artifact",
        "predictions",
        "runtime",
        "phase",
        "calibration",
        "selection",
        "artifact_prepared",
    ],
)
def test_partial_results_never_verified(tmp_path, kind):
    s, records = evidence(tmp_path)
    records[:] = [r for r in records if r["kind"] != kind]
    s["completion"]["records_hash"] = digest(records)
    with pytest.raises(CampaignError):
        verify_session(SimpleNamespace(records=lambda _: records), s, lambda *_: None)


def test_checkpoint_mutation_and_invalid_load(tmp_path):
    s, records = evidence(tmp_path)

    def bad(*args):
        raise CampaignError("NOT_LOADABLE")

    with pytest.raises(CampaignError, match="NOT_LOADABLE"):
        verify_session(SimpleNamespace(records=lambda _: records), s, bad)
    (tmp_path / "epoch_1.keras").write_bytes(b"altered")
    with pytest.raises(CampaignError, match="CONTENT_CHANGED"):
        verify_session(SimpleNamespace(records=lambda _: records), s, lambda *_: None)


@pytest.mark.parametrize(
    "override", ["--model", "--optimizer", "--seed", "--max-epochs", "--model-config"]
)
def test_campaign_overrides_rejected(override):
    with pytest.raises(SystemExit):
        parse_args(["--campaign-id", str(uuid4()), override, "1"])


def test_inspection_cli_and_unknown_host():
    assert parse_args(["--campaign-id", str(uuid4()), "--inspect"]).inspect
    assert (
        dead_local({"host": "not-this-host", "parent_pid": 1, "child_pid": None})
        is False
    )


def test_migration_has_no_accidental_binds():
    import importlib.util

    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import psycopg

    p = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/20260912_01_train_execution.py"
    )
    spec = importlib.util.spec_from_file_location("e5_migration", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert text(m.DDL).compile(dialect=psycopg.dialect()).construct_params({}) == {}


def test_train_uses_only_train_and_val_without_csv(tmp_path, monkeypatch):
    """Real E5 TRAIN control flow with synthetic adapter/callback processes, no neural fit."""
    import tensorflow as tf
    from src import metrics
    from src.malaria_dl.data import loaders
    from src.malaria_dl.execution.train import train
    from src.malaria_dl.models import adapters
    from src.malaria_dl.training import checkpoint_policy

    roles = []
    predictions = []
    records = []

    class Callback:
        def __init__(self, *a, **k):
            pass

    class Model:
        optimizer = SimpleNamespace(learning_rate=0.1)

        def save(self, path):
            Path(path).write_bytes(b"synthetic")

        def fit(self, data, validation_data, epochs, callbacks):
            assert data.role == "train" and validation_data.role == "val"
            for callback in callbacks:
                callback.model = self
                if hasattr(callback, "on_epoch_end"):
                    callback.on_epoch_end(
                        0,
                        {
                            "val_f2_parasitized": 0.8,
                            "val_recall_parasitized": 0.9,
                            "val_specificity": 0.8,
                            "val_loss": 0.2,
                        },
                    )
            return SimpleNamespace(epoch=[0])

    model = Model()
    monkeypatch.setattr(tf.keras.callbacks, "Callback", Callback)
    monkeypatch.setattr(tf.keras.callbacks, "EarlyStopping", Callback)
    monkeypatch.setattr(tf.keras.callbacks, "ReduceLROnPlateau", Callback)
    monkeypatch.setattr(
        checkpoint_policy, "ClinicalValidationMetricsCallback", Callback
    )
    monkeypatch.setattr(tf.keras.models, "load_model", lambda *a, **k: model)
    monkeypatch.setattr(adapters, "compile_phase", lambda *a, **k: {"synthetic": True})

    def dataset_factory(path, *a, **k):
        role = Path(path).name
        roles.append(role)
        assert role in ("train", "val")
        return SimpleNamespace(role=role, file_paths=[str(path / "a"), str(path / "b")])

    monkeypatch.setattr(loaders, "make_image_dataset_from_directory", dataset_factory)
    monkeypatch.setattr(loaders, "preprocess_physical_dataset", lambda ds, *a, **k: ds)

    def collect(model, ds, **kwargs):
        predictions.append(ds.role)
        assert ds.role == "val"
        return [0, 1], [0, 1], [0.1, 0.9]

    monkeypatch.setattr(metrics, "collect_predictions", collect)
    s, _ = evidence(tmp_path)
    s["artifact_root"] = str(tmp_path / "attempt")
    s["owner"] = str(uuid4())
    s["configuration"]["resolved"]["execution"]["seed"] = 11
    s["configuration"]["resolved"]["execution"]["early_stopping"] = False
    s["configuration"]["resolved"]["execution"]["calibrate_threshold"] = False
    finished = []
    repo = SimpleNamespace(
        put=lambda run, owner, kind, phase, key, payload: records.append(
            {"kind": kind, "phase": phase, "record_key": str(key), "payload": payload}
        ),
        records=lambda run: records,
        finish=lambda *args: finished.append(args),
    )
    descriptor = SimpleNamespace(
        create_adapter=lambda: SimpleNamespace(
            build=lambda config: SimpleNamespace(model=model)
        )
    )
    train(repo, s, descriptor)
    assert roles == ["train", "val"] and predictions == ["val", "val"]
    assert finished[-1][2] == "completed"
    assert not list(tmp_path.rglob("*.csv")) and not list(tmp_path.rglob("*.json"))
