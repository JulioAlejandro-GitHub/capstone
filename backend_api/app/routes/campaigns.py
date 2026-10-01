"""SWV2.2 Modelo IA -> Campaña: configure, validate and save campaigns.

Deliberately no execution endpoint: the saved campaign is run by the operator from a console with
``python run_train_all_models.py --campaign-id <UUID>``.
"""
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError

from app.audit import transactional_permission
from app.schemas.campaigns import CampaignCreate, CampaignMatrixConfiguration
from app.security import Permission, Principal, require_permission
from app.services.campaign_configuration import (
    campaign_catalog,
    campaign_detail,
    create_campaign,
    list_campaigns,
    preview,
)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("/catalog", dependencies=[Depends(require_permission(Permission.RUNS_READ))])
def catalog():
    return campaign_catalog()


@router.get("/preview", dependencies=[Depends(require_permission(Permission.RUNS_READ))])
def campaign_preview(
    configuration: str = Query(max_length=16000),
    dataset_version_id: UUID | None = Query(default=None),
):
    """Read-only validation and Total de Experimentos; a GET because nothing is persisted."""
    try:
        document = CampaignMatrixConfiguration.model_validate(json.loads(configuration))
    except (ValueError, ValidationError):
        raise HTTPException(422, detail=dict(code="CAMPAIGN_CONFIGURATION_MALFORMED")) from None
    return preview(document.model_dump(), dataset_version_id)


@router.get("", dependencies=[Depends(require_permission(Permission.RUNS_READ))])
def campaigns(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Report of created campaigns (newest first). Edit opens the configuration page by id."""
    return list_campaigns(limit, offset)


@router.post("", status_code=201)
def create(
    payload: CampaignCreate,
    request: Request,
    principal: Principal = Depends(transactional_permission(Permission.CAMPAIGNS_CONFIGURE)),
):
    return create_campaign(payload, principal, request)


@router.get("/{campaign_id}", dependencies=[Depends(require_permission(Permission.RUNS_READ))])
def detail(campaign_id: UUID):
    return campaign_detail(campaign_id)
