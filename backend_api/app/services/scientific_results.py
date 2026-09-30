"""Read the canonical v2 scientific records without legacy metric fallbacks."""
from sqlalchemy import text

from src.malaria_dl.execution.schema import require_e10_schema, V2_REVISION


def metric_dto(row):
    values = dict(row)
    aliases = {'recall': 'recall_parasitized', 'specificity': 'specificity',
               'precision': 'precision_parasitized', 'f1': 'f1_parasitized',
               'f2': 'f2_parasitized', 'roc_auc': 'roc_auc_parasitized',
               'pr_auc': 'pr_auc_parasitized', 'balanced_accuracy': 'balanced_accuracy',
               'accuracy': 'accuracy'}
    return dict(values, metrics={
        name: {'value': values[column], 'undefined_reason': (
            values['auc_unavailability_reason'] if name in ('roc_auc', 'pr_auc')
            else 'zero_denominator') if values[column] is None else None}
        for name, column in aliases.items()
    }, confusion_matrix_orientation={'rows': ['uninfected', 'parasitized'],
                                      'columns': ['uninfected', 'parasitized']})


def read_scientific_results(connection, run_id):
    revision = require_e10_schema(connection)['revision']
    params = {'run': run_id}
    run = connection.execute(text('SELECT id, parameters, release_status FROM runs WHERE id=:run'), params).mappings().one_or_none()
    if run is None:
        return None
    if revision != V2_REVISION:
        return {'contract_version': 'legacy_e10_v1', 'run_id': str(run_id),
                'historical_result': run['parameters'].get('training_results'),
                'release_status': run['release_status']}

    def rows(sql):
        return [dict(r) for r in connection.execute(text(sql), params).mappings()]

    evaluations = rows('SELECT * FROM evaluations WHERE run_id=:run ORDER BY created_at,id')
    metrics = rows('SELECT * FROM run_clinical_metrics WHERE run_id=:run ORDER BY created_at,run_clinical_metric_id')
    evidence_scope = 'SELECT id FROM xai_evidence WHERE run_id=:run'
    return dict(
        contract_version='scientific_results_v2', run_id=str(run_id), release_status=run['release_status'],
        run_configurations=rows('SELECT * FROM run_configurations WHERE run_id=:run'),
        evaluations=evaluations,
        evaluation_ensemble_members=rows('SELECT m.* FROM evaluation_ensemble_members m JOIN evaluations e ON e.id=m.evaluation_id WHERE e.run_id=:run ORDER BY m.evaluation_id,m.ordinal'),
        run_clinical_metrics=[metric_dto(r) for r in metrics],
        training_history=rows('SELECT * FROM training_history WHERE run_id=:run ORDER BY phase,epoch'),
        xai_evidence=rows('SELECT * FROM xai_evidence WHERE run_id=:run ORDER BY generated_at,id'),
        xai_artifacts=rows(f'SELECT * FROM xai_artifacts WHERE evidence_id IN ({evidence_scope}) ORDER BY evidence_id,role,ordinal'),
        xai_quantitative_evaluations=rows(f'SELECT * FROM xai_quantitative_evaluations WHERE evidence_id IN ({evidence_scope}) ORDER BY evaluated_at,id'),
        xai_interpretations=rows(f'SELECT * FROM xai_interpretations WHERE evidence_id IN ({evidence_scope}) ORDER BY created_at,id'),
        xai_specialist_reviews=rows(f'SELECT r.* FROM xai_specialist_reviews r JOIN xai_interpretations i ON i.id=r.interpretation_id WHERE i.evidence_id IN ({evidence_scope}) ORDER BY r.reviewed_at,r.id'),
    )
