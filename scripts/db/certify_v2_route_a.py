"""Explicit isolated Route A evidence runner; never reads application configuration."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(
    os.environ.get("PGV2_EVIDENCE_DIR", ROOT / "docs/audits/e10_10_5b_evidence/run_b01")
).resolve()
TARGET = EVIDENCE / "target.json"
DOCKER = ["docker", "--host", "unix:///Users/julio/.docker/run/docker.sock"]


def initialize():
    """Create a new descriptor; never overwrite an existing or partial target."""
    from uuid import uuid4

    port = int(sys.argv[2])
    if not 1024 <= port <= 65535 or port in (5432, 5433):
        raise ValueError("A dedicated non-operational port is required")
    nonce = str(uuid4())
    name = "capstone_v2_isolated_" + nonce.replace("-", "")[:12]
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with TARGET.open("x") as f:
        json.dump(
            {
                "authorized_stage": "E10.10.5B",
                "gate_a_approved": True,
                "isolation_id": nonce,
                "container_name": name,
                "volume": name,
                "host_port": port,
                "database": name,
            },
            f,
            indent=2,
        )
        f.write("\n")


def run(argv, *, input=None, env=None, check=True):
    result = subprocess.run(
        argv,
        input=input,
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        check=False,
    )
    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "argv": argv,
        "stdin": input,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    with (EVIDENCE / "commands.jsonl").open("a") as f:
        f.write(json.dumps(record) + "\n")
    if check and result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {argv}: {result.stderr}"
        )
    return result


def sql(target, statement, database="postgres"):
    return run(
        DOCKER
        + [
            "exec",
            "-i",
            target["container_id"],
            "psql",
            "-X",
            "-U",
            "postgres",
            "-d",
            database,
            "-v",
            "ON_ERROR_STOP=1",
            "-At",
        ],
        input=statement,
    ).stdout


def setup():
    t = json.loads(TARGET.read_text())
    assert "container_id" not in t, "Refuse to provision an existing target"
    label = "org.capstone.pgv2.isolation=" + t["isolation_id"]
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
    run(DOCKER + ["volume", "create", "--label", label, t["volume"]])
    t["container_id"] = run(
        DOCKER
        + [
            "run",
            "-d",
            "--name",
            t["container_name"],
            "--label",
            label,
            "-e",
            "POSTGRES_HOST_AUTH_METHOD=trust",
            "-e",
            "PGDATA=/var/lib/postgresql/data",
            "-p",
            f"127.0.0.1:{t['host_port']}:5432",
            "-v",
            f"{t['volume']}:/var/lib/postgresql/data",
            "postgres:17.9",
        ]
    ).stdout.strip()
    TARGET.write_text(json.dumps(t, indent=2) + "\n")
    # Readiness only, no SQL writes.
    import time

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
    sys.path.insert(0, str(ROOT))
    from alembic_v2.safety import inspect_isolation

    inspect_isolation(t)
    # Capture only target metadata (no operational inspect dump).
    run(DOCKER + ["inspect", t["container_id"]])
    run(DOCKER + ["volume", "inspect", t["volume"]])
    ident = json.loads(
        sql(
            t,
            "SELECT json_build_object('system_identifier',system_identifier::text,'version',current_setting('server_version_num'),'database',current_database(),'recovery',pg_is_in_recovery()) FROM pg_control_system();",
        )
    )
    assert 170000 <= int(ident["version"]) < 180000 and not ident["recovery"]
    t["postgres_system_identifier"] = ident["system_identifier"]
    (EVIDENCE / "preflight_before_provision.json").write_text(
        json.dumps(
            {"target": t, "identity": ident, "docker_isolation_verified": True},
            indent=2,
        )
        + "\n"
    )
    sql(
        t,
        "CREATE ROLE capstone_v2_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;\nCREATE ROLE capstone_v2_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;\n"
        + f"CREATE DATABASE {t['database']} OWNER capstone_v2_migrator TEMPLATE template0;\n",
    )
    sql(
        t,
        "GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO capstone_v2_migrator;",
        t["database"],
    )
    t["database_oid"] = int(
        sql(
            t,
            "SELECT oid FROM pg_database WHERE datname=current_database();",
            t["database"],
        )
    )
    TARGET.write_text(json.dumps(t, indent=2) + "\n")


def preflight():
    from sqlalchemy import create_engine

    sys.path.insert(0, str(ROOT))
    from alembic_v2.safety import (
        IDENTITY_SQL,
        ROLES_SQL,
        inspect_isolation,
        read_authorization,
        verify_connection,
    )

    t = json.loads(TARGET.read_text())
    url = f"postgresql+psycopg://capstone_v2_migrator@127.0.0.1:{t['host_port']}/{t['database']}"
    read_authorization(TARGET, url)
    inspect_isolation(t)
    engine = create_engine(url)
    with engine.connect() as c:
        verify_connection(c, t)
        evidence = {
            "identity": dict(c.exec_driver_sql(IDENTITY_SQL).mappings().one()),
            "roles": [dict(r) for r in c.exec_driver_sql(ROLES_SQL).mappings()],
            "public_relations": c.exec_driver_sql(
                "SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace"
            ).scalar_one(),
        }
    engine.dispose()
    (EVIDENCE / "preflight_before_alembic.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )


def upgrade():
    t = json.loads(TARGET.read_text())
    env = dict(
        os.environ,
        PGV2_DATABASE_URL=f"postgresql+psycopg://capstone_v2_migrator@127.0.0.1:{t['host_port']}/{t['database']}",
        PYTHONPATH=str(ROOT),
    )
    run(
        [
            str(ROOT / "malaria_dl_local_project/.venv/bin/python"),
            "-m",
            "alembic",
            "-c",
            "alembic_v2.ini",
            "-x",
            f"target={TARGET}",
            "upgrade",
            "head",
        ],
        env=env,
    )


if __name__ == "__main__":
    {"init": initialize, "setup": setup, "preflight": preflight, "upgrade": upgrade}[
        sys.argv[1]
    ]()
