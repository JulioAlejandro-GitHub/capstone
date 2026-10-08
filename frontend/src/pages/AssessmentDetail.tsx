import { Link, useParams } from 'react-router-dom';
import { AssessmentEvaluationSummary } from '../components/reports/AssessmentEvaluationCard';
import { InvalidEntityId } from '../components/RouteState';
import { Loading } from '../components/Loading';
import { useAssessment } from '../hooks/useAssessment';
import { isValidPublicId, routes, withAllowedQuery } from '../router';
import '../styles/report-components.css';

export function AssessmentDetail({ datasource }: { datasource: string }) {
  const { attemptId } = useParams();
  const valid = isValidPublicId(attemptId);
  const { data, error, loading } = useAssessment(valid ? attemptId : undefined);
  if (!valid) return <InvalidEntityId kind="evaluación E6" listPath={routes.runs} />;
  if (loading) return <Loading />;
  if (error || !data) return <div role="alert">{error || 'Evaluación no encontrada.'}</div>;
  return <section className="page">
    <h1>Evaluación E6</h1>
    <Link to={withAllowedQuery(routes.runDetail(data.training_run_id), { datasource })}>Ver TRAIN de origen</Link>
    <article className="lineage-child-card lineage-child-card--evaluation">
      <AssessmentEvaluationSummary assessment={{
        source_kind: 'assessment_e6', attempt_id: data.id,
        identity_id: data.identity_id, training_run_id: data.training_run_id,
        state: data.state, ordinal: data.ordinal,
        split: data.identity.split, purpose: data.identity.purpose,
        started_at: data.started_at, finished_at: data.finished_at,
        verification: data.verification,
      }} />
      <dl className="lineage-stats">
        <div><dt>Identidad científica</dt><dd>{data.identity_id}</dd></div>
        <div><dt>TRAIN</dt><dd>{data.training_run_id}</dd></div>
        <div><dt>Número de intento</dt><dd>{data.ordinal}</dd></div>
        <div><dt>Modelo</dt><dd>{data.identity.model.model_version_id}</dd></div>
        <div><dt>Checkpoint</dt><dd>{data.identity.model.checkpoint_artifact_id}</dd></div>
        <div><dt>Definición de métricas</dt><dd>{data.verification?.metrics?.definition ?? 'Sin métricas verificadas'}</dd></div>
      </dl>
      {data.cause ? <p role="status">Causa: {data.cause}</p> : null}
    </article>
  </section>;
}
