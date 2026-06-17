from fastapi import APIRouter, Query

from app.db import DATASOURCE_CONFIG, resolve_datasource, fetch_all, fetch_one
from app.services.serialization import row_to_dict, rows_to_list


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(datasource: str | None = Query(default="malaria")):
    key = resolve_datasource(datasource)
    totals = fetch_one(
        key,
        """
        SELECT
            COUNT(*) AS total_runs,
            COUNT(*) FILTER (WHERE status = 'completed') AS completed_runs,
            COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
            COUNT(*) FILTER (WHERE status = 'started') AS started_runs
        FROM runs
        """,
    )
    best = fetch_one(
        key,
        """
        SELECT
            MAX(best_accuracy) AS best_accuracy,
            MAX(best_recall) AS best_recall,
            MAX(best_f1_score) AS best_f1_score,
            MAX(best_auc) AS best_auc
        FROM vw_model_run_summary
        """,
    )
    runs_by_model = fetch_all(
        key,
        """
        SELECT
            model_name,
            model_type,
            total_runs,
            completed_runs,
            failed_runs,
            best_accuracy,
            best_recall,
            best_f1_score,
            best_auc
        FROM vw_model_run_summary
        ORDER BY total_runs DESC, model_name
        """,
    )
    recent_runs = fetch_all(
        key,
        """
        SELECT *
        FROM vw_run_dashboard
        ORDER BY started_at DESC NULLS LAST
        LIMIT 10
        """,
    )

    config = DATASOURCE_CONFIG[key]
    return {
        "datasource": key,
        "domain": config["domain"],
        "totals": row_to_dict(totals),
        "best_metrics": row_to_dict(best),
        "runs_by_model": rows_to_list(runs_by_model),
        "recent_runs": rows_to_list(recent_runs),
        "domains": [
            {
                "key": item,
                "domain": config_item["domain"],
                "enabled": config_item["enabled"],
            }
            for item, config_item in DATASOURCE_CONFIG.items()
        ],
    }

