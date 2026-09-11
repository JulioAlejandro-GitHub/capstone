"""E6 read API; historical /runs and /predictions keep their original semantics."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.db import read_only_transaction

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.get("")
def list_assessments(
    training_run_id: UUID | None = None,
    campaign_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    with read_only_transaction("malaria") as c:
        rows = (
            c.execute(
                text("""SELECT i.id,i.identity_hash,i.training_run_id,i.kind,a.id AS attempt_id,a.state,a.ordinal
          FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id=i.id
          WHERE (CAST(:train AS uuid) IS NULL OR i.training_run_id=CAST(:train AS uuid))
          AND (CAST(:campaign AS uuid) IS NULL OR EXISTS(SELECT 1 FROM assessment_campaign_consumers cc
              WHERE cc.identity_id=i.id AND cc.campaign_id=CAST(:campaign AS uuid)))
          ORDER BY i.id,a.ordinal LIMIT :limit OFFSET :offset"""),
                {
                    "train": str(training_run_id) if training_run_id else None,
                    "campaign": str(campaign_id) if campaign_id else None,
                    "limit": limit,
                    "offset": offset,
                },
            )
            .mappings()
            .all()
        )
    return {"items": [dict(r) for r in rows], "contract": "assessment_identity_v1"}


@router.get("/{attempt_id}")
def assessment(attempt_id: UUID):
    with read_only_transaction("malaria") as c:
        row = (
            c.execute(
                text("""SELECT a.*,i.identity,i.identity_hash,i.training_run_id,i.kind FROM assessment_attempts a
          JOIN assessment_identities i ON i.id=a.identity_id WHERE a.id=CAST(:id AS uuid)"""),
                {"id": str(attempt_id)},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(404, "Assessment not found")
    result = dict(row)
    result.pop("owner")
    result.pop("host")
    result.pop("pid")
    return result


@router.get("/{attempt_id}/results")
def results(
    attempt_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    with read_only_transaction("malaria") as c:
        rows = (
            c.execute(
                text("""SELECT payload FROM assessment_results WHERE attempt_id=CAST(:id AS uuid)
          ORDER BY sample_id LIMIT :limit OFFSET :offset"""),
                {"id": str(attempt_id), "limit": limit, "offset": offset},
            )
            .scalars()
            .all()
        )
    return {"items": rows}


@router.get("/{attempt_id}/artifacts")
def artifacts(
    attempt_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    with read_only_transaction("malaria") as c:
        rows = (
            c.execute(
                text("""SELECT payload FROM assessment_artifacts WHERE attempt_id=CAST(:id AS uuid)
          ORDER BY sample_id,role LIMIT :limit OFFSET :offset"""),
                {"id": str(attempt_id), "limit": limit, "offset": offset},
            )
            .scalars()
            .all()
        )
    return {"items": rows}
