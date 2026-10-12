import { useState } from 'react';
import { useAssessmentArtifacts } from '../../hooks/useAssessmentArtifacts';
import { api } from '../../services/api';
import type { AssessmentArtifact, AssessmentDetail } from '../../types/api';
import { StatusBadge } from '../StatusBadge';

function ArtifactReference({artifact, datasource}: {artifact: AssessmentArtifact; datasource: string}) {
  const [failed, setFailed] = useState(false);
  const [preview, setPreview] = useState(false);
  return <figure>
    <figcaption>{artifact.role} · {artifact.artifact_id}</figcaption>
    <p>Referencia: {artifact.path}</p>
    <p>SHA-256 registrado: {artifact.sha256}</p>
    {artifact.role === 'overlay' && !preview ? <button onClick={() => setPreview(true)}>Ver imagen</button> : null}
    {preview && !failed ? <img alt={`EXPLAIN ${artifact.role}`} src={api.artifactUrl(artifact.path, {datasource}) ?? undefined} onError={() => setFailed(true)} /> : null}
    {failed ? <p role="alert">Error de artefacto: archivo ausente o no accesible. La ejecución permanece registrada.</p> : null}
  </figure>;
}

export function AssessmentExplanationDetail({data, datasource}: {data: AssessmentDetail; datasource: string}) {
  const [offset, setOffset] = useState(0);
  const {items, loading, error} = useAssessmentArtifacts(data.id, offset);
  return <article className="lineage-child-card">
    <h2>EXPLAIN · {data.identity.explanation?.method ?? 'Método no registrado'}</h2>
    <StatusBadge status={data.state} />
    <p>Intento: {data.id} · #{data.ordinal}</p>
    <p>Identidad: {data.identity_id}</p>
    <p>TRAIN: {data.training_run_id}</p>
    <p>Checkpoint: {data.identity.model.checkpoint_artifact_id}</p>
    <p>Evidencia: {data.state === 'verified' ? data.verification?.sha256 : 'Sin evidencia verificada'}</p>
    {loading ? <p role="status">Cargando referencias…</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {!loading && !error && !items.length ? <p>Este intento no tiene referencias de artefactos en esta página.</p> : null}
    {items.map(artifact => <ArtifactReference key={artifact.artifact_id} artifact={artifact} datasource={datasource} />)}
    <nav aria-label="Páginas de artefactos">
      <button disabled={loading || offset === 0} onClick={() => setOffset(Math.max(0, offset - 100))}>Anterior</button>
      <button disabled={loading || items.length < 100} onClick={() => setOffset(offset + 100)}>Siguiente</button>
    </nav>
  </article>;
}
