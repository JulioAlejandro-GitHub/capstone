from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


def to_jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def row_to_dict(row):
    return to_jsonable(dict(row)) if row is not None else None


def rows_to_list(rows):
    return [row_to_dict(row) for row in rows]

