"""Fail-closed pure preflight shared by offline fixtures and future D executor."""

import json
import re
from collections import defaultdict
from urllib.parse import unquote, urlsplit
from uuid import UUID

from .core import ROOT, Blocked, contract, require, row_key, sha, table_digest

ACTIVE = {
    "train_execution_sessions": ("state", {"active", "completed"}),
    "assessment_attempts": ("state", {"active", "completed"}),
    "campaign_attempts": ("state", {"active", "completed"}),
    "campaign_members": ("state", {"active", "completed"}),
    "experimental_campaigns": ("state", {"active"}),
    "local_execution_jobs": ("state", {"held", "calculation_reported"}),
    "runs": ("status", {"running", "active", "pending", "queued", "started"}),
}


def _authorization(t, url):
    p = urlsplit(url)
    require(
        t.get("authorized_stage") == "E10.10.5D" and t.get("gate_c_approved") is True,
        "GATE_C_REQUIRED_FOR_EXECUTION",
    )
    require(
        t.get("copy_only") is True and t.get("writers_fenced") is True,
        "ISOLATED_COPY_REQUIRED",
    )
    require(
        t.get("isolation_id") == str(UUID(t.get("isolation_id", ""))),
        "INVALID_ISOLATION_UUID",
    )
    require(
        re.fullmatch(r"[0-9a-f]{64}", t.get("container_id", "")) is not None,
        "INVALID_CONTAINER",
    )
    require(
        all(
            re.fullmatch(r"capstone_v2_isolated_[a-z0-9_]+", t.get(k, ""))
            for k in ("database", "volume")
        ),
        "INVALID_ISOLATED_NAMES",
    )
    require(
        type(t.get("host_port")) is int
        and 1024 <= t["host_port"] <= 65535
        and t["host_port"] not in (5432, 5433),
        "INVALID_ISOLATED_PORT",
    )
    require(
        type(t.get("database_oid")) is int and t["database_oid"] > 0,
        "DATABASE_OID_REQUIRED",
    )
    require(t.get("postgres_system_identifier", "").isdigit(), "CLUSTER_ID_REQUIRED")
    require(
        t["postgres_system_identifier"] != t.get("origin_system_identifier")
        and bool(t.get("origin_system_identifier")),
        "ORIGIN_CLUSTER_FORBIDDEN",
    )
    for k in (
        "backup_sha256",
        "mapping_sha256",
        "source_inventory_sha256",
        "legacy_schema_sha256",
    ):
        require(
            re.fullmatch(r"[0-9a-f]{64}", t.get(k, "")) is not None, "PIN_REQUIRED", k
        )
    require(
        t.get("migration_role") == "capstone_v2_migrator"
        and t.get("runtime_role") == "capstone_v2_runtime",
        "ROLE_CONTRACT_MISMATCH",
    )
    require(
        p.scheme == "postgresql+psycopg"
        and p.hostname == "127.0.0.1"
        and p.port == t["host_port"]
        and unquote(p.username or "") == t["migration_role"]
        and unquote(p.path) == "/" + t["database"]
        and not p.query
        and not p.fragment,
        "UNAUTHORIZED_URL",
    )
    return t


def authorization(t, url):
    try:
        return _authorization(t, url)
    except Blocked:
        raise
    except (KeyError, ValueError, TypeError, AttributeError):
        raise Blocked("INVALID_AUTHORIZATION") from None


def schema_signature(observed):
    spec = contract()
    result = {}
    for kind, fields in spec["schema_fields"].items():
        rows = observed[kind]
        if kind == "triggers":
            rows = [r for r in rows if not r["internal"]]
        result[kind] = sorted(
            [{k: r[k] for k in fields} for r in rows],
            key=lambda r: json.dumps(r, sort_keys=True),
        )
    return result


def check_history(rows):
    expected = contract()["historical_ledger"]
    require(len(rows) == len(expected) == 22, "HISTORICAL_LEDGER_CARDINALITY")
    actual = {r["migration_id"]: r["checksum"] for r in rows}
    require(actual == expected, "HISTORICAL_CHECKSUM_MISMATCH")
    for name, expected_hash in expected.items():
        from hashlib import sha256

        path = ROOT / "malaria_dl_local_project/db/init" / name
        require(
            sha256(path.read_bytes()).hexdigest() == expected_hash,
            "HISTORICAL_FILE_CHANGED",
            name,
        )


def check_e10(rows):
    sequences = defaultdict(list)
    seen = set()
    for r in rows:
        if r.get("event_id") is None:
            require(
                r.get("event_sequence") is None and r["kind"] != "e10_event",
                "E10_METADATA_INVALID",
            )
            continue
        raw = r["payload"].get("canonical_event")
        require(
            type(raw) is str and set(r["payload"]) == {"canonical_event"},
            "E10_RAW_BYTES_REQUIRED",
        )
        event = json.loads(raw)
        require(
            set(event)
            == {
                "event_id",
                "run_id",
                "sequence",
                "event_type",
                "occurred_at",
                "payload",
                "attempt_id",
                "schema_version",
            },
            "E10_ENVELOPE_INVALID",
        )
        require(
            event["schema_version"] == "run_event_v1"
            and type(event["sequence"]) is int
            and event["sequence"] > 0,
            "E10_VERSION_SEQUENCE_INVALID",
        )
        from datetime import datetime

        require(
            event["event_type"]
            in (
                "heartbeat",
                "epoch_completed",
                "phase_started",
                "phase_completed",
                "artifact_prepared",
                "artifact_created",
                "predictions_completed",
                "selection_completed",
                "calibration_completed",
                "evaluation_completed",
                "training_completed",
                "training_failed",
            ),
            "E10_EVENT_TYPE_INVALID",
        )
        require(
            datetime.fromisoformat(event["occurred_at"]).utcoffset() is not None,
            "E10_TIMESTAMP_INVALID",
        )
        for field in ("event_id", "run_id"):
            require(str(UUID(event[field])) == event[field], "E10_UUID_INVALID")
        require(
            str(event["event_id"]) == str(r["event_id"]) == r["record_key"]
            and str(event["run_id"]) == str(r["run_id"])
            and event["sequence"] == r["event_sequence"]
            and r["kind"] == "e10_event"
            and r["phase"] == "run_event_v1",
            "E10_IDENTITY_MISMATCH",
        )
        require(event["event_id"] not in seen, "E10_DUPLICATE_EVENT_ID")
        require(
            raw
            == json.dumps(
                event,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ),
            "E10_NONCANONICAL_EVENT",
        )
        seen.add(event["event_id"])
        sequences[str(r["run_id"])].append(event["sequence"])
    for run, seq in sequences.items():
        require(
            sorted(seq) == list(range(1, len(seq) + 1)),
            "E10_SEQUENCE_GAP_OR_DUPLICATE",
            run,
        )


def preflight(snapshot):
    spec = contract()
    rows = snapshot["rows"]
    require(set(rows) == set(spec["tables"]), "LEGACY_TABLE_INVENTORY_INCOMPLETE")
    require(
        schema_signature(snapshot["catalog"]) == spec["expected_schema"],
        "LEGACY_SCHEMA_DRIFT",
    )
    require(
        rows["alembic_version"] == [{"version_num": spec["legacy_revision"]}],
        "LEGACY_REVISION_MISMATCH",
    )
    check_history(rows["schema_migrations"])
    for table, records in rows.items():
        keys = [row_key(table, r) for r in records]
        require(len(keys) == len(set(keys)), "DUPLICATE_SOURCE_IDENTIFIER", table)
    gates = rows["experiment_execution_gate"]
    require(
        len(gates) == 1
        and gates[0]["singleton"] is True
        and all(gates[0].get(k) is None for k in ("owner", "db_pid", "blocked_reason")),
        "EXECUTION_GATE_NOT_FREE",
    )
    require(gates[0].get("process_evidence") == {}, "EXECUTION_GATE_EVIDENCE_NOT_EMPTY")
    for table, (field, active) in ACTIVE.items():
        require(
            not any(r.get(field) in active for r in rows[table]),
            "ACTIVE_STATE_FORBIDDEN",
            table,
        )
    check_e10(rows["train_execution_records"])
    for record in rows["train_execution_records"]:
        if not record.get("event_id"):
            continue
        event = json.loads(record["payload"]["canonical_event"])
        payload = event["payload"]
        if event["event_type"] == "epoch_completed":
            ref = payload.get("legacy_record", {})
            matches = [
                r
                for r in rows["train_execution_records"]
                if r.get("event_id") is None
                and r["run_id"] == record["run_id"]
                and all(r[k] == ref.get(k) for k in ("kind", "phase", "record_key"))
            ]
            require(
                len(matches) == 1
                and matches[0]["kind"] == "epoch"
                and matches[0]["payload"] == payload.get("result"),
                "E10_EPOCH_LEGACY_CONFLICT",
            )

    def legacy_json(value):
        if type(value) is float and value.is_integer():
            return int(value)
        if isinstance(value, list):
            return [legacy_json(v) for v in value]
        if isinstance(value, dict):
            return {k: legacy_json(v) for k, v in value.items()}
        return value

    for session in rows["train_execution_sessions"]:
        completion = session.get("completion") or {}
        if session.get("state") == "verified" or completion.get("records_hash"):
            records = [
                {k: r[k] for k in ("kind", "phase", "record_key", "payload")}
                for r in rows["train_execution_records"]
                if r["run_id"] == session["run_id"] and r.get("event_id") is None
            ]
            records.sort(key=lambda r: (r["kind"], r["phase"], r["record_key"]))
            raw = json.dumps(
                legacy_json(records),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            require(
                completion.get("records_hash") == sha(raw),
                "E10_LEGACY_RECORDS_HASH_MISMATCH",
            )
            if session.get("state") == "verified":
                require(
                    (session.get("verification") or {}).get("records_hash")
                    == completion["records_hash"],
                    "E10_VERIFICATION_HASH_MISMATCH",
                )
    require(len(rows["models"]) == 3, "THREE_MODELS_REQUIRED")
    return {
        t: {"count": len(v), "sha256": table_digest(v)} for t, v in sorted(rows.items())
    }
