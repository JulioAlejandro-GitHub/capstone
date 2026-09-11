"""Synthetic E6 contracts and failure recovery; no database or scientific inference."""

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from src.malaria_dl.assessment.contracts import (
    AssessmentError,
    identity,
    prediction,
    threshold,
    verify_rows,
)
from src.malaria_dl.assessment.service import explanation_spec, run
from src.malaria_dl.campaigns.contracts import digest
from src.malaria_dl.data.input_contract import make_input_contract
from src.malaria_dl.execution.artifacts import file_identity


def value(tmp_path):
    p = tmp_path / "synthetic.keras"
    p.write_bytes(b"synthetic checkpoint")
    model = {
        "training_run_id": str(uuid4()),
        "model_version_id": str(uuid4()),
        "checkpoint_artifact_id": str(uuid4()),
        "path": str(p),
        **file_identity(p),
        "input_contract": make_input_contract(
            "custom_cnn", "1", [8, 8, 3], "rescale_0_1"
        ),
    }
    samples = [
        {
            "sample_id": str(uuid4()),
            "patient_id": str(uuid4()),
            "label": i,
            "split": "val",
            "sha256": "a" * 64,
            "relative_path": f"val/{i}.png",
        }
        for i in (0, 1)
    ]
    protocol = {
        "version": "synthetic_v1",
        "splits": ["val"],
        "purposes": ["development"],
        "allowed_numeric_thresholds": [0.5, 0.7],
    }
    return identity(
        model,
        {"dataset_version_id": str(uuid4()), "dataset_root": str(tmp_path)},
        samples,
        split="val",
        purpose="development",
        protocol=protocol,
        decision=threshold(".5", protocol),
        code={"source": "synthetic"},
        seed=42,
        batch_size=1,
    )


class MemoryRepository:
    def __init__(self):
        self.attempts = {}
        self.identities = {}
        self.rows = {}
        self.files = {}

    def reserve(self, v, root):
        key = digest(v)
        for a in self.attempts.values():
            if a["identity_id"] == key and a["state"] in ("active", "verified"):
                return deepcopy(a), False
        aid = str(uuid4())
        self.identities[key] = deepcopy(v)
        a = {
            "id": aid,
            "identity_id": key,
            "owner": str(uuid4()),
            "state": "active",
            "verification": None,
            "artifact_root": str(Path(root) / aid),
        }
        self.attempts[aid] = a
        self.rows[aid] = {}
        self.files[aid] = []
        return deepcopy(a), True

    def attempt(self, aid):
        return deepcopy(self.attempts[aid])

    def identity(self, key):
        return deepcopy(self.identities[key])

    def results(self, aid):
        return deepcopy(list(self.rows[aid].values()))

    def artifacts(self, aid):
        return sorted(
            deepcopy(self.files[aid]), key=lambda a: (a["sample_id"], a["role"])
        )

    def write_batch(self, aid, owner, rows):
        assert (
            self.attempts[aid]["owner"] == owner
            and self.attempts[aid]["state"] == "active"
        )
        for r in rows:
            assert (
                r["sample_id"] not in self.rows[aid]
                or self.rows[aid][r["sample_id"]] == r
            )
            self.rows[aid][r["sample_id"]] = deepcopy(r)

    def artifact(self, aid, owner, payload):
        self.files[aid].append(deepcopy(payload))

    def finish(self, aid, owner, state, verification=None, cause=None):
        assert (
            self.attempts[aid]["owner"] == owner
            and self.attempts[aid]["state"] == "active"
        )
        self.attempts[aid].update(state=state, verification=verification, cause=cause)


class Runtime:
    calls = 0

    def __init__(self, v):
        self.v = v

    def predict(self, samples):
        type(self).calls += 1
        return [0.2 if s["label"] == 0 else 0.8 for s in samples]

    def explain(self, s):
        import numpy as np

        return (
            np.zeros((8, 8)),
            np.zeros((8, 8, 3)),
            {"score_explained": "raw", "class": 1},
        )


def test_exact_reuse_does_not_predict(tmp_path):
    repo = MemoryRepository()
    v = value(tmp_path)
    Runtime.calls = 0
    a = run(repo, v, tmp_path, Runtime)
    b = run(repo, v, tmp_path, Runtime)
    assert a["id"] == b["id"] and Runtime.calls == 2 and a["state"] == "verified"
    assert a["verification"]["metrics"]["confusion_matrix"] == [[1, 0], [0, 1]]
    assert not list(tmp_path.glob("*.csv"))


@pytest.mark.parametrize(
    "field", ["decision", "samples", "protocol", "model", "code", "seed"]
)
def test_identity_changes(field, tmp_path):
    v = value(tmp_path)
    other = deepcopy(v)
    if field == "decision":
        other[field]["effective"] = 0.7
    elif field == "samples":
        other[field] = other[field][:1]
    elif field == "seed":
        other[field] += 1
    else:
        other[field]["version"] = "changed"
    assert digest(v) != digest(other)


def test_partial_failure_retry_new_attempt(tmp_path):
    repo = MemoryRepository()
    v = value(tmp_path)

    class Broken(Runtime):
        calls = 0

        def predict(self, samples):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("synthetic interruption")
            return super().predict(samples)

    with pytest.raises(RuntimeError, match="synthetic"):
        run(repo, v, tmp_path, Broken)
    old = next(iter(repo.attempts.values()))
    assert old["state"] == "failed" and len(repo.results(old["id"])) == 1
    new = run(repo, v, tmp_path, Runtime)
    assert (
        new["state"] == "verified"
        and new["id"] != old["id"]
        and new["artifact_root"] != old["artifact_root"]
    )


def test_active_response_no_predict(tmp_path):
    repo = MemoryRepository()
    v = value(tmp_path)
    a, _ = repo.reserve(v, tmp_path)
    assert (
        run(repo, v, tmp_path, lambda v: pytest.fail("predict forbidden"))["id"]
        == a["id"]
    )


@pytest.mark.parametrize("fault", ["missing", "changed", "results"])
def test_corruption_never_reused(tmp_path, fault):
    repo = MemoryRepository()
    v = value(tmp_path)
    a = run(repo, v, tmp_path, Runtime)
    if fault == "missing":
        Path(v["model"]["path"]).unlink()
    elif fault == "changed":
        Path(v["model"]["path"]).write_bytes(b"corrupt")
    else:
        repo.rows[a["id"]].pop(v["samples"][0]["sample_id"])
    with pytest.raises(ValueError):
        run(repo, v, tmp_path, Runtime)


def test_threshold_no_implicit_clinical_fallback():
    with pytest.raises(AssessmentError):
        threshold("clinical", {})
    with pytest.raises(AssessmentError):
        threshold(".5", {})
    calibration = {
        "result": {
            "schema_version": 1,
            "calibration_split": "val",
            "positive_class_index": 1,
            "threshold_source": "validation_calibration",
            "threshold_selected": 0.63,
            "threshold_used": 0.63,
        }
    }
    assert threshold("clinical", {}, calibration)["effective"] == 0.63


def test_test_forbidden_development(tmp_path):
    v = value(tmp_path)
    with pytest.raises(AssessmentError, match="TEST"):
        identity(
            v["model"],
            v["dataset"],
            v["samples"],
            split="test",
            purpose="development",
            protocol={"version": "x", "splits": ["test"], "purposes": ["development"]},
            decision=v["decision"],
            code={},
            seed=1,
            batch_size=1,
        )


def test_explanations_artifacts_separate_and_tamper_rejected(tmp_path):
    repo = MemoryRepository()
    v = value(tmp_path)
    v.update(
        kind="explain", explanation=explanation_spec("gradcam", "conv", 1, None, [])
    )
    a = run(repo, v, tmp_path, Runtime)
    assert a["state"] == "verified" and len(repo.artifacts(a["id"])) == 4
    v2 = deepcopy(v)
    v2["seed"] += 1
    b = run(repo, v2, tmp_path, Runtime)
    assert a["artifact_root"] != b["artifact_root"]
    assert {x["path"] for x in repo.artifacts(a["id"])}.isdisjoint(
        x["path"] for x in repo.artifacts(b["id"])
    )
    Path(repo.artifacts(a["id"])[0]["path"]).write_bytes(b"corrupt")
    with pytest.raises(AssessmentError):
        run(repo, v, tmp_path, Runtime)


def test_reconstruction_rejects_conflicting_labels(tmp_path):
    v = value(tmp_path)
    rows = [prediction(s, 0.4, v["decision"]) for s in v["samples"]]
    rows[0]["patient_id"] = str(uuid4())
    with pytest.raises(AssessmentError):
        verify_rows(v, rows)


def test_artifact_write_failure_never_verified(tmp_path, monkeypatch):
    repo = MemoryRepository()
    v = value(tmp_path)
    v.update(
        kind="explain", explanation=explanation_spec("gradcam", "conv", 1, None, [])
    )

    def fail(*args):
        raise RuntimeError("synthetic database failure")

    monkeypatch.setattr(repo, "artifact", fail)
    with pytest.raises(RuntimeError):
        run(repo, v, tmp_path, Runtime)
    a = next(iter(repo.attempts.values()))
    assert (
        a["state"] == "failed"
        and list(Path(a["artifact_root"]).glob("*.png"))
        and not a["verification"]
    )


@pytest.mark.parametrize(
    "architecture,mode",
    [
        ("custom_cnn", "rescale_0_1"),
        ("vgg16", "vgg16_imagenet"),
        ("vgg16", "rescale_0_1"),
        ("densenet121", "rescale_0_1"),
    ],
)
def test_minimal_model_uses_exact_e3_input(tmp_path, architecture, mode):
    import numpy as np
    import tensorflow as tf
    from PIL import Image
    from src.malaria_dl.assessment.runtime import KerasRuntime
    from src.malaria_dl.data.input_contract import INTERNAL_DENSENET, transform_rgb

    v = value(tmp_path)
    contract = make_input_contract(
        architecture,
        "synthetic_v1",
        [8, 8, 3],
        mode,
        INTERNAL_DENSENET if architecture == "densenet121" else None,
    )
    inputs = tf.keras.Input((8, 8, 3))
    x = inputs
    if architecture == "densenet121":
        x = tf.keras.layers.Normalization(
            mean=[0.485, 0.456, 0.406],
            variance=np.square([0.229, 0.224, 0.225]),
            name="densenet_imagenet_normalization",
        )(x)
    x = tf.keras.layers.Conv2D(2, 3, name="conv")(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    model = tf.keras.Model(inputs, outputs)
    model.save(v["model"]["path"])
    v["model"].update(file_identity(v["model"]["path"]), input_contract=contract)
    sample = v["samples"][0]
    path = tmp_path / sample["relative_path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = np.full((8, 8, 3), [180, 100, 50], dtype=np.uint8)
    Image.fromarray(rgb).save(path)
    sample["sha256"] = file_identity(path)["sha256"]
    runtime = KerasRuntime(v)
    np.testing.assert_allclose(
        runtime.images([sample]).numpy()[0],
        transform_rgb(rgb, contract).numpy(),
        atol=1e-6,
    )
    assert len(runtime.predict([sample])) == 1
    if architecture == "custom_cnn":
        v["explanation"] = explanation_spec("gradcam", "conv", 1, None, [])
        heat, overlay, result = runtime.explain(sample)
        assert (
            heat.shape == (8, 8)
            and overlay.shape == (8, 8, 3)
            and result["score_explained"] == "raw"
        )


def test_not_loadable_checkpoint_rejected(tmp_path):
    from src.malaria_dl.assessment.runtime import KerasRuntime

    repo = MemoryRepository()
    with pytest.raises(ValueError):
        run(repo, value(tmp_path), tmp_path, KerasRuntime)
    assert next(iter(repo.attempts.values()))["state"] == "failed"


def test_exact_e5_binding_and_cross_version_rejected(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace

    from src.malaria_dl.assessment import lineage
    from src.malaria_dl.execution.artifacts import verify_session
    from test_campaign_executor_e5 import evidence

    session, records = evidence(tmp_path)
    version = str(uuid4())
    for r in records:
        if r["kind"] == "artifact":
            r["payload"]["version_id"] = version
        if r["kind"] == "calibration":
            r["payload"]["checkpoint_epoch"] = 1
    session["completion"]["records_hash"] = digest(records)
    session["verification"] = verify_session(
        SimpleNamespace(records=lambda _: records), session, lambda *_: None
    )
    session["state"] = "verified"
    result = SimpleNamespace(mappings=lambda: [session])
    monkeypatch.setattr(lineage, "execute", lambda *a, **k: result)
    monkeypatch.setattr(
        lineage,
        "ExecutionRepository",
        lambda scope: SimpleNamespace(records=lambda _: records),
    )
    repo = SimpleNamespace(transaction=lambda **kw: nullcontext(None), scope=None)
    binding, dataset, _ = lineage.resolve(repo, session["run_id"], version)
    assert binding["model_version_id"] == version and dataset == session["dataset"]
    assert binding == lineage.resolve(repo, session["run_id"])[0]
    with pytest.raises(AssessmentError, match="MODEL_VERSION_TRAIN_CONFLICT"):
        lineage.resolve(repo, session["run_id"], str(uuid4()))


def test_dataset_override_rejected_before_verifier(tmp_path, monkeypatch):
    from src.malaria_dl.assessment import lineage

    monkeypatch.setattr(
        lineage,
        "verify_dataset_for_execution",
        lambda *a, **kw: pytest.fail("must reject first"),
    )
    with pytest.raises(AssessmentError, match="DATASET_OVERRIDE_CONFLICT"):
        lineage.dataset_samples(
            None, {"dataset_version_id": str(uuid4())}, "val", str(uuid4())
        )


def test_prepare_rejects_input_and_foreign_evaluation(tmp_path, monkeypatch):
    from src.malaria_dl.assessment import service

    repo = MemoryRepository()
    v = value(tmp_path)
    monkeypatch.setattr(service, "resolve", lambda *a: (v["model"], v["dataset"], None))
    monkeypatch.setattr(service, "dataset_samples", lambda *a, **kw: v["samples"])
    options = {
        "split": "val",
        "purpose": "development",
        "protocol": v["protocol"],
        "requested_threshold": ".5",
        "seed": 42,
        "batch_size": 1,
    }
    with pytest.raises(AssessmentError, match="INPUT_OVERRIDE_CONFLICT"):
        service.prepare(repo, input_override={}, **options)
    a = run(repo, v, tmp_path, Runtime)
    v["model"]["model_version_id"] = str(uuid4())
    with pytest.raises(AssessmentError, match="EXPLANATION_EVALUATION_CONFLICT"):
        service.prepare(
            repo,
            evaluation_id=a["id"],
            explanation=explanation_spec("gradcam", "conv", 1, None, []),
            **options,
        )


def test_campaign_inspection_keeps_unaccepted_visible(monkeypatch):
    from types import SimpleNamespace

    from src.malaria_dl.assessment.lineage import campaign_inventory

    members = [
        {"id": str(uuid4()), "state": state, "accepted_attempt_id": None}
        for state in ("pending", "failed", "interrupted")
    ]
    repo = SimpleNamespace(
        get=lambda *a: {"state": "frozen", "members": members, "attempts": []}
    )
    _, items = campaign_inventory(repo, str(uuid4()))
    assert len(items) == 3 and all(not x["eligible"] and x["reason"] for x in items)


def test_cli_rejects_legacy_implicit_batch():
    from src.malaria_dl.assessment.cli import parser

    with pytest.raises(SystemExit):
        parser("evaluate", batch=True).parse_args(
            ["--dataset-version-id", str(uuid4())]
        )


def test_legacy_multiple_versions_rejected():
    from src.malaria_dl.governance.services.model_version_resolver import (
        ModelVersionResolutionError,
        ModelVersionResolver,
    )
    from test_model_version_resolver import Conn, factory

    with pytest.raises(ModelVersionResolutionError):
        ModelVersionResolver(
            factory(Conn([{"id": str(uuid4())}, {"id": str(uuid4())}]))
        ).resolve(source_training_run_id=str(uuid4()))


@pytest.mark.parametrize("method", ["lime", "shap"])
def test_minimal_attribution_methods_preserve_raw_domain(tmp_path, method):
    import numpy as np
    import tensorflow as tf
    from PIL import Image
    from src.malaria_dl.assessment.runtime import KerasRuntime

    v = value(tmp_path)
    inputs = tf.keras.Input((8, 8, 3))
    x = tf.keras.layers.Flatten()(inputs)
    model = tf.keras.Model(inputs, tf.keras.layers.Dense(1, activation="sigmoid")(x))
    model.save(v["model"]["path"])
    v["model"].update(file_identity(v["model"]["path"]))
    sample = v["samples"][0]
    path = tmp_path / sample["relative_path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = np.arange(8 * 8 * 3, dtype=np.uint8).reshape(8, 8, 3)
    Image.fromarray(rgb).save(path)
    sample["sha256"] = file_identity(path)["sha256"]
    v["explanation"] = explanation_spec(
        method, None, 1, 8, [sample] if method == "shap" else []
    )
    heat, overlay, result = KerasRuntime(v).explain(sample)
    assert (
        heat.shape == (8, 8) and overlay.shape == (8, 8, 3) and np.isfinite(heat).all()
    )
    assert result["score_explained"] == "raw"


def test_recovery_requires_proven_dead_local_owner(monkeypatch):
    import socket

    from src.malaria_dl.assessment.repository import AssessmentRepository

    repo = AssessmentRepository()
    aid = str(uuid4())
    owner = str(uuid4())
    calls = []
    a = {
        "id": aid,
        "owner": owner,
        "state": "active",
        "host": socket.gethostname(),
        "pid": 12345,
    }
    monkeypatch.setattr(repo, "attempt", lambda _: a)
    monkeypatch.setattr(repo, "finish", lambda *args, **kw: calls.append((args, kw)))
    monkeypatch.setattr("os.kill", lambda *a: None)
    with pytest.raises(AssessmentError, match="LIVENESS_UNKNOWN"):
        repo.recover(aid)
    assert not calls

    def absent(*a):
        raise ProcessLookupError()

    monkeypatch.setattr("os.kill", absent)
    repo.recover(aid)
    assert calls[0][0] == (aid, owner, "interrupted")


def test_finalization_failure_preserves_original_even_cleanup_fails(
    tmp_path, monkeypatch
):
    repo = MemoryRepository()
    v = value(tmp_path)

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic write failure")

    monkeypatch.setattr(repo, "finish", fail)
    with pytest.raises(RuntimeError, match="synthetic write failure") as exc:
        run(repo, v, tmp_path, Runtime)
    assert "ASSESSMENT_FAILURE_STATE_UNCONFIRMED" in exc.value.__notes__
    assert next(iter(repo.attempts.values()))["state"] == "active"


def test_e6_migration_renders_without_accidental_parameters():
    from importlib.util import module_from_spec, spec_from_file_location
    from io import StringIO

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import psycopg

    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/20260912_02_assessments.py"
    )
    spec = spec_from_file_location("assessment_migration", path)
    m = module_from_spec(spec)
    spec.loader.exec_module(m)
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        m.upgrade()
    assert m.down_revision == "20260912_01"
    assert text(m.DDL).compile(dialect=psycopg.dialect()).construct_params({}) == {}
    assert "CREATE UNIQUE INDEX uq_assessment_live" in output.getvalue()
    assert "SET search_path = public, pg_catalog" in output.getvalue()


from test_dataset_stage1 import (
    fixture as dataset_fixture,  # noqa: F401 -- reusable sealed synthetic fixture
)


def test_accredited_sample_population_and_equivalent_override(
    dataset_fixture,  # noqa: F811 -- imported fixture
    monkeypatch,
):
    from contextlib import nullcontext
    from types import SimpleNamespace

    from src.malaria_dl.assessment.lineage import dataset_samples
    from src.malaria_dl.data.governed_dataset import resolve_governed_dataset
    from test_dataset_stage1 import VERSION, Result

    monkeypatch.setattr(Result, "__iter__", lambda self: iter(self.rows), raising=False)

    f = dataset_fixture
    inherited = resolve_governed_dataset(VERSION).metadata()
    repo = SimpleNamespace(transaction=lambda **kw: nullcontext(f.connection))
    samples = dataset_samples(repo, inherited, "val", VERSION, inspection=True)
    assert len(samples) == 2 and {s["label"] for s in samples} == {0, 1}
    assert len({s["patient_id"] for s in samples}) == 1
    assert all(
        s["split"] == "val" and s["relative_path"].startswith("val/") for s in samples
    )


@pytest.mark.parametrize("conflict", ["exact", "structural_only", "different_payload"])
def test_reservation_conflicts_keep_exact_identity_required(
    tmp_path, monkeypatch, conflict
):
    from contextlib import nullcontext
    from types import SimpleNamespace

    from src.malaria_dl.assessment import repository as implementation

    v = value(tmp_path)
    existing = {"id": str(uuid4()), "owner": str(uuid4()), "state": "active"}
    stored = {"id": str(uuid4()), "identity": deepcopy(v)}
    if conflict == "structural_only":
        stored = None
    if conflict == "different_payload":
        stored["identity"]["seed"] += 1
    outcomes = iter([None, stored, existing])
    statements = []

    def execute(c, sql, **params):
        statements.append(sql)
        row = next(outcomes)
        return SimpleNamespace(
            mappings=lambda: SimpleNamespace(one_or_none=lambda: row)
        )

    monkeypatch.setattr(implementation, "execute", execute)
    repo = implementation.AssessmentRepository()
    monkeypatch.setattr(repo, "transaction", lambda **kw: nullcontext(None))
    if conflict == "exact":
        attempt, created = repo.reserve(v, tmp_path)
        assert attempt == existing and created is False
    else:
        with pytest.raises(
            AssessmentError, match="IDENTITY_CONFLICT_NOT_EXACT|IDENTITY_HASH_CONFLICT"
        ):
            repo.reserve(v, tmp_path)
    assert "ON CONFLICT DO NOTHING" in statements[0]
    assert "identity_hash=:hash FOR UPDATE" in statements[1]


def test_concurrency_diagnostic_never_exposes_driver_text():
    from types import SimpleNamespace

    from test_assessment_postgres import reservation_diagnostic

    error = RuntimeError("synthetic secret connection URL and parameters")
    error.orig = SimpleNamespace(
        sqlstate="23505",
        diag=SimpleNamespace(
            constraint_name="assessment_identities_structural_hash_key"
        ),
    )
    result = reservation_diagnostic(error, "original:INSERT")
    assert result["sqlstate"] == "23505"
    assert result["constraint"] == "assessment_identities_structural_hash_key"
    assert "secret" not in str(result) and "parameters" not in str(result)
    error.orig.diag.constraint_name = "untrusted arbitrary diagnostic text"
    assert reservation_diagnostic(error, "INSERT")["constraint"] is None
