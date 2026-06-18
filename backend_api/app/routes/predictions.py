from fastapi import APIRouter, Query

from app.db import fetch_all, fetch_one
from app.services.serialization import row_to_dict, rows_to_list


router = APIRouter(prefix="/predictions", tags=["predictions"])


UPLOAD_FILTER_COLUMNS = {
    "model_name": "model_name",
    "predicted_label": "predicted_label",
}


def build_upload_filters(model_name=None, predicted_label=None):
    requested = {
        "model_name": model_name,
        "predicted_label": predicted_label,
    }
    conditions = []
    params = {}

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
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = build_upload_filters(
        model_name=model_name,
        predicted_label=predicted_label,
    )
    count_row = fetch_one(
        datasource,
        f"SELECT COUNT(*) AS total FROM vw_uploaded_predictions {where_sql}",
        params,
    )
    rows = fetch_all(
        datasource,
        f"""
        SELECT *
        FROM vw_uploaded_predictions
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
