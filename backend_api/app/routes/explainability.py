from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.db import fetch_all, fetch_one
from app.services.explainability import enrich_explainability_items
from app.services.serialization import row_to_dict, rows_to_list


router = APIRouter(tags=["explainability"])

VISUAL_AUDIT_VIEW = "vw_visual_explainability_audit"

CASE_FILTER_COLUMNS = {
    "model_name": "model_name",
    "dataset_name": "dataset_name",
    "method": "method",
    "case_type": "case_type",
    "true_label": "true_label",
    "predicted_label": "predicted_label",
    "threshold_source": "threshold_source",
    "success": "success",
}


def _normalize_run_id(run_id) -> str | None:
    if run_id is None:
        return None
    try:
        return str(UUID(str(run_id)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail="run_id debe ser un UUID valido.") from exc


def _parse_date_filter(value, parameter_name: str, *, end: bool = False):
    if value is None:
        return None, False

    if isinstance(value, datetime):
        return value, False
    if isinstance(value, date):
        boundary = datetime.combine(value, time.min)
        return (boundary + timedelta(days=1), True) if end else (boundary, False)

    raw_value = str(value).strip()
    if not raw_value:
        return None, False

    try:
        parsed_date = date.fromisoformat(raw_value)
    except ValueError:
        try:
            parsed_datetime = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"{parameter_name} debe usar formato ISO-8601.",
            ) from exc
        return parsed_datetime, False

    boundary = datetime.combine(parsed_date, time.min)
    return (boundary + timedelta(days=1), True) if end else (boundary, False)


def build_case_filters(
    model_name=None,
    dataset_name=None,
    method=None,
    case_type=None,
    run_id=None,
    true_label=None,
    predicted_label=None,
    threshold_source=None,
    success=None,
    date_from=None,
    date_to=None,
    allowed_columns=None,
    extra_conditions=None,
):
    allowed_columns = allowed_columns or CASE_FILTER_COLUMNS
    requested = {
        "model_name": model_name,
        "dataset_name": dataset_name,
        "method": method,
        "case_type": case_type,
        "true_label": true_label,
        "predicted_label": predicted_label,
        "threshold_source": threshold_source,
        "success": success,
    }
    conditions = list(extra_conditions or [])
    params = {}

    if run_id is not None:
        conditions.append("run_id = CAST(:run_id AS uuid)")
        params["run_id"] = _normalize_run_id(run_id)

    for key, value in requested.items():
        column = allowed_columns.get(key)
        if column is None or value is None:
            continue
        conditions.append(f"{column} = :{key}")
        params[key] = value

    parsed_date_from, _ = _parse_date_filter(date_from, "date_from")
    parsed_date_to, date_to_is_exclusive = _parse_date_filter(date_to, "date_to", end=True)
    if parsed_date_from is not None:
        conditions.append("started_at >= :date_from")
        params["date_from"] = parsed_date_from
    if parsed_date_to is not None:
        operator = "<" if date_to_is_exclusive else "<="
        conditions.append(f"started_at {operator} :date_to")
        params["date_to"] = parsed_date_to
    if parsed_date_from is not None and parsed_date_to is not None:
        try:
            invalid_range = (
                parsed_date_from >= parsed_date_to
                if date_to_is_exclusive
                else parsed_date_from > parsed_date_to
            )
        except TypeError:
            # PostgreSQL can compare timestamp values with and without timezone,
            # while Python intentionally rejects that mixed comparison.
            invalid_range = False
        if invalid_range:
            raise HTTPException(status_code=422, detail="date_from no puede ser posterior a date_to.")

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
    enrich_cases=False,
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
    items = rows_to_list(rows)
    if enrich_cases:
        items = enrich_explainability_items(items)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def common_case_query_params(
    model_name,
    dataset_name,
    method,
    case_type,
    run_id,
    true_label,
    predicted_label,
    threshold_source,
    success,
    date_from,
    date_to,
    allowed_columns=None,
    extra_conditions=None,
):
    return build_case_filters(
        model_name=model_name,
        dataset_name=dataset_name,
        method=method,
        case_type=case_type,
        run_id=run_id,
        true_label=true_label,
        predicted_label=predicted_label,
        threshold_source=threshold_source,
        success=success,
        date_from=date_from,
        date_to=date_to,
        allowed_columns=allowed_columns,
        extra_conditions=extra_conditions,
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
    threshold_source: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = common_case_query_params(
        model_name=model_name,
        dataset_name=dataset_name,
        method=method,
        case_type=case_type,
        run_id=run_id,
        true_label=true_label,
        predicted_label=predicted_label,
        threshold_source=threshold_source,
        success=success,
        date_from=date_from,
        date_to=date_to,
    )
    return paged_view_response(
        datasource,
        VISUAL_AUDIT_VIEW,
        where_sql,
        params,
        limit,
        offset,
        enrich_cases=True,
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
    threshold_source: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = common_case_query_params(
        model_name=model_name,
        dataset_name=dataset_name,
        method=method,
        case_type="false_positive",
        run_id=run_id,
        true_label=true_label,
        predicted_label=predicted_label,
        threshold_source=threshold_source,
        success=success,
        date_from=date_from,
        date_to=date_to,
    )
    return paged_view_response(
        datasource,
        VISUAL_AUDIT_VIEW,
        where_sql,
        params,
        limit,
        offset,
        order_by="started_at DESC NULLS LAST, score_positive_label DESC NULLS LAST",
        enrich_cases=True,
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
    threshold_source: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = common_case_query_params(
        model_name=model_name,
        dataset_name=dataset_name,
        method=method,
        case_type="false_negative",
        run_id=run_id,
        true_label=true_label,
        predicted_label=predicted_label,
        threshold_source=threshold_source,
        success=success,
        date_from=date_from,
        date_to=date_to,
    )
    return paged_view_response(
        datasource,
        VISUAL_AUDIT_VIEW,
        where_sql,
        params,
        limit,
        offset,
        order_by="started_at DESC NULLS LAST, score_positive_label ASC NULLS LAST",
        enrich_cases=True,
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
    threshold_source: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where_sql, params = common_case_query_params(
        model_name=model_name,
        dataset_name=dataset_name,
        method=method,
        case_type=None,
        run_id=run_id,
        true_label=true_label,
        predicted_label=predicted_label,
        threshold_source=threshold_source,
        success=success,
        date_from=date_from,
        date_to=date_to,
        extra_conditions=[
            "(case_type = 'low_confidence' OR confidence_distance <= 0.10)"
        ],
    )
    return paged_view_response(
        datasource,
        VISUAL_AUDIT_VIEW,
        where_sql,
        params,
        limit,
        offset,
        order_by="confidence_distance ASC NULLS LAST, started_at DESC NULLS LAST",
        enrich_cases=True,
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
    threshold_source: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    gallery_conditions = ["explanation_output_path IS NOT NULL"]
    gallery_case_type = case_type
    if case_type == "low_confidence":
        gallery_case_type = None
        gallery_conditions.append(
            "(case_type = 'low_confidence' OR confidence_distance <= 0.10)"
        )

    where_sql, params = common_case_query_params(
        model_name=model_name,
        dataset_name=dataset_name,
        method=method,
        case_type=gallery_case_type,
        run_id=run_id,
        true_label=true_label,
        predicted_label=predicted_label,
        threshold_source=threshold_source,
        success=success,
        date_from=date_from,
        date_to=date_to,
        extra_conditions=gallery_conditions,
    )
    return paged_view_response(
        datasource,
        VISUAL_AUDIT_VIEW,
        where_sql,
        params,
        limit,
        offset,
        enrich_cases=True,
    )
