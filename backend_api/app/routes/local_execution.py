"""Explicit opt-in local TRAIN API; no arbitrary commands or automatic startup."""
import json
import os
from fastapi import APIRouter,Depends,HTTPException
from app.security import Principal,Permission,require_permission

router=APIRouter(prefix='/execution/local',tags=['local-execution'])


def event_service():
    if os.getenv('CAPSTONE_LOCAL_EXECUTION_ENABLED')!='1':
        raise HTTPException(503,'LOCAL_EXECUTION_DISABLED')
    from app.config import get_settings
    if get_settings().auth_mode != 'local_jwt':
        raise HTTPException(503,'LOCAL_EVENTS_REQUIRE_LOCAL_JWT')
    from src.malaria_dl.local_execution.event_backend import build_local_event_backend
    return build_local_event_backend()


# Register the explicit operation before /{operation}; legacy dispatch is intact.
@router.post('/events')
def local_event(data:dict, principal:Principal=Depends(require_permission(Permission.SYSTEM_ADMIN)),
                backend=Depends(event_service)):
    from src.malaria_dl.local_execution.event_transport import EventRequest
    from src.malaria_dl.results.errors import (
        ResultError, ResultPersistenceError, WriterNotAuthorized,
        UnsupportedEventSchema, InvalidEventType,
    )
    try:
        request=EventRequest.from_dict(data)
    except (KeyError,ValueError,TypeError):
        raise HTTPException(422,'LOCAL_EVENT_CONTRACT_INVALID') from None
    try:
        acceptance=backend.accept(request,principal.user_id)
        return {'status':acceptance.status.value, 'run_id':str(acceptance.run_id),
                'event_id':str(acceptance.event_id), 'sequence':acceptance.sequence}
    except WriterNotAuthorized:
        raise HTTPException(403,'WRITER_NOT_AUTHORIZED') from None
    except ResultPersistenceError:
        raise HTTPException(503,'RESULT_PERSISTENCE_ERROR') from None
    except (UnsupportedEventSchema,InvalidEventType) as exc:
        raise HTTPException(422,exc.code) from None
    except ResultError as exc:
        raise HTTPException(409,exc.code) from None
    except Exception:
        raise HTTPException(500,'LOCAL_EVENT_INTERNAL_ERROR') from None


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
