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


@router.get("/clinical")
def clinical_dashboard(
    datasource: str | None = Query(default="malaria"),
    limit: int = Query(default=10, ge=1, le=100),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM vw_clinical_run_summary
        ORDER BY started_at DESC NULLS LAST
        LIMIT :limit
        """,
        {"limit": limit},
    )
    latest_run = rows[0] if rows else None
    warnings = []
    for row in rows_to_list(rows):
        if row.get("prediction_collapse_detected") is True:
            warnings.append(
                {
                    "run_id": row.get("run_id"),
                    "type": "prediction_collapse",
                    "message": "Prediction collapse detectado.",
                }
            )
        if row.get("checkpoint_warning"):
            warnings.append(
                {
                    "run_id": row.get("run_id"),
                    "type": "checkpoint_policy",
                    "message": row.get("checkpoint_warning"),
                }
            )
        if row.get("threshold_warning"):
            warnings.append(
                {
                    "run_id": row.get("run_id"),
                    "type": "threshold_calibration",
                    "message": row.get("threshold_warning"),
                }
            )

    return {
        "latest_run": row_to_dict(latest_run),
        "items": rows_to_list(rows),
        "warnings": warnings,
        "label_mapping": {
            "0": "uninfected",
            "1": "parasitized",
            "positive_class": "parasitized",
            "positive_class_index": 1,
            "raw_model_score_meaning": "probability_parasitized",
        },
    }
