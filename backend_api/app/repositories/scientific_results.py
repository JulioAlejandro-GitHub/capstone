"""Read the canonical v2 scientific records without legacy metric fallbacks."""
import json
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
                   d.id IS NOT NULL AS dataset_registered,
                   jsonb_build_object('name',d.name,'status',d.status,'grouping_strategy',d.grouping_strategy,'split_algorithm',d.split_algorithm,'random_seed',d.random_seed,'source_record_count',d.source_record_count) AS dataset
            FROM runs r LEFT JOIN dataset_versions d ON d.id=r.dataset_version_id
            WHERE r.id=:run
        """), {'run': run_id}).mappings().one_or_none()
        return dict(row) if row else None

    def preflight_configuration(self, connection: Connection, run_id: UUID) -> dict[str, Any] | None:
        # Same canonical configuration table used by read_scientific_results.
        rows = read_run_configurations(connection, run_id)
        if rows:
            return rows[0]
        parameters = connection.execute(text('SELECT execution_parameters FROM runs WHERE id=:run'), {'run': run_id}).scalar_one_or_none() or {}
        resolved = ((parameters.get('model_configuration_e2') or {}).get('configuration') or {}).get('resolved') or {}
        if not resolved:
            return None
        execution, model, optimizer = (resolved.get(k) or {} for k in ('execution', 'model', 'optimizer'))
        return dict(execution, architecture=(resolved.get('input_contract') or {}).get('architecture'),
                    random_seed=execution.get('seed'), optimizer=optimizer.get('name'),
                    learning_rate=(optimizer.get('parameters') or {}).get('learning_rate'),
                    normalization=model.get('preprocessing'), dropout=model.get('dropout'), l2=model.get('l2'),
                    loss_function=(resolved.get('recipe') or {}).get('loss'), extension_configuration=resolved)

    def preflight_history(self, connection: Connection, run_id: UUID) -> dict[str, Any]:
        return dict(connection.execute(text("""
            SELECT count(*) AS rows, count(DISTINCT (phase,payload->>'epoch')) AS unique_epochs,
                   count(*) FILTER (WHERE phase IS NULL OR payload->>'epoch' IS NULL) AS unknown_axes
            FROM train_execution_records WHERE run_id=:run AND kind='epoch'
        """), {'run': run_id}).mappings().one())

    def evaluation(self, connection: Connection, evaluation_id: UUID) -> dict[str, Any] | None:
        row = connection.execute(text(
            'SELECT * FROM evaluations WHERE id=:id'
        ), {'id': evaluation_id}).mappings().one_or_none()
        return dict(row) if row else None

    def comparison_catalog(self, connection, run_id):
        """Historical evaluations and independent attempts, without inventing attempts."""
        params = {'run': run_id}
        return [dict(r) for r in connection.execute(text("""
            SELECT e.id AS evaluation_id, e.training_run_id, e.checkpoint_artifact_id,
                   e.split, e.evaluation_role, e.purpose, e.source_assessment_attempt_id AS attempt_id,
                   a.identity_id, e.created_at
            FROM evaluations e LEFT JOIN assessment_attempts a ON a.id=e.source_assessment_attempt_id
            WHERE e.training_run_id=:run
            UNION ALL
            SELECT NULL, i.training_run_id,
                   NULLIF(i.identity#>>'{model,checkpoint_artifact_id}', '')::uuid,
                   i.identity->>'split', 'independent_evaluate', i.identity->>'purpose',
                   a.id, i.id, a.started_at
            FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id=i.id
            WHERE i.training_run_id=:run AND i.kind='evaluate'
              AND NOT EXISTS (SELECT 1 FROM evaluations e WHERE e.source_assessment_attempt_id=a.id)
            ORDER BY created_at DESC NULLS LAST, evaluation_id, attempt_id
        """), params).mappings()]

    def comparison_governance(self, connection, run_id):
        params = {'run': run_id}
        row = connection.execute(text("""
            SELECT d.id,d.name,d.status,d.grouping_strategy,d.split_algorithm,d.random_seed,
                   d.source_record_count, c.id AS campaign_id,c.dataset_version_id AS campaign_dataset_version_id,
                   c.dataset_snapshot - 'dataset_root' AS campaign_snapshot,
                   m.id AS materialization_id,m.status AS materialization_status,
                   m.reconciliation_status,m.record_count,
                   m.dataset_version_id=d.id AS materialization_dataset_matches
            FROM runs r LEFT JOIN dataset_versions d ON d.id=r.dataset_version_id
            LEFT JOIN experimental_campaigns c ON c.id=r.campaign_id
            LEFT JOIN dataset_materializations m ON m.id::text=c.dataset_snapshot->>'dataset_materialization_id'
            WHERE r.id=:run
        """), params).mappings().one_or_none()
        if not row:
            return None
        result = dict(row)
        result['counts'] = dict(connection.execute(text("""
            SELECT split_name,count(*) FROM dataset_split_assignments
            WHERE dataset_version_id=(SELECT dataset_version_id FROM runs WHERE id=:run)
            GROUP BY split_name
        """), params).all())
        result['checks'] = [dict(r) for r in connection.execute(text("""
            SELECT check_name,status,observed_value,expected_value FROM dataset_split_validation_checks
            WHERE dataset_version_id=(SELECT dataset_version_id FROM runs WHERE id=:run)
            ORDER BY check_name
        """), params).mappings()]
        result['consumed_images'] = connection.execute(text(
            'SELECT count(*) FROM run_dataset_images WHERE run_id=:run'), params).scalar_one()
        return result

    def comparison_epochs(self, connection, run_id):
        return [dict(r) for r in connection.execute(text("""
            SELECT phase,record_key,payload,event_id FROM train_execution_records
            WHERE run_id=:run AND kind='epoch' ORDER BY event_sequence,created_at,record_key
        """), {'run': run_id}).mappings()]

    def comparison_checkpoint(self, connection, run_id):
        row = connection.execute(text("""
            SELECT a.id,a.run_id,a.checksum,a.metadata,a.path,a.file_size_bytes,
                   s.payload - 'checkpoint_path' - 'selected_record' AS selection
            FROM runs r
            LEFT JOIN artifacts a ON a.id::text=r.execution_parameters#>>'{e10_v2_evaluation_context_v1,checkpoint_artifact_id}'
                AND a.artifact_type='model_checkpoint'
            LEFT JOIN LATERAL (
                SELECT payload FROM train_execution_records WHERE run_id=r.id AND kind='selection'
                ORDER BY event_sequence DESC NULLS LAST,created_at DESC,record_key DESC LIMIT 1
            ) s ON true WHERE r.id=:run
        """), {'run': run_id}).mappings().one_or_none()
        return dict(row) if row else None

    def comparison_metrics(self, connection, evaluation_id):
        return [dict(r) for r in connection.execute(text(
            'SELECT * FROM run_clinical_metrics WHERE evaluation_id=:id ORDER BY created_at,run_clinical_metric_id'
        ), {'id': evaluation_id}).mappings()]

    def comparison_predictions(self, connection, run_id, epoch, phase):
        return list(connection.execute(text("""
            SELECT payload FROM train_execution_records WHERE run_id=:run AND kind='predictions'
                AND payload->>'epoch'=:epoch AND payload->>'role'='val'
                AND phase IS NOT DISTINCT FROM :phase ORDER BY record_key
        """), {'run': run_id, 'epoch': str(epoch), 'phase': phase}).scalars())

    def comparison_representation(self, connection, run_id, source_attempt_id, specification):
        """Latest verified REPRESENT of exactly this EVALUATE model, population and decision; never computes one."""
        row = connection.execute(text("""
            SELECT a.id AS attempt_id,a.identity_id,a.verification,a.artifact_root,a.finished_at,
                   i.identity->>'split' AS split,jsonb_array_length(i.identity->'samples') AS sample_count
            FROM assessment_attempts sa JOIN assessment_identities si ON si.id=sa.identity_id
            JOIN assessment_identities i ON i.training_run_id=si.training_run_id AND i.kind='represent'
            JOIN assessment_attempts a ON a.identity_id=i.id AND a.state='verified'
            WHERE sa.id=:source AND sa.state='verified' AND si.kind='evaluate' AND si.training_run_id=:run
              AND i.identity->'samples'=si.identity->'samples' AND i.identity->'decision'=si.identity->'decision'
              AND i.identity->>'split'=si.identity->>'split' AND i.identity->>'purpose'=si.identity->>'purpose'
              AND i.identity#>'{model,checkpoint_artifact_id}'=si.identity#>'{model,checkpoint_artifact_id}'
              AND i.identity#>'{model,sha256}'=si.identity#>'{model,sha256}'
              AND i.identity#>'{dataset,dataset_version_id}'=si.identity#>'{dataset,dataset_version_id}'
              AND i.identity->'representation'=CAST(:spec AS jsonb)
            ORDER BY a.finished_at DESC,a.id LIMIT 1
        """), {'run': run_id, 'source': source_attempt_id, 'spec': json.dumps(specification)}).mappings().one_or_none()
        return dict(row) if row else None

    def comparison_representation_rows(self, connection, attempt_id):
        return list(connection.execute(text("""
            SELECT payload FROM assessment_results WHERE attempt_id=:id ORDER BY (payload#>>'{result,row}')::int
        """), {'id': attempt_id}).scalars())

    def comparison_representation_artifacts(self, connection, attempt_id):
        return list(connection.execute(text(
            'SELECT payload FROM assessment_artifacts WHERE attempt_id=:id ORDER BY role'), {'id': attempt_id}).scalars())
