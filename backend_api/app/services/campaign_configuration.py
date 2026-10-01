"""SWV2.2 campaign configuration: discover, validate, save, reload. Never executes.

All scientific decisions (parameter domains, defaults, protocol, Total de Experimentos) come from
``src.malaria_dl.campaigns.configuration``; persistence is the E4 ``CampaignService``. This module
only binds them to HTTP: dataset lookup through the governed dataset service, one request
transaction for campaign rows + application audit, and public error codes.
"""
from contextlib import contextmanager
from uuid import UUID

from fastapi import HTTPException, Request

from app.audit import mutation_connection, record_event
from app.db import get_primary_engine
from app.security import Principal
from app.services.governed_datasets import list_governed_dataset_versions

DATASOURCE = "malaria"
CHECKS = (
    ("dataset", "Dataset válido"),
    ("models", "Modelos seleccionados"),
    ("configurations", "Configuraciones válidas"),
    ("parameters", "Parámetros válidos"),
    ("total_experiments", "Total de Experimentos"),
)


def campaign_catalog() -> dict:
    from src.malaria_dl.campaigns.configuration import catalog

    return catalog()


def _dataset(dataset_version_id: UUID | None) -> tuple[dict | None, str | None]:
    if dataset_version_id is None:
        return None, "DATASET_VERSION_REQUIRED"
    items = list_governed_dataset_versions(DATASOURCE)["items"]
    item = next((i for i in items if str(i["dataset_version_id"]) == str(dataset_version_id)), None)
    if item is None:
        return None, "DATASET_VERSION_NOT_FOUND"
    if item["status"] != "FROZEN" or not item["trainable"]:
        return item, "DATASET_VERSION_NOT_TRAINABLE"
    return item, None


def _counts(item: dict) -> dict:
    return {"train": item["train_records"], "val": item["val_records"], "test": item["test_records"]}


def _checks(result: dict, dataset_error: str | None) -> list[dict]:
    errors = result["errors"]

    def failing(*prefixes):
        return [e for e in errors if any(e["field"] == p or e["field"].startswith(p + ".")
                                         or e["field"].startswith(p + "[") for p in prefixes)]

    groups = {
        "dataset": [dict(field="dataset_version_id", code=dataset_error)] if dataset_error else [],
        "models": failing("models"),
        "configurations": failing("optimizers", "seeds", "version")
        + [e for e in failing("variants") if ".parameters." not in e["field"]]
        + [e for e in errors if e["field"] == ""],
        "parameters": [e for e in failing("variants", "protocol") if ".parameters." in e["field"]
                       or e["field"].startswith("protocol")],
    }
    total = (result["summary"] or {}).get("total_experiments")
    groups["total_experiments"] = [] if result["valid"] and total else [dict(field="", code="TOTAL_UNAVAILABLE")]
    return [dict(check=key, label=label, status="PASS" if not groups[key] else "FAIL",
                 errors=groups[key]) for key, label in CHECKS]


def _public_dataset(item: dict | None) -> dict | None:
    if item is None:
        return None
    keys = ("dataset_version_id", "name", "semantic_version", "status", "trainable", "train_records",
            "val_records", "test_records", "source_record_count", "patient_count")
    return {k: item.get(k) for k in keys}


def preview(configuration: dict, dataset_version_id: UUID | None) -> dict:
    """Read-only. The same resolution the save path uses, so both report the same total."""
    from src.malaria_dl.campaigns.configuration import resolve

    item, dataset_error = _dataset(dataset_version_id)
    result = resolve(configuration, _counts(item) if item and not dataset_error else None)
    return dict(
        valid=result["valid"] and dataset_error is None,
        checks=_checks(result, dataset_error),
        errors=result["errors"] + ([dict(field="dataset_version_id", code=dataset_error)] if dataset_error else []),
        summary=result["summary"],
        protocol=None if not result["protocol"] else dict(
            version=result["protocol"]["version"], early_stopping=result["protocol"]["early_stopping"],
            budget=result["protocol"]["budget"], sensitivity_target=result["protocol"]["sensitivity_target"]),
        dataset=_public_dataset(item),
    )


def _shared_scope(connection):
    @contextmanager
    def scope(readonly=False):  # noqa: ARG001 -- one request transaction; never switched to READ ONLY
        yield connection

    return scope


def _saved(plan: dict) -> dict:
    keys = ("campaign_id", "name", "purpose", "state", "contract_hash", "frozen_at", "dataset_version_id",
            "dataset", "models", "optimizers", "seeds", "protocol", "configurations", "experiments",
            "total_experiments", "experiments_per_model", "command", "execution_boundary")
    return {k: plan[k] for k in keys}


def create_campaign(payload, principal: Principal, request: Request) -> dict:
    from src.malaria_dl.campaigns.configuration import resolve
    from src.malaria_dl.campaigns.contracts import CampaignError
    from src.malaria_dl.campaigns.plan import resolve_plan
    from src.malaria_dl.campaigns.repository import CampaignRepository
    from src.malaria_dl.campaigns.service import CampaignService
    from src.malaria_dl.data.governed_dataset import GovernedDatasetError

    item, dataset_error = _dataset(payload.dataset_version_id)
    result = resolve(payload.configuration.model_dump(), _counts(item) if item and not dataset_error else None)
    if dataset_error or not result["valid"]:
        raise HTTPException(422, detail=dict(code="CAMPAIGN_CONFIGURATION_INVALID",
                                             checks=_checks(result, dataset_error)))
    name, purpose = payload.name.strip(), payload.purpose.strip()
    with mutation_connection(get_primary_engine()) as connection:
        service = CampaignService(repository=CampaignRepository(scope=_shared_scope(connection)))
        try:
            row = service.configure(
                campaign_id=payload.campaign_id, name=name, purpose=purpose,
                dataset_version_id=payload.dataset_version_id, request=result["request"],
                protocol=result["protocol"], actor=principal.username,
            )
        except CampaignError as exc:
            status = 409 if str(exc) == "CAMPAIGN_ID_CONFLICT" else 422
            raise HTTPException(status, detail=dict(code=str(exc))) from None
        except GovernedDatasetError as exc:
            raise HTTPException(422, detail=dict(code=str(exc))) from None
        plan = resolve_plan(row)
        if plan["total_experiments"] != result["summary"]["total_experiments"]:
            raise RuntimeError("TOTAL_EXPERIMENTS_DIVERGENCE")
        record_event(
            event_type="ml.campaign.configured", action="create", principal=principal, request=request,
            success=True, connection=connection, resource_type="experimental_campaigns",
            resource_id=plan["campaign_id"],
            after_state=dict(campaign_id=plan["campaign_id"], contract_hash=plan["contract_hash"],
                             dataset_version_id=plan["dataset_version_id"],
                             total_experiments=plan["total_experiments"], state=plan["state"]),
        )
    return _saved(plan)


def campaign_detail(campaign_id: UUID) -> dict:
    """Reload exclusively from PostgreSQL v2 (contract/hash revalidated by the repository)."""
    from src.malaria_dl.campaigns.contracts import CampaignError
    from src.malaria_dl.campaigns.plan import resolve_plan
    from src.malaria_dl.campaigns.repository import CampaignRepository

    try:
        return _saved(resolve_plan(CampaignRepository().get(campaign_id)))
    except CampaignError as exc:
        if str(exc) == "CAMPAIGN_NOT_FOUND":
            raise HTTPException(404, "Campaña no encontrada.") from None
        raise HTTPException(409, detail=dict(code=str(exc))) from None
