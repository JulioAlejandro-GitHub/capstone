import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import { ResponsiveContainer, ScatterChart, Scatter, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ZAxis } from 'recharts';
import { api } from '../../services/api';
import { executorLabel, useExplainExecutor } from '../../hooks/useExplainExecutor';
import { intensity } from '../../utils/analysisSummaries';
import type { RepresentState } from '../../types/explainGeneration';
import type { RepresentationEvidence, RepresentationRun } from '../../types/scientificReport';
import { EvidenceButton, Kpi, SectionAnswer } from './AnalysisWorkspace';
import { LazyScientificModule, type ModuleProps } from './ScientificReport';

const runLabel = (index: number) => `RUN ${String.fromCharCode(65 + index)}`;
const colors = ['var(--ds-blue-500)', 'var(--ds-green-700)', 'var(--ds-violet-700)', 'var(--ds-amber-700)'];
const percent = (n: number | null | undefined) => n == null ? 'Sin evidencia' : `${(n * 100).toLocaleString('es-CL', {maximumFractionDigits: 1})} %`;
const decimal = (n: number | null | undefined) => n == null ? '—' : n.toLocaleString('es-CL', {maximumFractionDigits: 3});
const POLL_MS = 5000;

type Projection = 'umap' | 'pca';
type ColorBy = 'label' | 'outcome';
const projectionLabels: Record<Projection, string> = {umap: 'UMAP 2D', pca: 'PCA (CP1 / CP2)'};
// Colours separate classes and decision outcomes; errors use warm tones so they stand out over correct cells.
const groupsBy: Record<ColorBy, {id: string; name: string; color: string}[]> = {
  label: [{id: '0', name: 'No parasitada (real)', color: 'var(--ds-blue-500)'}, {id: '1', name: 'Parasitada (real)', color: 'var(--ds-violet-700)'}],
  outcome: [{id: 'TN', name: 'VN', color: 'var(--ds-blue-500)'}, {id: 'TP', name: 'VP', color: 'var(--ds-green-700)'},
    {id: 'FP', name: 'FP', color: 'var(--ds-amber-700)'}, {id: 'FN', name: 'FN', color: 'var(--ds-red-700)'}],
};
const outcome = (label: number, predicted: number) => label ? (predicted ? 'TP' : 'FN') : (predicted ? 'FP' : 'TN');
// Shares of variance above which a component count is reported in the answer.
const VARIANCE_TARGETS = [0.8, 0.9];
const componentsFor = (run: RepresentationRun, target: number) => {
  const index = run.cumulative_variance?.findIndex(value => value >= target) ?? -1;
  return index >= 0 ? index + 1 : null;
};

// Status and generation of one RUN's REPRESENT for the EVALUATE chosen in its card.
function RepresentGeneration({run, index, canGenerate, blocked, onGenerated}: {run: RepresentationRun; index: number; canGenerate: boolean; blocked: string | null; onGenerated: () => void}) {
  const [status, setStatus] = useState<RepresentState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const source = run.source_attempt_id;
  useEffect(() => {
    if (!source || run.state === 'available') return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const read = async () => {
      try {
        const next = await api.getRepresentationState(source, controller.signal);
        setStatus(next); setError(null);
        if (next.state === 'completed') { onGenerated(); return; }
        if (next.state === 'pending' || next.state === 'running') timer = setTimeout(() => { void read(); }, POLL_MS);
      } catch { if (!controller.signal.aborted) setError('No se pudo consultar el estado de la representación.'); }
    };
    void read();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [source, run.state, revision, onGenerated]);
  if (!source) return <p>{runLabel(index)}: {run.issues.join(' ')}</p>;
  const busy = status?.state === 'pending' || status?.state === 'running';
  const generate = async () => {
    try { setError(null); await api.generateRepresentation(source); setRevision(n => n + 1); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo solicitar la representación.'); }
  };
  return <div className="scc-represent-run"><strong>{runLabel(index)}</strong>
    <span>{busy ? (status?.state === 'pending' ? 'En cola del ejecutor…' : 'Calculando embeddings y proyecciones…')
      : status?.state === 'failed' ? `Falló: ${status.error ?? 'ASSESSMENT_EXECUTION_FAILED'}` : run.issues.join(' ')}</span>
    {canGenerate && !busy && <button type="button" className="ds-button" data-size="compact" disabled={Boolean(blocked)} title={blocked ?? undefined} onClick={() => void generate()}>
      {status?.state === 'failed' ? 'Reintentar' : 'Generar representaciones'}</button>}
    {error && <span role="alert">{error}</span>}
  </div>;
}

function ProjectionChart({run, index, projection, colorBy}: {run: RepresentationRun; index: number; projection: Projection; colorBy: ColorBy}) {
  const series = useMemo(() => {
    const points = run[projection] ?? [];
    const groups = groupsBy[colorBy].map(group => ({...group, points: [] as {x: number; y: number; sample: string; label: number; predicted: number; score: number}[]}));
    points.forEach(([x, y], k) => {
      const label = run.labels![k], predicted = run.predicted![k];
      const key = colorBy === 'label' ? String(label) : outcome(label, predicted);
      groups.find(group => group.id === key)!.points.push({x, y, sample: run.samples![k], label, predicted, score: run.scores![k]});
    });
    return groups;
  }, [run, projection, colorBy]);
  return <section aria-label={`${projectionLabels[projection]} · ${runLabel(index)}`}><h4>{runLabel(index)} · {run.split?.toUpperCase()} · {run.count} células</h4>
    <div className="scc-chart"><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{top: 8, right: 16, bottom: 8, left: 0}}>
      <CartesianGrid strokeDasharray="3 3" /><XAxis type="number" dataKey="x" name="Eje 1" tick={false} domain={['auto', 'auto']} /><YAxis type="number" dataKey="y" name="Eje 2" tick={false} width={8} domain={['auto', 'auto']} />
      <ZAxis range={[10, 10]} />
      <Tooltip cursor={{strokeDasharray: '3 3'}} content={({payload}) => {
        const point = payload?.[0]?.payload as {sample: string; label: number; predicted: number; score: number} | undefined;
        return point ? <div className="scc-tooltip"><code>{point.sample}</code><br />Real {point.label ? 'parasitada' : 'no parasitada'} · predicha {point.predicted ? 'parasitada' : 'no parasitada'} · score {decimal(point.score)}</div> : null;
      }} />
      <Legend />
      {series.map(group => <Scatter key={group.id} name={`${group.name} (${group.points.length})`} data={group.points} fill={group.color} fillOpacity={colorBy === 'outcome' && (group.id === 'TP' || group.id === 'TN') ? 0.35 : 0.8} isAnimationActive={false} />)}
    </ScatterChart></ResponsiveContainer></div></section>;
}

function VarianceChart({runs}: {runs: {run: RepresentationRun; index: number}[]}) {
  const length = Math.max(...runs.map(({run}) => run.cumulative_variance?.length ?? 0));
  const rows = Array.from({length}, (_, k) => Object.fromEntries([['component', k + 1], ...runs.map(({run, index}) => [`r${index}`, run.cumulative_variance?.[k]])]));
  return <section aria-label="Varianza explicada PCA"><h4>Varianza explicada acumulada (PCA)</h4>
    <div className="scc-chart scc-chart--compact"><ResponsiveContainer width="100%" height="100%"><LineChart data={rows} margin={{top: 8, right: 24, bottom: 8, left: 0}}>
      <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="component" label={{value: 'Componentes', position: 'insideBottom', offset: -4}} /><YAxis domain={[0, 1]} tickFormatter={v => percent(v)} />
      <Tooltip formatter={v => percent(typeof v === 'number' ? v : null)} labelFormatter={v => `${v} componentes`} /><Legend />
      {runs.map(({index}) => <Line key={index} dataKey={`r${index}`} name={runLabel(index)} stroke={colors[index % colors.length]} dot={false} isAnimationActive={false} />)}
    </LineChart></ResponsiveContainer></div></section>;
}

function CkaHeatmap({data}: {data: RepresentationEvidence}) {
  const {values, common} = data.cka;
  return <section aria-label="CKA lineal"><h4>Similitud de representaciones · CKA lineal</h4>
    <div className="report-table-scroll"><table className="report-data-table scc-heatmap"><caption>CKA lineal sobre las muestras comunes de cada par; N común bajo cada valor</caption>
      <thead><tr><th>RUN</th>{data.runs.map((_, i) => <th key={i}>{runLabel(i)}</th>)}</tr></thead>
      <tbody>{values.map((row, i) => <tr key={i}><th scope="row">{runLabel(i)}</th>{row.map((score, j) => <td key={j} data-diagonal={i === j} style={{'--scc-heat': intensity(score ?? 0, 1)} as CSSProperties}>
        {score == null ? 'Sin evidencia' : decimal(score)}<small>N = {common[i][j]}</small></td>)}</tr>)}</tbody></table></div></section>;
}

export function RepresentationResults({data, canGenerate, blocked, onGenerated}: {data: RepresentationEvidence; canGenerate: boolean; blocked: string | null; onGenerated: () => void}) {
  const [projection, setProjection] = useState<Projection>('umap');
  const [colorBy, setColorBy] = useState<ColorBy>('outcome');
  const available = data.runs.map((run, index) => ({run, index})).filter(({run}) => run.state === 'available');
  const missing = data.runs.map((run, index) => ({run, index})).filter(({run}) => run.state !== 'available');
  const pairs = data.cka.values.flatMap((row, i) => row.flatMap((score, j) => j > i && score != null ? [{i, j, score}] : []));
  const closest = pairs.length ? pairs.reduce((best, pair) => pair.score > best.score ? pair : best) : null;
  return <>
    {available.length > 0 && <SectionAnswer indicators={<>
      {available.map(({run, index}) => <Kpi key={run.training_run_id} run={index} label={`${runLabel(index)} · dimensión`} value={run.dimension}
        detail={VARIANCE_TARGETS.map(target => `${percent(target)} varianza: ${componentsFor(run, target) ?? '> ' + (run.variance?.length ?? 0)} CP`).join(' · ')} />)}
      {closest && <Kpi label="Par más similar (CKA)" value={decimal(closest.score)} detail={`${runLabel(closest.i)}–${runLabel(closest.j)} · N = ${data.cka.common[closest.i][closest.j]}`} />}
    </>}>
      Embeddings de la capa {available[0].run.layer ?? 'GlobalAveragePooling2D'} sobre la población de la EVALUATE seleccionada.
      {' '}Las proyecciones son descriptivas: la separación visual de clases no acredita desempeño ni calibración.
    </SectionAnswer>}
    {missing.length > 0 && <div className="scc-represent-missing">
      <h4>Sin representaciones</h4>
      {missing.map(({run, index}) => <RepresentGeneration key={`${run.training_run_id}|${run.source_attempt_id}`} run={run} index={index} canGenerate={canGenerate} blocked={blocked} onGenerated={onGenerated} />)}
    </div>}
    {available.length > 0 && <>
      <div className="scc-chart-toolbar">
        <div role="tablist" aria-label="Proyección" className="scc-segmented">{(Object.keys(projectionLabels) as Projection[]).map(item => <button key={item} type="button" role="tab" aria-selected={item === projection} className="ds-button" data-size="compact" onClick={() => setProjection(item)}>{projectionLabels[item]}</button>)}</div>
        <div role="tablist" aria-label="Color" className="scc-segmented">{([['outcome', 'Acierto / error'], ['label', 'Clase real']] as [ColorBy, string][]).map(([item, label]) => <button key={item} type="button" role="tab" aria-selected={item === colorBy} className="ds-button" data-size="compact" onClick={() => setColorBy(item)}>{label}</button>)}</div>
      </div>
      <div className="scc-chart-grid">{available.map(({run, index}) => <ProjectionChart key={run.training_run_id} run={run} index={index} projection={projection} colorBy={colorBy} />)}</div>
      <p className="scc-meta">{data.definitions[projection]}</p>
      <div className="scc-chart-grid">
        <VarianceChart runs={available} />
        {data.runs.length > 1 ? <CkaHeatmap data={data} /> : <p>CKA compara dos o más RUN; selecciona otro TRAIN para medir la similitud de representaciones.</p>}
      </div>
      <p className="scc-meta">{data.definitions.cka}</p>
      <EvidenceButton title="Identidad de las representaciones" label="Identidad de las representaciones">
        {available.map(({run, index}) => <p key={run.training_run_id} className="report-identifier">{runLabel(index)} · REPRESENT {run.attempt_id}<br />EVALUATE {run.source_attempt_id} · {run.split?.toUpperCase()} · {run.count} células · dimensión {run.dimension} · capa {run.layer}</p>)}
        <p>{data.definitions.representation}</p><p>{data.definitions.pca}</p><p>{data.definitions.umap}</p>
      </EvidenceButton>
    </>}
    <p className="scc-meta">Al abrir esta sección no se ejecuta ningún modelo: PCA y UMAP se leen persistidos y CKA se calcula sobre los embeddings guardados.</p>
  </>;
}

export function ScientificRepresentations({canGenerate = false, ...props}: ModuleProps & {canGenerate?: boolean}) {
  const [generated, setGenerated] = useState(0);
  const {executor, blocked} = useExplainExecutor(Boolean(props.active && canGenerate));
  const onGenerated = useMemo(() => () => setGenerated(n => n + 1), []);
  return <LazyScientificModule<RepresentationEvidence> {...props} evidenceRevision={(props.evidenceRevision ?? 0) + generated}
    title="Embeddings y representaciones · PCA / UMAP / CKA" module="representations">{data => <>
      {canGenerate && data.runs.some(run => run.state !== 'available') && <p className="scc-executor" data-available={executor?.available ?? false} role="status">{executorLabel(executor)}{executor && !executor.available && executor.executor === 'host_gpu' && <> · Inícialo en el host: <code>{executor.start_command ?? 'scripts/host_services.sh start explain'}</code></>}</p>}
      <RepresentationResults data={data} canGenerate={canGenerate} blocked={blocked} onGenerated={onGenerated} />
    </>}</LazyScientificModule>;
}
