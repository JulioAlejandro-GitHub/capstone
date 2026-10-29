import { Link } from 'react-router-dom';
import { routes, withAllowedQuery } from '../../router';
import type { AssessmentExplanationChild } from '../../types/api';
import { StatusBadge } from '../StatusBadge';

export function AssessmentExplanationCard({assessment, datasource}: {
  assessment: AssessmentExplanationChild; datasource: string;
}) {
  return <article className="lineage-child-card lineage-child-card--explainability" aria-label={`EXPLAIN ${assessment.attempt_id}`}>
    <strong>EXPLAIN E6 · {assessment.method ?? 'Método no registrado'}</strong>
    <StatusBadge status={assessment.state} />
    <p>Intento: {assessment.attempt_id} · #{assessment.ordinal}</p>
    <p>Identidad: {assessment.identity_id}</p>
    <p>{assessment.state === 'verified' ? `${assessment.result_count ?? 0} resultados verificados` : 'Sin resultados certificados'}</p>
    <Link to={withAllowedQuery(routes.assessmentDetail(assessment.attempt_id), {datasource})}>Ver explicación E6 y artefactos</Link>
  </article>;
}
