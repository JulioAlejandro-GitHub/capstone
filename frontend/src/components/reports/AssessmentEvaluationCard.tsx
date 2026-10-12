import { Link } from 'react-router-dom';
import { routes, withAllowedQuery } from '../../router';
import type { AssessmentEvaluationChild } from '../../types/api';
import { StatusBadge } from '../StatusBadge';
import { MetricChip } from './MetricChip';
import { MiniConfusionMatrix } from './MiniConfusionMatrix';
import { ReportBadge } from './ReportBadge';
import { RunProcessBadge } from './RunProcessBadge';

export function AssessmentEvaluationSummary({ assessment }: { assessment: AssessmentEvaluationChild }) {
  const metrics = assessment.state === 'verified' ? assessment.verification?.metrics : null;
  return <>
    <header className="lineage-child-card__header">
      <RunProcessBadge kind="evaluation" />
      <ReportBadge level="neutral">E6</ReportBadge>
      <StatusBadge status={assessment.state} />
    </header>
    <div className="lineage-child-card__identity">
      <strong>EVALUATE · {assessment.split.toUpperCase()}</strong>
      <span>Intento: {assessment.attempt_id}</span>
      <span>Propósito: {assessment.purpose}</span>
      <span>Finalización: {assessment.finished_at ? new Date(assessment.finished_at).toLocaleString('es-CL') : 'Pendiente'}</span>
    </div>
    {metrics ? <div className="lineage-evaluation-results">
      <MiniConfusionMatrix counts={{ tn: metrics.tn, fp: metrics.fp, fn: metrics.fn, tp: metrics.tp }} />
      <div className="metric-grid lineage-child-metrics">
        <MetricChip label="Accuracy" value={metrics.accuracy} />
        <MetricChip label="Recall" value={metrics.recall} />
        <MetricChip label="Specificity" value={metrics.specificity} />
        <MetricChip label="Precision" value={metrics.precision} />
        <MetricChip label="F2" value={metrics.f2} />
      </div>
      <span>{metrics.count.toLocaleString('es-CL')} resultados persistidos</span>
    </div> : <p className="report-muted">{assessment.state === 'active'
      ? 'Evaluación en curso; métricas verificadas pendientes.'
      : 'Este intento no tiene métricas verificadas.'}</p>}
  </>;
}

export function AssessmentEvaluationCard({ assessment, datasource }: {
  assessment: AssessmentEvaluationChild;
  datasource: string;
}) {
  return <article className="lineage-child-card lineage-child-card--evaluation" aria-label={`Evaluación E6 ${assessment.attempt_id}`}>
    <AssessmentEvaluationSummary assessment={assessment} />
    <Link className="report-detail-button lineage-child-card__action"
      to={withAllowedQuery(routes.assessmentDetail(assessment.attempt_id), { datasource })}>
      Ver evaluación E6
    </Link>
  </article>;
}
