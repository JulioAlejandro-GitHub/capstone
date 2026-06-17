from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import artifacts, catalog, dashboard, explainability, health, metrics, observability, runs


app = FastAPI(
    title="Capstone Experiments API",
    description="Read-only API for ML experiment tracking dashboards.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(runs.router)
app.include_router(catalog.router)
app.include_router(metrics.router)
app.include_router(explainability.router)
app.include_router(observability.router)
app.include_router(artifacts.router)

