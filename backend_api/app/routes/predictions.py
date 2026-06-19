from fastapi import APIRouter, Query

from app.db import fetch_all, fetch_one
from app.services.serialization import row_to_dict, rows_to_list


router = APIRouter(prefix="/predictions", tags=["predictions"])


UPLOAD_FILTER_COLUMNS = {
    "model_name": "model_name",
    "predicted_label": "predicted_label",
    "quality_passed": "quality_passed",
    "calibration_method": "calibration_method",
    "calibration_applied": "calibration_applied",
    "ensemble_applied": "ensemble_applied",
    "tta_applied": "tta_applied",
    "confidence_level": "confidence_level",
    "case_type": "case_type",
    "decision_code": "decision_code",
}


def build_upload_filters(
    model_name=None,
    predicted_label=None,
    quality_passed=None,
    calibration_method=None,
    calibration_applied=None,
    ensemble_applied=None,
    tta_applied=None,
    confidence_level=None,
    case_type=None,
    decision_code=None,
    run_id=None,
):
    requested = {
        "model_name": model_name,
        "predicted_label": predicted_label,
        "quality_passed": quality_passed,
        "calibration_method": calibration_method,
        "calibration_applied": calibration_applied,
        "ensemble_applied": ensemble_applied,
        "tta_applied": tta_applied,
        "confidence_level": confidence_level,
        "case_type": case_type,
        "decision_code": decision_code,
    }
    conditions = []
    params = {}

    if run_id is not None:
        conditions.append("run_id = CAST(:run_id AS uuid)")
        params["run_id"] = run_id

    for key, value in requested.items():
        if value is None:
            continue
        conditions.append(f"{UPLOAD_FILTER_COLUMNS[key]} = :{key}")
        params[key] = value

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_sql, params


@router.get("/uploads")
def uploaded_predictions(
    datasource: str | None = Query(default="malaria"),
    model_name: str | None = Query(default=None),
    predicted_label: str | None = Query(default=None),
    quality_passed: bool | None = Query(default=None),
    calibration_method: str | None = Query(default=None),
    calibration_applied: bool | None = Query(default=None),
    ensemble_applied: bool | None = Query(default=None),
    tta_applied: bool | None = Query(default=None),
    confidence_level: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    decision_code: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = build_upload_filters(
        model_name=model_name,
        predicted_label=predicted_label,
        quality_passed=quality_passed,
        calibration_method=calibration_method,
        calibration_applied=calibration_applied,
        ensemble_applied=ensemble_applied,
        tta_applied=tta_applied,
        confidence_level=confidence_level,
        case_type=case_type,
        decision_code=decision_code,
        run_id=run_id,
    )
    count_row = fetch_one(
        datasource,
        f"SELECT COUNT(*) AS total FROM vw_clinical_inference_predictions {where_sql}",
        params,
    )
    rows = fetch_all(
        datasource,
        f"""
        SELECT
            *,
            image_stored_path AS artifact_path,
            image_original_path AS original_image_path,
            decision_code AS decision,
            tta_applied AS tta
        FROM vw_clinical_inference_predictions
        {where_sql}
        ORDER BY created_at DESC NULLS LAST
        LIMIT :limit OFFSET :offset
        """,
        {**params, "limit": limit, "offset": offset},
    )
    total = int(row_to_dict(count_row)["total"]) if count_row else 0
    return {
        "items": rows_to_list(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
    }
