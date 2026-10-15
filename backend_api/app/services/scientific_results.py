"""Shared scientific reading, preserving existing report responses."""
from typing import Annotated, Any
from uuid import UUID
from fastapi import Depends, HTTPException
from app.repositories.scientific_results import (
    ScientificReadRepository, metric_dto as metric_dto, read_scientific_results as read_scientific_results,
)
from app.repositories.assessments import AssessmentReadRepository
from app.services.scientific_public import public_evidence, assessment_projection


class ScientificReadService:
    def __init__(self, repository: ScientificReadRepository, assessments: AssessmentReadRepository) -> None:
        self.repository = repository
        self.assessments = assessments

    def read(self, training: UUID, datasource: str | None, traceability: bool, prediction_limit: int = 100, prediction_offset: int = 0) -> dict[str, Any]:
        result = self.repository.read(training, datasource, traceability, prediction_limit, prediction_offset)
        if result is None:
            raise HTTPException(404, "Run no encontrado")
        if not traceability:
            return result
        run = result.pop('training')
        model = result.pop('model')
        if run['run_type'] != 'training':
            raise HTTPException(422, "training_run_id debe identificar un TRAIN")
        if model is not None and model['model_type'] != 'classification':
            raise HTTPException(422, "El contrato SCC requiere un modelo de clasificación")
        result['artifacts'] = [{**artifact, 'artifact_id': artifact['id'],
                                'file_availability': 'not_checked'}
                               for artifact in result.get('artifacts', [])]
        attempts = [assessment_projection(a) for a in self.assessments.list(training, None, None, 0)]
        return dict(
            contract_version='scc_core_1', training_run_id=training,
            model=public_evidence(model), training=public_evidence(run),
            evidence=public_evidence(result), assessments=attempts,
            evidence_status={key: 'available' if value else 'not_persisted'
                             for key, value in result.items() if isinstance(value, list)},
            references={
                'assessments': f'/assessments?training_run_id={training}&view=traceability',
                'lineage': f'/runs/{training}/lineage-children?datasource=malaria',
                'predictions': f'/runs/{training}/image-predictions?datasource=malaria&view=traceability',
            },
        )


def get_scientific_read_service(
    repository: Annotated[ScientificReadRepository, Depends()],
    assessments: Annotated[AssessmentReadRepository, Depends()],
) -> ScientificReadService:
    return ScientificReadService(repository, assessments)
