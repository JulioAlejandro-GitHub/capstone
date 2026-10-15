"""Deliver one original image with governed lineage, confinement and SHA-256."""
from dataclasses import replace
from uuid import UUID

from app.config import get_settings
from app.repositories.dataset_samples import DatasetSampleReadRepository
from app.services.artifacts import ServedArtifact, artifact_error, validate_served_artifact
from app.services.local_storage import (LocalStorage, StorageContentMissingError,
    StorageChecksumMismatchError, StorageSizeMismatchError, StorageError, verify_regular_file)
from src.malaria_dl.data.dataset_integrity import materialized_relative_path
from src.malaria_dl.data.governed_dataset import GovernedDatasetError, assert_run_dataset_snapshot_unchanged


def original_sample_image(
    repository: DatasetSampleReadRepository, datasource: str | None,
    training_run_id: str | None, sample_id: str | None, attempt_id: str | None,
    dataset_version_id: str | None,
) -> ServedArtifact:
    try:
        train, sample, attempt, dataset = (str(UUID(value or '')) for value in
                                           (training_run_id, sample_id, attempt_id, dataset_version_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise artifact_error(400, 'ARTIFACT_ID_INVALID') from exc
    context = repository.explanation_context(datasource, train, attempt, sample)
    if context is None:
        raise artifact_error(404, 'ARTIFACT_RELATION_MISMATCH')
    identity = context['identity']
    split = identity.get('split')
    if split not in ('train', 'val', 'test') or identity.get('dataset', {}).get('dataset_version_id') != dataset:
        raise artifact_error(404, 'ARTIFACT_RELATION_MISMATCH')
    try:
        snapshot = repository.training_dataset(datasource, train)
        if str(snapshot.dataset_version_id) != dataset:
            raise artifact_error(404, 'ARTIFACT_RELATION_MISMATCH')
        assert_run_dataset_snapshot_unchanged(snapshot, identity['dataset'])
        reference = repository.sample_reference(datasource, dataset, split, sample)
        if reference is None:
            raise artifact_error(404, 'ARTIFACT_RELATION_MISMATCH')
        row, collisions = reference
        relative = materialized_relative_path(row, collisions)
        storage = LocalStorage(replace(get_settings(), storage_root=snapshot.dataset_root))
        path = storage.resolve(relative.as_posix(), must_exist=True)
        verify_regular_file(path, expected_size_bytes=path.stat().st_size,
                            expected_sha256=row['source_file_sha256'])
        image = validate_served_artifact(path)
        return replace(image, headers={
            'X-Training-Run-Id': train, 'X-Dataset-Version-Id': dataset,
            'X-Sample-Id': sample, 'X-Assessment-Identity-Id': str(context['identity_id']),
            'X-Attempt-Id': attempt, 'X-Content-SHA256': row['source_file_sha256'],
        })
    except StorageContentMissingError as exc:
        raise artifact_error(410, 'ARTIFACT_CONTENT_MISSING') from exc
    except (StorageChecksumMismatchError, StorageSizeMismatchError) as exc:
        raise artifact_error(409, 'ARTIFACT_INTEGRITY_FAILED') from exc
    except StorageError as exc:
        raise artifact_error(409, 'ARTIFACT_LOCATION_INVALID') from exc
    except GovernedDatasetError as exc:
        # Never publish resolver diagnostics containing physical locations.
        raise artifact_error(409, 'ARTIFACT_DATASET_EVIDENCE_INVALID') from exc
    except OSError as exc:
        raise artifact_error(503, 'ARTIFACT_STORAGE_UNAVAILABLE') from exc
