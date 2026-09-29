"""D-03 Route A recertification in a new isolated cluster; never reads operational settings."""

import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
E = ROOT / "docs/audits/e10_10_5d2_evidence/route_a"
D = ["docker", "--host", "unix:///Users/julio/.docker/run/docker.sock"]


def save(name, value):
    (E / name).write_text(json.dumps(value, indent=2, default=str) + "\n")


def run(args, env=None, input=None, sensitive=False):
    r = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        input=input,
        capture_output=True,
        text=True,
        check=False,
    )
    with (E / "orchestration.jsonl").open("a") as f:
        f.write(
            json.dumps(
                {
                    "argv": args,
                    "exit_code": r.returncode,
                    "stdout": r.stdout if not sensitive else "[private]",
                    "stderr": r.stderr if not sensitive else "[private]",
                }
            )
            + "\n"
        )
    if r.returncode:
        raise RuntimeError("Command failed; see orchestration.jsonl")
    return r.stdout


def setup():
    assert not (E / "target.json").exists()
    private = Path(tempfile.mkdtemp(prefix="e10_d03_", dir="/private/tmp"))
    os.chmod(private, 0o700)
    passwords = {
        r: secrets.token_hex(24)
        for r in ["postgres", "capstone_v2_migrator", "capstone_v2_runtime"]
    }
    envfile = private / "container.env"
    envfile.write_text(
        "POSTGRES_PASSWORD="
        + passwords["postgres"]
        + "\nPGDATA=/var/lib/postgresql/data\n"
    )
    os.chmod(envfile, 0o600)
    pgpass = private / "pgpass"
    pgpass.write_text(
        "".join(
            "127.0.0.1:55480:*:" + role + ":" + secret + "\n"
            for role, secret in passwords.items()
        )
    )
    os.chmod(pgpass, 0o600)
    save("private_paths.json", {"pgpass": str(pgpass), "directory": str(private)})
    nonce = str(uuid.uuid4())
    name = "capstone_v2_isolated_" + nonce.replace("-", "")[:12]
    label = "org.capstone.pgv2.isolation=" + nonce
    t = {
        "authorized_stage": "E10.10.5B",
        "gate_a_approved": True,
        "recertification_stage": "E10.10.5D.2",
        "decision": "D-03",
        "isolation_id": nonce,
        "container_name": name,
        "volume": name,
        "database": name,
        "host_port": 55480,
    }
    run(
        D
        + [
            "image",
            "inspect",
            "postgres:17.9",
            "--format",
            "{{.Id}} {{json .RepoDigests}}",
        ]
    )
    run(D + ["volume", "create", "--label", label, name])
    t["container_id"] = run(
        D
        + [
            "run",
            "-d",
            "--name",
            name,
            "--label",
            label,
            "--env-file",
            str(envfile),
            "-p",
            "127.0.0.1:55480:5432",
            "-v",
            name + ":/var/lib/postgresql/data",
            "postgres:17.9",
        ]
    ).strip()
    save("target.json", t)
    for _ in range(40):
        r = subprocess.run(
            D + ["exec", t["container_id"], "pg_isready", "-U", "postgres"],
            capture_output=True,
            check=False,
        )
        if r.returncode == 0:
            break
        time.sleep(1)
    from alembic_v2.safety import inspect_isolation

    inspect_isolation(t)

    def sql(statement, db="postgres", sensitive=False):
        return run(
            D
            + [
                "exec",
                "-i",
                t["container_id"],
                "psql",
                "-X",
                "-U",
                "postgres",
                "-d",
                db,
                "-At",
                "-v",
                "ON_ERROR_STOP=1",
            ],
            input=statement,
            sensitive=sensitive,
        )

    identity = json.loads(
        sql(
            "SELECT json_build_object('system_identifier',system_identifier::text,'version',current_setting('server_version_num')) FROM pg_control_system();"
        )
    )
    assert (
        identity["version"] == "170009"
        and identity["system_identifier"] != "7668020338728398886"
    )
    t["postgres_system_identifier"] = identity["system_identifier"]
    save("preflight_before_provision.json", identity)
    for role in ["capstone_v2_migrator", "capstone_v2_runtime"]:
        sql(
            "CREATE ROLE "
            + role
            + " LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '"
            + passwords[role]
            + "';",
            sensitive=True,
        )
    sql("CREATE DATABASE " + name + " OWNER capstone_v2_migrator TEMPLATE template0;")
    t["database_oid"] = int(
        sql("SELECT oid FROM pg_database WHERE datname=current_database();", name)
    )
    save("target.json", t)


def main():
    if sys.argv[1] == "setup":
        setup()
        return
    env = dict(
        os.environ,
        PGV2_EVIDENCE_DIR=str(E),
        PGPASSFILE=json.loads((E / "private_paths.json").read_text())["pgpass"],
        PYTHONPATH="/private/tmp/e10_10_5d_parser312:" + str(ROOT),
    )
    action = sys.argv[1]
    if action in ["preflight", "upgrade"]:
        args = [sys.executable, "scripts/db/certify_v2_route_a.py", action]
    elif action == "server":
        args = [sys.executable, "scripts/db/test_v2_route_a_server.py"]
    elif action == "d03":
        args = [sys.executable, "scripts/db/test_v2_d03_server.py"]
    else:
        args = [sys.executable, "scripts/db/verify_v2_route_a.py", action]
    run(args, env=env)
    print(action + " passed")


if __name__ == "__main__":
    main()
