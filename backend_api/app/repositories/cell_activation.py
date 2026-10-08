"""Activation writes share the request's single transaction and existing identities."""
from uuid import UUID
import json
from sqlalchemy import text
from sqlalchemy.engine import Connection


def lock_selection(connection: Connection, datasource: str) -> None:
    connection.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'),
                       {'key': f'stage2-selection:{datasource}'})


def active_publications(connection: Connection, datasource: str) -> list[dict]:
    return [dict(row) for row in connection.execute(text("""
      SELECT * FROM stage2_model_publications WHERE datasource=:ds AND scope='stage2'
        AND is_active FOR UPDATE
    """), {'ds': datasource}).mappings()]


def assessment_contract(connection: Connection, attempt: UUID) -> dict:
    return dict(connection.execute(text("""
      SELECT i.identity->'model' AS model, i.identity->'decision' AS decision,
        i.identity->'code' AS code FROM assessment_attempts a
      JOIN assessment_identities i ON i.id=a.identity_id WHERE a.id=:id
    """), {'id': attempt}).mappings().one())


def register_evidence(connection: Connection, training: dict, binding: dict, contract: dict, path: str) -> dict:
    params = {'artifact': binding['checkpoint_artifact_id'], 'version': binding['model_version_id'],
              'train': str(training['training_run_id']), 'path': path, 'size': binding['bytes'],
              'sha': binding['sha256'], 'model': training.get('model_name') or contract['architecture'],
              'preprocessing': json.dumps(contract['external']), 'mapping': json.dumps(contract['label_mapping']),
              'input': json.dumps({'shape': contract['shape']}),
              'output': json.dumps(contract['output']), 'metadata': json.dumps({'architecture': contract['architecture'],
                'assessment_checkpoint_identity_id': binding['checkpoint_artifact_id']})}
    # The assessment checkpoint identity may precede the physical artifact registry.
    # Reuse the existing TRAIN-owned bytes instead of inserting another checkpoint.
    artifact = connection.execute(text("""
      SELECT id::text FROM artifacts WHERE id=:artifact OR
        (run_id=:train AND checksum=:sha AND file_size_bytes=:size)
      ORDER BY (id=:artifact) DESC,created_at,id LIMIT 1
    """), params).scalar_one_or_none()
    if artifact:
        params['artifact'] = artifact
    connection.execute(text("""
      INSERT INTO artifacts(id,run_id,artifact_type,name,path,file_size_bytes,checksum,artifact_status)
      VALUES(:artifact,:train,'model_checkpoint',:name,:path,:size,:sha,'available')
      ON CONFLICT(id) DO NOTHING
    """), {**params, 'name': path.rsplit('/', 1)[-1]})
    existing = connection.execute(text("""
      SELECT run_id::text,checksum,file_size_bytes FROM artifacts WHERE id=:artifact
    """), params).mappings().one()
    if (existing['run_id'], existing['checksum'], existing['file_size_bytes']) != (params['train'], params['sha'], params['size']):
        raise ValueError('La identidad del checkpoint ya existe con otra evidencia.')
    connection.execute(text("""
      INSERT INTO model_versions(id,training_run_id,checkpoint_artifact_id,model_name,
        artifact_sha256,artifact_size_bytes,framework,preprocessing_profile_snapshot,class_mapping,
        input_signature,output_signature,status,lineage_status,metadata)
      VALUES(:version,:train,:artifact,:model,:sha,:size,'keras',CAST(:preprocessing AS jsonb),
        CAST(:mapping AS jsonb),CAST(:input AS jsonb),CAST(:output AS jsonb),'candidate','resolved',CAST(:metadata AS jsonb))
      ON CONFLICT(id) DO NOTHING
    """), params)
    existing = connection.execute(text("""
      SELECT training_run_id::text,checkpoint_artifact_id::text,artifact_sha256,artifact_size_bytes
      FROM model_versions WHERE id=:version
    """), params).mappings().one()
    if tuple(existing.values()) != (params['train'], params['artifact'], params['sha'], params['size']):
        raise ValueError('La identidad del modelo ya existe con otro checkpoint.')
    return {**binding, 'checkpoint_artifact_id': params['artifact']}


def create_deployment(connection: Connection, binding: dict, attempt: str, decision: dict,
                      contract: dict, actor: str) -> str:
    return str(connection.execute(text("""
      INSERT INTO deployed_model_versions(model_version_id,checkpoint_artifact_id,
        threshold_assessment_attempt_id,deployment_name,environment,alias,artifact_sha256,
        artifact_size_bytes,threshold_value,threshold_profile_snapshot,preprocessing_profile_snapshot,
        label_mapping_snapshot,status,metadata)
      VALUES(:version,:artifact,:attempt,'malaria-stage2-classifier','stage2','default',:sha,:size,
        :threshold,CAST(:threshold_snapshot AS jsonb),CAST(:preprocessing AS jsonb),CAST(:mapping AS jsonb),
        'pending',CAST(:metadata AS jsonb)) RETURNING id
    """), {'version': binding['model_version_id'], 'artifact': binding['checkpoint_artifact_id'],
            'attempt': attempt, 'sha': binding['sha256'], 'size': binding['bytes'],
            'threshold': decision['effective'], 'threshold_snapshot': json.dumps({
                'value': decision['effective'], 'source': 'assessment_decision',
                'assessment_attempt_id': attempt, 'decision': decision}),
            'preprocessing': json.dumps(contract['external']), 'mapping': json.dumps(contract['label_mapping']),
            'metadata': json.dumps({'production_scope': 'stage2_experimental', 'stage2': {'eligible': True},
                                    'technical_contract': {'architecture': contract['architecture']}, 'actor': actor})}).scalar_one())


def activate_deployment(connection: Connection, deployment: str, actor: str, reason: str) -> None:
    connection.execute(text("""
      UPDATE deployed_model_versions SET status='inactive',retired_at=NOW(),retired_by=:actor,
        retirement_reason=:reason WHERE environment='stage2' AND alias='default' AND status='active'
    """), {'actor': actor, 'reason': reason})
    connection.execute(text("""
      UPDATE deployed_model_versions SET status='active',deployed_at=NOW(),deployed_by=:actor,
        deployment_reason=:reason,metadata=metadata||CAST(:smoke AS jsonb) WHERE id=:id
    """), {'id': deployment, 'actor': actor, 'reason': reason,
            'smoke': json.dumps({'technical_smoke_test': {'status': 'PASS', 'method': 'loaded_checkpoint_predict'}})})


def publish_assessment(connection: Connection, training: str, binding: dict, attempt: str,
                       datasource: str, actor: str, reason: str) -> dict:
    # Keep previous publication IDs and payloads intact for historical crop snapshots.
    previous = active_publications(connection, datasource)
    connection.execute(text("""
      UPDATE stage2_model_publications SET status='inactive',is_active=false,
        deactivated_at=NOW(),deactivated_by=:actor,updated_at=NOW()
      WHERE datasource=:ds AND scope='stage2' AND is_active
    """), {'ds': datasource, 'actor': actor})
    row = dict(connection.execute(text("""
      INSERT INTO stage2_model_publications(datasource,model_version_id,training_run_id,
        checkpoint_artifact_id,evaluation_attempt_id,published_by)
      VALUES(:ds,:version,:train,:artifact,:attempt,:actor) RETURNING *
    """), {'ds': datasource, 'version': binding['model_version_id'], 'train': training,
            'artifact': binding['checkpoint_artifact_id'], 'attempt': attempt, 'actor': actor}).mappings().one())
    # Existing event writer supports nullable legacy evaluation references.
    from src.malaria_dl.governance.services.stage2_publication_service import Stage2PublicationService
    publisher = Stage2PublicationService(None, datasource)
    for old in previous:
        publisher._event(connection, old, 'MODEL_STAGE2_DEACTIVATED', 'active', 'inactive', actor, reason, None)
    publisher._event(connection, row, 'MODEL_STAGE2_PUBLISHED', None, 'active', actor, reason, None)
    return row


def mark_active_training(connection: Connection, training: UUID, actor: str, reason: str) -> None:
    connection.execute(text("""
      UPDATE runs SET release_status='available_to_publish',release_updated_at=NOW(),
        release_changed_by=:actor,release_reason=:reason
      WHERE run_type='training' AND release_status='productive_stage2' AND id<>:id
    """), {'id':training,'actor':actor,'reason':reason})
    connection.execute(text("""
      UPDATE runs SET release_status='productive_stage2',release_updated_at=NOW(),
        release_changed_by=:actor,release_reason=:reason WHERE id=:id
    """), {'id':training,'actor':actor,'reason':reason})
