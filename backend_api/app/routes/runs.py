from fastapi import APIRouter, HTTPException, Query

from app.db import fetch_all, fetch_one
from app.services.serialization import row_to_dict, rows_to_list


router = APIRouter(tags=["runs"])


@router.get("/runs")
def list_runs(
    datasource: str | None = Query(default="malaria"),
    limit: int = Query(default=100, ge=1, le=500),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM vw_run_dashboard
        ORDER BY started_at DESC NULLS LAST
        LIMIT :limit
        """,
        {"limit": limit},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/clinical/summary")
def list_clinical_run_summary(
    datasource: str | None = Query(default="malaria"),
    run_type: str | None = Query(default=None),
    model_name: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    conditions = []
    params = {"limit": limit}
    if run_type is not None:
        conditions.append("run_type = :run_type")
        params["run_type"] = run_type
    if model_name is not None:
        conditions.append("model_name = :model_name")
        params["model_name"] = model_name
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    rows = fetch_all(
        datasource,
        f"""
        SELECT *
        FROM vw_clinical_run_summary
        {where_sql}
        ORDER BY started_at DESC NULLS LAST
        LIMIT :limit
        """,
        params,
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/{run_id}")
def get_run(run_id: str, datasource: str | None = Query(default="malaria")):
    run = fetch_one(
        datasource,
        """
        SELECT
            r.*,
            e.name AS experiment_name,
            m.name AS model_name,
            m.model_type,
            d.name AS dataset_name
        FROM runs r
        LEFT JOIN experiments e ON e.id = r.experiment_id
        LEFT JOIN models m ON m.id = r.model_id
        LEFT JOIN datasets d ON d.id = r.dataset_id
        WHERE r.id = :run_id
        """,
        {"run_id": run_id},
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Run no encontrado.")

    metrics = fetch_all(
        datasource,
        "SELECT * FROM run_metrics WHERE run_id = :run_id ORDER BY created_at",
        {"run_id": run_id},
    )
    artifacts = fetch_all(
        datasource,
        "SELECT * FROM artifacts WHERE run_id = :run_id ORDER BY created_at DESC",
        {"run_id": run_id},
    )
    training_history = fetch_all(
        datasource,
        "SELECT * FROM training_history WHERE run_id = :run_id ORDER BY epoch",
        {"run_id": run_id},
    )
    errors = fetch_all(
        datasource,
        "SELECT * FROM errors WHERE run_id = :run_id ORDER BY created_at DESC",
        {"run_id": run_id},
    )
    return {
        "run": row_to_dict(run),
        "metrics": rows_to_list(metrics),
        "artifacts": rows_to_list(artifacts),
        "training_history": rows_to_list(training_history),
        "errors": rows_to_list(errors),
    }


@router.get("/runs/{run_id}/clinical-metrics")
def get_run_clinical_metrics(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM run_clinical_metrics
        WHERE run_id = CAST(:run_id AS uuid)
        ORDER BY created_at
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/{run_id}/checkpoint-policy")
def get_run_checkpoint_policy(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM vw_checkpoint_policy_summary
        WHERE run_id = CAST(:run_id AS uuid)
        ORDER BY created_at DESC
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/{run_id}/threshold-calibration")
def get_run_threshold_calibration(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM vw_threshold_calibration_summary
        WHERE run_id = CAST(:run_id AS uuid)
        ORDER BY created_at DESC
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/{run_id}/artifacts-summary")
def get_run_artifacts_summary(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM vw_run_artifacts_summary
        WHERE run_id = CAST(:run_id AS uuid)
        ORDER BY created_at DESC
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/{run_id}/image-predictions")
def get_run_image_predictions(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM vw_run_image_predictions_summary
        WHERE run_id = CAST(:run_id AS uuid)
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """,
        {"run_id": run_id, "limit": limit, "offset": offset},
    )
    return {"items": rows_to_list(rows), "limit": limit, "offset": offset}


@router.get("/runs/{run_id}/io-records")
def get_run_io_records(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM run_io_records
        WHERE run_id = CAST(:run_id AS uuid)
        ORDER BY created_at DESC
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}
