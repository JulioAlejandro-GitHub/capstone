import { useCallback, useEffect, useState } from 'react';

import { useAuth } from '../../auth';
import { api } from '../../services/api';
import type { ActivationTrace, ActivationTraceCandidate, ActivationTraceCatalog, ActivationTraceStep, TraceCategory } from '../../types/activationTrace';
import { megabytes, number, outcomeOf, percent, points, stepChange, traceCategories } from './traceSteps';

const PLAY_MS = 1800;
const png = (data: string) => `data:image/png;base64,${data}`;
const message = (cause: unknown, fallback: string) => cause instanceof Error ? cause.message : fallback;
const shortId = (id: string) => `${id.slice(0, 8)}…`;

function StepDetail({ trace, index }: { trace: ActivationTrace; index: number }) {
  if (index === 0) return <div className="mx-trace-step"><h4>Entrada · célula original</h4>
    <img className="mx-trace-input" src={png(trace.input_image)} alt="Célula original" /></div>;
  const steps = trace.steps, step: ActivationTraceStep = steps[index - 1], change = stepChange(steps, index - 1);
  return <div className="mx-trace-step"><h4><code>{step.layer}</code> · {step.shape.join(' × ')}</h4>
    <dl className="mx-trace-stats">
      <div><dt>Media</dt><dd>{number(step.stats.mean)}</dd></div><div><dt>Máximo</dt><dd>{number(step.stats.max)}</dd></div>
      <div><dt>Valores activos</dt><dd>{percent(step.stats.active)}</dd></div>
      {change && <div><dt>Cambio de activos</dt><dd>{change.active >= 0 ? '+' : ''}{points(change.active)}</dd></div>}
    </dl>
    {step.kind === 'spatial' && <><div className="mx-trace-maps">{step.maps.map(map => <figure key={map.channel}><img src={png(map.png)} alt={`Canal ${map.channel}`} /><figcaption>{map.channel}</figcaption></figure>)}</div>
      <p className="scc-meta">{trace.selection} de {step.shape[2]}. Cada mapa usa su propia escala.</p></>}
    {step.kind === 'vector' && <ol className="mx-trace-top">{step.top.slice(0, 8).map(item => <li key={item.index}><span>{item.index}</span><strong>{number(item.value)}</strong></li>)}</ol>}
    {step.kind === 'output' && <dl className="mx-trace-stats">
      <div><dt>Logit</dt><dd>{number(trace.logit)}</dd></div><div><dt>Score (sigmoide)</dt><dd>{number(trace.score)}</dd></div>
      <div><dt>Umbral</dt><dd>{number(trace.threshold)}</dd></div><div><dt>Resultado</dt><dd>{outcomeOf(trace)}</dd></div>
    </dl>}
    {step.kind === 'output' && !trace.consistent && <p className="ds-callout" data-tone="warning" role="alert">El score recalculado ({number(trace.score)}) no coincide con el guardado en la evaluación ({number(trace.persisted_score)}).</p>}
  </div>;
}

/** Saved forward passes of one TRAIN. Opening it reads files only; the model runs when «Calcular» is pressed. */
export function ActivationTracePanel({ runId, datasource, onBlock }: { runId: string; datasource: string; onBlock: (id: string) => void }) {
  const { user } = useAuth();
  const canCalculate = Boolean(user?.permissions?.includes('scientific.cell_classification.explain'));
  const [catalog, setCatalog] = useState<ActivationTraceCatalog | null>(null);
  const [category, setCategory] = useState<TraceCategory>('false_negative');
  const [candidates, setCandidates] = useState<ActivationTraceCandidate[]>([]);
  const [trace, setTrace] = useState<ActivationTrace | null>(null);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [calculating, setCalculating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const open = useCallback(async (sampleId: string) => {
    setError(null); setPlaying(false);
    try { setTrace(await api.getActivationTrace(runId, sampleId)); setIndex(0); }
    catch (cause) { setError(message(cause, 'No fue posible abrir el recorrido.')); }
  }, [runId]);

  const refresh = useCallback(async () => {
    const next = await api.getActivationTraces(datasource, runId);
    setCatalog(next);
    return next;
  }, [datasource, runId]);

  useEffect(() => {
    let active = true;
    setTrace(null); setCatalog(null); setPlaying(false);
    // The latest saved trace opens by itself: returning to the RUN shows the work already done.
    refresh().then(next => { if (active && next.items[0]) void open(next.items[0].sample_id); })
      .catch(cause => { if (active) setError(message(cause, 'No fue posible consultar los recorridos.')); });
    return () => { active = false; };
  }, [refresh, open]);

  const available = catalog?.available;
  useEffect(() => {
    if (!available) return;
    const controller = new AbortController();
    api.getActivationTraceCandidates(datasource, runId, category, controller.signal).then(setCandidates)
      .catch(cause => { if (!controller.signal.aborted) setError(message(cause, 'No fue posible listar células.')); });
    return () => controller.abort();
  }, [available, category, datasource, runId]);

  const total = trace ? trace.steps.length + 1 : 0;
  useEffect(() => { if (trace && index > 0) onBlock(trace.steps[index - 1].block); else if (trace) onBlock('input'); }, [trace, index, onBlock]);
  useEffect(() => {
    if (!playing) return;
    if (index >= total - 1) { setPlaying(false); return; }
    const timer = window.setTimeout(() => setIndex(value => value + 1), PLAY_MS);
    return () => window.clearTimeout(timer);
  }, [playing, index, total]);

  const calculate = async (sampleId: string) => {
    setCalculating(sampleId); setError(null);
    try {
      const created = await api.createActivationTrace(datasource, runId, sampleId);
      setTrace(created); setIndex(0); setPlaying(false);
      await refresh();
    } catch (cause) { setError(message(cause, 'No fue posible calcular el recorrido.')); }
    finally { setCalculating(null); }
  };
  const remove = async (sampleId: string) => {
    if (!window.confirm('¿Eliminar este recorrido guardado?')) return;
    setError(null);
    try {
      await api.deleteActivationTrace(runId, sampleId);
      if (trace?.sample_id === sampleId) setTrace(null);
      await refresh();
    } catch (cause) { setError(message(cause, 'No fue posible eliminar el recorrido.')); }
  };

  if (catalog && !catalog.available) return null;
  const saved = new Set(catalog?.items.map(item => item.sample_id));
  return <section className="report-section mx-trace" aria-label="Recorrido de una célula">
    <div className="ds-page-header"><h3>Recorrido de una célula</h3>
      {catalog && <span className="scc-meta">{catalog.items.length} guardados · {megabytes(catalog.used_bytes)} de {megabytes(catalog.max_bytes)} · {catalog.split?.toUpperCase()}</span>}</div>
    {error && <p className="ds-callout" data-tone="warning" role="alert">{error}</p>}
    <div className="mx-trace-columns">
      <div><h4>Recorridos guardados</h4>
        {catalog?.items.length ? <ul className="mx-trace-list">{catalog.items.map(item => <li key={item.sample_id} data-active={item.sample_id === trace?.sample_id}>
          <button type="button" className="ds-button" data-size="compact" title={item.sample_id} onClick={() => void open(item.sample_id)}>{outcomeOf(item)} · {number(item.score, 3)} · {shortId(item.sample_id)}</button>
          {canCalculate && <button type="button" className="ds-button" data-size="compact" aria-label={`Eliminar recorrido ${shortId(item.sample_id)}`} onClick={() => void remove(item.sample_id)}>×</button>}
        </li>)}</ul> : <p className="scc-meta">Aún no hay recorridos para este RUN.</p>}
      </div>
      {canCalculate && <div><h4>Nueva célula</h4>
        <label className="mx-filter">Tipo<select className="ds-control" value={category} onChange={event => setCategory(event.target.value as TraceCategory)}>
          {(Object.keys(traceCategories) as TraceCategory[]).map(item => <option key={item} value={item}>{traceCategories[item]}</option>)}</select></label>
        {candidates.length ? <ul className="mx-trace-list">{candidates.map(item => <li key={item.sample_id}>
          <button type="button" className="ds-button" data-size="compact" disabled={Boolean(calculating)} title={item.sample_id} onClick={() => void (saved.has(item.sample_id) ? open(item.sample_id) : calculate(item.sample_id))}>
            {calculating === item.sample_id ? 'Calculando…' : `${saved.has(item.sample_id) ? 'Ver' : 'Calcular'} · ${number(item.score, 3)} · ${shortId(item.sample_id)}`}</button>
        </li>)}</ul> : <p className="scc-meta">Sin células de este tipo.</p>}
      </div>}
    </div>
    {trace && <>
      <div className="mx-trace-player" role="group" aria-label="Reproducción del recorrido">
        <button type="button" className="ds-button" data-size="compact" disabled={index === 0} onClick={() => { setPlaying(false); setIndex(index - 1); }}>Anterior</button>
        <button type="button" className="ds-button" data-size="compact" onClick={() => { if (index >= total - 1) setIndex(0); setPlaying(!playing); }}>{playing ? 'Pausar' : 'Reproducir'}</button>
        <button type="button" className="ds-button" data-size="compact" disabled={index >= total - 1} onClick={() => { setPlaying(false); setIndex(index + 1); }}>Siguiente</button>
        <span className="scc-meta">Paso {index + 1} de {total} · célula {shortId(trace.sample_id)} · {outcomeOf(trace)}</span>
      </div>
      <StepDetail trace={trace} index={index} />
      <p className="scc-meta">Reproducción de valores ya calculados con este checkpoint. Lo observado en una célula es una hipótesis, no una conclusión sobre el modelo.</p>
    </>}
  </section>;
}
