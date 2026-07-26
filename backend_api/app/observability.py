from __future__ import annotations

import contextvars
import json
import logging
import re
import time
from uuid import UUID, uuid4

from fastapi import Request

from app.config import get_settings


correlation_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")
SENSITIVE = re.compile(r"(password|authorization|cookie|jwt|token|database_url)", re.I)


def sanitize(value):
    if isinstance(value, dict):
        return {key: ("<redacted>" if SENSITIVE.search(str(key)) else sanitize(item)) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    return value


def valid_correlation_id(value: str | None) -> str:
    if not value or len(value) > 64:
        return str(uuid4())
    try:
        return str(UUID(value))
    except ValueError:
        return str(uuid4())


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"timestamp": self.formatTime(record), "level": record.levelname,
                   "logger": record.name, "event": record.getMessage(),
                   "correlation_id": correlation_id_context.get()}
        for field in ("method", "path", "status_code", "duration_ms", "user_id", "environment"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        return json.dumps(sanitize(payload), ensure_ascii=False)


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if settings.log_format == "json" else logging.Formatter("%(levelname)s %(message)s"))
    logging.getLogger().handlers = [handler]
    logging.getLogger().setLevel(settings.log_level)


async def request_context_middleware(request: Request, call_next):
    settings = get_settings()
    correlation_id = valid_correlation_id(request.headers.get(settings.correlation_id_header))
    token = correlation_id_context.set(correlation_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers[settings.correlation_id_header] = correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
    finally:
        if settings.request_logging:
            logging.getLogger("capstone.request").info(
                "request.completed",
                extra={"method": request.method, "path": request.url.path,
                       "status_code": locals().get("response").status_code if "response" in locals() else 500,
                       "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                       "environment": settings.app_env},
            )
        correlation_id_context.reset(token)
