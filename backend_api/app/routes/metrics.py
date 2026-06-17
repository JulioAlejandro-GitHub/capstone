from fastapi import APIRouter, Query

from app.db import fetch_all
from app.services.serialization import rows_to_list


router = APIRouter(tags=["metrics"])


@router.get("/metrics/{run_id}")
def metrics(run_id: str, datasource: str | None = Query(default="malaria")):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM run_metrics
        WHERE run_id = :run_id
        ORDER BY split_name, class_name, metric_name, epoch, step, created_at
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}


@router.get("/confusion-matrix/{run_id}")
def confusion_matrix(run_id: str, datasource: str | None = Query(default="malaria")):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM confusion_matrices
        WHERE run_id = :run_id
        ORDER BY created_at DESC
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}


@router.get("/classification-report/{run_id}")
def classification_report(run_id: str, datasource: str | None = Query(default="malaria")):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM classification_reports
        WHERE run_id = :run_id
        ORDER BY split_name, class_name
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}

