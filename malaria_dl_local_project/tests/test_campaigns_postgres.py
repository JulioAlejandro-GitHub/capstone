"""Compose only: actual E4 migration in disposable schema, synthetic parent rows.

No public scientific writes. Most cases keep an outer transaction and roll back
DDL and data. The concurrency case commits ONLY the isolated schema/fixtures so
independent connections can race, then drops that validated test schema.
"""

import importlib.util
import os
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from src.malaria_dl.campaigns.contracts import (
    CampaignError,
    canonical,
    member_configuration,
)
from src.malaria_dl.campaigns.repository import CampaignRepository
from src.malaria_dl.campaigns.service import CampaignService
from src.malaria_dl.data.governed_dataset import GovernedDatasetSnapshot
from src.malaria_dl.persistence.database import get_engine
from test_campaigns_e4 import dataset, protocol
from test_campaigns_e4 import request as matrix_request

pytestmark = [
    pytest.mark.requires_docker_postgres,
    pytest.mark.skipif(
        os.getenv("RUN_STAGE4_POSTGRES_TESTS") != "1",
        reason="Authorized Compose E4 opt-in required",
    ),
]
ROOT = Path(__file__).resolve().parents[2]


def migration(revision="20260911_01_experimental_campaigns"):
    spec = importlib.util.spec_from_file_location(
        "campaign_migration",
        ROOT / "alembic/versions" / (revision + ".py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sanitized(exc):
    original = getattr(exc, "orig", exc)
    return {
        "type": type(exc).__name__,
        "original_type": type(original).__name__,
        "sqlstate": getattr(original, "sqlstate", None),
    }


def safe_test(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as exc:  # noqa: BLE001 -- sanitized diagnostics, including cleanup
            raise pytest.fail.Exception(
                f"E4 synthetic test {fn.__name__}: {sanitized(exc)}", pytrace=False
            ) from None

    return wrapped


def sql(c, statement, **params):
    return c.execute(text(statement), params)


@pytest.fixture
def isolated():
    schema = "capstone_test_e4_" + uuid4().hex
    assert re.fullmatch(r"capstone_test_[a-z0-9_]{6,48}", schema)
    engine = None
    connection = None
    outer = None
    created = False
    committed = False
    phase = "synthetic_prerequisites"
    try:
        engine = get_engine()
        connection = engine.connect()
        outer = connection.begin()
        sql(connection, f"CREATE SCHEMA {schema}")
        created = True
        sql(connection, f"SET LOCAL search_path TO {schema},pg_catalog")
        assert sql(connection, "SELECT current_schema()").scalar_one() == schema
        # Synthetic prerequisites. These do NOT accredit all public parent constraints.
        sql(
            connection,
            """CREATE TABLE experiments(id uuid PRIMARY KEY);
          CREATE TABLE dataset_versions(id uuid PRIMARY KEY);
          CREATE TABLE models(id uuid PRIMARY KEY,name text NOT NULL);
          CREATE TABLE runs(id uuid PRIMARY KEY,experiment_id uuid REFERENCES experiments(id),run_type text,model_id uuid REFERENCES models(id),
            status text DEFAULT 'started',metadata jsonb DEFAULT '{}',parameters jsonb DEFAULT '{}',finished_at timestamptz,
            dataset_version_id uuid REFERENCES dataset_versions(id),random_seed integer,execution_parameters jsonb);
          CREATE TABLE audit_events (LIKE public.audit_events INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);""",
        )
        # Retain append-only semantics on the isolated audit copy.
        sql(
            connection,
            """CREATE FUNCTION forbid_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
          BEGIN RAISE EXCEPTION 'audit append-only'; END $$;
          CREATE TRIGGER audit_append_only BEFORE UPDATE OR DELETE ON audit_events
          FOR EACH ROW EXECUTE FUNCTION forbid_audit_mutation();""",
        )
        mod = migration()
        mod.op = Operations(MigrationContext.configure(connection))
        phase = "migration_20260911_01"
        mod.upgrade()
        correction = migration("20260911_02_campaign_integrity")
        correction.op = mod.op
        phase = "migration_20260911_02"
        correction.upgrade()
        phase = "synthetic_seed"
        models = {}
        for name in (
            "custom_cnn",
            "vgg16",
            "densenet121",
            "vgg16_transfer_learning",
            "incompatible",
        ):
            models[name] = str(uuid4())
            sql(
                connection,
                "INSERT INTO models(id,name) VALUES(CAST(:id AS uuid),:name)",
                id=models[name],
                name=name,
            )
        d = dataset()
        evidence = str(uuid4())
        sql(
            connection,
            "INSERT INTO dataset_versions VALUES(CAST(:id AS uuid))",
            id=d["dataset_version_id"],
        )
        sql(
            connection,
            """INSERT INTO audit_events(id,event_type,action,resource_type,resource_id,request_method,request_path,
          correlation_id,after_state,metadata,success) VALUES(CAST(:id AS uuid),'ml.dataset_verification','verify','dataset_version',
          :dataset,'TEST','synthetic',:correlation,CAST(:payload AS jsonb),'{}',true)""",
            id=evidence,
            correlation=evidence,
            dataset=d["dataset_version_id"],
            payload=canonical(
                {
                    "dataset_version_id": d["dataset_version_id"],
                    "snapshot": d,
                    "integrity_status": "verified",
                }
            ),
        )

        @contextmanager
        def scope(readonly=False):
            with connection.begin_nested():
                yield connection

        repo = CampaignRepository(scope)
        environment = {
            "source_sha256": "e" * 64,
            "tensorflow": "synthetic",
            "determinism_environment": {},
            "python": "synthetic",
            "packages": {"synthetic": "1"},
        }
        snapshot = GovernedDatasetSnapshot(
            UUID(d["dataset_version_id"]),
            UUID(d["dataset_materialization_id"]),
            Path(d["dataset_root"]),
            d["patient_assignment_fingerprint"],
            d["record_assignment_fingerprint"],
            d["source_population_fingerprint"],
            d["clinical_identity_fingerprint"],
            d["counts"],
            evidence,
        )
        service = CampaignService(repo, lambda *a, **kw: snapshot, lambda: environment)

        def draft(seeds=None):
            return service.create(
                name="Synthetic E4",
                purpose="isolated planning test",
                dataset_version_id=d["dataset_version_id"],
                request=matrix_request(seeds),
                protocol=protocol(),
                actor="synthetic-test",
            )

        def freeze(seeds=None):
            row = draft(seeds)
            return service.freeze(str(row["id"]))

        def make_visible(barrier=None, pids=None):
            nonlocal committed
            outer.commit()
            committed = True

            @contextmanager
            def concurrent_scope(readonly=False):
                with engine.begin() as c:
                    if readonly:
                        sql(c, "SET TRANSACTION READ ONLY")
                    sql(c, f"SET LOCAL search_path TO {schema},pg_catalog")
                    sql(c, "SET LOCAL lock_timeout='5s'")
                    if not readonly and barrier is not None:
                        pids.append(sql(c, "SELECT pg_backend_pid()").scalar_one())
                        barrier.wait(timeout=5)
                    yield c

            return concurrent_scope

        yield SimpleNamespace(
            c=connection,
            repo=repo,
            service=service,
            draft=draft,
            freeze=freeze,
            dataset=d,
            evidence=evidence,
            environment=environment,
            models=models,
            schema=schema,
            make_visible=make_visible,
        )
    except Exception as exc:  # noqa: BLE001 -- sanitized diagnostics, including cleanup
        raise pytest.fail.Exception(
            f"E4 isolated setup/body: phase={phase}, {sanitized(exc)}", pytrace=False
        ) from None
    finally:
        # Pytest preserves a body failure separately if cleanup also fails.
        failures = []
        try:
            if outer is not None and outer.is_active:
                outer.rollback()
        except Exception as exc:  # noqa: BLE001 -- sanitized diagnostics, including cleanup
            failures.append({"phase": "rollback", **sanitized(exc)})
        try:
            if connection is not None:
                connection.close()
            if engine is not None:
                if created:
                    with engine.begin() as probe:
                        sql(probe, "SET TRANSACTION READ ONLY")
                        remains = sql(
                            probe,
                            "SELECT count(*) FROM pg_namespace WHERE nspname=:name",
                            name=schema,
                        ).scalar_one()
                    if remains:
                        if not committed:
                            failures.append(
                                {"phase": "unexpected_schema_after_rollback"}
                            )
                        with engine.begin() as cleanup:
                            sql(cleanup, f"DROP SCHEMA {schema} CASCADE")
                with engine.begin() as check:
                    sql(check, "SET TRANSACTION READ ONLY")
                    assert (
                        sql(
                            check,
                            "SELECT count(*) FROM pg_namespace WHERE nspname=:name",
                            name=schema,
                        ).scalar_one()
                        == 0
                    )
        except Exception as exc:  # noqa: BLE001 -- sanitized diagnostics, including cleanup
            failures.append({"phase": "schema_absence", **sanitized(exc)})
        finally:
            if engine is not None:
                try:
                    engine.dispose()
                except Exception as exc:  # noqa: BLE001 -- preserve cleanup diagnostics
                    failures.append({"phase": "dispose", **sanitized(exc)})
        if failures:
            pytest.fail(f"E4 cleanup: {failures}", pytrace=False)


def rejected(c, statement, **params):
    with pytest.raises(DBAPIError) as caught, c.begin_nested():
        sql(c, statement, **params)
    assert sql(c, "SELECT 1").scalar_one() == 1
    return caught.value.orig.sqlstate


@safe_test
def test_public_migration_readonly():
    engine = get_engine()
    try:
        with engine.begin() as c:
            sql(c, "SET TRANSACTION READ ONLY")
            assert (
                sql(c, "SELECT version_num FROM public.alembic_version").scalar_one()
                == "20260911_02"
            )
            assert (
                sql(
                    c,
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('experimental_campaigns','campaign_configurations','campaign_members','campaign_attempts')",
                ).scalar_one()
                == 4
            )
            assert (
                sql(
                    c,
                    "SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND indexname='uq_campaign_one_active_attempt'",
                ).scalar_one()
                == 1
            )
            assert (
                sql(
                    c,
                    "SELECT count(*) FROM pg_trigger WHERE tgrelid='public.runs'::regclass AND tgname='campaign_run_identity_guard' AND tgenabled<>'D'",
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


@pytest.mark.parametrize("seeds,count", [([11], 12), ([11, 12, 13], 36)])
@safe_test
def test_freeze_roundtrip_immutable_and_reconstruct(
    isolated, monkeypatch, seeds, count
):
    s = isolated
    row = s.freeze(seeds)
    cid = str(row["id"])
    assert (
        row["state"] == "frozen"
        and len(row["members"]) == count
        and row["attempts"] == []
    )
    # New repository instance reconstructs entirely from DB, no config file reads.
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("configuration read forbidden")
        ),
    )
    assert CampaignRepository(s.repo.scope).get(cid)["contract"] == row["contract"]
    for statement in (
        "UPDATE experimental_campaigns SET protocol='{}' WHERE id=CAST(:id AS uuid)",
        "UPDATE campaign_members SET seed=seed+100 WHERE campaign_id=CAST(:id AS uuid)",
        "DELETE FROM campaign_members WHERE campaign_id=CAST(:id AS uuid)",
        "UPDATE campaign_configurations SET configuration='{}' WHERE campaign_id=CAST(:id AS uuid)",
    ):
        rejected(s.c, statement, id=cid)
    before = row["contract_hash"]
    after = s.repo.transition(cid, "active")
    assert after["contract_hash"] == before and after["contract"] == row["contract"]
    with pytest.raises(CampaignError):
        s.repo.transition(cid, "finalized")
    with pytest.raises(CampaignError):
        s.repo.get(cid, str(uuid4()))
    assert (
        sql(
            s.c,
            "SELECT count(*) FROM audit_events WHERE event_type LIKE 'ml.campaign.%'",
        ).scalar_one()
        > count
    )


@safe_test
def test_atomic_failure_leaves_draft_no_partial_matrix(isolated):
    s = isolated
    row = s.draft()
    cid = str(row["id"])
    sql(
        s.c,
        """CREATE FUNCTION inject_member_failure() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN IF NEW.position=3 THEN RAISE EXCEPTION 'synthetic member insertion failure'; END IF; RETURN NEW; END $$;
      CREATE TRIGGER inject_member_failure BEFORE INSERT ON campaign_members FOR EACH ROW EXECUTE FUNCTION inject_member_failure();""",
    )
    with pytest.raises(CampaignError):
        s.service.freeze(cid)
    result = s.repo.get(cid)
    assert result["state"] == "draft" and result["contract"] is None
    assert (
        result["members"] == []
        and result["configurations"] == []
        and result["attempts"] == []
    )
    assert (
        sql(
            s.c,
            "SELECT count(*) FROM audit_events WHERE event_type='ml.campaign.campaign_members'",
        ).scalar_one()
        == 0
    )


@safe_test
def test_attempts_retry_identity_and_train_link(isolated):
    s = isolated
    row = s.freeze()
    cid = str(row["id"])
    member = row["members"][0]
    mid = str(member["id"])
    result = s.repo.create_attempt(cid, mid)
    attempt = str(result["attempts"][0]["id"])
    assert len(result["members"]) == 12 and result["members"][0]["state"] == "active"
    with pytest.raises(CampaignError):
        s.repo.create_attempt(cid, mid)
    with pytest.raises(CampaignError):
        s.repo.update_attempt(cid, attempt, state="verified")
    result = s.repo.update_attempt(
        cid, attempt, state="failed", cause="synthetic interruption"
    )
    result = s.repo.create_attempt(cid, mid)
    second = str(result["attempts"][1]["id"])
    assert [a["ordinal"] for a in result["attempts"]] == [1, 2] and len(
        result["members"]
    ) == 12
    config = row["contract"]["matrix"]["configurations"][member["configuration_hash"]][
        "configuration"
    ]
    run = str(uuid4())
    effective = member_configuration(config, member["seed"])
    snapshot = {
        "configuration": effective,
        "dataset": s.dataset,
        "environment": s.environment,
    }
    sql(
        s.c,
        """INSERT INTO runs(id,model_id,run_type,dataset_version_id,random_seed,execution_parameters)
       VALUES(CAST(:id AS uuid),CAST(:model AS uuid),'training',CAST(:dataset AS uuid),:seed,CAST(:parameters AS jsonb))""",
        id=run,
        model=s.models[config["model_id"]],
        dataset=s.dataset["dataset_version_id"],
        seed=member["seed"] + 1,
        parameters=canonical({"model_configuration_e2": snapshot}),
    )
    with pytest.raises(CampaignError):
        s.repo.update_attempt(cid, second, training_run_id=run)
    sql(
        s.c,
        "UPDATE runs SET random_seed=:seed WHERE id=CAST(:id AS uuid)",
        seed=member["seed"],
        id=run,
    )
    result = s.repo.update_attempt(cid, second, training_run_id=run)
    assert str(result["attempts"][1]["training_run_id"]) == run
    rejected(
        s.c,
        "UPDATE runs SET random_seed=random_seed+1 WHERE id=CAST(:id AS uuid)",
        id=run,
    )
    result = s.repo.update_attempt(cid, second, state="completed")
    assert (
        result["members"][0]["state"] == "completed"
        and result["members"][0]["accepted_attempt_id"] is None
    )
    with pytest.raises(CampaignError):
        s.repo.create_attempt(cid, mid)
    rejected(s.c, "DELETE FROM campaign_attempts WHERE id=CAST(:id AS uuid)", id=second)
    rejected(
        s.c,
        "UPDATE campaign_members SET state='verified' WHERE id=CAST(:id AS uuid)",
        id=mid,
    )
    rejected(
        s.c,
        "INSERT INTO campaign_attempts(id,member_id,ordinal,state) VALUES(gen_random_uuid(),CAST(:id AS uuid),1,'active')",
        id=str(uuid4()),
    )


@safe_test
def test_concurrent_active_attempt_two_connections(isolated):
    s = isolated
    row = s.freeze()
    cid = str(row["id"])
    mid = str(row["members"][0]["id"])
    barrier = Barrier(2)
    pids = []
    scope = s.make_visible(barrier, pids)

    def worker():
        repo = CampaignRepository(scope)
        try:
            repo.create_attempt(cid, mid)
            return "created"
        except CampaignError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(worker) for _ in range(2)]
        results = [f.result(timeout=15) for f in futures]
    if sorted(results) != ["created", "rejected"]:
        pytest.fail(
            f"E4 concurrent phase=workers outcomes={sorted(results)}", pytrace=False
        )
    if len(set(pids)) != 2:
        pytest.fail("E4 concurrent phase=distinct_connections", pytrace=False)
    loaded = CampaignRepository(scope).get(cid)
    assert len(loaded["attempts"]) == 1 and loaded["attempts"][0]["state"] == "active"
    assert loaded["members"][0]["state"] == "active"

    # Reconstruct from a fresh process while the isolated fixture is visible.
    import subprocess
    import sys

    code = """
import sys,json
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import text
from src.malaria_dl.campaigns.repository import CampaignRepository
from src.malaria_dl.persistence.database import get_engine
assert 'src.malaria_dl.models.registry' not in sys.modules
config_root=(Path.cwd()/'configs').resolve()
original_read_bytes,original_read_text=Path.read_bytes,Path.read_text
def guarded(reader):
    def read(path,*a,**kw):
        if path.resolve().is_relative_to(config_root):
            raise AssertionError('local configuration read forbidden')
        return reader(path,*a,**kw)
    return read
Path.read_bytes=guarded(original_read_bytes)
Path.read_text=guarded(original_read_text)
schema,campaign=sys.argv[1:]
assert schema.startswith('capstone_test_e4_') and schema.replace('_','').isalnum()
engine=get_engine()
@contextmanager
def scope(readonly=False):
    with engine.begin() as c:
        c.execute(text('SET TRANSACTION READ ONLY'))
        c.execute(text('SET LOCAL search_path TO '+schema+',pg_catalog'))
        yield c
try:
    result=CampaignRepository(scope).get(campaign)
    assert len(result['members'])==12 and len(result['attempts'])==1
    assert 'src.malaria_dl.models.registry' not in sys.modules
    print('fresh_process_readback_ok')
finally:engine.dispose()
"""
    child = subprocess.run(
        [sys.executable, "-B", "-c", code, s.schema, cid],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if child.returncode != 0 or child.stdout.strip() != "fresh_process_readback_ok":
        pytest.fail(
            f"E4 concurrent phase=fresh_process returncode={child.returncode}",
            pytrace=False,
        )


@pytest.mark.parametrize(
    "conflict", ["dataset", "configuration", "environment", "run_type"]
)
@safe_test
def test_incompatible_train_association(isolated, conflict):
    from copy import deepcopy

    s = isolated
    row = s.freeze()
    cid = str(row["id"])
    m = row["members"][0]
    result = s.repo.create_attempt(cid, str(m["id"]))
    aid = str(result["attempts"][0]["id"])
    config = row["contract"]["matrix"]["configurations"][m["configuration_hash"]][
        "configuration"
    ]
    snapshot = {
        "configuration": member_configuration(config, m["seed"]),
        "dataset": deepcopy(s.dataset),
        "environment": deepcopy(s.environment),
    }
    dataset_id = s.dataset["dataset_version_id"]
    kind = "training"
    if conflict == "dataset":
        dataset_id = str(uuid4())
        sql(
            s.c, "INSERT INTO dataset_versions VALUES(CAST(:id AS uuid))", id=dataset_id
        )
    if conflict == "configuration":
        snapshot["configuration"]["resolved"]["model"]["dropout"] = 0.123
    if conflict == "environment":
        snapshot["environment"]["source_sha256"] = "f" * 64
    if conflict == "run_type":
        kind = "evaluation"
    run = str(uuid4())
    sql(
        s.c,
        """INSERT INTO runs(id,model_id,run_type,dataset_version_id,random_seed,execution_parameters)
       VALUES(CAST(:id AS uuid),CAST(:model AS uuid),:kind,CAST(:dataset AS uuid),:seed,CAST(:parameters AS jsonb))""",
        id=run,
        model=s.models[config["model_id"]],
        kind=kind,
        dataset=dataset_id,
        seed=m["seed"],
        parameters=canonical({"model_configuration_e2": snapshot}),
    )
    with pytest.raises(CampaignError):
        s.repo.update_attempt(cid, aid, training_run_id=run)
    assert s.repo.get(cid)["attempts"][0]["training_run_id"] is None


@safe_test
def test_database_uniqueness_and_cross_campaign_fk(isolated):
    s = isolated
    source = s.freeze()
    draft = s.draft()
    cid = str(draft["id"])
    other = s.draft()
    h = source["members"][0]["configuration_hash"]
    statement = """INSERT INTO campaign_configurations(campaign_id,configuration_hash,configuration,canonical_configuration,requests)
       SELECT CAST(:id AS uuid),configuration_hash,configuration,canonical_configuration,requests
       FROM campaign_configurations WHERE campaign_id=CAST(:source AS uuid) AND configuration_hash=:hash"""
    params = {"id": cid, "source": str(source["id"]), "hash": h}
    sql(s.c, statement, **params)
    assert rejected(s.c, statement, **params) == "23505"
    member_sql = """INSERT INTO campaign_members(id,campaign_id,configuration_hash,seed,position,state)
       VALUES(CAST(:member AS uuid),CAST(:campaign AS uuid),:hash,11,0,'pending')"""
    sql(s.c, member_sql, member=str(uuid4()), campaign=cid, hash=h)
    assert (
        rejected(s.c, member_sql, member=str(uuid4()), campaign=cid, hash=h) == "23505"
    )
    assert (
        rejected(
            s.c, member_sql, member=str(uuid4()), campaign=str(other["id"]), hash=h
        )
        == "23503"
    )


def stage_frozen_contract(s):
    """Prepare relational draft rows; final UPDATE below bypasses Python validation."""
    from src.malaria_dl.campaigns.contracts import expand_matrix

    row = s.draft()
    cid = str(row["id"])
    matrix = expand_matrix(
        row["requested"], row["protocol"], frozen=True, dataset=s.dataset
    )
    contract = {
        "version": "campaign_contract_v1",
        "name": row["name"],
        "purpose": row["purpose"],
        "experiment_id": None,
        "dataset": s.dataset,
        "dataset_evidence_id": s.evidence,
        "requested": row["requested"],
        "protocol": row["protocol"],
        "environment": s.environment,
        "matrix": matrix,
    }
    for h, item in matrix["configurations"].items():
        sql(
            s.c,
            """INSERT INTO campaign_configurations(campaign_id,configuration_hash,configuration,canonical_configuration,requests)
          VALUES(CAST(:id AS uuid),:hash,CAST(:config AS jsonb),:canonical,CAST(:requests AS jsonb))""",
            id=cid,
            hash=h,
            config=canonical(item["configuration"]),
            canonical=canonical(item["configuration"]),
            requests=canonical(item["requests"]),
        )
    for m in matrix["members"]:
        sql(
            s.c,
            """INSERT INTO campaign_members(id,campaign_id,configuration_hash,seed,position,state)
           VALUES(CAST(:id AS uuid),CAST(:campaign AS uuid),:hash,:seed,:position,'pending')""",
            id=str(uuid4()),
            campaign=cid,
            hash=m["configuration_hash"],
            seed=m["seed"],
            position=m["position"],
        )
    return cid, contract


# Missing and JSON null are different encodings, and SQL NULL hash is separate.
NULL_CASES = [
    ("sql_hash_null",),
    ("missing", "protocol", "budget", "max_members"),
    ("null", "protocol", "budget", "max_members"),
    ("missing", "protocol", "budget", "max_attempts_per_member"),
    ("null", "protocol", "budget", "max_attempts_per_member"),
    ("null", "protocol", "budget"),
    ("string_budget",),
    ("bool_budget",),
    ("zero_attempt_budget",),
    ("null", "matrix", "seeds"),
    ("missing", "matrix", "seeds"),
    ("null_seed",),
    ("object_seeds",),
    ("null", "matrix", "configurations"),
    ("null", "matrix", "registry"),
    ("null", "environment", "source_sha256"),
    ("missing", "version"),
    ("null", "protocol", "metrics"),
    ("null", "matrix", "expected_count"),
]


@pytest.mark.parametrize("case", NULL_CASES, ids=lambda c: "_".join(c))
@safe_test
def test_sql_rejects_missing_and_null_frozen_fields(isolated, case):
    from src.malaria_dl.campaigns.contracts import digest

    s = isolated
    cid, contract = stage_frozen_contract(s)
    if case[0] in ("missing", "null"):
        value = contract
        for key in case[1:-1]:
            value = value[key]
        if case[0] == "missing":
            value.pop(case[-1])
        else:
            value[case[-1]] = None
    elif case[0] == "string_budget":
        contract["protocol"]["budget"]["max_members"] = "100"
    elif case[0] == "bool_budget":
        contract["protocol"]["budget"]["max_attempts_per_member"] = True
    elif case[0] == "zero_attempt_budget":
        contract["protocol"]["budget"]["max_attempts_per_member"] = 0
    elif case[0] == "null_seed":
        contract["matrix"]["seeds"] = [None]
    elif case[0] == "object_seeds":
        contract["matrix"]["seeds"] = {}
    state = rejected(
        s.c,
        """UPDATE experimental_campaigns SET state='frozen',frozen_at=now(),expected_count=12,
       contract=CAST(:contract AS jsonb),canonical_contract=:canonical,contract_hash=:hash,
       protocol=CAST(:protocol AS jsonb),environment=CAST(:environment AS jsonb),registry_snapshot=CAST(:registry AS jsonb)
       WHERE id=CAST(:id AS uuid)""",
        id=cid,
        contract=canonical(contract),
        canonical=canonical(contract),
        hash=None if case[0] == "sql_hash_null" else digest(contract),
        protocol=canonical(contract["protocol"]),
        environment=canonical(contract["environment"]),
        registry=canonical(contract["matrix"]["registry"]),
    )
    if case[0] == "sql_hash_null" or case in (
        ("missing", "protocol", "budget", "max_members"),
        ("null", "protocol", "budget", "max_members"),
    ):
        assert (
            state == "23514"
        )  # New CHECK, not an inconsistent test fixture caught elsewhere.
    assert s.repo.get(cid)["state"] == "draft"


@pytest.mark.parametrize(
    "path,value",
    [
        ((field,), None)
        for field in ("model", "optimizer", "execution", "recipe", "input_contract")
    ]
    + [
        (("model", "dropout"), True),
        (("model", "head_units"), -1),
        (("model", "head_units"), None),
        (("model", "head_units"), True),
        (("model", "head_units"), "0"),
        (("model", "preprocessing"), 12),
        (("execution", "deterministic_ops"), "false"),
        (("recipe", "metrics"), []),
        (("selection", "beta"), None),
    ],
)
@safe_test
def test_sql_rejects_null_configuration(isolated, path, value):
    from copy import deepcopy

    from src.malaria_dl.campaigns.contracts import digest

    s = isolated
    cid, c = stage_frozen_contract(s)
    item = deepcopy(next(iter(c["matrix"]["configurations"].values())))
    target = item["configuration"]["resolved"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert (
        rejected(
            s.c,
            """INSERT INTO campaign_configurations(campaign_id,configuration_hash,configuration,canonical_configuration,requests)
       VALUES(CAST(:id AS uuid),:hash,CAST(:config AS jsonb),:canonical,CAST(:requests AS jsonb))""",
            id=cid,
            hash=digest(item["configuration"]),
            config=canonical(item["configuration"]),
            canonical=canonical(item["configuration"]),
            requests=canonical(item["requests"]),
        )
        == "23514"
    )


def insert_linkable_train(s, model_name="custom_cnn", catalog_name=None):
    row = s.freeze()
    cid = str(row["id"])
    m = next(
        m
        for m in row["members"]
        if row["contract"]["matrix"]["configurations"][m["configuration_hash"]][
            "configuration"
        ]["model_id"]
        == model_name
    )
    cfg = member_configuration(
        row["contract"]["matrix"]["configurations"][m["configuration_hash"]][
            "configuration"
        ],
        m["seed"],
    )
    result = s.repo.create_attempt(cid, str(m["id"]))
    aid = str(result["attempts"][0]["id"])
    run = str(uuid4())
    model_id = s.models[catalog_name or model_name]
    sql(
        s.c,
        """INSERT INTO runs(id,model_id,run_type,dataset_version_id,random_seed,execution_parameters)
       VALUES(CAST(:id AS uuid),CAST(:model AS uuid),'training',CAST(:dataset AS uuid),:seed,CAST(:parameters AS jsonb))""",
        id=run,
        model=model_id,
        dataset=s.dataset["dataset_version_id"],
        seed=m["seed"],
        parameters=canonical(
            {
                "model_configuration_e2": {
                    "configuration": cfg,
                    "dataset": s.dataset,
                    "environment": s.environment,
                }
            }
        ),
    )
    return cid, aid, run, cfg


@pytest.mark.parametrize("case", ["canonical", "alias", "wrong", "null"])
@safe_test
def test_relational_model_and_explicit_alias(isolated, case):
    s = isolated
    cid, aid, run, _ = insert_linkable_train(
        s, "vgg16", "vgg16_transfer_learning" if case == "alias" else "vgg16"
    )
    if case in ("wrong", "null"):
        sql(
            s.c,
            "UPDATE runs SET model_id=CAST(:model AS uuid) WHERE id=CAST(:id AS uuid)",
            id=run,
            model=s.models["incompatible"] if case == "wrong" else None,
        )
        with pytest.raises(CampaignError):
            s.repo.update_attempt(cid, aid, training_run_id=run)
    else:
        assert (
            s.repo.update_attempt(cid, aid, training_run_id=run)["attempts"][0][
                "training_run_id"
            ]
            is not None
        )


@safe_test
def test_train_identity_guard_allows_real_e2_progress_writer(isolated, monkeypatch):
    from contextlib import nullcontext

    from src.malaria_dl.persistence import model_configuration as e2

    s = isolated
    cid, aid, run, cfg = insert_linkable_train(s)
    s.repo.update_attempt(cid, aid, training_run_id=run)
    rejected(
        s.c,
        "UPDATE runs SET model_id=CAST(:model AS uuid) WHERE id=CAST(:id AS uuid)",
        id=run,
        model=s.models["incompatible"],
    )
    rejected(
        s.c,
        "UPDATE models SET name='changed' WHERE id=CAST(:id AS uuid)",
        id=s.models["custom_cnn"],
    )
    rejected(
        s.c,
        """UPDATE runs SET execution_parameters=jsonb_set(execution_parameters,
        '{model_configuration_e2,environment,source_sha256}','\"changed\"') WHERE id=CAST(:id AS uuid)""",
        id=run,
    )
    # The actual E2 writer refreshes observed metadata and runtime on each phase.
    monkeypatch.setattr(
        e2,
        "get_engine",
        lambda: SimpleNamespace(begin=lambda: s.repo.scope(), dispose=lambda: None),
    )
    monkeypatch.setattr(e2, "dataset_read_connection", lambda: nullcontext(s.c))
    observed = {
        **s.environment,
        "git_dirty": True,
        "git_commit": "same-effective-code-metadata",
        "devices": [{"name": "synthetic", "type": "CPU"}],
    }
    monkeypatch.setattr(e2, "environment_identity", lambda: observed)
    snapshot = e2.persist_model_configuration(
        run, cfg, {"fine_tuning": {"synthetic": True}}, s.dataset, {"progress": 2}
    )
    assert snapshot["environment"] == observed
    sql(
        s.c,
        """UPDATE runs SET status='completed',finished_at=now(),metadata='{"checkpoint":"synthetic"}',
       parameters='{"progress": 2}' WHERE id=CAST(:id AS uuid)""",
        id=run,
    )
    assert (
        sql(
            s.c, "SELECT status FROM runs WHERE id=CAST(:id AS uuid)", id=run
        ).scalar_one()
        == "completed"
    )
    s.repo.update_attempt(cid, aid, state="completed")


@safe_test
def test_configuration_json_shape_operator_precedence(isolated):
    from src.malaria_dl.campaigns.contracts import expand_matrix

    s = isolated

    def require(condition, phase):
        if not condition:
            # Only controlled phase/model identifiers, never driver text or payload.
            pytest.fail(f"E4 synthetic check failed: {phase}", pytrace=False)

    require(
        rejected(
            s.c,
            "SELECT CAST(:payload AS jsonb)->'shape' - 0",
            payload=canonical({"shape": [None, 200, 200, 3]}),
        )
        == "22P02",
        "original_shape_expression_sqlstate",
    )
    require(
        sql(
            s.c,
            "SELECT (CAST(:payload AS jsonb)->'shape') - 0",
            payload=canonical({"shape": [None, 200, 200, 3]}),
        ).scalar_one()
        == [200, 200, 3],
        "corrected_shape_expression",
    )
    matrix = expand_matrix(matrix_request(), protocol(), frozen=True, dataset=s.dataset)
    for item in matrix["configurations"].values():
        config = item["configuration"]
        require(
            sql(
                s.c,
                "SELECT campaign_configuration_valid(CAST(:config AS jsonb))",
                config=canonical(config),
            ).scalar_one()
            is True,
            "configuration_valid:"
            + config["model_id"]
            + ":"
            + config["resolved"]["optimizer"]["name"],
        )
