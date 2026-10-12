"""Explicit cell activation: eligibility first, technical execution in one transaction."""
from contextlib import contextmanager
from typing import Any
from uuid import UUID
import math

from sqlalchemy.engine import Engine

from app.audit import mutation_connection
from app.repositories import cell_activation as repository
from app.repositories import stage2_status as evidence
from app.services.productive_model import ProductiveModelResolver, ProductiveModelError, _signature_shape
from src.malaria_dl.governance.eligibility import evaluation_completed, stage2_eligibility
from src.malaria_dl.governance.services.deployment_service import _project_path
from src.malaria_dl.governance.services.stage2_publication_service import Stage2PublicationService
from src.malaria_dl.governance.services.stage2_availability_service import Stage2ModelAvailabilityService
from src.malaria_dl.governance.services.prepare_release_service import PrepareModelReleaseService
from src.model_governance.errors import GovernanceStateError, GovernanceNotFoundError


class CellActivationService:
    def __init__(self, engine: Engine, datasource: str = 'malaria',
                 resolver: ProductiveModelResolver | None = None):
        self.engine = engine
        self.datasource = datasource
        self.resolver = resolver or ProductiveModelResolver(engine=engine)

    @staticmethod
    def _smoke(model: Any, resolved: Any) -> None:
        import numpy as np
        expected = (resolved.input_height, resolved.input_width, resolved.input_channels)
        if tuple(model.input_shape[1:]) != expected:
            raise GovernanceStateError('Las dimensiones del checkpoint no coinciden con el contrato evaluado.')
        output = np.asarray(model.predict(np.zeros((1, *expected), dtype='float32'), verbose=0))
        width = int(_signature_shape(resolved.output_signature, output=True)[-1])
        if output.shape != (1, width) or not np.isfinite(output).all() or not ((output >= 0) & (output <= 1)).all():
            raise GovernanceStateError('El checkpoint no produce probabilidades válidas para clasificación celular.')

    def activate(self, training_run_id: UUID, *, actor: str, replace_existing: bool = False,
                 reason: str = 'Activación para clasificación celular') -> dict:
        try:
            return self._activate(training_run_id, actor=actor, replace_existing=replace_existing, reason=reason)
        except ProductiveModelError as exc:
            raise GovernanceStateError(exc.reason or 'No se pudo cargar el checkpoint para clasificación celular.') from exc

    def _activate(self, training_run_id: UUID, *, actor: str, replace_existing: bool, reason: str) -> dict:
        with mutation_connection(self.engine) as connection:
            # A failed operation rolls back even when a caller catches its error in a larger transaction.
            with connection.begin_nested():
                repository.lock_selection(connection, self.datasource)
                training = evidence.read_training(connection, training_run_id)
                if training is None:
                    raise GovernanceNotFoundError('No se encontró el entrenamiento.')
                candidates = evidence.read_evaluations(connection, training_run_id)
                evaluation = next((item for item in candidates if evaluation_completed(item)), {})
                eligible, detail = stage2_eligibility({**training, **evaluation})
                if not eligible:
                    raise GovernanceStateError('; '.join(detail['missing_conditions']))
                version_id = evaluation.get('model_version_id')
                current = repository.active_publications(connection, self.datasource)
                if current and str(current[0]['model_version_id']) == str(version_id):
                    rows = self.resolver._fetch_candidates(connection=connection)
                    if len(rows) != 1:
                        raise GovernanceStateError('No se pudo resolver un único modelo activo.')
                    resolved = self.resolver._safe_validate(rows[0], require_active=True)
                    self.resolver.load(resolved)
                    return self._result(training_run_id, resolved.model_version_id, resolved.deployment_id, True)
                if current and not replace_existing:
                    raise GovernanceStateError('STAGE2_SELECTION_EXISTS: ya hay otro modelo activo. Confirma el reemplazo.')

                @contextmanager
                def shared_connection():
                    yield connection

                if evaluation.get('evaluation_source_kind') != 'assessment_e6':
                    version = evidence.read_version(connection, training_run_id, version_id)
                    if version is None:
                        prepared = PrepareModelReleaseService(shared_connection).prepare_release(str(training_run_id), requester=actor)
                        version_id = prepared['model_version_id']
                    else:
                        version_id = str(version['id'])
                    Stage2PublicationService(shared_connection, self.datasource).publish(
                        version_id, actor, reason, replace_existing=replace_existing)
                    result = Stage2ModelAvailabilityService(shared_connection).enable(
                        str(training_run_id), actor=actor, reason=reason, confirm_stage2_enablement=True)
                    if str(result.get('model_version_id')) != str(version_id):
                        raise GovernanceStateError('La activación seleccionó una versión distinta de la evaluada.')
                    if not result.get('available_for_inference'):
                        raise GovernanceStateError('No se pudo cargar el modelo activado.')
                    repository.mark_active_training(connection, training_run_id, actor, reason)
                    return self._result(training_run_id, version_id, result['deployment_id'], False)

                attempt = str(evaluation['evaluation_attempt_id'])
                stored = repository.assessment_contract(connection, UUID(attempt))
                binding, decision = stored['model'], stored['decision']
                contract = binding['input_contract']
                if decision.get('comparison') != '>=' or decision.get('score_domain') != 'raw':
                    raise GovernanceStateError('La regla de decisión evaluada no está soportada por el clasificador.')
                threshold = float(decision['effective'])
                if not math.isfinite(threshold) or not 0 <= threshold <= 1:
                    raise GovernanceStateError('El umbral evaluado no es válido.')
                path = _project_path(binding['path'])
                binding = repository.register_evidence(connection, training, binding, contract, str(path))
                deployment = repository.create_deployment(connection, binding, attempt, decision, contract, actor)
                publication = repository.publish_assessment(connection, str(training_run_id), binding, attempt,
                                                              self.datasource, actor, reason)
                snapshot = {'production_model_id': deployment, 'model_registry_id': binding['model_version_id'],
                            'checkpoint_artifact_id': binding['checkpoint_artifact_id'],
                            'stage2_publication_id': str(publication['id']), 'checkpoint_sha256': binding['sha256']}
                rows = self.resolver._fetch_candidates(snapshot=snapshot, connection=connection)
                if len(rows) != 1:
                    raise GovernanceStateError('No se pudo resolver el checkpoint seleccionado.')
                resolved = self.resolver._safe_validate(rows[0], require_active=False)
                self._smoke(self.resolver.load(resolved), resolved)
                repository.activate_deployment(connection, deployment, actor, reason)
                repository.mark_active_training(connection, training_run_id, actor, reason)
                return self._result(training_run_id, binding['model_version_id'], deployment, False)

    @staticmethod
    def _result(training: UUID, version: str, deployment: str, idempotent: bool) -> dict:
        return {'training_run_id': str(training), 'model_version_id': str(version),
                'deployment_id': str(deployment), 'available_for_inference': True, 'idempotent': idempotent}
