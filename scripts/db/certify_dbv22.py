"""DBV2.2 disposable PostgreSQL 17.9 certification. No application configuration."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from v2_catalog_probe import snapshot

from alembic_v2.safety import (
    IDENTITY_SQL,
    ROLES_SQL,
    inspect_isolation,
    validate_server_snapshot,
)

E = Path(
    os.environ.get("DBV22_EVIDENCE_DIR", ROOT / "docs/audits/db_v2/dbv2_2/restart_r1")
).resolve()
TARGET = E / "target.json"
DOCKER = ["docker", "--host", "unix:///Users/julio/.docker/run/docker.sock"]
PYTHON = ROOT / "malaria_dl_local_project/.venv/bin/python"


def save(name, data):
    (E / name).write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str, ensure_ascii=False)
        + "\n"
    )


def run(argv, input=None, env=None, check=True):
    p = subprocess.run(
        list(map(str, argv)),
        input=input,
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=env,
        check=False,
    )
    with (E / "commands.jsonl").open("a") as f:
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
        raise RuntimeError(p.stderr or p.stdout)
    return p


def connect(t, role="capstone_v2_migrator", database=None):
    return psycopg.connect(
        host="127.0.0.1",
        port=t["host_port"],
        dbname=database or t["database"],
        user=role,
        autocommit=True,
        row_factory=dict_row,
    )


def guard(t=None):
    t = t or json.loads(TARGET.read_text())
    inspect_isolation(t)
    with connect(t) as c:
        i = c.execute(IDENTITY_SQL).fetchone()
        roles = c.execute(ROLES_SQL).fetchall()
        validate_server_snapshot(t, i, roles)
    save("latest_preflight.json", {"target": t, "identity": i, "roles": roles})
    return t


def provision():
    E.mkdir(parents=True, exist_ok=True)
    assert not TARGET.exists(), "Never reuse an existing target"
    nonce = str(uuid4())
    name = "capstone_v2_isolated_" + nonce.replace("-", "")[:12]
    t = {
        "authorized_stage": "DBV2.2",
        "gate_dbv21_approved": True,
        "isolation_id": nonce,
        "container_name": name,
        "volume": name,
        "host_port": int(os.environ.get("DBV22_PORT", "56439")),
        "database": name,
    }
    assert 1024 <= t["host_port"] <= 65535 and t["host_port"] not in (5432, 5433)
    label = "org.capstone.pgv2.isolation=" + nonce
    run(
        DOCKER
        + [
            "image",
            "inspect",
            "postgres:17.9",
            "--format",
            "{{.Id}} {{json .RepoDigests}}",
        ]
    )
    run(DOCKER + ["volume", "create", "--label", label, name])
    t["container_id"] = run(
        DOCKER
        + [
            "run",
            "-d",
            "--name",
            name,
            "--label",
            label,
            "-e",
            "POSTGRES_HOST_AUTH_METHOD=trust",
            "-e",
            "PGDATA=/var/lib/postgresql/data",
            "-p",
            f"127.0.0.1:{t['host_port']}:5432",
            "-v",
            name + ":/var/lib/postgresql/data",
            "postgres:17.9",
        ]
    ).stdout.strip()
    save("provisioning_target.json", t)
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
    # Read-only identity before provisioning any role/database.
    with connect(t, role="postgres", database="postgres") as c:
        ident = c.execute(
            "SELECT current_database() AS database,current_setting('server_version_num')::int AS version,system_identifier::text AS system_identifier,inet_server_addr()::text AS address FROM pg_control_system()"
        ).fetchone()
        assert ident["version"] == 170009 and ident["database"] == "postgres"
        t["postgres_system_identifier"] = ident["system_identifier"]
        save(
            "preflight_before_provision.json",
            {"target": t, "identity": ident, "docker_isolation_verified": True},
        )
        for role in ("capstone_v2_migrator", "capstone_v2_runtime"):
            c.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                ).format(sql.Identifier(role))
            )
        c.execute(
            sql.SQL(
                "CREATE DATABASE {} OWNER capstone_v2_migrator TEMPLATE template0"
            ).format(sql.Identifier(name))
        )
    with connect(t, role="postgres") as c:
        assert c.execute(
            "SELECT current_setting('server_version_num')::int AS version,current_database() AS database,system_identifier::text AS id FROM pg_control_system()"
        ).fetchone() == {
            "version": 170009,
            "database": name,
            "id": t["postgres_system_identifier"],
        }
        c.execute(
            "GRANT EXECUTE ON FUNCTION pg_control_system() TO capstone_v2_migrator"
        )
        t["database_oid"] = c.execute(
            "SELECT oid::int AS oid FROM pg_database WHERE datname=current_database()"
        ).fetchone()["oid"]
    save("target.json", t)
    guard(t)
    with connect(t) as c:
        empty = snapshot(c)
        assert (
            not empty["relations"]
            and not empty["functions"]
            and not empty["triggers"]
            and not empty["views"]
        )
        save("empty_catalog.json", empty)


def upgrade(t=None, fail=False):
    t = guard(t)
    path = E / (t["database"] + "_target.json")
    save(path.name, t)
    env = dict(
        os.environ,
        PGV2_DATABASE_URL=f"postgresql+psycopg://capstone_v2_migrator@127.0.0.1:{t['host_port']}/{t['database']}",
        PGV2_TARGET=str(path),
        PYTHONPATH=str(ROOT),
    )
    if fail:
        return run(
            [PYTHON, ROOT / "scripts/db/v2_inject_failure.py", path],
            env=env,
            check=False,
        )
    return run(
        [PYTHON, "-m", "alembic", "-c", "alembic_v2.ini", "upgrade", "head"], env=env
    )


def catalog():
    t = guard()
    with connect(t) as c:
        actual = snapshot(c)
        assert c.execute("SELECT version_num FROM alembic_version").fetchall() == [
            {"version_num": "pg_v2_baseline"}
        ]
    save("dbv2_2_catalog_manifest.json", actual)
    counts = {key: len(actual[key]) for key in ("views", "triggers", "indexes")}
    counts["tables"] = sum(
        r["relkind"] == "r" and r["name"] != "alembic_version"
        for r in actual["relations"]
    )
    counts["functions"] = sum(r["extension"] is None for r in actual["functions"])
    for kind, name in [("p", "PK"), ("f", "FK"), ("c", "CHECK"), ("u", "UNIQUE")]:
        counts[name] = sum(
            r["contype"] == kind and r["relation"] != "alembic_version"
            for r in actual["constraints"]
        )
    save("catalog_counts.json", counts)
    print(counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["provision", "upgrade", "catalog"])
    a = parser.parse_args()
    globals()[a.action]()
