"""Explicit opt-in local TRAIN API; no arbitrary commands or automatic startup."""
import json
import os
from fastapi import APIRouter,Depends,HTTPException
from app.security import Principal,Permission,require_permission

router=APIRouter(prefix='/execution/local',tags=['local-execution'])


def service():
    if os.getenv('CAPSTONE_LOCAL_EXECUTION_ENABLED')!='1':
        raise HTTPException(503,'LOCAL_EXECUTION_DISABLED')
    from src.malaria_dl.execution.controlled import ControlledRepository
    from src.malaria_dl.local_execution.backend import LocalBackend
    roots=json.loads(os.environ['CAPSTONE_LOCAL_STORAGE_ROOTS'])
    return LocalBackend(ControlledRepository(),roots)


@router.post('/{operation}')
def local_operation(operation:str,data:dict,principal:Principal=Depends(require_permission(Permission.SYSTEM_ADMIN)),backend=Depends(service)):
    from src.malaria_dl.campaigns.contracts import CampaignError
    try:
        if operation=='dry-run':return backend.dry_run(data)
        if operation=='claim':return backend.claim(data,principal.user_id)
        if operation in ('heartbeat','record','records','calculation-ended','exit','status'):
            return backend.operation(operation,data,principal.user_id)
        raise HTTPException(404,'LOCAL_OPERATION_UNKNOWN')
    except CampaignError as exc:
        raise HTTPException(409,str(exc)) from None
    except (KeyError,ValueError,TypeError):
        raise HTTPException(422,'LOCAL_CONTRACT_INVALID') from None
