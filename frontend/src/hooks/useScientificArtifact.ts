import { useCallback, useState } from 'react';
import { api } from '../services/api';
import { useAuthenticatedObjectUrl } from '../components/cell-review/AuthenticatedCellImage';
import type { XAIArtifact, XAIDatasetSample, XAIAvailability } from '../components/reports/xai/comparison';

export function artifactFailure(error: unknown): { availability: XAIAvailability; message: string } {
  const status = error && typeof error === 'object' && 'status' in error ? error.status : undefined;
  const code = error && typeof error === 'object' && 'code' in error ? error.code : undefined;
  const availability = status === 401 || status === 403 ? 'denied'
    : code === 'ARTIFACT_INTEGRITY_FAILED' ? 'integrity_failed'
    : code === 'ARTIFACT_CONTENT_MISSING' || code === 'ARTIFACT_NOT_REGISTERED' ? 'missing'
    : code === 'ARTIFACT_RELATION_MISMATCH' || code === 'ARTIFACT_DATASET_EVIDENCE_INVALID' ? 'not_comparable' : 'error';
  return { availability, message: error instanceof Error ? error.message : 'Error al recuperar el artefacto.' };
}

/** SCC-ART.1 client and object URL lifecycle; one owner supplies inline and modal. */
export function useScientificArtifact(artifact: XAIArtifact | XAIDatasetSample | undefined, datasource: string | undefined, enabled: boolean, imageOnly = true) {
  const artifactId = artifact && 'artifactId' in artifact ? artifact.artifactId : undefined;
  const sampleId = artifact?.source === 'dataset_sample' ? artifact.sampleId : undefined;
  const datasetVersionId = artifact?.source === 'dataset_sample' ? artifact.datasetVersionId : undefined;
  const source = artifact?.source ?? 'assessment';
  const attemptId = artifact?.attemptId;
  const trainingRunId = artifact?.trainingRunId;
  const key = JSON.stringify([source, artifactId, sampleId, datasetVersionId, attemptId, trainingRunId, datasource]);
  const [failure, setFailure] = useState<ReturnType<typeof artifactFailure> | null>(null);
  const [type, setType] = useState('');
  const load = useCallback(async (signal: AbortSignal) => {
    setFailure(null);
    setType('');
    try {
      const blob = source === 'dataset_sample'
        ? await api.getDatasetSampleBlob({trainingRunId: trainingRunId!, sampleId: sampleId!, datasetVersionId: datasetVersionId!, attemptId: attemptId!, datasource}, signal)
        : await api.getArtifactBlob(artifactId!, {source, attemptId, trainingRunId, datasource}, signal);
      if (imageOnly && !blob.type.startsWith('image/')) throw new Error('El artefacto no es una imagen compatible.');
      if (!signal.aborted) setType(blob.type);
      return blob;
    } catch (error: unknown) {
      if (!signal.aborted) setFailure(artifactFailure(error));
      throw error;
    }
  }, [artifactId, sampleId, datasetVersionId, source, attemptId, trainingRunId, datasource, imageOnly]);
  const content = useAuthenticatedObjectUrl(load, enabled && Boolean(artifactId || sampleId), key);
  return { ...content, type, failure: content.error ? failure : null,
    extension: type === 'image/jpeg' ? '.jpg' : type === 'image/webp' ? '.webp' : type === 'image/png' ? '.png' : type === 'application/json' ? '.json' : type.startsWith('text/csv') ? '.csv' : '.npy' };
}
export type XAIImageResource = ReturnType<typeof useScientificArtifact>;
