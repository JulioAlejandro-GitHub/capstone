"""Synthetic PRE-01/PRE-02 tests; no datasets, downloads, CSV or publication."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
import tensorflow as tf
from src.malaria_dl.data.input_contract import (
    MAPPING,
    InputContractError,
    make_input_contract,
    resolve_checkpoint_input,
    transform_bytes,
    transform_rgb,
    validate_input_contract,
    validate_model_input,
)
from src.malaria_dl.data.preprocessing import (
    resolve_preprocessing_mode,
)
from src.malaria_dl.models.adapters import compile_phase
from src.malaria_dl.models.configuration import resolve_config
from src.malaria_dl.models.registry import resolve_descriptor


def contract(mode="vgg16_imagenet", architecture="vgg16", size=32):
    return make_input_contract(
        architecture,
        "fixture_historical_v1",
        [size, size, 3],
        mode,
        "densenet_imagenet_channel_mean_std" if architecture == "densenet121" else None,
    )


def stored(c):
    return (
        {"mode": c["external"]["mode"], "input_contract": c},
        {"shape": c["shape"], "dtype": "float32"},
        {"shape": [None, 1], "dtype": "float32"},
        deepcopy(MAPPING),
    )


def tiny_model(size=32):
    inputs = tf.keras.Input((size, size, 3))
    outputs = tf.keras.layers.Dense(
        1,
        activation="sigmoid",
        kernel_initializer=tf.keras.initializers.Constant(0.001),
    )(tf.keras.layers.GlobalAveragePooling2D()(inputs))
    return tf.keras.Model(inputs, outputs)


def test_vgg_reference_independent_and_dark_input():
    rgb = np.broadcast_to([10.0, 20.0, 30.0], (32, 32, 3)).astype("float32")
    result = transform_rgb(rgb, contract()).numpy()
    np.testing.assert_allclose(
        result, tf.keras.applications.vgg16.preprocess_input(rgb.copy()), atol=1e-6
    )
    np.testing.assert_allclose(result[0, 0], [-73.939, -96.779, -113.68], atol=1e-5)
    assert not np.allclose(
        result, tf.keras.applications.vgg16.preprocess_input(rgb / 255)
    )
    assert not np.allclose(
        result, tf.keras.applications.vgg16.preprocess_input(result.copy())
    )
    dark = np.broadcast_to([0.1, 0.2, 0.3], (32, 32, 3)).astype("float32")
    np.testing.assert_allclose(
        transform_rgb(dark, contract())[0, 0], [-103.639, -116.579, -123.58], atol=1e-5
    )


def test_new_vgg_resolution_and_historical_auto():
    for mode in ("auto", "vgg16_imagenet"):
        cfg = resolve_config("vgg16", {"model": {"preprocessing": mode}})
        assert cfg["resolved"]["model"]["preprocessing"] == "vgg16_imagenet"
        assert cfg["resolved"]["input_contract"]["external"]["mode"] == "vgg16_imagenet"
    with pytest.raises(ValueError):
        resolve_config("vgg16", {"model": {"preprocessing": "rescale_0_1"}})
    assert resolve_preprocessing_mode("vgg16", "auto") == "rescale_0_1"
    for name in ("custom_cnn", "densenet121"):
        with pytest.raises(ValueError):
            resolve_config(name, {"model": {"preprocessing": "vgg16_imagenet"}})


@pytest.mark.parametrize(
    "change",
    [
        {"source_scale": "0_1"},
        {"channels": 1},
        {"dtype": "float64"},
        {"extra": 1},
        {"resize": {"method": "nearest"}},
    ],
)
def test_invalid_contract(change):
    c = contract()
    c.update(change)
    with pytest.raises(InputContractError):
        validate_input_contract(c)


def test_historical_contract_preserved_and_overrides_rejected(tmp_path):
    c = contract("rescale_0_1")
    original = deepcopy(c)
    model = tiny_model()
    path = tmp_path / "historical.keras"
    model.save(path)
    metadata = tmp_path / "accredited.json"
    metadata.write_text(json.dumps(c))
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (path, metadata)]
    raw = np.random.default_rng(11).integers(0, 256, (32, 32, 3), dtype="uint8")
    loaded = tf.keras.models.load_model(path, compile=False)
    historical = resolve_checkpoint_input(*stored(c), architecture="vgg16", mode="auto")
    validate_model_input(loaded, historical)
    np.testing.assert_array_equal(
        transform_rgb(raw, historical), raw.astype("float32") / 255
    )
    np.testing.assert_allclose(
        loaded(transform_rgb(raw, historical)[None], training=False),
        model((raw.astype("float32") / 255)[None], training=False),
        atol=1e-6,
    )
    resolve_config("vgg16")
    for kwargs in (
        {"mode": "vgg16_imagenet"},
        {"img_size": 224},
        {"architecture": "custom_cnn"},
        {"label_mapping": "legacy_tfds_parasitized_zero"},
    ):
        with pytest.raises(InputContractError):
            resolve_checkpoint_input(*stored(c), **kwargs)
    with pytest.raises(InputContractError):
        resolve_checkpoint_input({"mode": "rescale_0_1"}, stored(c)[1])
    assert c == original
    assert hashes == [
        hashlib.sha256(p.read_bytes()).hexdigest() for p in (path, metadata)
    ]


@pytest.mark.parametrize("architecture", ["custom_cnn", "densenet121"])
def test_other_architectures_unchanged(architecture):
    cfg = resolve_config(
        architecture, {"model": {"weights": "none", "input_shape": [32, 32, 3]}}
    )["resolved"]
    built = resolve_descriptor(architecture).create_adapter().build(cfg)
    validate_model_input(built.model, cfg["input_contract"])
    raw = np.random.default_rng(17).integers(0, 256, (32, 32, 3), dtype="uint8")
    observed = transform_rgb(raw, cfg["input_contract"])
    baseline = raw.astype("float32") / 255
    np.testing.assert_array_equal(observed, baseline)
    np.testing.assert_allclose(
        built.model(observed[None], training=False),
        built.model(baseline[None], training=False),
        atol=1e-6,
    )
    if architecture == "densenet121":
        normalization = built.model.get_layer("densenet_imagenet_normalization")
        np.testing.assert_allclose(
            normalization(observed[None]).numpy()[0],
            tf.keras.applications.densenet.preprocess_input(raw.astype("float32")),
            atol=1e-6,
        )
    tf.keras.backend.clear_session()


@pytest.mark.parametrize("optimizer", ["adam", "adamw", "sgd", "adadelta"])
def test_vgg_four_optimizers_step_reload(optimizer, tmp_path):
    import run_train_all_models as batch

    args = batch.parse_args(["--dataset-version-id", str(uuid4()), "--models", "vgg16"])
    assert {o for _, o, _ in batch.build_matrix(args)} == {
        "adam",
        "adamw",
        "sgd",
        "adadelta",
    }
    cfg = resolve_config(
        "vgg16",
        {
            "model": {"weights": "none", "input_shape": [32, 32, 3]},
            "optimizer": {"name": optimizer},
        },
    )["resolved"]
    adapter = resolve_descriptor("vgg16").create_adapter()
    built = adapter.build(cfg)
    tf.keras.utils.set_random_seed(3)
    x = transform_rgb(
        np.random.default_rng(3).integers(0, 256, (2, 32, 32, 3), dtype="uint8"),
        cfg["input_contract"],
    )
    y = np.array([0.0, 1.0], dtype="float32")
    compile_phase(adapter, built, cfg, "base")
    assert not any(l.trainable for l in built.backbone.layers)
    assert np.isfinite(built.model.train_on_batch(x, y)).all()
    compile_phase(adapter, built, cfg, "fine_tuning")
    assert sum(l.trainable for l in built.backbone.layers) == 4
    assert np.isfinite(built.model.train_on_batch(x, y)).all()
    prediction = built.model(x, training=False).numpy()
    assert np.isfinite(prediction).all()
    path = tmp_path / "vgg.keras"
    built.model.save(path)
    loaded = tf.keras.models.load_model(path)
    validate_model_input(loaded, cfg["input_contract"])
    np.testing.assert_allclose(
        loaded(x, training=False), prediction, rtol=1e-5, atol=1e-6
    )
    assert not list(tmp_path.glob("*.csv"))
    tf.keras.backend.clear_session()


@pytest.mark.parametrize("mode", ["vgg16_imagenet", "rescale_0_1"])
def test_consumer_tensor_and_prediction_equivalence(mode, tmp_path, monkeypatch):
    from src.malaria_dl.data import loaders
    from src.malaria_dl.explainability import pipeline as explain
    from src.malaria_dl.inference.traceable import TraceableInferenceService

    # Application imports use synthetic configuration; no connection is opened.
    monkeypatch.setenv("JWT_SECRET", "synthetic-unit-test-secret-32-characters")
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused:unused@db:5432/capstone")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.syspath_prepend(
        str(Path(__file__).resolve().parents[2] / "backend_api")
    )
    from app.services.cell_classification import CellClassificationService

    c = contract(mode)
    raw = np.random.default_rng(41).integers(0, 256, (47, 39, 3), dtype="uint8")
    content = tf.io.encode_png(raw).numpy()
    for label in ("uninfected", "parasitized"):
        (tmp_path / label).mkdir()
    image_path = tmp_path / "uninfected" / "synthetic.png"
    image_path.write_bytes(content)
    ds = loaders.make_image_dataset_from_directory(tmp_path, 32, 1, False)
    # TRAIN without augmentation, VALIDATION, EVAL and EXPLAIN use this loader.
    batch, _ = next(iter(loaders.preprocess_physical_dataset(ds, mode, augment=False)))
    expected = transform_bytes(content, c).numpy()
    np.testing.assert_allclose(batch[0], expected, rtol=0, atol=1e-5)
    pp, ins, outs, mapping = stored(c)
    resolved = SimpleNamespace(
        preprocessing=pp,
        input_signature=ins,
        output_signature=outs,
        label_mapping=mapping,
        model_name="vgg16",
        input_height=32,
        input_width=32,
        input_channels=3,
    )
    service = CellClassificationService.__new__(CellClassificationService)
    service.preprocessor = None
    service._verified_crop_bytes = lambda item: content
    backend = service._preprocess({}, resolved)
    np.testing.assert_allclose(backend, expected, rtol=0, atol=1e-5)
    model = tiny_model()
    path = tmp_path / "same.keras"
    model.save(path)
    loaded = tf.keras.models.load_model(path, compile=False)
    validate_model_input(loaded, c)
    service._validate_loaded_model_contract(loaded, resolved)
    reference = model(batch, training=False).numpy().reshape(-1)[0]
    from src.malaria_dl.evaluation.evaluator import collect_predictions

    _, _, eval_scores = collect_predictions(
        loaded, loaders.preprocess_physical_dataset(ds, mode, augment=False)
    )
    np.testing.assert_allclose(eval_scores, [reference], atol=1e-6)
    np.testing.assert_allclose(
        loaded(backend[None], training=False), [[reference]], atol=1e-6
    )
    np.testing.assert_allclose(
        TraceableInferenceService._predict(loaded, image_path, pp, ins),
        reference,
        atol=1e-6,
    )
    display = explain.model_image_to_display(expected, mode)
    resized = tf.image.resize(tf.cast(raw, tf.float32), (32, 32)).numpy() / 255
    np.testing.assert_allclose(display, resized, atol=1e-6)
    np.testing.assert_allclose(
        explain.display_images_to_model_inputs(display[None], mode), batch, atol=2e-5
    )
    np.testing.assert_allclose(
        explain.predict_positive_scores(loaded, batch, 1), [reference], atol=1e-6
    )
    np.testing.assert_allclose(
        explain.binary_predict_proba(loaded, display[None], 1, mode)[:, 1],
        [reference],
        atol=1e-6,
    )
    assert not list(tmp_path.rglob("*.csv"))


def test_vgg_augmentation_before_preprocessing_only_on_train(monkeypatch):
    from src.malaria_dl.data import loaders

    raw = tf.ones((1, 32, 32, 3), tf.float32) * 20

    def augmentation(images, training):
        assert training is True
        tf.debugging.assert_equal(images, raw)
        return images + 10

    monkeypatch.setattr(loaders, "build_augmentation", lambda: augmentation)
    ds = tf.data.Dataset.from_tensors((raw, tf.constant([1.0])))
    train, _ = next(
        iter(loaders.preprocess_physical_dataset(ds, "vgg16_imagenet", augment=True))
    )
    validation, _ = next(
        iter(loaders.preprocess_physical_dataset(ds, "vgg16_imagenet", augment=False))
    )
    np.testing.assert_array_equal(
        train, tf.keras.applications.vgg16.preprocess_input(raw + 10)
    )
    np.testing.assert_array_equal(
        validation, tf.keras.applications.vgg16.preprocess_input(raw)
    )


def test_loaded_signature_and_double_normalization_rejected():
    with pytest.raises(InputContractError):
        validate_model_input(tiny_model(64), contract())
    inputs = tf.keras.Input((32, 32, 3))
    x = tf.keras.layers.Rescaling(1 / 255)(inputs)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    model = tf.keras.Model(inputs, tf.keras.layers.Dense(1, activation="sigmoid")(x))
    with pytest.raises(InputContractError, match="UNDECLARED_INTERNAL_NORMALIZATION"):
        validate_model_input(model, contract())


@pytest.mark.parametrize("consumer", ["evaluate", "explain"])
@pytest.mark.parametrize("failure", ["missing", "override"])
def test_consumer_main_blocks_before_load_or_predict(
    consumer, failure, tmp_path, monkeypatch
):
    from unittest.mock import Mock
    from src.malaria_dl.assessment import service
    from src.malaria_dl.assessment.contracts import AssessmentError
    from test_assessment_e6 import value

    v = value(tmp_path)
    c = contract("rescale_0_1")
    v["model"]["input_contract"] = None if failure == "missing" else c
    monkeypatch.setattr(service, "resolve", lambda *a: (v["model"], v["dataset"], None))
    monkeypatch.setattr(service, "dataset_samples", lambda *a, **kw: v["samples"])
    monkeypatch.setattr(service, "inference_environment", lambda *a: {"source":"synthetic"})
    loader = Mock(side_effect=AssertionError("must reject before model load"))
    monkeypatch.setattr(tf.keras.models, "load_model", loader)
    with pytest.raises((InputContractError, AssessmentError)):
        service.prepare(None, split="val", purpose="development", protocol=v["protocol"], requested_threshold=".5", seed=42, batch_size=2,
            input_override=contract("vgg16_imagenet") if failure=="override" else None,
            explanation={"method":"gradcam"} if consumer=="explain" else None)
    loader.assert_not_called()
    assert not list(tmp_path.rglob("*.csv"))
