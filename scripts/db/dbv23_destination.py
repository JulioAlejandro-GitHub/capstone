"""Create/certify/restart persistent DBV2.3. Deliberately has NO delete operation."""

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import psycopg
from dbv23_source import DOCKER, E, metadata, save
from dbv23_source import read as source_read
from psycopg import sql
from psycopg.rows import dict_row
from v2_catalog_probe import snapshot

from alembic_v2.safety import (
    IDENTITY_SQL,
    ROLES_SQL,
    inspect_isolation,
    validate_server_snapshot,
)

TARGET = E / "persistent_target.json"
PRIVATE = ROOT / "var/maintenance/dbv23_persistent"
PYTHON = ROOT / "malaria_dl_local_project/.venv/bin/python"
EXPECTED_MANIFEST = "15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb"
EXPECTED_REVISION = "e3aaad12e49e65cff8ad9742fcdd83af075f2e2fcfaa81733a2bec121efef279"


def run(argv, env=None, check=True):
    p = subprocess.run(
        list(map(str, argv)), env=env, text=True, capture_output=True, check=False
    )
    with (E / "destination_commands.jsonl").open("a") as f:
        f.write(
            json.dumps(
                {
                    "argv": list(map(str, argv)),
                    "returncode": p.returncode,
                    "stdout": p.stdout,
                    "stderr": p.stderr,
                }
            )
            + "\n"
        )
    if check and p.returncode:
        raise RuntimeError("Destination command failed; see non-secret command log")
    return p


def verify_baseline():
    p = ROOT / "alembic_v2/versions/20260929_01_pg_v2_baseline.py"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == EXPECTED_REVISION
    p = ROOT / "docs/audits/db_v2/dbv2_2/restart_r1/dbv2_2_catalog_manifest.json"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == EXPECTED_MANIFEST
    p = ROOT / "alembic_v2/baseline/catalog_manifest.json"
    m = json.loads(p.read_text())
    expected = json.loads(
        (ROOT / "docs/audits/db_v2/dbv2_2/restart_r1/certificate.json").read_text()
    )["resource_manifest_sha256"]
    assert hashlib.sha256(p.read_bytes()).hexdigest() == expected
    for name, h in m["files"].items():
        assert hashlib.sha256((p.parent / name).read_bytes()).hexdigest() == h


def connect(t, role="capstone_v2_migrator", database=None):
    credentials = json.loads((PRIVATE / "credentials.json").read_text())
    return psycopg.connect(
        host="127.0.0.1",
        port=t["host_port"],
        dbname=database or t["database"],
        user=role,
        password=credentials[role],
        autocommit=True,
        row_factory=dict_row,
    )


def separation(t, system_id):
    s = json.loads((E / "source_identity.json").read_text())
    assert metadata() == s["environment"]
    assert t["container_id"] != s["environment"]["container_id"]
    assert (
        t["database"] != s["server"]["database"]
        and t["host_port"] != s["environment"]["host_port"]
    )
    assert (
        t["volume"] != s["environment"]["volume"]
        and system_id != s["server"]["system_identifier"]
    )
    save(
        "source_destination_separation.json",
        {
            "status": "PASS",
            "source": s,
            "destination": dict(t, postgres_system_identifier=system_id),
            "same_physical_host": True,
            "different_container": True,
            "different_port": True,
            "different_database": True,
            "different_cluster": True,
            "different_volume": True,
        },
    )


def guard():
    verify_baseline()
    t = json.loads(TARGET.read_text())
    inspect_isolation(t)
    with connect(t) as c:
        identity = c.execute(IDENTITY_SQL).fetchone()
        roles = c.execute(ROLES_SQL).fetchall()
        validate_server_snapshot(t, identity, roles)
    separation(t, identity["system_identifier"])
    save(
        "destination_identity.json", {"target": t, "identity": identity, "roles": roles}
    )
    return t


def provision():
    verify_baseline()
    assert not TARGET.exists(), "Persistent target already exists: NEVER recreate"
    source_read("SELECT json_build_object('pre_provision','read_only')")
    name = "capstone_db_v2"
    volume = "capstone_v2_isolated_persistent_data"
    database = "capstone_v2_isolated_persistent"
    # Refuse both existing container and existing volume, even if a descriptor is absent.
    assert run(DOCKER + ["container", "inspect", name], check=False).returncode != 0
    assert run(DOCKER + ["volume", "inspect", volume], check=False).returncode != 0
    assert not PRIVATE.exists(), "Refuse to replace persistent credentials"
    PRIVATE.mkdir(parents=True, mode=0o700)
    PRIVATE.chmod(0o700)
    credentials = {
        r: secrets.token_hex(32)
        for r in ("postgres", "capstone_v2_migrator", "capstone_v2_runtime")
    }
    p = PRIVATE / "credentials.json"
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(credentials, f)
    nonce = str(uuid4())
    label = "org.capstone.pgv2.isolation=" + nonce
    life = "org.capstone.pgv2.lifecycle=persistent"
    t = {
        "authorized_stage": "DBV2.3",
        "gate_dbv22_approved": True,
        "persistent": True,
        "isolation_id": nonce,
        "container_name": name,
        "volume": volume,
        "host_port": 56440,
        "database": database,
    }
    # Names/configuration separation before creating storage or starting the cluster.
    s = json.loads((E / "source_identity.json").read_text())
    assert (
        name != s["environment"]["container_name"]
        and volume != s["environment"]["volume"]
        and database != s["server"]["database"]
        and t["host_port"] != s["environment"]["host_port"]
    )
    run(DOCKER + ["image", "inspect", "postgres:17.9", "--format", "{{.Id}}"])
    run(DOCKER + ["volume", "create", "--label", label, "--label", life, volume])
    env = dict(os.environ, POSTGRES_PASSWORD=credentials["postgres"])
    t["container_id"] = run(
        DOCKER
        + [
            "run",
            "-d",
            "--name",
            name,
            "--restart",
            "unless-stopped",
            "--label",
            label,
            "--label",
            life,
            "-e",
            "POSTGRES_PASSWORD",
            "-e",
            "POSTGRES_HOST_AUTH_METHOD=scram-sha-256",
            "-e",
            "PGDATA=/var/lib/postgresql/data",
            "-p",
            "127.0.0.1:56440:5432",
            "-v",
            volume + ":/var/lib/postgresql/data",
            "postgres:17.9",
        ],
        env=env,
    ).stdout.strip()
    save("provisioning_persistent_target.json", t)
    for _ in range(30):
        if (
            run(
                DOCKER + ["exec", t["container_id"], "pg_isready", "-U", "postgres"],
                check=False,
            ).returncode
            == 0
        ):
            break
        time.sleep(1)
    inspect_isolation(t)
    with connect(t, role="postgres", database="postgres") as c:
        identity = c.execute(
            "SELECT current_database() AS database,current_setting('server_version_num')::int AS version,system_identifier::text AS id FROM pg_control_system()"
        ).fetchone()
        assert identity["database"] == "postgres" and identity["version"] == 170009
        separation(t, identity["id"])
        t["postgres_system_identifier"] = identity["id"]
        save(
            "before_first_destination_sql_write.json",
            {"identity": identity, "source_destination_different": True, "target": t},
        )
        for role in ("capstone_v2_migrator", "capstone_v2_runtime"):
            c.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                ).format(sql.Identifier(role), sql.Literal(credentials[role]))
            )
        c.execute(
            sql.SQL(
                "CREATE DATABASE {} OWNER capstone_v2_migrator TEMPLATE template0"
            ).format(sql.Identifier(database))
        )
    with connect(t, role="postgres") as c:
        identity = c.execute(
            "SELECT current_database() AS database,current_setting('server_version_num')::int AS version,system_identifier::text AS id FROM pg_control_system()"
        ).fetchone()
        assert identity == {
            "database": database,
            "version": 170009,
            "id": t["postgres_system_identifier"],
        }
        separation(t, identity["id"])
        c.execute(
            "GRANT EXECUTE ON FUNCTION pg_control_system() TO capstone_v2_migrator"
        )
        t["database_oid"] = c.execute(
            "SELECT oid::int AS oid FROM pg_database WHERE datname=current_database()"
        ).fetchone()["oid"]
    save("persistent_target.json", t)
    p = PRIVATE / "pgpass"
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        for role, pw in credentials.items():
            f.write(f"127.0.0.1:{t['host_port']}:*:{role}:{pw}\n")
    guard()
    with connect(t) as c:
        state = snapshot(c)
        assert (
            not state["relations"] and not state["functions"] and not state["triggers"]
        )
        save("destination_empty_catalog.json", state)
    print(
        "Persistent empty target provisioned; source != destination verified before SQL writes."
    )


def upgrade():
    t = guard()
    env = dict(
        os.environ,
        PGV2_DATABASE_URL=f"postgresql+psycopg://capstone_v2_migrator@127.0.0.1:{t['host_port']}/{t['database']}",
        PGV2_TARGET=str(TARGET),
        PGPASSFILE=str(PRIVATE / "pgpass"),
        PYTHONPATH=str(ROOT),
    )
    run([PYTHON, "-m", "alembic", "-c", "alembic_v2.ini", "upgrade", "head"], env=env)
    for cmd in ("current", "heads"):
        run([PYTHON, "-m", "alembic", "-c", "alembic_v2.ini", cmd], env=env)
    print("Persistent target installed only via certified Alembic baseline.")


def certify(suffix="before_restart"):
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    t = guard()
    with connect(t) as c:
        actual = snapshot(c)
        head = c.execute("SELECT version_num FROM alembic_version").fetchall()
        counts = {
            r["name"]: c.execute(
                sql.SQL("SELECT count(*) AS n FROM {}").format(
                    sql.Identifier(r["name"])
                )
            ).fetchone()["n"]
            for r in actual["relations"]
            if r["relkind"] == "r"
        }
    save("catalog_" + suffix + ".json", actual)
    digest = hashlib.sha256(
        (E / ("catalog_" + suffix + ".json")).read_bytes()
    ).hexdigest()
    expected = json.loads(
        (
            ROOT / "docs/audits/db_v2/dbv2_2/restart_r1/dbv2_2_catalog_manifest.json"
        ).read_text()
    )
    differences = {
        k: {"expected": expected[k], "actual": actual[k]}
        for k in expected
        if expected[k] != actual[k]
    }
    assert not differences and digest == EXPECTED_MANIFEST, differences.keys()
    assert head == [{"version_num": "pg_v2_baseline"}]
    assert {n: v for n, v in counts.items() if v} == {
        "alembic_version": 1,
        "experiment_execution_gate": 1,
    }
    history = ScriptDirectory.from_config(Config(str(ROOT / "alembic_v2.ini")))
    assert history.get_heads() == history.get_bases() == ["pg_v2_baseline"]
    assert history.get_revision("pg_v2_baseline").down_revision is None
    save(
        "state_" + suffix + ".json",
        {
            "status": "PASS",
            "manifest_sha256": digest,
            "head": head,
            "roots": history.get_bases(),
            "heads": history.get_heads(),
            "row_counts": counts,
            "differences": differences,
            "target": t,
            "test_fixtures_remaining": 0,
        },
    )
    print(
        suffix
        + ": PASS exact certified manifest, root/head and zero legacy/fixture rows"
    )


def restart():
    t = guard()
    certify()
    run(DOCKER + ["stop", t["container_id"]])
    v = json.loads(run(DOCKER + ["volume", "inspect", t["volume"]]).stdout)[0]
    assert (
        v["Name"] == t["volume"]
        and v["Labels"]["org.capstone.pgv2.lifecycle"] == "persistent"
    )
    run(DOCKER + ["start", t["container_id"]])
    for _ in range(30):
        if (
            run(
                DOCKER + ["exec", t["container_id"], "pg_isready", "-U", "postgres"],
                check=False,
            ).returncode
            == 0
        ):
            break
        time.sleep(1)
    certify("after_restart")
    save(
        "restart_result.json",
        {
            "status": "PASS",
            "same_container_id": t["container_id"],
            "same_volume": t["volume"],
            "volume_deleted": False,
            "service_running": True,
            "retained_for_dbv24": True,
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["provision", "upgrade", "certify", "restart"])
    a = p.parse_args()
    globals()[a.action]()
