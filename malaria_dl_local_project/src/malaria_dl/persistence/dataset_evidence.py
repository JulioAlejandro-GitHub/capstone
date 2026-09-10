"""Fail-closed dataset evidence in existing append-only PostgreSQL audit_events.

No CSV/JSON sidecars; verified is returned only after commit and a fresh read.
"""

from dataclasses import replace
import json
from uuid import uuid4

from sqlalchemy import text

from .database import get_engine
from ..data.dataset_integrity import VERIFIER_VERSION
from ..data.governed_dataset import (
    GovernedDatasetError,
    normalize_dataset_version_id,
    resolve_governed_dataset,
    training_dataset_metadata,
    assert_run_dataset_snapshot_unchanged,
    validate_dataset_location,
    dataset_read_connection,
)

EVENT_TYPE = "ml.dataset_verification"


def read_dataset_evidence(evidence_id):
    evidence_id = normalize_dataset_version_id(evidence_id)
    with dataset_read_connection() as connection:
        row = (
            connection.execute(
                text("""
            SELECT after_state,success,error_code FROM audit_events
            WHERE id=:id AND event_type=:event
        """),
                {"id": evidence_id, "event": EVENT_TYPE},
            )
            .mappings()
            .one_or_none()
        )
    if not row:
        raise GovernedDatasetError("DATASET_EVIDENCE_NOT_FOUND")
    return dict(row)


def persist_dataset_evidence(payload, *, success, error_code=None, evidence_id=None):
    evidence_id = evidence_id or str(uuid4())
    engine = None
    try:
        engine = get_engine()
        with engine.begin() as connection:
            connection.execute(
                text("""
                INSERT INTO audit_events
                  (id,event_type,action,resource_type,resource_id,request_method,
                   request_path,correlation_id,after_state,metadata,success,error_code)
                VALUES (:id,:event,'verify','dataset_version',:version,'CLI',:source,
                        :id,CAST(:payload AS jsonb),'{}'::jsonb,:success,:error)
            """),
                {
                    "id": evidence_id,
                    "event": EVENT_TYPE,
                    "version": payload.get("dataset_version_id"),
                    "source": payload["consumer"],
                    "payload": json.dumps(payload),
                    "success": success,
                    "error": error_code,
                },
            )
        stored = read_dataset_evidence(evidence_id)
        if stored != {
            "after_state": payload,
            "success": success,
            "error_code": error_code,
        }:
            raise GovernedDatasetError("DATASET_EVIDENCE_ROUND_TRIP_FAILED")
    except Exception:
        # Driver messages can contain connection details. Never fall back to a file.
        raise GovernedDatasetError("DATASET_EVIDENCE_PERSISTENCE_FAILED") from None
    finally:
        if engine is not None:
            engine.dispose()
    return evidence_id


def verify_dataset_for_execution(
    dataset_version_id=None,
    *,
    training_run_id=None,
    expected_evidence_id=None,
    dataset_dir=None,
    data_source="physical",
    consumer="src.train",
):
    # Invalid public/programmatic identifiers fail before any DB or file access.
    if training_run_id is None or dataset_version_id is not None:
        dataset_version_id = normalize_dataset_version_id(dataset_version_id)
    requested = None
    payload = {
        "verifier_version": VERIFIER_VERSION,
        "consumer": consumer,
        "training_run_id": str(training_run_id) if training_run_id else None,
        "expected_evidence_id": expected_evidence_id,
    }
    try:
        parent = training_dataset_metadata(training_run_id) if training_run_id else None
        if parent is not None:
            requested = parent["dataset_version_id"]
            if (
                dataset_version_id is not None
                and normalize_dataset_version_id(dataset_version_id) != requested
            ):
                raise GovernedDatasetError("TRAIN_DATASET_VERSION_MISMATCH")
        else:
            requested = normalize_dataset_version_id(dataset_version_id)
        payload["dataset_version_id"] = requested
        resolved = resolve_governed_dataset(requested)
        if parent is not None:
            assert_run_dataset_snapshot_unchanged(resolved, parent)
        if expected_evidence_id is not None:
            expected = read_dataset_evidence(expected_evidence_id)
            if (
                not expected["success"]
                or expected["after_state"].get("verifier_version") != VERIFIER_VERSION
            ):
                raise GovernedDatasetError("DATASET_EVIDENCE_NOT_VERIFIED")
            assert_run_dataset_snapshot_unchanged(
                resolved, expected["after_state"].get("snapshot") or {}
            )
        validate_dataset_location(resolved, dataset_dir, data_source)
        payload.update(snapshot=resolved.metadata(), integrity_status="verified")
    except GovernedDatasetError as exc:
        if getattr(exc, "evidence", None):
            payload["rejection_evidence"] = exc.evidence
        payload.update(
            dataset_version_id=requested, integrity_status="rejected", reason=str(exc)
        )
        persist_dataset_evidence(payload, success=False, error_code=str(exc))
        raise
    except Exception:
        payload.update(
            dataset_version_id=requested,
            integrity_status="unverified",
            reason="DATASET_VERIFICATION_UNAVAILABLE",
        )
        persist_dataset_evidence(
            payload, success=False, error_code="DATASET_VERIFICATION_UNAVAILABLE"
        )
        raise GovernedDatasetError("DATASET_VERIFICATION_UNAVAILABLE") from None
    evidence_id = persist_dataset_evidence(payload, success=True)
    return replace(resolved, evidence_id=evidence_id)


def bind_dataset_evidence_to_run(snapshot, run_context):
    """Strict linkage, not safe_track: failure stops before fit/predict."""
    run_id = (run_context or {}).get("run_id")
    if not run_id or not snapshot.evidence_id:
        raise GovernedDatasetError("DATASET_EVIDENCE_RUN_LINK_REQUIRED")
    engine = None
    try:
        engine = get_engine()
        with engine.begin() as connection:
            row = connection.execute(
                text("""
                UPDATE runs SET metadata=COALESCE(metadata,'{}'::jsonb) ||
                    jsonb_build_object('dataset_verification_evidence_id',CAST(:evidence AS text))
                WHERE id=:id AND dataset_version_id=:version
                  AND (metadata->>'dataset_verification_evidence_id' IS NULL
                       OR metadata->>'dataset_verification_evidence_id'=:evidence)
                RETURNING metadata->>'dataset_verification_evidence_id'
            """),
                {
                    "id": str(run_id),
                    "version": str(snapshot.dataset_version_id),
                    "evidence": snapshot.evidence_id,
                },
            ).scalar_one()
            if row != snapshot.evidence_id:
                raise ValueError("link mismatch")
    except Exception:
        raise GovernedDatasetError("DATASET_EVIDENCE_RUN_LINK_FAILED") from None
    finally:
        if engine is not None:
            engine.dispose()
