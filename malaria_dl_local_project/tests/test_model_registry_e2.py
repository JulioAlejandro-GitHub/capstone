"""E2 synthetic tests; no downloads, operational dataset or result writers."""

from dataclasses import replace
import json
import subprocess
import sys
from types import SimpleNamespace
from contextlib import nullcontext
from uuid import uuid4
import pytest
import run_train_all_models as batch
from src.malaria_dl.models import registry as reg
from src.malaria_dl.models.configuration import resolve_config
from src.malaria_dl.models.optimizers import OPTIMIZER_DEFAULTS, optimizer_config
from src.malaria_dl.training.cli import parse_args
from src.malaria_dl.persistence import model_configuration as persistence

UUID = "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"


class TinyAdapter:
    def build(self, config):
        import tensorflow as tf
        from src.malaria_dl.models.adapters import AdapterResult

        inputs = tf.keras.Input(tuple(config["model"]["input_shape"]))
        m = config["model"]
        x = tf.keras.layers.GlobalAveragePooling2D()(inputs)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Dense(
            m["head_units"],
            activation="relu",
            kernel_regularizer=tf.keras.regularizers.l2(m["l2"]),
        )(x)
        x = tf.keras.layers.Dropout(m["dropout"])(x)
        outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
        return AdapterResult(
            tf.keras.Model(inputs, outputs),
            None,
            {"shape": config["model"]["input_shape"]},
            {"shape": [None, 1]},
            ("base",),
        )

    def set_phase(self, built, config, phase):
        assert phase == "base"
        return built.trainable_layers()


def test_lazy_cli():
    code = (
        "from src.malaria_dl.training.cli import parse_args; import sys; parse_args(['--model','custom_cnn','--dataset-version-id','"
        + UUID
        + "']); assert 'tensorflow' not in sys.modules"
    )
    subprocess.run([sys.executable, "-B", "-c", code], check=True)


def test_discovery_and_descriptor_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(reg, "MODEL_REGISTRY", reg.MODEL_REGISTRY.copy())
    tiny = replace(
        reg.resolve_descriptor("custom_cnn"),
        id="synthetic",
        adapter="test_model_registry_e2:TinyAdapter",
    )
    reg.register(tiny)
    reg.register(replace(tiny, id="disabled", enabled=False))
    reg.register(replace(tiny, id="not_trainable", trainable=False))
    matrix = batch.build_matrix(batch.parse_args(["--dataset-version-id", UUID]))
    assert len(matrix) == 16
    assert {m for m, _, _ in matrix} == set(reg.enabled_models())
    assert (
        parse_args(["--model", "synthetic", "--dataset-version-id", UUID]).model
        == "synthetic"
    )
    from src.malaria_dl.models.adapters import compile_phase
    import numpy as np
    import tensorflow as tf

    config = resolve_config("synthetic", {"model": {"input_shape": [32, 32, 3]}})[
        "resolved"
    ]
    adapter = reg.resolve_descriptor("synthetic").create_adapter()
    built = adapter.build(config)
    compile_phase(adapter, built, config, "base")
    x = np.ones((2, 32, 32, 3), dtype="float32")
    assert np.isfinite(built.model.train_on_batch(x, np.array([0.0, 1.0]))).all()
    built.model.save(tmp_path / "tiny.keras")
    loaded = tf.keras.models.load_model(tmp_path / "tiny.keras")
    np.testing.assert_allclose(loaded(x).numpy(), built.model(x).numpy(), atol=1e-6)
    for name in ("disabled", "not_trainable", "unknown"):
        with pytest.raises(ValueError):
            reg.resolve_descriptor(name)
    for d in (
        tiny,
        replace(tiny, id="ambiguous", aliases=("custom_cnn",)),
        replace(tiny, id="incomplete", version=""),
    ):
        with pytest.raises(ValueError):
            reg.register(d)


def test_matrix_and_identical_child_resolution():
    matrix = batch.build_matrix(batch.parse_args(["--dataset-version-id", UUID]))
    assert len(matrix) == 12
    assert ("vgg16", "sgd") in [(m, o) for m, o, _ in matrix]
    for model, opt, cmd in matrix:
        child = parse_args(cmd[3:])
        assert (
            child.model == model
            and child.optimizer == opt
            and child.dataset_version_id == UUID
        )
        assert child.max_epochs == 100
    args = batch.parse_args(
        [
            "--dataset-version-id",
            UUID,
            "--models",
            "vgg16_transfer_learning",
            "--optimizers",
            "sgd",
        ]
    )
    assert [(m, o) for m, o, _ in batch.build_matrix(args)] == [("vgg16", "sgd")]


@pytest.mark.parametrize(
    "selected",
    [
        {"extra": 1},
        {"model": {"dropout": float("nan")}},
        {"model": {"l2": float("inf")}},
        {"optimizer": {"parameters": {"learning_rate": 0}}},
        {"optimizer": {"parameters": {"learning_rate": True}}},
        {"optimizer": {"parameters": {"momentum": 0.9}}},
        {"execution": {"fine_tune_epochs": 1}},
        {"execution": {"beta": 2.5}},
        {"execution": {"batch_size": "64"}},
        {"model": {"head_units": 99}},
        {"model": {"weights": "imagenet"}},
        {"model": {"input_shape": [31, 31, 3]}},
    ],
)
def test_invalid_config_before_adapter(selected):
    with pytest.raises((ValueError, TypeError)):
        resolve_config("custom_cnn", selected)


def test_precedence_requested_resolved_and_tracking(tmp_path):
    path = tmp_path / "selected.json"
    path.write_text(
        json.dumps(
            {
                "execution": {"max_epochs": 7, "batch_size": 3},
                "optimizer": {"parameters": {"learning_rate": 0.002}},
            }
        )
    )
    args = parse_args(
        [
            "--model",
            "custom_cnn",
            "--dataset-version-id",
            UUID,
            "--model-config",
            str(path),
            "--max-epochs",
            "9",
        ]
    )
    assert (
        args.max_epochs == 9
        and args.batch_size == 3
        and args.learning_rate == 0.002
        and args.track_db
    )
    assert (
        args.model_configuration["requested"]["selected"]["execution"]["max_epochs"]
        == 7
    )
    assert args.model_configuration["resolved"]["execution"]["max_epochs"] == 9
    assert (
        resolve_config("vgg16")["resolved"]["model"]["preprocessing"] == "vgg16_imagenet"
    )


def test_beta_rejected_in_cli_and_policy():
    from src.checkpoint_policy import CheckpointPolicyConfig

    with pytest.raises(SystemExit):
        parse_args(
            ["--model", "custom_cnn", "--dataset-version-id", UUID, "--beta", "2.5"]
        )
    with pytest.raises(ValueError):
        CheckpointPolicyConfig(beta=2.5)


@pytest.mark.parametrize("name", tuple(OPTIMIZER_DEFAULTS))
def test_optimizer_config(name):
    from src.malaria_dl.models.optimizers import build_optimizer

    config = optimizer_config(name)
    optimizer = build_optimizer(name, config=config)
    assert float(optimizer.learning_rate.numpy()) == pytest.approx(
        config["learning_rate"]
    )
    if name == "sgd":
        assert optimizer.momentum == 0.9
    if name == "adamw":
        assert optimizer.weight_decay == 0.004


@pytest.mark.parametrize("name", ("custom_cnn", "vgg16", "densenet121"))
def test_real_adapters_step_and_reload(name, tmp_path):
    import numpy as np
    import tensorflow as tf
    from src.malaria_dl.models.adapters import compile_phase

    tf.keras.utils.set_random_seed(17)
    config = resolve_config(
        name,
        {
            "model": {"weights": "none", "input_shape": [32, 32, 3]},
            "execution": {"no_augment": True},
        },
    )["resolved"]
    adapter = reg.resolve_descriptor(name).create_adapter()
    built = adapter.build(config)
    assert built.model.output_shape == (None, 1)
    assert getattr(built.model, "optimizer", None) is None
    x = np.random.default_rng(17).random((2, 32, 32, 3), dtype=np.float32)
    y = np.array([0.0, 1.0], dtype=np.float32)
    for optimizer in OPTIMIZER_DEFAULTS:
        if getattr(built.model, "optimizer", None) is not None:
            built = adapter.build(config)
        config["optimizer"]["name"] = optimizer
        config["optimizer"]["parameters"] = optimizer_config(optimizer)
        runtime = compile_phase(adapter, built, config, "base")
        if built.backbone is not None:
            assert not any(layer.trainable for layer in built.backbone.layers)
        assert np.isfinite(built.model.train_on_batch(x, y)).all()
        assert runtime["loss"]["name"] == "binary_crossentropy"
        assert runtime["loss"]["from_logits"] is False
        assert runtime["loss"]["reduction"] == "sum_over_batch_size"
    if built.backbone is not None:
        previous = built.model.optimizer
        compile_phase(adapter, built, config, "fine_tuning")
        assert built.model.optimizer is not previous
        assert sum(layer.trainable for layer in built.backbone.layers) == 4
        assert np.isfinite(built.model.train_on_batch(x, y)).all()
    expected = built.model(x, training=False).numpy()
    checkpoint = tmp_path / "model.keras"
    built.model.save(checkpoint)
    loaded = tf.keras.models.load_model(checkpoint)
    np.testing.assert_allclose(
        loaded(x, training=False).numpy(), expected, rtol=1e-5, atol=1e-6
    )
    assert not list(tmp_path.glob("*.csv"))
    tf.keras.backend.clear_session()


def test_persistence_roundtrip_failure_no_files(monkeypatch, tmp_path):
    store = {}

    class Connection:
        def execute(self, sql, params):
            if "UPDATE" in str(sql):
                store["value"] = json.loads(params["snapshot"])
                return SimpleNamespace(scalar_one_or_none=lambda: params["id"])
            return SimpleNamespace(scalar_one_or_none=lambda: store.get("value"))

    engine = SimpleNamespace(
        begin=lambda: nullcontext(Connection()), dispose=lambda: None
    )
    monkeypatch.setattr(persistence, "get_engine", lambda: engine)
    monkeypatch.setattr(
        persistence, "dataset_read_connection", lambda: nullcontext(Connection())
    )
    monkeypatch.setattr(
        persistence, "environment_identity", lambda: {"synthetic": True}
    )
    result = persistence.persist_model_configuration(
        str(uuid4()),
        resolve_config("custom_cnn"),
        {"base": {}},
        {"dataset_version_id": UUID},
        {},
    )
    assert result == store["value"]
    monkeypatch.setattr(
        persistence,
        "get_engine",
        lambda: (_ for _ in ()).throw(RuntimeError("unavailable")),
    )
    with pytest.raises(
        persistence.ModelConfigurationPersistenceError, match="PERSISTENCE_FAILED"
    ):
        persistence.persist_model_configuration(
            str(uuid4()),
            resolve_config("custom_cnn"),
            {},
            {"dataset_version_id": UUID},
            {},
        )
    assert list(tmp_path.iterdir()) == []


def test_persistence_failure_blocks_fit(monkeypatch, tmp_path):
    from unittest.mock import Mock
    from src.malaria_dl.training import trainer
    from src.malaria_dl.persistence import tracking

    args = parse_args(
        [
            "--model",
            "custom_cnn",
            "--dataset-version-id",
            UUID,
            "--output-dir",
            str(tmp_path),
        ]
    )
    snapshot = SimpleNamespace(
        dataset_version_id=UUID,
        dataset_root=tmp_path,
        metadata=lambda: {"dataset_version_id": UUID},
    )
    monkeypatch.setattr(
        trainer, "verify_dataset_for_execution", lambda *a, **k: snapshot
    )
    monkeypatch.setattr(trainer, "dataset_tracking_metadata", lambda *a, **k: {})
    monkeypatch.setattr(trainer, "bind_dataset_evidence_to_run", lambda *a: None)
    monkeypatch.setattr(
        tracking, "start_tracking_run", lambda **k: {"run_id": str(uuid4())}
    )
    monkeypatch.setattr(tracking, "fail_tracking_run", lambda *a, **k: None)
    model = Mock()
    built = SimpleNamespace(model=model, backbone=None)
    descriptor = SimpleNamespace(
        internal_preprocessing=None,
        create_adapter=lambda: SimpleNamespace(build=lambda config: built),
    )
    monkeypatch.setattr(trainer, "resolve_descriptor", lambda name: descriptor)
    monkeypatch.setattr(
        trainer, "load_malaria_splits", lambda **k: (None, None, None, None)
    )
    monkeypatch.setattr(trainer, "compile_phase", lambda *a: {"phase": "base"})
    monkeypatch.setattr(trainer, "build_phase_callbacks", lambda **k: [])
    monkeypatch.setattr(trainer, "acquire_training_output_lock", lambda p: None)
    monkeypatch.setattr(trainer, "stage_latest_run_artifacts", lambda *a: None)
    monkeypatch.setattr(trainer, "restore_latest_artifact_backup", lambda *a: None)
    failure = Mock(
        side_effect=persistence.ModelConfigurationPersistenceError(
            "MODEL_CONFIGURATION_PERSISTENCE_FAILED"
        )
    )
    monkeypatch.setattr(trainer, "persist_model_configuration", failure)
    with pytest.raises(persistence.ModelConfigurationPersistenceError):
        trainer.main(args)
    assert failure.call_count == 1
    model.fit.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_f2_and_monitor_semantics():
    import numpy as np
    from src.metrics import compute_clinical_metrics

    metrics = compute_clinical_metrics(
        np.array([1, 1, 0, 0]), np.array([0.9, 0.1, 0.2, 0.1])
    )
    assert metrics["f2_parasitized"] == pytest.approx(5 / 9)
    config = resolve_config(
        "custom_cnn",
        {
            "execution": {
                "checkpoint_policy": "auc_with_min_recall",
                "checkpoint_monitor": "val_f2_parasitized",
            }
        },
    )
    selection = config["resolved"]["selection"]
    assert selection["monitor"] == "val_f2_parasitized" and selection["explicit"]
    assert selection["early_stopping_monitor"] == "val_f2_parasitized"
    assert selection["threshold"] == 0.5


def test_matrix_invalid_combination_rejected_before_preflight(monkeypatch):
    from unittest.mock import Mock

    args = batch.parse_args(["--dataset-version-id", UUID, "--batch-size", "0"])
    monkeypatch.setattr(batch, "parse_args", lambda: args)
    verify = Mock()
    monkeypatch.setattr(batch, "verify_dataset_for_execution", verify)
    with pytest.raises(ValueError):
        batch.main()
    verify.assert_not_called()


def test_clinical_target_independent_of_technical_selection():
    from src.malaria_dl.training.trainer import clinical_objective_status

    summary = {
        "policy_satisfied": True,
        "selected_metrics": {"val_recall_parasitized": 0.9},
    }
    assert clinical_objective_status(summary, 0.98)["attained"] is False
    summary["selected_metrics"]["val_recall_parasitized"] = 1.0
    summary["all_epochs_collapsed"] = True
    assert clinical_objective_status(summary, 0.98)["attained"] is False
    assert clinical_objective_status({}, 0.98)["attained"] is None


def test_explicit_loss_matches_legacy_function():
    import tensorflow as tf
    from src.malaria_dl.models.architectures import compile_binary_model

    model = tf.keras.Sequential(
        [tf.keras.Input((1,)), tf.keras.layers.Dense(1, activation="sigmoid")]
    )
    compile_binary_model(model)
    y = tf.constant([[0.0], [1.0]])
    scores = tf.constant([[0.2], [0.7]])
    expected = tf.reduce_mean(tf.keras.losses.binary_crossentropy(y, scores))
    assert float(model.loss(y, scores)) == pytest.approx(float(expected))


def test_persistence_rejects_changed_readback(monkeypatch):
    engine = SimpleNamespace(
        begin=lambda: nullcontext(
            SimpleNamespace(
                execute=lambda *a, **k: SimpleNamespace(scalar_one_or_none=lambda: UUID)
            )
        ),
        dispose=lambda: None,
    )
    monkeypatch.setattr(persistence, "get_engine", lambda: engine)
    monkeypatch.setattr(
        persistence, "environment_identity", lambda: {"synthetic": True}
    )
    monkeypatch.setattr(
        persistence,
        "dataset_read_connection",
        lambda: nullcontext(
            SimpleNamespace(
                execute=lambda *a, **k: SimpleNamespace(
                    scalar_one_or_none=lambda: {"tampered": True}
                )
            )
        ),
    )
    with pytest.raises(persistence.ModelConfigurationPersistenceError):
        persistence.persist_model_configuration(
            UUID, resolve_config("custom_cnn"), {}, {"dataset_version_id": UUID}, {}
        )
