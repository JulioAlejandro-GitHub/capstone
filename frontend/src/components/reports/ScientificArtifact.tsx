import { useState } from 'react';
import { useScientificArtifact } from '../../hooks/useScientificArtifact';

/** Shared authenticated, deferred access using the existing object URL lifecycle. */
export function ScientificArtifact({artifactId, source, attemptId, trainingRunId, datasource, label, preview = false, autoLoad = false}: {
  artifactId: string; source: 'assessment' | 'training'; attemptId?: string;
  trainingRunId?: string; datasource?: string; label: string; preview?: boolean; autoLoad?: boolean;
}) {
  const [requested, setRequested] = useState(false);
  const content = useScientificArtifact({artifactId, source, attemptId, trainingRunId}, datasource, requested || autoLoad, false);
  const {type, extension} = content;
  const errorMessage = content.failure?.message ?? 'Artefacto no disponible.';
  return <figure>
    <figcaption>{label} · {artifactId}</figcaption>
    {!requested && !autoLoad && <button onClick={() => setRequested(true)}>{preview ? 'Ver imagen' : 'Preparar descarga'}</button>}
    {content.loading && <p role="status">Cargando artefacto…</p>}
    {content.error && <p role="alert">{errorMessage} La ejecución permanece registrada.</p>}
    {content.url && preview && type.startsWith('image/') && <img src={content.url} alt={label} />}
    {content.url && <a href={content.url} download={`${artifactId}${extension}`}>Descargar</a>}
  </figure>;
}
