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

