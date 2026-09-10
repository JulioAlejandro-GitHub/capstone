"""Stage 1: synthetic rows and temporary bytes only; never connects to PostgreSQL."""

from contextlib import nullcontext
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

import run_train_all_models as batch
import run_evaluate_all_trainings as eval_batch
import run_explain_all_trainings as explain_batch
from src.malaria_dl.data import governed_dataset as gd
from src.malaria_dl.data.dataset_integrity import canonical_digest, VERIFIER_VERSION
from src.malaria_dl.persistence import dataset_evidence as ev

VERSION = "12345678-abcd-4234-8234-123456789abc"
MATERIALIZATION = "22345678-abcd-4234-8234-123456789abc"
TRAIN = "32345678-abcd-4234-8234-123456789abc"


class Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return deepcopy(self.rows)

    def one_or_none(self):
        return deepcopy(self.rows[0]) if self.rows else None

    def scalar_one(self):
        assert len(self.rows) == 1
        return self.rows[0]


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    root = tmp_path / "data" / "sealed"
    monkeypatch.setattr(gd, "PROJECT_ROOT", tmp_path)
    patients, assignments, sources, identities, files = [], [], [], [], []
    for i, split in enumerate(("train", "val", "test")):
        patient = str(UUID(int=i + 1))
        patients.append((patient, split))
        identities.append((patient, f"synthetic-{i}", "VERIFIED"))
        for j, cls in enumerate(("uninfected", "parasitized")):
            record = str(UUID(int=10 + i * 2 + j))
            filename = f"fixture-{j}.png"
            data = f"{i}/{j}: synthetic image bytes".encode()
            path = root / split / cls / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            checksum = hashlib.sha256(data).hexdigest()
            assignments.append((record, patient, split))
            sources.append((record, patient, cls, checksum, "0" * 64))
            files.append(
                dict(
                    source_record_id=record,
                    clinical_identity_id=patient,
                    split_name=split,
                    class_name=cls,
                    source_filename=filename,
                    source_file_sha256=checksum,
                )
            )
    # Independent spelling of the established upstream serialization.
    digest = lambda rows, end: hashlib.sha256(
        ("\n".join("|".join(map(str, r)) for r in rows) + end).encode()
    ).hexdigest()
    contract = dict(
        version="malaria_patient_split_freeze_v1",
        dataset_version_id=VERSION,
        dataset_materialization_id=MATERIALIZATION,
        assignment_count=6,
        source_record_count=6,
        clinical_identity_count=3,
        fingerprints=dict(
            patient_assignment_sha256=digest(patients, ""),
            record_assignment_sha256=digest(assignments, ""),
            source_population_sha256=digest(sources, "\n"),
            clinical_identity_sha256=digest(identities, "\n"),
        ),
    )
    f = SimpleNamespace(
        root=root,
        patients=patients,
        assignments=assignments,
        sources=sources,
        identities=identities,
        files=files,
        contract=contract,
        queries=[],
        version=dict(
            id=VERSION, status="FROZEN", methodology_json={"freeze_contract": contract}
        ),
        materialization=dict(
            id=MATERIALIZATION,
            dataset_version_id=VERSION,
            status="READY",
            reconciliation_status="PASS",
            relative_root="sealed",
        ),
        checks=[
            dict(check_name=n, status="PASS", blocking_for_validation=True)
            for n in gd.REQUIRED_CHECKS
        ],
        training=None,
    )

    def execute(query, params=None):
        q = " ".join(str(query).split())
        f.queries.append((q, params))
        if "FROM dataset_versions WHERE" in q:
            return Result([f.version] if f.version else [])
        if "FROM dataset_materializations WHERE" in q:
            return Result([f.materialization] if f.materialization else [])
        if "FROM dataset_split_validation_checks" in q:
            return Result(f.checks)
        if "FROM runs" in q:
            return Result([f.training] if f.training else [])
        if "GROUP BY clinical_identity_id,split_name" in q:
            return Result(f.patients)
        if "SELECT source_record_id,clinical_identity_id,split_name" in q:
            return Result(f.assignments)
        if "SELECT r.id,r.clinical_identity_id" in q:
            return Result(f.sources)
        if "SELECT i.id,i.source_identifier" in q:
            return Result(f.identities)
        if "SELECT a.source_record_id" in q:
            return Result(f.files)
        raise AssertionError(q)

    f.connection = SimpleNamespace(execute=execute)
    monkeypatch.setattr(
        gd, "dataset_read_connection", lambda: nullcontext(f.connection)
    )
    return f


@pytest.fixture
def evidence_store(monkeypatch):
    store = {}

    def persist(payload, *, success, error_code=None, evidence_id=None):
        key = evidence_id or str(uuid4())
        store[key] = dict(
            after_state=deepcopy(payload), success=success, error_code=error_code
        )
        return key

    monkeypatch.setattr(ev, "persist_dataset_evidence", persist)
    monkeypatch.setattr(ev, "read_dataset_evidence", lambda key: deepcopy(store[key]))
    return store


@pytest.mark.parametrize(
    "value,code",
    [(None, "REQUIRED"), ("", "REQUIRED"), ("  ", "REQUIRED"), ("bad", "INVALID")],
)
def test_resolver_rejects_before_database(value, code, monkeypatch):
    connection = Mock(side_effect=AssertionError("must not connect"))
    monkeypatch.setattr(gd, "dataset_read_connection", connection)
    with pytest.raises(gd.GovernedDatasetError, match=code):
        gd.resolve_governed_dataset(value)
    connection.assert_not_called()


def test_exact_seal_and_upstream_hashing(fixture):
    snap = gd.resolve_governed_dataset(VERSION.upper())
    assert str(snap.dataset_version_id) == VERSION
    assert str(snap.dataset_materialization_id) == MATERIALIZATION
    assert snap.counts == dict(train=2, val=2, test=2)
    material_queries = [
        (q, p) for q, p in fixture.queries if "FROM dataset_materializations" in q
    ]
    assert material_queries[0][1]["id"] == MATERIALIZATION
    assert "ORDER BY" not in material_queries[0][0]
    assert (
        canonical_digest([(None, "a"), ("b", "c")])
        == hashlib.sha256(b"|a\nb|c\n").hexdigest()
    )
    assert (
        canonical_digest([("a", "b")], trailing_newline=False)
        == hashlib.sha256(b"a|b").hexdigest()
    )


@pytest.mark.parametrize(
    "case,code",
    [
        ("missing", "NOT_FOUND"),
        ("state", "NOT_TRAINABLE"),
        ("checks", "CHECKS_NOT_PASS"),
        ("materialization", "FREEZE_CONTRACT_MISMATCH"),
        ("not_ready", "NOT_READY_PASS"),
        ("reconciliation", "NOT_READY_PASS"),
        ("root", "ROOT_MISSING"),
        ("seal", "NOT_SEALED"),
        ("reference", "FINGERPRINT_MISSING"),
    ],
)
def test_rejected_contracts(fixture, case, code):
    if case == "missing":
        fixture.version = None
    elif case == "state":
        fixture.version["status"] = "VALIDATED"
    elif case == "checks":
        fixture.checks[0]["status"] = "FAIL"
    elif case == "materialization":
        fixture.materialization["dataset_version_id"] = str(uuid4())
    elif case == "not_ready":
        fixture.materialization["status"] = "FAILED"
    elif case == "reconciliation":
        fixture.materialization["reconciliation_status"] = "FAIL"
    elif case == "root":
        fixture.materialization["relative_root"] = "missing"
    elif case == "seal":
        fixture.contract["version"] = "unknown"
    elif case == "reference":
        fixture.contract["fingerprints"].pop("source_population_sha256")
    with pytest.raises(gd.GovernedDatasetError, match=code):
        gd.resolve_governed_dataset(VERSION)


@pytest.mark.parametrize(
    "collection", ["patients", "assignments", "sources", "identities"]
)
def test_each_fingerprint_is_recomputed(fixture, collection):
    rows = getattr(fixture, collection)
    rows[0] = tuple(["changed", *rows[0][1:]])
    with pytest.raises(gd.GovernedDatasetError, match="FINGERPRINT_MISMATCH"):
        gd.resolve_governed_dataset(VERSION)


def test_changed_bytes_same_name_and_count_rejected(fixture):
    path = next(fixture.root.rglob("*.png"))
    original = path.read_bytes()
    path.write_bytes(b"x" * len(original))
    assert len(list(fixture.root.rglob("*.png"))) == 6
    with pytest.raises(gd.GovernedDatasetError, match="CONTENT_HASH_MISMATCH"):
        gd.resolve_governed_dataset(VERSION)


def test_missing_or_unexpected_file_rejected(fixture):
    (fixture.root / "unexpected.png").write_bytes(b"not part of seal")
    with pytest.raises(gd.GovernedDatasetError, match="CONTENT_SET_MISMATCH"):
        gd.resolve_governed_dataset(VERSION)


def parent_fixture(fixture):
    metadata = gd.resolve_governed_dataset(VERSION).metadata()
    fixture.training = dict(
        dataset_version_id=VERSION,
        execution_parameters=metadata,
        parameters={},
        metadata={},
    )
    return metadata


def test_parent_inheritance_normalized_and_pinned(fixture, evidence_store):
    parent = parent_fixture(fixture)
    snap = ev.verify_dataset_for_execution(
        VERSION.upper(), training_run_id=TRAIN, consumer="src.evaluate"
    )
    assert snap.metadata() == parent
    assert evidence_store[snap.evidence_id]["success"]
    inherited = ev.verify_dataset_for_execution(
        training_run_id=TRAIN, consumer="src.explain"
    )
    assert inherited.metadata() == parent
    with pytest.raises(gd.GovernedDatasetError, match="TRAIN_DATASET_VERSION_MISMATCH"):
        ev.verify_dataset_for_execution(str(uuid4()), training_run_id=TRAIN)
    fixture.training["execution_parameters"]["dataset_materialization_id"] = str(
        uuid4()
    )
    with pytest.raises(gd.GovernedDatasetError, match="SNAPSHOT_IMMUTABLE"):
        ev.verify_dataset_for_execution(training_run_id=TRAIN)


def test_historical_unaccredited_blocked_without_backfill(fixture, evidence_store):
    fixture.training = dict(
        dataset_version_id=None, execution_parameters={}, parameters={}, metadata={}
    )
    original = deepcopy(fixture.training)
    with pytest.raises(gd.GovernedDatasetError, match="NOT_ACCREDITED"):
        ev.verify_dataset_for_execution(training_run_id=TRAIN)
    assert fixture.training == original
    assert all("UPDATE runs" not in q for q, _ in fixture.queries)


def test_batch_pin_cannot_substitute_materialization(fixture, evidence_store):
    initial = ev.verify_dataset_for_execution(VERSION, consumer="run_train_all_models")
    other = str(uuid4())
    fixture.materialization["id"] = other
    fixture.contract["dataset_materialization_id"] = other
    with pytest.raises(gd.GovernedDatasetError, match="SNAPSHOT_IMMUTABLE"):
        ev.verify_dataset_for_execution(
            VERSION, expected_evidence_id=initial.evidence_id
        )


@pytest.mark.parametrize("override", ["different", "tfds"])
def test_path_and_source_cannot_replace_governed_dataset(
    fixture, evidence_store, override
):
    kwargs = (
        {"dataset_dir": "different"}
        if override == "different"
        else {"data_source": "tfds"}
    )
    with pytest.raises(gd.GovernedDatasetError, match="CONFLICT|REQUIRES_PHYSICAL"):
        ev.verify_dataset_for_execution(VERSION, **kwargs)
    assert (
        ev.verify_dataset_for_execution(VERSION, dataset_dir="data/sealed").dataset_root
        == fixture.root
    )


@pytest.mark.parametrize("module", [batch, eval_batch, explain_batch])
@pytest.mark.parametrize("value", [None, "", "bad"])
def test_batch_cli_requires_uuid(module, value):
    argv = [] if value is None else ["--dataset-version-id", value]
    with pytest.raises(SystemExit):
        module.parse_args(argv)


def test_batch_resolves_once_propagates_pin_to_twelve(fixture, monkeypatch):
    snap = replace(gd.resolve_governed_dataset(VERSION), evidence_id=str(uuid4()))
    verify = Mock(return_value=snap)
    launch = Mock(return_value=0)
    monkeypatch.setattr(batch, "verify_dataset_for_execution", verify)
    monkeypatch.setattr(batch, "run_command", launch)
    monkeypatch.setattr(
        batch,
        "parse_args",
        lambda: SimpleNamespace(
            project_dir=str(Path.cwd()),
            models=batch.DEFAULT_MODELS,
            optimizers=batch.DEFAULT_OPTIMIZERS,
            max_epochs=1,
            img_size=32,
            batch_size=2,
            seed=42,
            target_recall=0.98,
            early_stopping_patience=2,
            dataset_version_id=VERSION,
            dry_run=False,
            continue_on_error=False,
        ),
    )
    assert batch.main() == 0
    assert verify.call_count == 1 and launch.call_count == 12
    for call in launch.call_args_list:
        cmd = call.args[0]
        assert cmd[cmd.index("--dataset-version-id") + 1] == VERSION
        assert cmd[cmd.index("--expected-dataset-evidence-id") + 1] == snap.evidence_id


def test_dry_run_does_not_accredit_or_connect(monkeypatch, capsys):
    args = batch.parse_args(["--dataset-version-id", VERSION, "--dry-run"])
    monkeypatch.setattr(batch, "parse_args", lambda: args)
    verify = Mock(side_effect=AssertionError("no DB"))
    monkeypatch.setattr(batch, "verify_dataset_for_execution", verify)
    assert batch.main() == 0
    verify.assert_not_called()
    assert "NO VERIFICADA" in capsys.readouterr().out


def test_failed_persistence_never_returns_verified(fixture, monkeypatch):
    monkeypatch.setattr(ev, "get_engine", Mock(side_effect=RuntimeError("private DSN")))
    with pytest.raises(gd.GovernedDatasetError, match="PERSISTENCE_FAILED") as error:
        ev.verify_dataset_for_execution(VERSION)
    assert "private" not in str(error.value)
    assert not list(fixture.root.rglob("*.csv"))


def test_evidence_round_trip_without_sidecars(tmp_path, monkeypatch):
    store = {}

    class Connection:
        def execute(self, sql, params):
            q = str(sql)
            if "INSERT INTO audit_events" in q:
                store[params["id"]] = dict(
                    after_state=json.loads(params["payload"]),
                    success=params["success"],
                    error_code=params["error"],
                )
                return Result([])
            assert "SELECT after_state" in q
            return Result([store[params["id"]]] if params["id"] in store else [])

    engine = SimpleNamespace(
        begin=lambda: nullcontext(Connection()), dispose=lambda: None
    )
    monkeypatch.setattr(ev, "get_engine", lambda: engine)
    monkeypatch.setattr(
        ev, "dataset_read_connection", lambda: nullcontext(Connection())
    )
    payload = dict(
        consumer="fixture",
        dataset_version_id=VERSION,
        verifier_version=VERIFIER_VERSION,
        snapshot={
            "dataset_version_id": VERSION,
            "dataset_materialization_id": MATERIALIZATION,
        },
        integrity_status="verified",
    )
    key = ev.persist_dataset_evidence(payload, success=True)
    assert ev.read_dataset_evidence(key)["after_state"] == payload
    assert list(tmp_path.iterdir()) == []
    monkeypatch.setattr(ev, "read_dataset_evidence", lambda _: {})
    with pytest.raises(gd.GovernedDatasetError, match="PERSISTENCE_FAILED"):
        ev.persist_dataset_evidence(payload, success=True)


def test_run_link_failure_is_fatal(monkeypatch):
    snapshot = SimpleNamespace(evidence_id=str(uuid4()), dataset_version_id=VERSION)
    with pytest.raises(gd.GovernedDatasetError, match="LINK_REQUIRED"):
        ev.bind_dataset_evidence_to_run(snapshot, {"run_id": None})
    monkeypatch.setattr(ev, "get_engine", Mock(side_effect=RuntimeError("private")))
    with pytest.raises(gd.GovernedDatasetError, match="LINK_FAILED"):
        ev.bind_dataset_evidence_to_run(snapshot, {"run_id": TRAIN})


@pytest.mark.parametrize("value", [None, "", "bad"])
def test_programmatic_execution_missing_id_is_early(value, monkeypatch):
    persist = Mock(side_effect=AssertionError("no DB"))
    resolve = Mock(side_effect=AssertionError("no images"))
    monkeypatch.setattr(ev, "persist_dataset_evidence", persist)
    monkeypatch.setattr(ev, "resolve_governed_dataset", resolve)
    with pytest.raises(gd.GovernedDatasetError, match="REQUIRED|INVALID"):
        ev.verify_dataset_for_execution(value)
    persist.assert_not_called()
    resolve.assert_not_called()


@pytest.mark.parametrize("value", [None, "", "bad"])
def test_train_public_entry_rejects_before_model_or_images(value, monkeypatch):
    from src.malaria_dl.training import trainer

    argv = ["src.train", "--model", "custom_cnn"]
    if value is not None:
        argv += ["--dataset-version-id", value]
    monkeypatch.setattr("sys.argv", argv)
    model = Mock(side_effect=AssertionError("no model"))
    images = Mock(side_effect=AssertionError("no images"))
    verifier = Mock(side_effect=AssertionError("no preflight"))
    monkeypatch.setattr(trainer, "build_custom_cnn", model)
    monkeypatch.setattr(trainer, "load_malaria_splits", images)
    monkeypatch.setattr(trainer, "verify_dataset_for_execution", verifier)
    with pytest.raises(SystemExit):
        trainer.main()
    model.assert_not_called()
    images.assert_not_called()
    verifier.assert_not_called()


@pytest.mark.parametrize("kind", ["evaluate", "explain"])
@pytest.mark.parametrize("historic", [False, True])
def test_consumers_reject_before_inference(
    fixture, evidence_store, monkeypatch, kind, historic
):
    from src.malaria_dl.evaluation import evaluator
    from src.malaria_dl.explainability import pipeline
    from src.model_version_resolver import ModelVersionResolver

    parent_fixture(fixture)
    if historic:
        fixture.training["dataset_version_id"] = None
    module = evaluator if kind == "evaluate" else pipeline
    argv = ["--model-version-id", str(uuid4()), "--dataset-version-id", str(uuid4())]
    if kind == "explain":
        argv += ["--method", "all"]
    args = module.parse_args(argv)
    monkeypatch.setattr(module, "parse_args", lambda: args)
    monkeypatch.setattr(
        ModelVersionResolver,
        "resolve",
        lambda *a, **k: SimpleNamespace(
            checkpoint_path=fixture.root / "unused.keras", source_training_run_id=TRAIN
        ),
    )
    inference = Mock(side_effect=AssertionError("inference must not run"))
    if kind == "evaluate":
        monkeypatch.setattr(module, "collect_predictions", inference)
    else:
        monkeypatch.setattr(module, "collect_prediction_candidates", inference)
    with pytest.raises(
        gd.GovernedDatasetError, match="NOT_ACCREDITED|VERSION_MISMATCH"
    ):
        module.main()
    inference.assert_not_called()
    assert not list(fixture.root.rglob("*.csv"))


@pytest.mark.parametrize("module", [eval_batch, explain_batch])
def test_inventory_requires_scope_before_connect(module, monkeypatch):
    connection = Mock(side_effect=AssertionError("no DB"))
    monkeypatch.setattr(module, "connect", connection)
    with pytest.raises(gd.GovernedDatasetError, match="REQUIRED"):
        module.fetch_training_inventory(Path.cwd())
    connection.assert_not_called()


@pytest.mark.parametrize("module", [eval_batch, explain_batch])
def test_inventory_filters_and_rejects_wrong_training(module, monkeypatch):
    queries = []
    wrong = [
        TRAIN,
        str(uuid4()),
        "synthetic",
        "custom_cnn",
        "adam",
        "model.keras",
        32,
        2,
        "auto",
        str(uuid4()),
        "candidate",
        "resolved",
        True,
        True,
    ]

    class Cursor:
        def execute(self, q, p=None):
            queries.append((q, p))

        def fetchall(self):
            return [wrong]

    conn = SimpleNamespace(cursor=lambda: nullcontext(Cursor()))
    monkeypatch.setattr(module, "connect", lambda _: nullcontext(conn))
    with pytest.raises(gd.GovernedDatasetError, match="BATCH_TRAIN_DATASET_MISMATCH"):
        module.fetch_training_inventory(Path.cwd(), VERSION)
    assert queries[0][0] == "BEGIN READ ONLY"
    assert queries[1][1]["dataset_version_id"] == VERSION
    assert "IS NULL" not in queries[1][0]


def test_byte_exact_canonical_rules_match_upstream_sources():
    # Load ONLY pure functions by AST, not upstream module initialization/DB writers.
    import ast

    namespace = {
        "hashlib": hashlib,
        "Iterable": __import__("typing").Iterable,
        "Any": __import__("typing").Any,
    }
    upstream = Path.cwd().parent / "malaria_dataset_split_project/src/malaria_split"
    for file, name in [
        ("governance/freeze.py", "_canonical_digest"),
        ("persistence/split_generation.py", "_sha256_lines"),
    ]:
        tree = ast.parse((upstream / file).read_text())
        node = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name
        )
        exec(compile(ast.Module(body=[node], type_ignores=[]), file, "exec"), namespace)
    rows = [("a", None, 42), ("b", "c", 5)]
    assert canonical_digest(rows) == namespace["_canonical_digest"](rows)
    rows = [("a", "b"), ("c", "d")]
    assert canonical_digest(rows, trailing_newline=False) == namespace["_sha256_lines"](
        ["a|b", "c|d"]
    )


def test_additional_blocking_failure_is_not_ignored(fixture):
    fixture.checks.append(
        dict(check_name="additional", status="FAIL", blocking_for_validation=True)
    )
    with pytest.raises(gd.GovernedDatasetError, match="CHECKS_NOT_PASS"):
        gd.resolve_governed_dataset(VERSION)


def test_rejection_evidence_retains_sealed_reference(fixture, evidence_store):
    next(fixture.root.rglob("*.png")).write_bytes(b"altered fixture")
    with pytest.raises(gd.GovernedDatasetError, match="CONTENT_HASH_MISMATCH"):
        ev.verify_dataset_for_execution(VERSION)
    result = next(iter(evidence_store.values()))
    assert result["success"] is False
    assert result["after_state"]["integrity_status"] == "rejected"
    assert (
        result["after_state"]["rejection_evidence"]["expected_fingerprints"]
        == fixture.contract["fingerprints"]
    )
