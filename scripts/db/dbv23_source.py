"""Legacy metadata/count inspection exclusively in enforced READ ONLY transactions."""

import json
import subprocess
from pathlib import Path

from v2_catalog_probe import QUERIES

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "docs/audits/db_v2/dbv2_3"
DOCKER = ["docker", "--host", "unix:///Users/julio/.docker/run/docker.sock"]
EXPECTED_ID = "2604ff9884655b3b78ffc85997cbe30d6392afca7b904b5df2b37dacedb30d89"
DATASET = [
    "datasets",
    "dataset_versions",
    "clinical_identities",
    "dataset_source_records",
    "identity_evidence",
    "dataset_version_sources",
    "dataset_split_assignments",
    "dataset_split_statistics",
    "dataset_split_validation_checks",
    "dataset_splits",
    "dataset_materializations",
    "dataset_materialization_activations",
    "dataset_split_images",
]
USER = ["roles", "users", "user_roles"]
OFFICIAL = "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"


def save(name, value):
    (E / name).write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )


def metadata():
    result = subprocess.run(
        DOCKER + ["inspect", "capstone_db"], capture_output=True, text=True, check=True
    )
    c = json.loads(result.stdout)[0]
    assert c["Id"] == EXPECTED_ID and c["Name"] == "/capstone_db"
    assert c["Config"]["Labels"]["com.docker.compose.project"] == "capstone-malaria"
    assert c["Config"]["Labels"]["com.docker.compose.service"] == "db"
    assert c["State"]["Running"]
    assert any(m.get("Name") == "capstone-malaria_postgres_data" for m in c["Mounts"])
    settings = dict(
        v.split("=", 1)
        for v in c["Config"]["Env"]
        if v.startswith(("POSTGRES_DB=", "POSTGRES_USER="))
    )
    # Cross-check only these non-secret names from the existing app configuration.
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(("POSTGRES_DB=", "POSTGRES_USER=")):
            k, v = line.split("=", 1)
            env[k] = v.strip().strip("\"'")
    assert all(settings[k] == env[k] for k in settings)
    return {
        "container_id": c["Id"],
        "container_name": "capstone_db",
        "database": settings["POSTGRES_DB"],
        "role": settings["POSTGRES_USER"],
        "logical_host": "capstone_db",
        "host_port": 5432,
        "volume": "capstone-malaria_postgres_data",
        "configuration_identity": "capstone-malaria/db",
    }


def read(query, initialize=False):
    assert query.lstrip().upper().startswith("SELECT ") and ";" not in query
    source = metadata()
    ident = "SELECT json_build_object('database',current_database(),'role',current_user,'version',current_setting('server_version_num'),'system_identifier',system_identifier::text,'transaction_read_only',current_setting('transaction_read_only'),'default_transaction_read_only',current_setting('default_transaction_read_only'),'server_address',inet_server_addr(),'server_port',current_setting('port')) FROM pg_control_system()"
    if not initialize:
        expected = json.loads((E / "source_identity.json").read_text())
        assert source == expected["environment"]
    result = subprocess.run(
        DOCKER
        + [
            "exec",
            "-i",
            "-e",
            "PGOPTIONS=-c default_transaction_read_only=on",
            source["container_id"],
            "psql",
            "-X",
            "-qAt",
            "-U",
            source["role"],
            "-d",
            source["database"],
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input="BEGIN READ ONLY;\n" + ident + ";\n" + query + ";\nROLLBACK;\n",
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Read-only source query failed: " + result.stderr)
    rows = result.stdout.splitlines()
    identity = json.loads(rows[0])
    assert (
        identity["database"] == source["database"]
        and identity["role"] == source["role"]
    )
    assert (
        identity["transaction_read_only"]
        == identity["default_transaction_read_only"]
        == "on"
    )
    if initialize:
        save("source_identity.json", {"environment": source, "server": identity})
    else:
        assert identity == expected["server"]
    with (E / "source_readonly_queries.jsonl").open("a") as f:
        f.write(
            json.dumps(
                {
                    "query": query,
                    "identity": identity,
                    "read_only": True,
                    "write_statements": 0,
                }
            )
            + "\n"
        )
    return json.loads("\n".join(rows[1:]))


def capture():
    read("SELECT json_build_object('preflight','READ_ONLY')", initialize=True)
    # Full structural metadata, never row values (especially never password_hash).
    catalog = {}
    for name, q in QUERIES.items():
        if name in ("roles", "runtime_privileges", "runtime_database"):
            continue
        if name == "database_acl":
            pass
        catalog[name] = read(
            "SELECT coalesce(json_agg(q),'[]'::json) FROM (" + q + ") q"
        )
    save("source_catalog.json", catalog)
    counts = {
        t: read('SELECT count(*) FROM public."' + t + '"') for t in DATASET + USER
    }
    save("source_table_counts.json", counts)
    print(
        "Legacy source verified READ ONLY; structural metadata and authorized counts captured."
    )


if __name__ == "__main__":
    capture()
