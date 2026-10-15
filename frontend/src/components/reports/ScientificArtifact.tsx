import { useCallback, useState } from 'react';
import { api } from '../../services/api';
import { useAuthenticatedObjectUrl } from '../cell-review/AuthenticatedCellImage';

/** Shared authenticated, deferred access using the existing object URL lifecycle. */
export function ScientificArtifact({artifactId, source, attemptId, trainingRunId, datasource, label, preview = false, autoLoad = false}: {
  artifactId: string; source: 'assessment' | 'training'; attemptId?: string;
  trainingRunId?: string; datasource?: string; label: string; preview?: boolean; autoLoad?: boolean;
}) {
  const [requested, setRequested] = useState(false);
  const [type, setType] = useState('');
  const [errorMessage, setErrorMessage] = useState('Artefacto no disponible.');
  const load = useCallback(async (signal: AbortSignal) => {
    const blob = await api.getArtifactBlob(artifactId, {source, attemptId, trainingRunId, datasource}, signal).catch((error: unknown) => {
      if (!signal.aborted) setErrorMessage(error instanceof Error ? error.message : 'Artefacto no disponible.');
      throw error;
    });
    if (!signal.aborted) setType(blob.type);
    return blob;
  }, [artifactId, source, attemptId, trainingRunId, datasource]);
  const content = useAuthenticatedObjectUrl(load, requested || autoLoad, `${source}:${artifactId}:${attemptId}:${trainingRunId}:${datasource}`);
  const extension = type === 'image/png' ? '.png' : type === 'application/json' ? '.json'
    : type.startsWith('text/csv') ? '.csv' : type === 'image/jpeg' ? '.jpg' : type === 'image/webp' ? '.webp' : '.npy';
  return <figure>
    <figcaption>{label} · {artifactId}</figcaption>
    {!requested && !autoLoad && <button onClick={() => setRequested(true)}>{preview ? 'Ver imagen' : 'Preparar descarga'}</button>}
    {content.loading && <p role="status">Cargando artefacto…</p>}
    {content.error && <p role="alert">{errorMessage} La ejecución permanece registrada.</p>}
    {content.url && preview && type.startsWith('image/') && <img src={content.url} alt={label} />}
    {content.url && <a href={content.url} download={`${artifactId}${extension}`}>Descargar</a>}
  </figure>;
}
