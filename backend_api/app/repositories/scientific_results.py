"""Read the canonical v2 scientific records without legacy metric fallbacks."""
from typing import Any
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.engine import Connection



def metric_dto(row: dict[str, Any]) -> dict[str, Any]:
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


def read_run_configurations(connection: Connection, run_id: UUID) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(text(
        'SELECT * FROM run_configurations WHERE run_id=:run'
    ), {'run': run_id}).mappings()]


def read_scientific_results(connection: Connection, run_id: UUID) -> dict[str, Any] | None:
    params = {'run': run_id}
    run = connection.execute(text('SELECT id, parameters, release_status FROM runs WHERE id=:run'), params).mappings().one_or_none()
    if run is None:
        return None
    def rows(sql: str) -> list[dict[str, Any]]:
        return [dict(r) for r in connection.execute(text(sql), params).mappings()]

    evaluations = rows('SELECT * FROM evaluations WHERE run_id=:run ORDER BY created_at,id')
    metrics = rows('SELECT * FROM run_clinical_metrics WHERE run_id=:run ORDER BY created_at,run_clinical_metric_id')
    evidence_scope = 'SELECT id FROM xai_evidence WHERE run_id=:run'
    return dict(
        contract_version='scientific_results_v2', run_id=str(run_id), release_status=run['release_status'],
        run_configurations=read_run_configurations(connection, run_id),
        evaluations=evaluations,
        evaluation_ensemble_members=rows('SELECT m.* FROM evaluation_ensemble_members m JOIN evaluations e ON e.id=m.evaluation_id WHERE e.run_id=:run ORDER BY m.evaluation_id,m.ordinal'),
        run_clinical_metrics=[metric_dto(r) for r in metrics],
        training_history=rows('SELECT * FROM training_history WHERE run_id=:run ORDER BY phase,epoch'),
        xai_evidence=rows('SELECT * FROM xai_evidence WHERE run_id=:run ORDER BY generated_at,id'),
        xai_artifacts=rows(f'SELECT * FROM xai_artifacts WHERE evidence_id IN ({evidence_scope}) ORDER BY evidence_id,role,ordinal'),
        xai_quantitative_evaluations=rows(f'SELECT * FROM xai_quantitative_evaluations WHERE id IN (SELECT evaluation_id FROM xai_evaluation_members WHERE xai_evidence_id IN ({evidence_scope})) ORDER BY evaluated_at,id'),
        xai_interpretations=rows(f'SELECT * FROM xai_interpretations WHERE evidence_id IN ({evidence_scope}) ORDER BY created_at,id'),
        xai_specialist_reviews=rows(f'SELECT r.* FROM xai_specialist_reviews r JOIN xai_interpretations i ON i.id=r.interpretation_id WHERE i.evidence_id IN ({evidence_scope}) ORDER BY r.reviewed_at,r.id'),
    )


class ScientificReadRepository:
    def read(self, run_id: UUID, datasource: str | None, traceability: bool, prediction_limit: int = 100, prediction_offset: int = 0) -> dict[str, Any] | None:
        from app.db import read_only_transaction
        with read_only_transaction(datasource) as connection:
            result = read_scientific_results(connection, run_id)
            if result is None or not traceability:
                return result
            params = {'run': run_id, 'limit': prediction_limit, 'offset': prediction_offset}
            parent = connection.execute(text('''
                SELECT to_jsonb(r) AS training, to_jsonb(m) AS model
                FROM runs r LEFT JOIN models m ON m.id=r.model_id WHERE r.id=:run
            '''), params).mappings().one()
            result.update(parent)
            result['dataset_version'] = connection.execute(text(
                'SELECT to_jsonb(d) FROM dataset_versions d JOIN runs r ON r.dataset_version_id=d.id WHERE r.id=:run'
            ), params).scalar_one_or_none()
            result['model_versions'] = [dict(r) for r in connection.execute(text(
                'SELECT * FROM model_versions WHERE training_run_id=:run ORDER BY created_at,id'
            ), params).mappings()]
            for key, table, order in (
                ('checkpoint_policy', 'run_checkpoint_policy', 'created_at,run_checkpoint_policy_id'),
                ('metrics', 'run_metrics', 'created_at,id'),
                ('artifacts', 'artifacts', 'created_at,id'),
                ('io_records', 'run_io_records', 'created_at,run_io_id'),
            ):
                result[key] = [dict(r) for r in connection.execute(text(
                    f'SELECT * FROM {table} WHERE run_id=:run ORDER BY {order}'
                ), params).mappings()]
            result['predictions'] = {
                'items': [dict(r) for r in connection.execute(text("""
                    SELECT p.*, e.split AS split
                    FROM predictions p LEFT JOIN evaluations e ON e.id=p.evaluation_id
                    WHERE p.run_id=:run ORDER BY p.created_at,p.id LIMIT :limit OFFSET :offset
                """), params).mappings()],
                'total': connection.execute(text('SELECT count(*) FROM predictions WHERE run_id=:run'), params).scalar_one(),
                'limit': prediction_limit, 'offset': prediction_offset,
            }
            return result

    def preflight_training(self, connection: Connection, run_id: UUID) -> dict[str, Any] | None:
        """Small projection; no history series, predictions or XAI contents."""
        row = connection.execute(text("""
            SELECT r.id,r.run_type,r.dataset_version_id,r.model_id,
                   d.id IS NOT NULL AS dataset_registered
            FROM runs r LEFT JOIN dataset_versions d ON d.id=r.dataset_version_id
            WHERE r.id=:run
        """), {'run': run_id}).mappings().one_or_none()
        return dict(row) if row else None

    def preflight_configuration(self, connection: Connection, run_id: UUID) -> dict[str, Any] | None:
        # Same canonical configuration table used by read_scientific_results.
        rows = read_run_configurations(connection, run_id)
        return rows[0] if rows else None

    def preflight_history(self, connection: Connection, run_id: UUID) -> dict[str, Any]:
        return dict(connection.execute(text("""
            SELECT count(*) AS rows, count(DISTINCT (phase,epoch)) AS unique_epochs,
                   count(*) FILTER (WHERE phase IS NULL OR epoch IS NULL) AS unknown_axes
            FROM training_history WHERE run_id=:run
        """), {'run': run_id}).mappings().one())

    def evaluation(self, connection: Connection, evaluation_id: UUID) -> dict[str, Any] | None:
        row = connection.execute(text(
            'SELECT * FROM evaluations WHERE id=:id'
        ), {'id': evaluation_id}).mappings().one_or_none()
        return dict(row) if row else None
