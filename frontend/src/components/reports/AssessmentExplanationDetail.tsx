import { useState } from 'react';
import { useAssessmentArtifacts } from '../../hooks/useAssessmentArtifacts';
import { ScientificArtifact } from './ScientificArtifact';
import type { AssessmentDetail } from '../../types/api';
import { StatusBadge } from '../StatusBadge';


export function AssessmentExplanationDetail({data, datasource}: {data: AssessmentDetail; datasource: string}) {
  const [offset, setOffset] = useState(0);
  const {items, loading, error} = useAssessmentArtifacts(data.id, offset);
  const explanation = data.identity.explanation;
  const method = explanation?.method === 'gradcam' ? 'Grad-CAM' : explanation?.method.toUpperCase() ?? 'Método no registrado';
  return <article className="lineage-child-card">
    <h2>EXPLAIN · {method}</h2>
    <StatusBadge status={data.state} />
    <p>Intento: {data.id} · #{data.ordinal}</p>
    <p>Identidad: {data.identity_id}</p>
    <p>TRAIN: {data.training_run_id}</p>
    <p>Checkpoint: {data.identity.model.checkpoint_artifact_id}</p>
    <p>Evidencia: {data.state === 'verified' ? data.verification?.sha256 : 'Sin evidencia verificada'}</p>
    {explanation?.method === 'shap' && <p>Referencia SHAP: {explanation.background?.map(sample => sample.sample_id).join(', ') || 'No registrada'}</p>}
    {loading ? <p role="status">Cargando referencias…</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {!loading && !error && !items.length ? <p>{offset === 0 ? 'Sin evidencia registrada para este intento.' : 'No hay más artefactos en esta página.'}</p> : null}
    {items.map(artifact => <section key={`${data.id}:${artifact.artifact_id}`}>
      <p>Muestra explicada: {artifact.sample_id ?? 'No registrada'}</p>
      <ScientificArtifact key={`${data.id}:${artifact.artifact_id}`} artifactId={artifact.artifact_id} source="assessment" attemptId={data.id} trainingRunId={data.training_run_id} datasource={datasource} label={`${method} · ${artifact.role}`} preview={artifact.role === 'overlay'} autoLoad={artifact.role === 'overlay'} />
    </section>)}
    <nav aria-label="Páginas de artefactos">
      <span>Página {offset / 100 + 1}</span>
      <button disabled={loading || offset === 0} onClick={() => setOffset(Math.max(0, offset - 100))}>Anterior</button>
      <button disabled={loading || items.length < 100} onClick={() => setOffset(offset + 100)}>Siguiente</button>
    </nav>
  </article>;
}
