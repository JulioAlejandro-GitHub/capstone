"""Atomic external model ingestion through the common model/run/artifact repositories."""
from __future__ import annotations

import hashlib
from pathlib import Path
from sqlalchemy import text
from ..persistence import run_repository as runs
from ..persistence.database import get_connection, transaction_scope
from ..governance.repository import create_model_version


def verified_file(item: dict) -> dict:
    from ..execution.storage_paths import local_scientific_path
    path = local_scientific_path(Path(item['path']).expanduser())
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError(f'Symlink artifact is not allowed: {path}')
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError(f'Not a regular file: {path}')
    with path.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    size = path.stat().st_size
    if checksum != item['sha256'] or size != item['bytes']:
        raise ValueError(f'Artifact identity mismatch: {path}')
    return {**item, 'path': str(path), 'sha256': checksum, 'bytes': size}


def resolve_dependencies(profile: dict, artifacts: list[dict], path_resolver) -> dict:
    """Bind frozen dependency evidence to registered roles, never to cached paths."""
    from collections import Counter
    expected = profile.get('dependencies') or []
    roles = [item['role'] for item in expected]
    if not roles or any(count != 1 for count in Counter(roles).values()):
        raise ValueError('Missing or duplicate dependency roles')
    resolved = []
    for frozen in expected:
        matches = [a for a in artifacts if a['role'] == frozen['role']]
        if len(matches) != 1:
            raise ValueError('Dependency role is absent or ambiguous: ' + frozen['role'])
        artifact = matches[0]
        if (artifact['status'] != 'available' or artifact['sha256'] != frozen['sha256']
                or artifact['bytes'] != frozen['bytes']
                or (frozen.get('artifact_id') and frozen['artifact_id'] != artifact['artifact_id'])):
            raise ValueError('Registered dependency conflicts with frozen evidence')
        resolved.append(verified_file({**frozen, 'artifact_id': artifact['artifact_id'],
                                      'path': str(path_resolver(artifact['path']))}))
    return {**profile, 'dependencies': resolved}


def preprocessing_identity(profile: dict) -> dict:
    """Physical locations can differ; the frozen transform and bytes cannot."""
    return {**profile, **({'dependencies': [
        {key: item[key] for key in ('role', 'sha256', 'bytes')}
        for item in profile['dependencies']]} if 'dependencies' in profile else {})}


def register_external_model(spec: dict) -> dict:
    """Repeat an identical registration safely; conflicting scientific evidence is rejected."""
    metadata = spec['metadata']
    if metadata.get('training_mode') != 'logical':
        raise ValueError('External ingestion requires models.metadata.training_mode=logical')
    if metadata.get('scientific_origin', {}).get('kind') != 'pretrained_external':
        raise ValueError('External scientific origin is required')
    files = [verified_file(item) for item in spec['files']]
    checkpoints = [item for item in files if item['role'] == 'checkpoint']
    if len(checkpoints) != 1:
        raise ValueError('Exactly one checkpoint must be selected')
    checkpoint = checkpoints[0]
    roles = [item['role'] for item in files]
    if len(set(roles)) != len(roles):
        raise ValueError('Duplicate artifact roles')
    with get_connection() as connection, transaction_scope(connection):
        connection.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
                           {'key': 'model-registration:' + spec['name']})
        model_id = runs.get_or_create_model(
            name=spec['name'], model_type=spec['model_type'], framework=spec['framework'],
            architecture=spec['architecture'], pretrained=True,
            pretrained_source=metadata['scientific_origin']['repo_id'], metadata=metadata)
        if not model_id:
            raise RuntimeError('Model registration failed')
        model = connection.execute(text('SELECT * FROM models WHERE id=:id'), {'id': model_id}).mappings().one()
        if any(model[key] != spec[key] for key in ('framework', 'model_type', 'architecture')) or model['metadata'] != metadata:
            raise ValueError('Existing model has conflicting metadata; explicit reconciliation required')
        versions = connection.execute(text('''SELECT mv.*,r.status AS run_status FROM model_versions mv
            JOIN runs r ON r.id=mv.training_run_id WHERE mv.model_id=:model AND artifact_sha256=:sha'''),
            {'model': model_id, 'sha': checkpoint['sha256']}).mappings().all()
        if len(versions) > 1:
            raise ValueError('Ambiguous existing checkpoint versions')
        if versions:
            version = versions[0]
            if (version['run_status'] != 'completed' or version['framework'] != spec['framework']
                    or preprocessing_identity(version['preprocessing_profile_snapshot']) != preprocessing_identity(spec['preprocessing'])
                    or version['input_signature'] != spec['input_signature']
                    or version['output_signature'] != spec['output_signature']
                    or version['class_mapping'] != spec['class_mapping']):
                raise ValueError('Existing version conflicts with ingestion evidence')
            registered = connection.execute(text(
                'SELECT artifact_type,path,checksum,file_size_bytes,artifact_status,metadata FROM artifacts WHERE run_id=:id'),
                {'id': version['training_run_id']}).mappings().all()
            expected = {(item['role'], item['sha256'], item['bytes']) for item in files}
            actual = {(item['metadata'].get('role'), item['checksum'], item['file_size_bytes'])
                      for item in registered if item['artifact_status'] == 'available'}
            if expected != actual or len(registered) != len(files):
                raise ValueError('Existing registered artifacts conflict with ingestion evidence')
            for item in registered:
                verified_file({'path': item['path'], 'sha256': item['checksum'],
                               'bytes': item['file_size_bytes']})
            return dict(model_id=model_id, run_id=str(version['training_run_id']),
                        artifact_id=str(version['checkpoint_artifact_id']), version_id=str(version['id']), idempotent=True)
        partial = connection.execute(text('SELECT id FROM runs WHERE model_id=:id'), {'id': model_id}).first()
        if partial:
            raise ValueError('Existing run without matching version requires explicit reconciliation')
        origin = {'training_performed': False, 'scientific_origin': metadata['scientific_origin']}
        run_id = runs.start_run(model_id=model_id, run_name=spec['name'] + ' external ingestion',
            run_type='training', total_epochs=0, completed_epochs=0, metadata=origin,
            execution_type='local_python', execution_parameters=origin)
        if not run_id:
            raise RuntimeError('Logical TRAIN creation failed')
        from ..execution.storage_paths import incorporate_training_files
        files = incorporate_training_files(run_id, files)
        checkpoint = next(item for item in files if item['role'] == 'checkpoint')
        artifact_id = None
        dependencies = []
        for item in files:
            identifier = runs.log_artifact(run_id, 'model_checkpoint' if item['role']=='checkpoint' else 'model_dependency',
                item['path'], name=Path(item['path']).name, checksum=item['sha256'], file_size_bytes=item['bytes'],
                metadata={'role': item['role'], 'format': Path(item['path']).suffix, **origin})
            if not identifier:
                raise RuntimeError('Artifact registration failed')
            dependencies.append({**item, 'artifact_id': identifier})
            if item['role'] == 'checkpoint':
                artifact_id = identifier
        preprocessing = dict(spec['preprocessing'])
        if 'dependencies' in preprocessing:
            by_role = {item['role']: item for item in dependencies}
            preprocessing['dependencies'] = [by_role[item['role']] for item in preprocessing['dependencies']]
        number = connection.execute(text('SELECT COALESCE(MAX(version_number),0)+1 FROM model_versions WHERE model_id=:id'), {'id':model_id}).scalar_one()
        version = create_model_version(training_run_id=run_id, model_name=spec['name'], version_number=number,
            checkpoint_artifact_id=artifact_id, artifact_path=checkpoint['path'], artifact_sha256=checkpoint['sha256'],
            artifact_size_bytes=checkpoint['bytes'], framework=spec['framework'],
            preprocessing_profile_snapshot=preprocessing, class_mapping=spec['class_mapping'],
            input_signature=spec['input_signature'], output_signature=spec['output_signature'],
            status='candidate', metadata={**origin, 'dependencies':dependencies, 'architecture':spec['architecture']},
            connection_or_session=connection)
        if not runs.finish_run(run_id, completed_epochs=0, metadata=origin):
            raise RuntimeError('Logical TRAIN completion failed')
        return dict(model_id=model_id, run_id=run_id, artifact_id=artifact_id, version_id=str(version.id), idempotent=False)


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    print(json.dumps(register_external_model(json.loads(args.manifest.read_text())), indent=2))


if __name__ == '__main__':
    main()
