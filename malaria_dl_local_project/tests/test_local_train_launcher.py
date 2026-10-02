"""Local TRAIN launcher contract: `run_train_all_models.py --campaign-id <UUID>` only.

No database, model or child process: synthetic repositories and connections.
The real campaign b54ea684 is never touched here.
"""
import json
import os
import platform
import sys
from urllib.parse import quote
from uuid import uuid4

import pytest

from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.data import governed_dataset as gd
from src.malaria_dl.execution import campaign as executor
from src.malaria_dl.execution import global_gate as gg
from src.malaria_dl.execution import local_launch
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.persistence import database

REFERENCE = {"source_sha256": "a" * 64, "python": "3.12.14", "tensorflow": "2.17.1",
             "packages": {"keras": "3.15.1", "SQLAlchemy": "2.0.52"},
             "determinism_environment": {"PYTHONHASHSEED": "42", "TF_DETERMINISTIC_OPS": None}}
PASSWORD = "fictional-pass/word@x"
URL = local_launch.database_url


class Campaign:
    """New frozen campaign: members pending, 0 attempts, no technical revision."""

    def __init__(self, members=3, train=None):
        self.state = "frozen"
        self.members = [dict(id=str(uuid4()), state="pending", position=i) for i in range(members)]
        self.calls = []
        self.train = train or (lambda session: 0)

    def get(self, campaign_id, dataset=None):
        return {"id": campaign_id, "state": self.state, "attempts": [], "members": self.members,
                "environment": REFERENCE}

    def preflight_e10_schema(self):
        self.calls.append(("schema",))

    def claim(self, campaign_id, owner, host, pid, root, **kwargs):
        self.calls.append(("claim", kwargs))
        member = next((m for m in self.members if m["state"] in ("pending", "failed", "interrupted")), None)
        if member is None:
            return None
        member["state"] = "active"
        self.state = "active"
        self.current = {"run_id": str(uuid4()), "owner": owner, "member": member, "state": "active",
                        "configuration": {"model_id": "custom_cnn", "resolved": {}}}
        return dict(self.current)

    def session(self, run_id):
        return dict(self.current)

    def finish(self, run, owner, state, evidence=None, cause=None):
        self.calls.append(("finish", state, cause))
        self.current["state"] = state
        self.current["member"]["state"] = state
        self.current["cause"] = cause

    def finalize_terminal(self, campaign_id):
        self.calls.append(("finalize",))

    def pause(self, campaign_id, code):
        self.calls.append(("pause", code))
        self.state = "paused"

    def resume(self, campaign_id):
        self.calls.append(("resume",))
        if self.state == "paused":
            self.state = "active"

    def summary(self, campaign_id):
        verified = sum(m["state"] == "verified" for m in self.members)
        return {"state": self.state, "matrix_complete": verified == len(self.members),
                "members": {"verified": verified}}

    def kinds(self, kind):
        return [c for c in self.calls if c[0] == kind]


def launch_for(repo):
    def launch(session, _):
        code = repo.train(session)
        if code == 0:
            repo.current["state"] = "completed"
        return code
    return launch


def run(repo, **kwargs):
    return executor.execute_campaign(
        repo, "c", "/unused", resume=True, check=lambda *a: None,
        launch=launch_for(repo), loader=lambda *a: None, **kwargs)


@pytest.fixture(autouse=True)
def _runtime(monkeypatch):
    # The Mac venv as observed: different Python/SQLAlchemy patch than the Docker reference.
    current = dict(REFERENCE, python="3.12.13", packages={"keras": "3.15.1", "SQLAlchemy": "2.0.53"})
    monkeypatch.setattr(executor, "planning_environment", lambda: current)
    monkeypatch.setattr(executor, "verify_session", lambda repo, session, loader: {"status": "verified"})


# Cases 1, 2, 3 and 7: a new frozen campaign starts locally; no previous attempt and
# no technical revision exist or are required; each TRAIN is verified before the next.
def test_new_frozen_campaign_runs_every_member_without_revision_or_previous_attempt():
    repo = Campaign()
    code, summary = run(repo)
    assert code == 0 and summary["matrix_complete"]
    claims = repo.kinds("claim")
    assert len(claims) == 4  # three members + the empty claim that ends the loop
    for _, kwargs in claims:
        assert "revision_id" not in kwargs and "previous_attempt_id" not in kwargs
        runtime = kwargs["observed_runtime"]
        assert runtime["python"] == "3.12.13" and runtime["execution_mode"] in ("local_python", "docker")
        assert runtime["platform"] == platform.system()
    assert [c[1] for c in repo.kinds("finish")] == ["verified"] * 3
    assert repo.kinds("finalize") and not repo.kinds("pause")


# Case 8: a failed TRAIN is recorded, the launcher exits != 0 and claims nothing else.
def test_failed_train_stops_before_next_member():
    repo = Campaign(train=lambda session: 2)
    code, summary = run(repo)
    assert code == 1
    assert len(repo.kinds("claim")) == 1
    assert repo.kinds("finish") == [("finish", "failed", "CHILD_EXIT_2")]
    assert not repo.kinds("finalize") and not repo.kinds("pause")


# Case 9: rerunning continues; verified members are never trained again.
def test_rerun_continues_without_duplicating_verified_work():
    trained = []
    repo = Campaign(train=lambda session: trained.append(session["member"]["id"]) or
                    (2 if len(trained) == 2 else 0))
    assert run(repo)[0] == 1
    code, summary = run(repo)
    assert code == 0 and summary["matrix_complete"]
    assert len(trained) == 4  # 3 members + one retry of the failed one
    assert trained[1] == trained[2]
    assert len(set(trained)) == 3


# Case 5: a wrong dataset stops before any claim and without pausing the campaign.
def test_initial_preflight_failure_is_mutation_free():
    repo = Campaign()

    def reject(*args):
        raise gd.GovernedDatasetError("RUN_DATASET_SNAPSHOT_IMMUTABLE")

    with pytest.raises(gd.GovernedDatasetError):
        executor.execute_campaign(repo, "c", "/unused", resume=True, check=reject)
    assert repo.calls == [("schema",)]


# Ctrl+C: the run is marked interrupted, nothing else is claimed, rerun resumes.
def test_interrupt_marks_run_and_rerun_resumes():
    def interrupt(session):
        raise KeyboardInterrupt

    repo = Campaign(train=interrupt)
    code, _ = run(repo)
    assert code == 130
    assert ("finish", "interrupted", "PARENT_INTERRUPTED_CHILD_REAPED") in repo.calls
    assert len(repo.kinds("claim")) == 1 and repo.state == "paused"
    repo.train = lambda session: 0
    code, summary = run(repo)
    assert code == 0 and summary["matrix_complete"] and ("resume",) in repo.calls


def test_runtime_differences_are_reported_not_blocking():
    row = {"environment": REFERENCE}
    current = executor.runtime_environment()
    assert executor.runtime_differences(row, current) == ["packages", "python"]
    assert "environment" not in executor.preflight.__code__.co_varnames


def test_campaign_determinism_reaches_train_children(monkeypatch):
    monkeypatch.delenv("PYTHONHASHSEED", raising=False)
    executor.apply_determinism({"environment": REFERENCE})
    assert os.environ["PYTHONHASHSEED"] == "42"
    assert "TF_DETERMINISTIC_OPS" not in os.environ or os.environ["TF_DETERMINISTIC_OPS"] != "None"


# Runtime is recorded on the run; the guarded campaign identity is left untouched.
class Connection:
    def __init__(self, catalog):
        self.catalog, self.statements = catalog, []

    def execute(self, statement, params):
        sql = str(statement)
        self.statements.append((sql, params))
        outer = self

        class Result:
            def scalars(self):
                return self

            def all(self):
                return list(outer.catalog)

            def scalar_one(self):
                outer.catalog.append("new-model-id")
                return "new-model-id"
        return Result()


def create_run(monkeypatch, catalog):
    monkeypatch.setattr("src.malaria_dl.execution.schema.require_e10_schema",
                        lambda c: {"revision": "20260922_01"})
    c = Connection(catalog)
    config = {"model_id": "custom_cnn", "resolved": {"execution": {"seed": 47}}}
    dataset = {"dataset_version_id": str(uuid4())}
    runtime = dict(REFERENCE, python="3.12.13", execution_mode="local_python", platform="Darwin")
    ExecutionRepository._create_run(c, str(uuid4()), config, dataset, REFERENCE, runtime=runtime)
    return c, runtime


def test_claim_records_runtime_without_changing_campaign_identity(monkeypatch):
    c, runtime = create_run(monkeypatch, ["model-id"])
    sql, params = next(s for s in c.statements if s[0].startswith("INSERT INTO runs"))
    parameters = json.loads(params["parameters"])
    assert parameters["model_configuration_e2"]["environment"] == REFERENCE
    assert parameters["runtime_environment"] == runtime
    assert params["model"] == "model-id"
    assert not any(s.startswith("INSERT INTO models") for s, _ in c.statements)


def test_first_run_registers_missing_model_catalog_row(monkeypatch):
    c, _ = create_run(monkeypatch, [])
    insert = [p for s, p in c.statements if s.startswith("INSERT INTO models")]
    assert len(insert) == 1 and insert[0]["name"] == "custom_cnn"
    assert insert[0]["framework"] == "tensorflow/keras"


def test_duplicate_model_catalog_rows_stay_an_identity_error(monkeypatch):
    with pytest.raises(CampaignError, match="CANONICAL_MODEL_CATALOG_IDENTITY_REQUIRED"):
        create_run(monkeypatch, ["a", "b"])


# Dataset location: the same governed materialization in Docker and on the host.
DOCKER_ROOT = "/app/malaria_dl_local_project/data/malaria_dataset_versions/d8c0cab5"
MAC_ROOT = "/Users/someone/capstone/malaria_dl_local_project/data/malaria_dataset_versions/d8c0cab5"


def snapshot(root, **changes):
    value = {k: "x" for k in ("dataset_version_id", "dataset_materialization_id",
                              "patient_assignment_fingerprint", "record_assignment_fingerprint",
                              "source_population_fingerprint", "clinical_identity_fingerprint")}
    return {**value, "dataset_root": root, "counts": {"train": 1, "val": 1, "test": 1}, **changes}


def test_relocated_host_prefix_is_the_same_dataset():
    gd.assert_run_dataset_snapshot_unchanged(snapshot(MAC_ROOT), snapshot(DOCKER_ROOT))
    assert gd.local_dataset_root(DOCKER_ROOT) == gd.PROJECT_ROOT / "data/malaria_dataset_versions/d8c0cab5"


@pytest.mark.parametrize("left", [
    snapshot(MAC_ROOT.replace("d8c0cab5", "other")),
    snapshot(MAC_ROOT, record_assignment_fingerprint="y"),
    snapshot(MAC_ROOT, counts={"train": 2, "val": 1, "test": 1}),
])
def test_different_dataset_is_still_rejected(left):
    with pytest.raises(gd.GovernedDatasetError):
        gd.assert_run_dataset_snapshot_unchanged(left, snapshot(DOCKER_ROOT))


# Case 4: wrong interpreter stops before any database access or attempt.
def test_wrong_virtualenv_is_rejected_before_database(monkeypatch, capsys):
    monkeypatch.setattr(local_launch.sys, "prefix", "/usr/local")
    monkeypatch.setattr(local_launch.sys, "base_prefix", "/usr/local")
    monkeypatch.setattr(local_launch, "database_url",
                        lambda: pytest.fail("database must not be configured"))
    environ = {}
    with pytest.raises(SystemExit) as stop:
        local_launch.bootstrap(environ, docker=False)
    assert stop.value.code == 2 and environ == {}
    err = capsys.readouterr().err
    assert "LOCAL_ENVIRONMENT_INVALID" in err and "source .venv-local-train/bin/activate" in err


def test_environment_problem_detects_version_and_missing_packages():
    venv = "/x/.venv-local-train"
    assert local_launch.environment_problem(venv, "/usr", (3, 12), lambda m: object()) is None
    assert "3.11" in local_launch.environment_problem(venv, "/usr", (3, 11), lambda m: object())
    missing = local_launch.environment_problem(venv, "/usr", (3, 12),
                                               lambda m: None if m == "tensorflow" else object())
    assert missing == "faltan paquetes: tensorflow"


def test_docker_bootstrap_changes_nothing():
    environ = {"DATABASE_URL": "postgresql://u:p@db:5432/x"}
    local_launch.bootstrap(environ, docker=True)
    assert environ == {"DATABASE_URL": "postgresql://u:p@db:5432/x"}


# Case 10: no JWT, bearer or agent_config.json: the database target comes from the Compose .env.
def test_host_bootstrap_needs_no_jwt(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text(f"POSTGRES_DB=capstone\nCAPSTONE_V2_RUNTIME_PASSWORD={PASSWORD}\nJWT_SECRET=never-used\n")
    monkeypatch.setattr(local_launch, "environment_problem", lambda: None)
    monkeypatch.setattr(local_launch, "database_url", lambda: URL(env))
    environ = {}
    local_launch.bootstrap(environ, docker=False)
    assert set(environ) == {"DATABASE_URL", "CAPSTONE_LOCAL_TRAIN"}
    assert environ["DATABASE_URL"].startswith("postgresql+psycopg://capstone_v2_runtime:")
    assert "@127.0.0.1:5432/capstone" in environ["DATABASE_URL"]
    assert "never-used" not in environ["DATABASE_URL"]
    assert "CAPSTONE_AGENT_BEARER" not in environ


def test_missing_compose_env_is_reported_without_secrets(tmp_path):
    env = tmp_path / ".env"
    env.write_text("POSTGRES_DB=capstone\n")
    with pytest.raises(local_launch.LocalLaunchError, match="LOCAL_DATABASE_CONFIG_MISSING"):
        local_launch.database_url(env)


# Case 11: the loopback relaxation is opt-in, loopback-only and not an auth change.
@pytest.fixture
def no_dotenv(monkeypatch):
    monkeypatch.setattr(database, "load_environment", lambda: None)


def test_loopback_database_requires_the_launcher_flag(monkeypatch, no_dotenv):
    local = f"postgresql+psycopg://capstone_v2_runtime:{quote(PASSWORD, safe='')}@127.0.0.1:5432/capstone"
    monkeypatch.setenv("DATABASE_URL", local)
    monkeypatch.delenv("CAPSTONE_LOCAL_TRAIN", raising=False)
    with pytest.raises(RuntimeError) as error:
        database.get_database_url()
    assert quote(PASSWORD, safe='') not in str(error.value)
    monkeypatch.setenv("CAPSTONE_LOCAL_TRAIN", "1")
    assert database.get_database_url() == local


@pytest.mark.parametrize("host", ["localhost", "[::1]", "host.docker.internal", "10.0.0.5", "other"])
def test_launcher_flag_never_admits_other_hosts(monkeypatch, no_dotenv, host):
    monkeypatch.setenv("CAPSTONE_LOCAL_TRAIN", "1")
    monkeypatch.setenv("DATABASE_URL", f"postgresql://u:{quote(PASSWORD, safe='')}@{host}:5432/capstone")
    with pytest.raises(RuntimeError) as error:
        database.get_database_url()
    assert quote(PASSWORD, safe='') not in str(error.value)


def test_database_is_published_on_loopback_only():
    from pathlib import Path
    compose = (Path(local_launch.PROJECT_ROOT).parent / "docker-compose.override.yml")
    if not compose.is_file():
        pytest.skip("Compose override not present in this checkout")
    text = compose.read_text()
    assert '"127.0.0.1:5432:5432"' in text and '"5432:5432"' not in text


def test_backend_authentication_is_unchanged():
    from pathlib import Path
    route = Path(local_launch.PROJECT_ROOT).parent / "backend_api/app/routes/local_execution.py"
    if not route.is_file():
        pytest.skip("backend not present in this checkout")
    # The launcher uses no HTTP: the local API still requires SYSTEM_ADMIN + local_jwt.
    assert "require_permission(Permission.SYSTEM_ADMIN)" in route.read_text()
    assert "local_jwt" in route.read_text()


# Case 6 and portability: the gate works on macOS (psutil) and still blocks.
def test_process_identity_is_stable_on_this_host():
    me = gg.process_identity(os.getpid())
    assert me["start_ticks"] is not None and me == gg.process_identity(os.getpid())
    assert not gg.process_absent(me)
    assert gg.resources()["available_bytes"] > 0


def test_remote_released_evidence_is_accepted_unreleased_is_not():
    remote = {"host": "other-host", "boot_id": "b", "pid": 1, "start_ticks": "1"}
    gg.verify_retained_processes({"identities": [remote], "sessions": [1], "release_confirmed": True})
    with pytest.raises(CampaignError, match="REMOTE_PROCESS_ABSENCE_UNPROVEN"):
        gg.verify_retained_processes({"identities": [remote], "sessions": [], "release_confirmed": False})


def test_local_live_process_still_blocks():
    me = gg.process_identity(os.getpid())
    with pytest.raises(CampaignError, match="PREVIOUS_EXPERIMENT_PROCESS_STILL_ALIVE"):
        gg.verify_retained_processes({"identities": [me], "sessions": [], "release_confirmed": True})


class GateEngine:
    """Scripted SQL: gate installed, advisory lock held by another coordinator."""

    def __init__(self, lock):
        self.lock, self.statements = lock, []

    def connect(self):
        return self

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append(sql)
        value = {"to_regclass": True, "pg_try_advisory_lock": self.lock}
        result = next((v for k, v in value.items() if k in sql), None)

        class Result:
            def scalar_one(self):
                return result
        return Result()

    def commit(self):
        pass

    def close(self):
        pass

    def dispose(self):
        pass


def test_busy_global_gate_stops_without_a_second_train():
    engine = GateEngine(lock=False)
    with pytest.raises(CampaignError, match="GLOBAL_EXPERIMENT_BUSY"):
        with gg.GlobalGate("campaign", engine_factory=lambda: engine):
            pytest.fail("no TRAIN may start while another coordinator holds the gate")
    assert not any("UPDATE experiment_execution_gate" in s for s in engine.statements)
    assert gg.CURRENT.get() is None


def test_launcher_bootstraps_before_heavy_imports():
    from pathlib import Path
    source = (Path(local_launch.PROJECT_ROOT) / "run_train_all_models.py").read_text()
    assert source.index("bootstrap()") < source.index("from src.malaria_dl.data.governed_dataset")
