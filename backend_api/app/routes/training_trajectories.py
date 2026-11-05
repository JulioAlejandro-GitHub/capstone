"""Authenticated read of the per-epoch VAL trajectories of one TRAIN."""
from typing import Annotated, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.schemas.training_trajectories import TrainingTrajectories
from app.security import Permission, require_permission
from app.services.training_trajectories import TrainingTrajectoryService, get_training_trajectory_service

router = APIRouter(prefix='/runs/{run_id}/training-trajectories', tags=['training-trajectories'],
                   dependencies=[Depends(require_permission(Permission.RUNS_READ))])


@router.get('', response_model=TrainingTrajectories)
def read(run_id: UUID, service: Annotated[TrainingTrajectoryService, Depends(get_training_trajectory_service)],
         datasource: str | None = Query(None)) -> dict[str, Any]:
    return service.read(run_id, datasource)
