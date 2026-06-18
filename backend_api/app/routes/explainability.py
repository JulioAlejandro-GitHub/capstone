from fastapi import APIRouter, Query

from app.db import fetch_all, fetch_one
from app.services.serialization import row_to_dict, rows_to_list


router = APIRouter(tags=["explainability"])


CASE_FILTER_COLUMNS = {
    "model_name": "model_name",
    "dataset_name": "dataset_name",
    "method": "method",
    "case_type": "case_type",
    "true_label": "true_label",
    "predicted_label": "predicted_label",
    "success": "success",
}


def build_case_filters(
    model_name=None,
    dataset_name=None,
    method=None,
    case_type=None,
    run_id=None,
    true_label=None,
    predicted_label=None,
    success=None,
    allowed_columns=None,
):
    allowed_columns = allowed_columns or CASE_FILTER_COLUMNS
    requested = {
        "model_name": model_name,
        "dataset_name": dataset_name,
        "method": method,
        "case_type": case_type,
        "true_label": true_label,
        "predicted_label": predicted_label,
        "success": success,
    }
    conditions = []
    params = {}

    if run_id is not None:
        conditions.append("run_id = CAST(:run_id AS uuid)")
        params["run_id"] = run_id

    for key, value in requested.items():
        column = allowed_columns.get(key)
        if column is None or value is None:
            continue
        conditions.append(f"{column} = :{key}")
        params[key] = value

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_sql, params


def paged_view_response(
    datasource,
    view_name,
    where_sql,
    params,
    limit,
    offset,
    order_by="started_at DESC NULLS LAST",
):
    count_row = fetch_one(
        datasource,
        f"SELECT COUNT(*) AS total FROM {view_name} {where_sql}",
        params,
    )
    rows = fetch_all(
        datasource,
        f"""
        SELECT *
        FROM {view_name}
        {where_sql}
        ORDER BY {order_by}
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


def common_case_query_params(
    datasource,
    model_name,
    dataset_name,
    method,
    case_type,
    run_id,
    true_label,
    predicted_label,
    success,
    limit,
    offset,
    allowed_columns=None,
):
    return build_case_filters(
        model_name=model_name,
        dataset_name=dataset_name,
        method=method,
        case_type=case_type,
        run_id=run_id,
        true_label=true_label,
        predicted_label=predicted_label,
        success=success,
        allowed_columns=allowed_columns,
    )


@router.get("/explainability")
def explainability(
    datasource: str | None = Query(default="malaria"),
    limit: int = Query(default=100, ge=1, le=500),
):
    rows = fetch_all(
        datasource,
        """
        SELECT
            er.*,
            r.run_name,
            r.run_type,
            m.name AS model_name
        FROM explainability_results er
        LEFT JOIN runs r ON r.id = er.run_id
        LEFT JOIN models m ON m.id = r.model_id
        ORDER BY er.created_at DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )
    summary = fetch_all(
        datasource,
        """
        SELECT
            s.*,
            r.run_name,
            m.name AS model_name
        FROM vw_explainability_summary s
        LEFT JOIN runs r ON r.id = s.run_id
        LEFT JOIN models m ON m.id = r.model_id
        ORDER BY total_explanations DESC, method
        """,
    )
    return {"summary": rows_to_list(summary), "items": rows_to_list(rows)}


@router.get("/explainability/cases")
def explainability_cases(
    datasource: str | None = Query(default="malaria"),
    model_name: str | None = Query(default=None),
    dataset_name: str | None = Query(default=None),
    method: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    true_label: str | None = Query(default=None),
    predicted_label: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = common_case_query_params(
        datasource,
        model_name,
        dataset_name,
        method,
        case_type,
        run_id,
        true_label,
        predicted_label,
        success,
        limit,
        offset,
    )
    return paged_view_response(
        datasource,
        "vw_case_level_explainability",
        where_sql,
        params,
        limit,
        offset,
    )


@router.get("/explainability/cases/false-positives")
def false_positive_cases(
    datasource: str | None = Query(default="malaria"),
    model_name: str | None = Query(default=None),
    dataset_name: str | None = Query(default=None),
    method: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    true_label: str | None = Query(default=None),
    predicted_label: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = common_case_query_params(
        datasource,
        model_name,
        dataset_name,
        method,
        case_type,
        run_id,
        true_label,
        predicted_label,
        success,
        limit,
        offset,
    )
    return paged_view_response(
        datasource,
        "vw_false_positive_cases",
        where_sql,
        params,
        limit,
        offset,
        order_by="started_at DESC NULLS LAST, score_positive_label DESC NULLS LAST",
    )


@router.get("/explainability/cases/false-negatives")
def false_negative_cases(
    datasource: str | None = Query(default="malaria"),
    model_name: str | None = Query(default=None),
    dataset_name: str | None = Query(default=None),
    method: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    true_label: str | None = Query(default=None),
    predicted_label: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = common_case_query_params(
        datasource,
        model_name,
        dataset_name,
        method,
        case_type,
        run_id,
        true_label,
        predicted_label,
        success,
        limit,
        offset,
    )
    return paged_view_response(
        datasource,
        "vw_false_negative_cases",
        where_sql,
        params,
        limit,
        offset,
        order_by="started_at DESC NULLS LAST, score_positive_label ASC NULLS LAST",
    )


@router.get("/explainability/cases/low-confidence")
def low_confidence_cases(
    datasource: str | None = Query(default="malaria"),
    model_name: str | None = Query(default=None),
    dataset_name: str | None = Query(default=None),
    method: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    true_label: str | None = Query(default=None),
    predicted_label: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = common_case_query_params(
        datasource,
        model_name,
        dataset_name,
        method,
        case_type,
        run_id,
        true_label,
        predicted_label,
        success,
        limit,
        offset,
    )
    return paged_view_response(
        datasource,
        "vw_low_confidence_cases",
        where_sql,
        params,
        limit,
        offset,
        order_by="confidence_distance ASC NULLS LAST, started_at DESC NULLS LAST",
    )


@router.get("/explainability/cases/summary")
def case_type_summary(
    datasource: str | None = Query(default="malaria"),
    model_name: str | None = Query(default=None),
    dataset_name: str | None = Query(default=None),
    method: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    true_label: str | None = Query(default=None),
    predicted_label: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = build_case_filters(
        model_name=model_name,
        dataset_name=dataset_name,
        method=method,
        case_type=case_type,
        allowed_columns={
            "model_name": "model_name",
            "dataset_name": "dataset_name",
            "method": "method",
            "case_type": "case_type",
        },
    )
    return paged_view_response(
        datasource,
        "vw_case_type_summary",
        where_sql,
        params,
        limit,
        offset,
        order_by="model_name, dataset_name, method, case_type",
    )


@router.get("/explainability/gallery")
def explainability_gallery(
    datasource: str | None = Query(default="malaria"),
    model_name: str | None = Query(default=None),
    dataset_name: str | None = Query(default=None),
    method: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    true_label: str | None = Query(default=None),
    predicted_label: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = common_case_query_params(
        datasource,
        model_name,
        dataset_name,
        method,
        case_type,
        run_id,
        true_label,
        predicted_label,
        success,
        limit,
        offset,
    )
    return paged_view_response(
        datasource,
        "vw_explainability_gallery",
        where_sql,
        params,
        limit,
        offset,
    )
