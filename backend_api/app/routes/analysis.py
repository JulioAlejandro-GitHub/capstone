from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

from app.audit import transactional_permission
from app.schemas.analysis import AnalysisRunCreate, QualityDecisionCreate, QualityQueueCreate, QualityQueueRetry
from app.security import Permission, Principal, require_permission
from app.services.microscopy_analysis import AnalysisError, MicroscopyAnalysisService
from app.services.quality_queue import QualityQueueService

router = APIRouter(prefix="/api/v1/analysis", tags=["microscopy-analysis"])
service = MicroscopyAnalysisService()
queue_service = QualityQueueService()

def execute(call):
    try: return call()
    except AnalysisError as exc: raise HTTPException(exc.status_code, exc.detail) from exc

@router.get("/eligible-batches")
def eligible_batches(subject_code:str|None=None,sample_code:str|None=None,source_system:str|None=None,status:str|None=None,
 limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),
 _:Principal=Depends(require_permission(Permission.SCIENTIFIC_ANALYSIS_READ))):
    return service.eligible_batches(subject_code=subject_code,sample_code=sample_code,source_system=source_system,status=status,limit=limit,offset=offset)

@router.post("/runs",status_code=201)
def create_run(body:AnalysisRunCreate,request:Request,
 principal:Principal=Depends(transactional_permission(Permission.SCIENTIFIC_ANALYSIS_CREATE))):
    return execute(lambda:service.create(str(body.ingestion_batch_id),principal,request))

@router.post("/runs/{run_id}/quality-assessment")
async def quality_assessment(run_id:UUID,request:Request,
 principal:Principal=Depends(transactional_permission(Permission.SCIENTIFIC_ANALYSIS_QUALITY_EXECUTE))):
    try: run,results=await run_in_threadpool(service.measurements,str(run_id))
    except AnalysisError as exc: raise HTTPException(exc.status_code,exc.detail) from exc
    return execute(lambda:service.persist_measurements(run,results,principal,request))

@router.get("/runs")
def list_runs(run_code:str|None=None,subject_code:str|None=None,sample_code:str|None=None,run_status:str|None=None,
 quality_gate_status:str|None=None,source_system:str|None=None,limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),
 _:Principal=Depends(require_permission(Permission.SCIENTIFIC_ANALYSIS_READ))):
    return service.list_runs(limit=limit,offset=offset,run_code=run_code,subject_code=subject_code,sample_code=sample_code,
      run_status=run_status,quality_gate_status=quality_gate_status,source_system=source_system)

@router.get("/runs/{run_id}")
def detail(run_id:UUID,_:Principal=Depends(require_permission(Permission.SCIENTIFIC_ANALYSIS_READ))):
    return execute(lambda:service.get(str(run_id)))

@router.get("/runs/{run_id}/events")
def events(run_id:UUID,limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),
 _:Principal=Depends(require_permission(Permission.SCIENTIFIC_ANALYSIS_READ))):
    return execute(lambda:service.events(str(run_id),limit,offset))

@router.post("/runs/{run_id}/quality-decision")
def decision(run_id:UUID,body:QualityDecisionCreate,request:Request,
 principal:Principal=Depends(transactional_permission(Permission.SCIENTIFIC_ANALYSIS_QUALITY_REVIEW))):
    return execute(lambda:service.review(str(run_id),body.decision,body.comment,principal,request))

@router.post("/queue",status_code=201)
def enqueue(body:QualityQueueCreate,request:Request,
 principal:Principal=Depends(require_permission(Permission.SCIENTIFIC_ANALYSIS_QUEUE_CREATE))):
    return execute(lambda:queue_service.enqueue(body.analysis_run_id,body.priority,principal,request))

@router.get("/queue")
def queue(status:str|None=None,priority:int|None=None,run_code:str|None=None,
 subject_code:str|None=None,sample_code:str|None=None,limit:int=Query(50,ge=1,le=200),
 offset:int=Query(0,ge=0),
 _:Principal=Depends(require_permission(Permission.SCIENTIFIC_ANALYSIS_QUEUE_READ))):
    return queue_service.list(status=status,priority=priority,run_code=run_code,
      subject_code=subject_code,sample_code=sample_code,limit=limit,offset=offset)

@router.post("/queue/{queue_item_id}/execute")
async def execute_queue_item(queue_item_id:UUID,request:Request,
 principal:Principal=Depends(require_permission(Permission.SCIENTIFIC_ANALYSIS_QUEUE_EXECUTE))):
    try:
        return await run_in_threadpool(queue_service.execute,str(queue_item_id),principal,request)
    except AnalysisError as exc:
        raise HTTPException(exc.status_code,exc.detail) from exc

@router.post("/queue/{queue_item_id}/retry")
def retry_queue_item(queue_item_id:UUID,body:QualityQueueRetry,request:Request,
 principal:Principal=Depends(require_permission(Permission.SCIENTIFIC_ANALYSIS_QUEUE_RETRY))):
    return execute(lambda:queue_service.retry(str(queue_item_id),body.priority,principal,request))
