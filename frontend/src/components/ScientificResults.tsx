import { useEffect, useState } from 'react';
import { api } from '../services/api';

type Measurement = { value: number | null; undefined_reason: string | null };
export type ScientificResult = {
  contract_version: 'scientific_results_v2' | 'legacy_e10_v1';
  release_status: string | null;
  evaluations?: Array<{ id: string; split: string; training_run_id: string; model_version_id: string | null; checkpoint_artifact_id: string | null }>;
  run_clinical_metrics?: Array<{ evaluation_id: string; tn: number; fp: number; fn: number; tp: number; metrics: Record<string, Measurement> }>;
  xai_evidence?: Array<{ id: string; method: string; method_version: string; checkpoint_artifact_id: string }>;
  xai_interpretations?: Array<{ id: string; interpretation: string; limitations: string }>;
  xai_specialist_reviews?: Array<{ id: string; interpretation_id: string; decision: string; rationale: string }>;
};

export function ScientificResultsView({ result }: { result: ScientificResult }) {
  if (result.contract_version !== 'scientific_results_v2') return null;
  return <section className="panel" aria-label="Resultados científicos">
    <h2>Resultados científicos</h2>
    <p>Publicación: {result.release_status ?? 'Sin información'}</p>
    {result.evaluations?.map(e => <article key={e.id}>
      <h3>Evaluación {e.split.toUpperCase()}</h3>
      <p>TRAIN: {e.training_run_id} · Modelo: {e.model_version_id ?? 'No registrado'} · Checkpoint: {e.checkpoint_artifact_id ?? 'Ensemble'}</p>
      {result.run_clinical_metrics?.filter(m => m.evaluation_id === e.id).map(m => <div key={m.evaluation_id}>
        <dl>{Object.entries(m.metrics).map(([name, metric]) => <div key={name}>
          <dt>{name}</dt><dd>{metric.value === null ? `Indefinida (${metric.undefined_reason ?? 'Sin motivo registrado'})` : metric.value.toFixed(4)}</dd>
        </div>)}</dl>
        <table><caption>Matriz de confusión: filas reales, columnas predichas</caption>
          <thead><tr><th>Real / Predicha</th><th>Uninfected</th><th>Parasitized</th></tr></thead>
          <tbody><tr><th>Uninfected</th><td>TN {m.tn}</td><td>FP {m.fp}</td></tr>
            <tr><th>Parasitized</th><td>FN {m.fn}</td><td>TP {m.tp}</td></tr></tbody>
        </table>
      </div>)}
    </article>)}
    {result.xai_evidence?.map(e => <p key={e.id}>XAI: {e.method} {e.method_version} · Checkpoint: {e.checkpoint_artifact_id}</p>)}
    {result.xai_interpretations?.map(i => <article key={i.id}><p>{i.interpretation}</p><p>Limitaciones: {i.limitations}</p>
      {result.xai_specialist_reviews?.filter(r => r.interpretation_id === i.id).map(r => <p key={r.id}>Revisión: {r.decision} — {r.rationale}</p>)}
    </article>)}
  </section>;
}

export function ScientificResults({ runId, datasource }: { runId: string; datasource: string }) {
  const [state, setState] = useState<{ result?: ScientificResult; error?: string }>({});
  useEffect(() => {
    let active = true;
    setState({});
    api.scientificResults(runId, datasource).then(result => { if (active) setState({ result }); })
      .catch(() => { if (active) setState({ error: 'No se pudieron verificar los resultados científicos.' }); });
    return () => { active = false; };
  }, [runId, datasource]);
  if (state.error) return <p role="alert">{state.error}</p>;
  return state.result ? <ScientificResultsView result={state.result} /> : <p>Cargando resultados científicos…</p>;
}
