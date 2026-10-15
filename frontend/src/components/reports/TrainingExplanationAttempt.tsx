import { useState } from 'react';
import { useAssessment } from '../../hooks/useAssessment';
import type { AssessmentExplanationChild } from '../../types/api';
import { AssessmentExplanationDetail } from './AssessmentExplanationDetail';
import { StatusBadge } from '../StatusBadge';

export function TrainingExplanationEvidence({attemptId, trainingRunId, datasource}: {
  attemptId: string; trainingRunId: string; datasource: string;
}) {
  const {data, loading, error} = useAssessment(attemptId);
  if (loading) return <p role="status">Cargando intento EXPLAIN…</p>;
  if (error || !data) return <p role="alert">{error ?? 'No fue posible recuperar el intento.'}</p>;
  if (data.kind !== 'explain' || data.training_run_id !== trainingRunId || data.id !== attemptId) {
    return <p role="alert">El intento EXPLAIN no corresponde al TRAIN solicitado.</p>;
  }
  return <AssessmentExplanationDetail key={data.id} data={data} datasource={datasource} />;
}

export function TrainingExplanationAttempt({assessment, datasource}: {
  assessment: AssessmentExplanationChild; datasource: string;
}) {
  const [expanded, setExpanded] = useState(false);
  return <article className="lineage-child-card">
    <strong>EXPLAIN · {assessment.method?.toUpperCase() ?? 'Método no registrado'}</strong>
    <StatusBadge status={assessment.state} />
    <p>Intento: {assessment.attempt_id}</p>
    <p>{assessment.result_count ?? 'Sin conteo de'} resultados registrados</p>
    <button type="button" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>
      {expanded ? 'Ocultar imágenes y artefactos' : 'Ver imágenes y artefactos'}
    </button>
    {expanded && <TrainingExplanationEvidence attemptId={assessment.attempt_id}
      trainingRunId={assessment.training_run_id} datasource={datasource} />}
  </article>;
}
