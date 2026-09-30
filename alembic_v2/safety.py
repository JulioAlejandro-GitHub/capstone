"""Fail-closed identity checks for an explicitly approved isolated target.

No environment settings from the running application are loaded. Docker calls
only inspect metadata; SQL checks only read the server. No attestation file is
created here. Preparing/authorizing a target belongs to stage B, after Gate A.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import UUID

MIGRATOR = "capstone_v2_migrator"
RUNTIME = "capstone_v2_runtime"
LABEL = "org.capstone.pgv2.isolation"


class UnsafeTarget(RuntimeError):
    pass


def require(condition, code):
    if not condition:
        raise UnsafeTarget(code)


def read_authorization(path, url):
    require(bool(path) and bool(url), "V2_EXPLICIT_TARGET_REQUIRED")
    try:
        target = json.loads(Path(path).read_text())
        parsed = urlsplit(url)
        nonce = str(UUID(target["isolation_id"]))
        valid = (
            ((target["authorized_stage"] == "E10.10.5B"
              and target.get("gate_a_approved") is True)
             or (target["authorized_stage"] == "E10.10.5E"
                 and target.get("gate_d_approved") is True)
             or (target["authorized_stage"] == "DBV2.2"
                 and target.get("gate_dbv21_approved") is True)
             or (target["authorized_stage"] == "DBV2.3"
                 and target.get("gate_dbv22_approved") is True
                 and target.get("persistent") is True))
            and target["isolation_id"] == nonce
            and re.fullmatch(r"capstone_v2_isolated_[a-z0-9_]+", target["database"])
            and re.fullmatch(r"[0-9a-f]{64}", target["container_id"])
            and re.fullmatch(r"capstone_v2_isolated_[a-z0-9_]+", target["volume"])
            and re.fullmatch(r"[0-9]+", target["postgres_system_identifier"])
            and int(target["postgres_system_identifier"]) > 0
            and type(target["database_oid"]) is int
            and target["database_oid"] > 0
            and parsed.scheme == "postgresql+psycopg"
            and parsed.hostname == "127.0.0.1"
            and parsed.port == target["host_port"]
            and type(target["host_port"]) is int
            and 1024 <= target["host_port"] <= 65535
            and target["host_port"] not in (5432, 5433)
            and unquote(parsed.username or "") == MIGRATOR
            and unquote(parsed.path) == "/" + target["database"]
            and not parsed.query
            and not parsed.fragment
        )
    except (KeyError, ValueError, TypeError, OSError):
        raise UnsafeTarget("V2_AUTHORIZATION_INVALID") from None
    require(valid, "V2_AUTHORIZATION_MISMATCH")
    return target


def docker_json(args):
    try:
        result = subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=15, check=True
        )
        return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        # Never propagate inspect output, environment variables, passwords or URLs.
        raise UnsafeTarget("V2_DOCKER_IDENTITY_UNAVAILABLE") from None


def validate_docker_snapshot(target, container, volume, other_containers):
    """Pure checks, separately testable without starting Docker or PostgreSQL."""
    try:
        require(container["Id"] == target["container_id"], "V2_CONTAINER_ID_MISMATCH")
        require(container["State"]["Running"] is True, "V2_CONTAINER_NOT_RUNNING")
        if target.get("authorized_stage") == "DBV2.3":
            require(
                container["Config"]["Labels"].get("org.capstone.pgv2.lifecycle") == "persistent"
                and volume["Labels"].get("org.capstone.pgv2.lifecycle") == "persistent",
                "V2_PERSISTENT_STORAGE_REQUIRED",
            )
        require(
            container["Config"]["Labels"].get(LABEL) == target["isolation_id"],
            "V2_CONTAINER_LABEL_MISMATCH",
        )
        require(
            not container["HostConfig"].get("Privileged", False),
            "V2_PRIVILEGED_CONTAINER",
        )
        require(not container["HostConfig"].get("VolumesFrom"), "V2_SHARED_VOLUMES")
        require(
            container["HostConfig"].get("NetworkMode") not in ("host", "none"),
            "V2_NETWORK_NOT_ISOLATED",
        )
        ports = container["NetworkSettings"]["Ports"]
        bindings = ports.get("5432/tcp")
        require(
            bindings == [{"HostIp": "127.0.0.1", "HostPort": str(target["host_port"])}],
            "V2_PORT_BINDING_MISMATCH",
        )
        require(
            all(k == "5432/tcp" or not v for k, v in ports.items()),
            "V2_UNEXPECTED_PORT",
        )
        mounts = container["Mounts"]
        require(len(mounts) == 1, "V2_UNEXPECTED_MOUNTS")
        mount = mounts[0]
        require(
            mount["Type"] == "volume"
            and mount["Name"] == target["volume"]
            and mount["Destination"] == "/var/lib/postgresql/data"
            and mount["RW"] is True,
            "V2_DATA_VOLUME_MISMATCH",
        )
        require(
            volume["Name"] == target["volume"]
            and volume["Driver"] == "local"
            and not volume.get("Options")
            and volume.get("Scope") != "global"
            and volume["Labels"].get(LABEL) == target["isolation_id"],
            "V2_VOLUME_IDENTITY_MISMATCH",
        )
        require(volume["Mountpoint"] == mount["Source"], "V2_VOLUME_SOURCE_MISMATCH")
        for other in other_containers:
            if other["Id"] == target["container_id"]:
                continue
            require(
                not any(
                    m.get("Name") == target["volume"]
                    or m.get("Source") == mount["Source"]
                    for m in other.get("Mounts", [])
                ),
                "V2_VOLUME_SHARED_WITH_ANOTHER_CONTAINER",
            )
        pgdata = [
            v for v in container["Config"].get("Env", []) if v.startswith("PGDATA=")
        ]
        require(pgdata == ["PGDATA=/var/lib/postgresql/data"], "V2_PGDATA_MISMATCH")
    except (KeyError, TypeError):
        raise UnsafeTarget("V2_DOCKER_METADATA_INCOMPLETE") from None


def inspect_isolation(target):
    contexts = docker_json(["context", "inspect"])
    try:
        host = contexts[0]["Endpoints"]["docker"]["Host"]
    except (IndexError, KeyError, TypeError):
        raise UnsafeTarget("V2_DOCKER_CONTEXT_INVALID") from None
    require(host.startswith("unix://"), "V2_REMOTE_DOCKER_FORBIDDEN")
    prefix = ["--host", host]
    container = docker_json(
        prefix + ["inspect", "--type", "container", target["container_id"]]
    )[0]
    volume = docker_json(prefix + ["volume", "inspect", target["volume"]])[0]
    try:
        listing = subprocess.run(
            ["docker", *prefix, "container", "ls", "-aq"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        ).stdout.split()
    except (OSError, subprocess.SubprocessError):
        raise UnsafeTarget("V2_CONTAINER_INVENTORY_UNAVAILABLE") from None
    require(
        target["container_id"] in listing
        or any(target["container_id"].startswith(i) for i in listing),
        "V2_CONTAINER_NOT_IN_INVENTORY",
    )
    others = docker_json(prefix + ["inspect", "--type", "container", *listing])
    validate_docker_snapshot(target, container, volume, others)


IDENTITY_SQL = """
SELECT current_database() AS database, current_user AS role, session_user AS session_role,
       (SELECT oid::bigint FROM pg_database WHERE datname=current_database()) AS database_oid,
       (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()) AS database_owner,
       current_setting('server_version_num')::integer AS server_version_num,
       (SELECT system_identifier::text FROM pg_control_system()) AS system_identifier,
       pg_is_in_recovery() AS recovery,
       current_setting('transaction_read_only') AS read_only
"""

ROLES_SQL = """
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls,
       EXISTS (SELECT 1 FROM pg_auth_members m WHERE m.member=r.oid) AS has_membership
FROM pg_roles r WHERE rolname IN ('capstone_v2_migrator','capstone_v2_runtime')
"""


def validate_server_snapshot(target, identity, roles):
    require(
        identity["database"] == target["database"]
        and identity["database_oid"] == target["database_oid"],
        "V2_DATABASE_ID_MISMATCH",
    )
    require(
        identity["system_identifier"] == target["postgres_system_identifier"],
        "V2_CLUSTER_ID_MISMATCH",
    )
    require(
        identity["role"]
        == identity["session_role"]
        == identity["database_owner"]
        == MIGRATOR,
        "V2_MIGRATOR_IDENTITY_MISMATCH",
    )
    require(
        170000 <= identity["server_version_num"] < 180000, "V2_POSTGRESQL_17_REQUIRED"
    )
    if target.get("authorized_stage") in ("DBV2.2", "DBV2.3"):
        require(identity["server_version_num"] == 170009, "DBV22_POSTGRESQL_17_9_REQUIRED")
    require(
        identity["recovery"] is False and identity["read_only"] == "off",
        "V2_SERVER_MODE_INVALID",
    )
    require({r["rolname"] for r in roles} == {MIGRATOR, RUNTIME}, "V2_ROLES_REQUIRED")
    require(
        not any(
            r[k]
            for r in roles
            for k in (
                "rolsuper",
                "rolcreatedb",
                "rolcreaterole",
                "rolreplication",
                "rolbypassrls",
                "has_membership",
            )
        ),
        "V2_EXCESSIVE_ROLE_PRIVILEGES",
    )


def verify_connection(connection, target):
    try:
        identity = dict(connection.exec_driver_sql(IDENTITY_SQL).mappings().one())
        roles = [dict(r) for r in connection.exec_driver_sql(ROLES_SQL).mappings()]
        validate_server_snapshot(target, identity, roles)
    except UnsafeTarget:
        raise
    except Exception:  # noqa: BLE001 -- driver errors must not expose connection/credential details
        raise UnsafeTarget("V2_SERVER_IDENTITY_UNVERIFIABLE") from None
