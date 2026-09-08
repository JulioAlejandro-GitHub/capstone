"""Tests del purgador por subsistema scripts/db/purge.py.

Cubren: cada flag aislado, combinaciones, orden topológico hijo→padre, que --cell nunca
purgue tablas ajenas, que ninguna combinación toque `users`/`audit_events`, el chequeo de
dependencias FK cruzadas y el aislamiento transaccional por subsistema.
"""
from __future__ import annotations

import importlib.util
import itertools
import sys
from pathlib import Path

import pytest

_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "scripts/db/purge.py",  # árbol del repo (host)
    Path("/app/scripts/db/purge.py"),                             # imagen del backend
)
SCRIPT = next((path for path in _CANDIDATES if path.exists()), _CANDIDATES[0])
if not SCRIPT.exists():
    pytest.skip(
        "scripts/db/purge.py no disponible (reconstruya la imagen del backend)",
        allow_module_level=True,
    )
SPEC = importlib.util.spec_from_file_location("db_purge", SCRIPT)
purge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = purge
SPEC.loader.exec_module(purge)


# --------------------------------------------------------------------------- flags

def test_dry_run_is_default_and_execution_is_opt_in():
    args = purge.parse_args([])
    assert args.yes is False
    assert args.dry_run is False


def test_no_flag_is_refused():
    with pytest.raises(purge.PurgeRefused):
        purge.selected_subsystems(purge.parse_args([]))


def test_dry_run_and_yes_together_are_refused(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://julio:root@db:5432/malaria_experiments")
    monkeypatch.setenv(purge.EXECUTION_ENV_FLAG, "1")
    assert purge.run(["--cell", "--dry-run", "--yes"]) == 2


@pytest.mark.parametrize("flag,expected", [
    ("--dataset", ["dataset"]),
    ("--run", ["run"]),
    ("--cell", ["cell"]),
])
def test_single_flag(flag, expected):
    assert purge.selected_subsystems(purge.parse_args([flag])) == expected


def test_combined_flags_are_ordered_cell_run_dataset():
    for combo in itertools.permutations(["--dataset", "--run", "--cell"]):
        assert purge.selected_subsystems(purge.parse_args(list(combo))) == [
            "cell", "run", "dataset",
        ]


# ------------------------------------------------------------------- clasificación

def test_every_known_table_maps_to_exactly_one_bucket():
    buckets = [purge.CELL_TABLES, purge.RUN_TABLES, purge.DATASET_TABLES,
               purge.USERS_TABLES, purge.SYSTEM_TABLES]
    for a, b in itertools.combinations(buckets, 2):
        assert not (a & b), f"solapamiento entre buckets: {a & b}"


def test_users_and_audit_are_never_a_subsystem():
    for table in ("users", "roles", "user_roles"):
        assert purge.classify_table(table) == "users"
        assert table not in purge.target_tables(["cell", "run", "dataset"])
    assert purge.classify_table("audit_events") == "system"
    assert purge.classify_table("alembic_version") == "system"
    assert purge.classify_table("schema_migrations") == "system"


def test_no_flag_combination_touches_users_or_system_tables():
    protected = purge.USERS_TABLES | purge.SYSTEM_TABLES
    names = list(purge.SUBSYSTEMS)
    for size in range(1, len(names) + 1):
        for combo in itertools.combinations(names, size):
            assert not (purge.target_tables(list(combo)) & protected)


def test_cell_flag_never_reaches_dataset_or_run_tables():
    assert not (purge.CELL_TABLES & purge.DATASET_TABLES)
    assert not (purge.CELL_TABLES & purge.RUN_TABLES)
    # microscopy_* pertenece a cell (misma capa del pipeline, no subsistema aparte)
    for table in ("microscopy_images", "microscopy_analysis_runs",
                  "cell_predictions", "smear_analysis_summaries"):
        assert purge.classify_table(table) == "cell"
    # la capa de validación científica se resolvió DENTRO de --cell
    for table in ("scientific_validation_sessions", "scientific_validation_annotations"):
        assert table in purge.CELL_TABLES


def test_unknown_table_is_fail_closed():
    assert purge.classify_table("some_future_table") is None


# ---------------------------------------------------------------------- toposort

def test_toposort_puts_children_before_parents():
    tables = {"a", "b", "c", "d"}
    edges = [("b", "a"), ("c", "a"), ("d", "b"), ("d", "c")]  # hijo -> padre
    order = purge.toposort(tables, edges)
    assert order.index("d") < order.index("b") < order.index("a")
    assert order.index("d") < order.index("c") < order.index("a")


def test_toposort_is_deterministic_alpha_tiebreak():
    tables = {"z", "y", "x"}
    assert purge.toposort(tables, []) == ["x", "y", "z"]


def test_toposort_survives_a_cycle():
    order = purge.toposort({"a", "b"}, [("a", "b"), ("b", "a")])
    assert sorted(order) == ["a", "b"]


def test_toposort_ignores_edges_outside_the_set():
    order = purge.toposort({"a", "b"}, [("b", "a"), ("a", "external"), ("x", "b")])
    assert order == ["b", "a"]


def test_real_cell_order_keeps_specimen_roots_last():
    # el orden real se recalcula en runtime; aquí validamos la forma con las FK conocidas.
    edges = [
        ("cell_explanations", "cell_predictions"),
        ("cell_predictions", "cell_classification_inputs"),
        ("cell_classification_inputs", "cell_classification_runs"),
        ("cell_classification_runs", "cell_detection_runs"),
        ("cell_detection_runs", "microscopy_analysis_runs"),
        ("microscopy_analysis_runs", "image_ingestion_batches"),
        ("image_ingestion_batches", "smear_slides"),
        ("smear_slides", "blood_samples"),
        ("blood_samples", "scientific_cases"),
        ("scientific_cases", "research_subjects"),
    ]
    order = purge.toposort(set(purge.CELL_TABLES), edges)
    assert order.index("cell_explanations") < order.index("cell_predictions")
    assert order.index("microscopy_analysis_runs") < order.index("image_ingestion_batches")
    assert order[-1] == "research_subjects"


# ----------------------------------------------------- dependencias FK cruzadas

def _edges_from_pairs(pairs):
    return list(pairs)


def test_run_alone_is_refused_when_cell_rows_reference_it():
    # cell_classification_runs (cell) -> deployed_model_versions (run)
    edges = [("cell_classification_runs", "deployed_model_versions")]
    conflicts = purge.cross_subsystem_conflicts(
        ["run"], edges, referencing_rows_exist=lambda c, p: True,
    )
    assert any("--cell" in message for message in conflicts)


def test_run_alone_is_allowed_when_no_cell_rows_reference_it():
    edges = [("cell_classification_runs", "deployed_model_versions")]
    conflicts = purge.cross_subsystem_conflicts(
        ["run"], edges, referencing_rows_exist=lambda c, p: False,
    )
    assert conflicts == []


def test_dataset_alone_is_refused_when_run_rows_reference_it():
    edges = [("predictions", "dataset_split_images"), ("runs", "dataset_versions")]
    conflicts = purge.cross_subsystem_conflicts(
        ["dataset"], edges, referencing_rows_exist=lambda c, p: True,
    )
    assert any("--run" in message for message in conflicts)


def test_all_three_flags_have_no_cross_subsystem_conflict():
    edges = [
        ("cell_classification_runs", "deployed_model_versions"),
        ("predictions", "dataset_split_images"),
        ("runs", "dataset_versions"),
    ]
    conflicts = purge.cross_subsystem_conflicts(
        ["cell", "run", "dataset"], edges, referencing_rows_exist=lambda c, p: True,
    )
    assert conflicts == []


def test_unknown_dependent_table_fails_closed():
    edges = [("mystery_table", "runs")]
    conflicts = purge.cross_subsystem_conflicts(
        ["run"], edges, referencing_rows_exist=lambda c, p: True,
    )
    assert any("desconocida" in message for message in conflicts)


def test_child_in_target_parent_outside_is_not_a_conflict():
    # predictions (run, seleccionado) -> dataset_split_images (dataset, NO seleccionado):
    # borrar predictions no toca dataset -> sin conflicto.
    edges = [("predictions", "dataset_split_images")]
    conflicts = purge.cross_subsystem_conflicts(
        ["run"], edges, referencing_rows_exist=lambda c, p: True,
    )
    assert conflicts == []


# ------------------------------------------------------------------- build_engine

def test_execution_needs_a_verified_backup(tmp_path):
    with pytest.raises(purge.PurgeRefused):
        purge.validate_backup(None)
    tiny = tmp_path / "tiny.dump"
    tiny.write_bytes(b"PGDMP")
    with pytest.raises(purge.PurgeRefused):
        purge.validate_backup(str(tiny))
    wrong = tmp_path / "wrong.dump"
    wrong.write_bytes(b"NOTPG" + b"0" * 4096)
    with pytest.raises(purge.PurgeRefused):
        purge.validate_backup(str(wrong))
    good = tmp_path / "good.dump"
    good.write_bytes(b"PGDMP" + b"0" * 4096)
    assert purge.validate_backup(str(good)) == str(good)


@pytest.mark.parametrize("url", [
    "postgresql://julio:root@localhost:5432/malaria_experiments",
    "postgresql://julio:root@db:5433/malaria_experiments",
    "mysql://julio:root@db:5432/malaria_experiments",
    "postgresql://db:5432/malaria_experiments",  # sin usuario
])
def test_build_engine_rejects_non_canonical_urls(url):
    with pytest.raises(purge.PurgeRefused):
        purge.build_engine(url)


# ------------------------------------------------- ejecución por subsistema (fake)

class _Result:
    def __init__(self, value=None, rowcount=0):
        self._value = value
        self.rowcount = rowcount

    def scalar_one(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value

    def one(self):
        return self._value


class _FakeConnection:
    def __init__(self, engine):
        self.engine = engine

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def begin(self):
        return _FakeTransaction(self.engine)

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        self.engine.statements.append(sql)
        if sql.startswith("SET "):
            return _Result()
        if "current_database" in sql:
            return _Result(("malaria_experiments", "julio", "public"))
        if "alembic_version" in sql:
            return _Result(purge.EXPECTED_HEAD)
        if sql.startswith("DELETE FROM"):
            table = sql.split('"')[1]
            remaining = self.engine.counts.get(table, 0)
            self.engine.counts[table] = 0
            return _Result(rowcount=remaining)
        if sql.startswith("SELECT count(*)"):
            table = sql.split('"')[1]
            return _Result(self.engine.counts.get(table, 0))
        raise AssertionError(f"consulta inesperada: {sql}")


class _FakeTransaction:
    def __init__(self, engine):
        self.engine = engine
        self.is_active = True

    def commit(self):
        self.is_active = False
        self.engine.commits.append(True)

    def rollback(self):
        self.is_active = False
        self.engine.rollbacks.append(True)


class _FakeEngine:
    def __init__(self, counts):
        self.counts = dict(counts)
        self.statements: list[str] = []
        self.commits: list[bool] = []
        self.rollbacks: list[bool] = []

    def connect(self):
        return _FakeConnection(self)


def test_purge_one_subsystem_disables_triggers_and_commits_once():
    url = purge.make_url("postgresql://julio:root@db:5432/malaria_experiments")
    engine = _FakeEngine({"cell_predictions": 3, "cell_classification_runs": 1})
    deleted = purge.purge_one_subsystem(
        engine, url, "cell",
        ["cell_predictions", "cell_classification_runs"], ["cell"], verbose=False,
    )
    assert deleted == {"cell_predictions": 3, "cell_classification_runs": 1}
    assert "SET LOCAL session_replication_role = replica" in engine.statements
    assert engine.commits == [True]
    assert engine.rollbacks == []
    # el DELETE respeta el orden recibido (hijo antes que padre)
    deletes = [s for s in engine.statements if s.startswith("DELETE FROM")]
    assert deletes == ['DELETE FROM "cell_predictions"', 'DELETE FROM "cell_classification_runs"']


def test_purge_one_subsystem_rolls_back_if_table_not_emptied():
    url = purge.make_url("postgresql://julio:root@db:5432/malaria_experiments")

    class _StubbornConnection(_FakeConnection):
        def execute(self, statement, params=None):
            sql = " ".join(str(statement).split())
            if sql.startswith("DELETE FROM"):
                self.engine.statements.append(sql)
                return _Result(rowcount=0)  # no borra nada
            return super().execute(statement, params)

    class _StubbornEngine(_FakeEngine):
        def connect(self):
            return _StubbornConnection(self)

    engine = _StubbornEngine({"cell_predictions": 5})
    with pytest.raises(purge.PurgeRefused):
        purge.purge_one_subsystem(
            engine, url, "cell", ["cell_predictions"], ["cell"], verbose=False,
        )
    assert engine.rollbacks == [True]
    assert engine.commits == []
