"""SCC admission from persisted evidence; independent of A1–A6 comparability.

Admission requires TRAIN and EVALUATE. EXPLAIN is still reported but does not gate: it can be generated
from the analysis report itself."""
from uuid import UUID, uuid5

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.db import read_only_transaction
from app.repositories.assessments import AssessmentReadRepository
from app.repositories.scientific_results import ScientificReadRepository
from app.services.scientific_report import checkpoint_evidence


def checkpoint_binding(run_id, training, checkpoint):
    training, checkpoint = training or {}, checkpoint or {}
    registered = checkpoint_evidence(checkpoint, run_id)['logical_lineage']
    binding = dict(training_run_id=str(run_id), checkpoint_artifact_id=str(checkpoint.get('id')),
                   path=checkpoint.get('path'), sha256=checkpoint.get('checksum'),
                   bytes=checkpoint.get('file_size_bytes'))
    if training.get('session_state') is not None:
        proof = training.get('verification') or {}
        artifact = proof.get('artifact') or {}
        version = artifact.get('version_id')
        try:
            binding['checkpoint_artifact_id'] = str(uuid5(UUID(str(version)), 'e5-selected-checkpoint'))
        except ValueError:
            registered = False
        binding.update(model_version_id=version, input_contract=training.get('input_contract'),
                       source=dict(kind='e5_selected_record', epoch=artifact.get('epoch'),
                                   records_hash=proof.get('records_hash')))
        registered = registered and training['session_state'] == 'verified' and all((
            artifact.get('run_id') == str(run_id),
            artifact.get('sha256') == binding['sha256'],
            artifact.get('bytes') == binding['bytes'],
            artifact.get('path') == binding['path'],
            artifact.get('epoch') == (checkpoint.get('selection') or {}).get('selected_epoch'),
            artifact.get('phase') == (checkpoint.get('selection') or {}).get('phase'),
        ))
    registered = bool(registered and binding['sha256'] and binding['path'] and binding['bytes'])
    return registered, binding


def decision(run_id, training, checkpoint, attempts):
    result = dict(run_id=str(run_id), eligible=False, train=False, evaluate=False,
                  explain=False, reasons=[], evidence={})

    def reason(stage, code, message):
        result['reasons'].append(dict(stage=stage, code=code, message=message))

    checkpoint = checkpoint or {}
    training = training or {}
    completed = training.get('run_type') == 'training' and training.get('status') == 'completed'
    if not completed:
        reason('train', 'TRAIN_NOT_COMPLETED', 'TRAIN no completado.')
    registered, binding = checkpoint_binding(run_id, training, checkpoint)
    if not registered:
        reason('train', 'CHECKPOINT_UNACCREDITED', 'Checkpoint seleccionado no acreditado.')
    result['train'] = completed and registered
    for kind in ('evaluate', 'explain'):
        candidates = [a for a in attempts if a['kind'] == kind]
        valid_results = []
        for attempt in candidates:
            verification = attempt.get('verification') or {}
            count = attempt['result_count']
            if (attempt['state'] == 'verified' and attempt['finished_at'] is not None
                    and count > 0 and count == attempt['expected_count'] == verification.get('count')
                    and verification.get('sha256')
                    and (kind != 'explain' or (attempt['artifact_count'] == 2 * count
                                              and verification.get('artifacts_hash')))):
                valid_results.append(attempt)
        matching = [a for a in valid_results if registered and all(
            (a['identity'].get('model') or {}).get(key) == value for key, value in binding.items())]
        if matching:
            result[kind] = True
            result['evidence'][kind] = [dict(identity_id=str(a['identity_id']), attempt_id=str(a['attempt_id']))
                                        for a in matching]
        elif not candidates:
            reason(kind, f'{kind.upper()}_NOT_EXECUTED', f'{kind.upper()} no ejecutado.'
                   + (' Opcional: se puede generar desde Análisis.' if kind == 'explain' else ''))
        elif valid_results:
            reason(kind, 'INCOMPATIBLE_LINEAGE', f'{kind.upper()}: linaje incompatible con el checkpoint seleccionado.')
        else:
            reason(kind, f'{kind.upper()}_INVALID_EVIDENCE',
                   f'{kind.upper()} sin intento finalizado y verificado con resultados'
                   + (' y artefactos válidos.' if kind == 'explain' else ' válidos.'))
    result['eligible'] = bool(result['train'] and result['evaluate'])
    return result


def query_error(run_id):
    return dict(run_id=str(run_id), eligible=False, train=None, evaluate=None, explain=None,
                evidence={}, reasons=[dict(stage='query', code='ERROR_DE_CONSULTA',
                                           message='Error de consulta de elegibilidad. Reintente.')])


class ComparisonEligibilityService:
    def __init__(self, assessments=None, scientific=None, transaction=None):
        self.assessments = assessments or AssessmentReadRepository()
        self.scientific = scientific or ScientificReadRepository()
        self.transaction = transaction or read_only_transaction

    def read(self, run_ids, datasource):
        results = {}
        try:
            with self.transaction(datasource, repeatable_read=True) as connection:
                for run_id in run_ids:
                    try:
                        with connection.begin_nested():
                            results[str(run_id)] = decision(run_id,
                                self.assessments.eligibility_training(connection, run_id),
                                self.scientific.comparison_checkpoint(connection, run_id),
                                self.assessments.eligibility_attempts(connection, run_id))
                    except SQLAlchemyError:
                        results[str(run_id)] = query_error(run_id)
        except SQLAlchemyError:
            return {str(run_id): query_error(run_id) for run_id in run_ids}
        return results

    def require(self, selections, datasource):
        results = self.read([s.training_run_id for s in selections], datasource)
        rejected = [r for r in results.values() if not r['eligible']]
        if rejected:
            technical = any(r['train'] is None for r in rejected)
            raise HTTPException(503 if technical else 422, detail={
                'code': 'ERROR_DE_CONSULTA' if technical else 'RUN_NOT_ELIGIBLE',
                'eligibility': rejected})
