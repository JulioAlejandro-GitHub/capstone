from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.observability import configure_logging, correlation_id_context, request_context_middleware
from app.routes import analysis, artifacts, auth, catalog, cell_analysis, dashboard, dataset, explainability, governance, health, metrics, observability, predictions, runs, scientific


settings = get_settings()
configure_logging()
app = FastAPI(title=settings.app_name, description="Scientific experimental platform; not diagnostic.",
              version=settings.app_version)
app.middleware("http")(request_context_middleware)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type", settings.correlation_id_header],
                   expose_headers=[
                       settings.correlation_id_header, "ETag", "Content-Length",
                       "X-Content-Type-Options",
                   ])


def error_response(status: int, code: str, message: str, details: dict | list | None = None):
    return JSONResponse({"error": {"code": code, "message": message, "details": details or {},
                                  "correlation_id": correlation_id_context.get(), "retryable": status >= 500}},
                        status_code=status)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    codes = {401: "AUTHENTICATION_REQUIRED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT", 503: "DATABASE_UNAVAILABLE"}
    message = exc.detail if isinstance(exc.detail, str) else "La operación no pudo completarse."
    return error_response(exc.status_code, codes.get(exc.status_code, "REQUEST_ERROR"), message,
                          exc.detail if isinstance(exc.detail, dict) else {})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return error_response(422, "VALIDATION_ERROR", "Solicitud inválida.", exc.errors())


@app.exception_handler(Exception)
async def internal_error(_: Request, __: Exception):
    return error_response(500, "INTERNAL_ERROR", "Error interno.")


for router in (health.router, auth.router, dashboard.router, runs.router, catalog.router, dataset.router,
               metrics.router, explainability.router, predictions.router, observability.router,
               artifacts.router, governance.router, scientific.router, analysis.router,
               cell_analysis.router):
    app.include_router(router)
