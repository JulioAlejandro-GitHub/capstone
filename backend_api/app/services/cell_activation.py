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
from src.malaria_dl.governance.eligibility import evaluation_completed, is_zero_shot, select_evaluation, stage2_eligibility
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

    def preview(self, training_run_id: str) -> dict:
        from app.services.stage2_status import Stage2StatusService
        return Stage2StatusService().status(UUID(training_run_id), self.datasource).model_dump(mode='json')

    def enable(self, training_run_id: str, *, actor: str, reason: str,
               confirm_stage2_enablement: bool, preprocessing_candidate_id=None,
               threshold_candidate_id=None, source_image_id=None) -> dict:
        """Existing Stage 2 endpoints share the cellular activation operation."""
        if not confirm_stage2_enablement:
            raise GovernanceStateError('confirmación explícita requerida')
        if preprocessing_candidate_id or threshold_candidate_id or source_image_id:
            # Explicit Keras release preparation retains its established parameters.
            @contextmanager
            def shared_connection():
                with mutation_connection(self.engine) as connection:
                    yield connection
            return Stage2ModelAvailabilityService(shared_connection).enable(
                training_run_id, actor=actor, reason=reason,
                confirm_stage2_enablement=True, preprocessing_candidate_id=preprocessing_candidate_id,
                threshold_candidate_id=threshold_candidate_id, source_image_id=source_image_id)
        result = self.activate(UUID(training_run_id), actor=actor, reason=reason)
        with mutation_connection(self.engine) as connection:
            rows = self.resolver._fetch_candidates(connection=connection)
            if len(rows) != 1:
                raise GovernanceStateError('No se pudo resolver un único modelo activo.')
            resolved = self.resolver._safe_validate(rows[0], require_active=True)
        return {**result, 'environment': 'stage2', 'alias': 'default', 'status': 'active',
                'artifact_sha256': resolved.checkpoint_sha256, 'threshold': resolved.threshold,
                'threshold_source': resolved.threshold_source, 'deployed_at': resolved.published_at,
                'smoke_status': 'PASS', 'warnings': [] if (resolved.source_evaluation_run_id or
                    resolved.source_evaluation_attempt_id) else ['Sin evidencia de evaluación']}

    @staticmethod
    def _smoke(model: Any, resolved: Any) -> None:
        import numpy as np
        expected = (resolved.input_height, resolved.input_width, resolved.input_channels)
        if tuple(model.input_shape[1:]) != expected:
            raise GovernanceStateError('Las dimensiones del checkpoint no coinciden con el contrato registrado.')
        output = np.asarray(model.predict(np.zeros((1, *expected), dtype='float32'), verbose=0))
        width = int(_signature_shape(resolved.output_signature, output=True)[-1])
        if output.shape != (1, width) or not np.isfinite(output).all() or not ((output >= 0) & (output <= 1)).all():
            raise GovernanceStateError('El checkpoint no produce scores válidos para clasificación celular.')

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
                evaluation = select_evaluation(candidates) or {}
                eligible, detail = stage2_eligibility({**training, **evaluation})
                if not eligible:
                    raise GovernanceStateError('; '.join(detail['missing_conditions']))
                version_id = evaluation.get('model_version_id')
                version = evidence.read_version(connection, training_run_id, version_id)
                if version is not None:
                    version_id = str(version['id'])
                current = repository.active_publications(connection, self.datasource)
                same_decision = not is_zero_shot(evaluation) or (
                    str(current[0].get('evaluation_attempt_id') or '') if current else ''
                ) == str(evaluation.get('evaluation_attempt_id') or '')
                # A zero-shot version already serving another decision (e.g. a new VAL
                # calibration) is republished below; anything else stays idempotent.
                if current and str(current[0]['model_version_id']) == str(version_id) and same_decision:
                    rows = self.resolver._fetch_candidates(connection=connection)
                    if len(rows) == 1 and rows[0].get('deployment_id'):
                        resolved = self.resolver._safe_validate(rows[0], require_active=True)
                        self.resolver.load(resolved)
                        return self._result(training_run_id, resolved.model_version_id, resolved.deployment_id, True)
                if current and str(current[0]['model_version_id']) != str(version_id) and not replace_existing:
                    raise GovernanceStateError('STAGE2_SELECTION_EXISTS: ya hay otro modelo activo. Confirma el reemplazo.')

                @contextmanager
                def shared_connection():
                    yield connection

                if version is None and not evaluation_completed(evaluation):
                    raise GovernanceStateError('No existe una versión con checkpoint registrado para activar.')
                if version is not None and not evaluation_completed(evaluation):
                    binding = {'model_version_id': version_id,
                               'checkpoint_artifact_id': str(version['checkpoint_artifact_id']),
                               'sha256': version['artifact_sha256'], 'bytes': version['artifact_size_bytes']}
                    contract = {'external': version['preprocessing_profile_snapshot'],
                                'label_mapping': version['class_mapping'],
                                'architecture': (version['metadata'] or {}).get('architecture') or version['model_name'],
                                'output': version['output_signature']}
                    decision = {'effective': 0.5, 'comparison': '>=', 'score_domain': 'raw',
                                'source': 'configured_decision'}
                    deployment = repository.create_deployment(connection, binding, None, decision, contract, actor)
                    publication = repository.publish_assessment(connection, str(training_run_id), binding, None,
                                                                  self.datasource, actor, reason)
                    snapshot = {'production_model_id': deployment, 'model_registry_id': version_id,
                                'checkpoint_artifact_id': binding['checkpoint_artifact_id'],
                                'stage2_publication_id': str(publication['id']), 'checkpoint_sha256': binding['sha256']}
                    rows = self.resolver._fetch_candidates(snapshot=snapshot, connection=connection)
                    if len(rows) != 1:
                        raise GovernanceStateError('No se pudo resolver la versión seleccionada.')
                    resolved = self.resolver._safe_validate(rows[0], require_active=False)
                    self._smoke(self.resolver.load(resolved), resolved)
                    repository.activate_deployment(connection, deployment, actor, reason)
                    repository.mark_active_training(connection, training_run_id, actor, reason)
                    return self._result(training_run_id, version_id, deployment, False)

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
