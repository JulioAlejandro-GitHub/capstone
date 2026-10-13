"""Read-only C2.12.1 provisioning diagnostic for the existing Compose instance."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alembic_v2.safety import (  # noqa: E402
    UnsafeTarget, read_authorization, validate_docker_snapshot,
)


def docker_json(*args: str, stdin: str | None = None) -> object:
    result = subprocess.run(
        ["docker", *args], input=stdin, capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        raise RuntimeError("Docker diagnostic failed; output withheld to protect configuration")
    return json.loads(result.stdout)


def main() -> int:
    container_id = subprocess.run(
        ["docker", "compose", "ps", "-q", "db"], capture_output=True,
        text=True, check=True, timeout=15,
    ).stdout.strip()
    container = docker_json("inspect", container_id)[0]
    # Inspect is retained only in memory; never publish container environment.
    sql = """BEGIN READ ONLY;
    SELECT json_build_object(
      'read_only',current_setting('transaction_read_only'),
      'system_identifier',(SELECT system_identifier::text FROM pg_control_system()),
      'roles',(SELECT json_agg(row_to_json(r)) FROM (
        SELECT rolname,rolsuper,rolcreatedb,rolcreaterole FROM pg_roles
        WHERE rolname IN (current_user,'capstone_v2_migrator','capstone_v2_runtime')
        ORDER BY rolname) r),
      'databases',(SELECT json_agg(row_to_json(d)) FROM (
        SELECT oid,datname,pg_get_userbyid(datdba) AS owner FROM pg_database
        WHERE NOT datistemplate ORDER BY datname) d));
    ROLLBACK;"""
    state = docker_json(
        "compose", "exec", "-T", "db", "sh", "-c",
        'psql -X -qAt -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1',
        stdin=sql,
    )
    nonce = str(uuid4())
    # Candidate descriptor only: no database is created, no old approval invented.
    target = dict(
        authorized_stage="C2.12.1", isolation_id=nonce,
        database="capstone_v2_isolated_c212_" + nonce.replace("-", ""),
        container_id=container["Id"], postgres_system_identifier=state["system_identifier"],
        host_port=5432,
    )
    errors = {}
    with tempfile.TemporaryDirectory(prefix="c212_preflight_") as directory:
        path = Path(directory) / "candidate.json"
        path.write_text(json.dumps(target))
        try:
            read_authorization(str(path),
                "postgresql+psycopg://capstone_v2_migrator@127.0.0.1:5432/" + target["database"])
        except UnsafeTarget as exc:
            errors["authorization"] = str(exc)
    try:
        validate_docker_snapshot(target, container, {}, [])
    except UnsafeTarget as exc:
        errors["docker_identity"] = str(exc)
    evidence = dict(
        observed_at=datetime.now(timezone.utc).isoformat(), status="BLOCKED",
        server=state,
        docker=dict(service="db", container_id=container["Id"],
                    isolation_label_present="org.capstone.pgv2.isolation" in container["Config"]["Labels"],
                    ports=container["NetworkSettings"]["Ports"]),
        guard_rejections=errors,
        candidate_only=True, writes_performed=0, databases_created=0,
        integration_tests_executed=0,
        limitation="Existing v2 installer does not authorize this Compose lifecycle; no guard changed",
    )
    print(json.dumps(evidence, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
