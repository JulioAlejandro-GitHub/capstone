import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAssessmentChoices } from '../../hooks/useAssessmentChoices';
import { useAssessment } from '../../hooks/useAssessment';
import { routes, withAllowedQuery } from '../../router';
import { AssessmentEvaluationSummary } from './AssessmentEvaluationCard';

function SelectedEvidence({ id, datasource }: { id: string; datasource: string }) {
  const { data, loading, error } = useAssessment(id);
  if (loading) return <p>Cargando evidencia {id}…</p>;
  if (error || !data) return <p role="alert">{error ?? 'Sin evidencia'}</p>;
  return <article aria-label={`Evidencia seleccionada ${id}`}>
    <p>TRAIN: {data.training_run_id}</p>
    <p>Dataset: {data.identity.dataset?.dataset_version_id ?? 'Sin evidencia'} · Umbral: {data.identity.decision?.effective ?? 'N/A'}</p>
    {data.kind === 'evaluate' ? <AssessmentEvaluationSummary assessment={{
      ...data, source_kind: 'assessment_e6', attempt_id: data.id,
      split: data.identity.split, purpose: data.identity.purpose,
    }} /> : <p>{data.kind === 'represent' ? 'REPRESENT' : 'EXPLAIN'} · {data.id} · {data.state}</p>}
    <Link to={withAllowedQuery(routes.assessmentDetail(id), { datasource })}>Consultar esta ejecución</Link>
  </article>;
}

export function AssessmentComparison({ datasource }: { datasource: string }) {
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const { items, loading, error } = useAssessmentChoices(offset);
  return <section className="panel">
    <h2>Evidencia por ejecución</h2>
    <p>Seleccione las ejecuciones que desea comparar. La fecha indica el orden del historial.</p>
    {error ? <p role="alert">{error}</p> : null}
    {loading ? <p>Cargando historial…</p> : items.length === 0 ? <p>Sin evidencia</p> :
      <ul>{items.map(item => <li key={item.attempt_id}>
        <label><input type="checkbox" checked={selected.includes(item.attempt_id)}
          onChange={event => setSelected(current => event.target.checked
            ? [...current, item.attempt_id] : current.filter(id => id !== item.attempt_id))} />
          {item.kind === 'explain' ? 'EXPLAIN' : item.kind === 'represent' ? 'REPRESENT' : item.split === 'test' ? 'TEST' : 'EVALUATE'} · {item.attempt_id} · TRAIN {item.training_run_id} · {item.state} · {new Date(item.started_at).toLocaleString('es-CL')}
        </label>
      </li>)}</ul>}
    <button disabled={loading || offset === 0} onClick={() => setOffset(current => Math.max(0,current-100))}>Anteriores</button>
    <button disabled={loading || items.length < 100} onClick={() => setOffset(current => current+100)}>Siguientes</button>
    {selected.length === 0 ? <p>Sin evidencia seleccionada</p> : selected.map(id =>
      <SelectedEvidence key={id} id={id} datasource={datasource} />)}
  </section>;
}
