import { useEffect, useMemo, useRef, useState, type MouseEvent, type ReactNode } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { TrainingCurves } from '../reports/ScientificReport';
import type { CurveEvidence } from '../../types/scientificReport';
import type { TrainingTrajectories } from '../../types/trainingTrajectories';
import {
  CHECKPOINT_ANALYSES, ORIGIN_LABELS, OUTCOME_LABELS, TRAINING_VIEWS, accuracyByEpoch, fineTuneStart, learningRateChanges,
  learningRateSeries, orderTrajectories, outcomeCounts, sampleTrajectories, trueClassProbability,
  type EvidenceOrigin, type SampleTrajectory, type TrainingView, type TrajectoryOutcome,
} from './trainingHistoryModel';

type Load<T> = { state: 'idle' | 'loading' | 'ready' | 'error'; data: T | null; error: string | null };

const pct = (value: number | null) => value == null ? '—' : `${(100 * value).toFixed(1)} %`;
const lrText = (value: number) => value.toExponential(2).replace('e', ' × 10^').replace('+', '');
const PHASES: Record<string, string> = { base: 'Fase base', fine_tuning: 'Ajuste fino' };

export function OriginTag({ origin }: { origin: EvidenceOrigin }) {
  return <span className="mt-origin" data-origin={origin}>{ORIGIN_LABELS[origin]}</span>;
}

/** Barra de pestañas compartida por el diagrama y los gráficos de la historia del TRAIN. */
export function TrainingTabs({ view, onChange }: { view: TrainingView; onChange: (view: TrainingView) => void }) {
  return <div className="mt-tabs" role="tablist" aria-label="Vistas del entrenamiento">
    {TRAINING_VIEWS.map(item => <button key={item.id} type="button" role="tab" className="mt-tab" aria-selected={item.id === view}
      data-origin={item.origin ?? undefined} onClick={() => onChange(item.id)}>{item.label}</button>)}
  </div>;
}

function Status<T>({ load, empty }: { load: Load<T>; empty?: string | null }) {
  if (load.state === 'loading' || load.state === 'idle') return <p className="mt-muted" role="status">Consultando los registros del TRAIN…</p>;
  if (load.state === 'error') return <p className="mt-callout" role="alert">{load.error}</p>;
  return empty ? <p className="mt-pending-note">{empty}</p> : null;
}

export function TrainingHistoryCard({ view, tabs, curve, trajectories, selectedEpoch, requestedSample }: {
  view: Exclude<TrainingView, 'flujo'>;
  tabs: ReactNode;
  curve: Load<CurveEvidence>;
  trajectories: Load<TrainingTrajectories>;
  selectedEpoch: number | null;
  requestedSample: string | null;
}) {
  const hint = { curvas: 'loss y métricas TRAIN/VAL de cada época', lr: 'tasa de aprendizaje efectiva al cerrar cada época',
    trayectorias: 'score VAL de cada célula en cada época', checkpoints: 'lo que se puede calcular desde los checkpoints por época' }[view];
  return <div className="mt-card mt-history">
    <div className="mt-card-h">{tabs}<span className="mt-hint">{hint}</span></div>
    <div className="mt-history-body ds-report" data-surface="workbench">
      {view === 'curvas' && <><OriginTag origin="registrado" />
        {curve.state === 'ready' && curve.data ? <TrainingCurves data={[curve.data]} /> : <Status load={curve} empty={curve.state === 'ready' ? 'El TRAIN no registró épocas.' : null} />}</>}
      {view === 'lr' && <LearningRatePanel curve={curve} selectedEpoch={selectedEpoch} />}
      {view === 'trayectorias' && <TrajectoryPanel load={trajectories} selectedEpoch={selectedEpoch} requestedSample={requestedSample} />}
      {view === 'checkpoints' && <CheckpointAnalyses />}
    </div>
  </div>;
}

/* ── Learning rate ─────────────────────────────────────────────────────────── */

function LearningRatePanel({ curve, selectedEpoch }: { curve: Load<CurveEvidence>; selectedEpoch: number | null }) {
  const points = useMemo(() => learningRateSeries(curve.data), [curve.data]);
  const changes = useMemo(() => learningRateChanges(points), [points]);
  if (curve.state !== 'ready') return <><OriginTag origin="registrado" /><Status load={curve} /></>;
  if (!points.length) return <><OriginTag origin="registrado" /><p className="mt-pending-note">Este TRAIN no registró el learning rate por época.</p></>;
  const fine = fineTuneStart(points);
  const first = points[0].lr, last = points[points.length - 1].lr;
  return <>
    <OriginTag origin="registrado" />
    <div className="mt-history-kpis">
      <div className="mt-fact"><div className="mt-k">Inicial</div><div className="mt-v">{lrText(first)}</div></div>
      <div className="mt-fact"><div className="mt-k">Final</div><div className="mt-v">{lrText(last)}<small>{(first / last).toFixed(0)}× menor</small></div></div>
      <div className="mt-fact"><div className="mt-k">Cambios registrados</div><div className="mt-v">{changes.length}<small>{changes.filter(c => c.phaseStart).length} al cambiar de fase</small></div></div>
      <div className="mt-fact"><div className="mt-k">Checkpoint</div><div className="mt-v">{selectedEpoch != null ? `Época ${selectedEpoch}` : '—'}<small>{(() => { const lr = points.find(p => p.epoch === selectedEpoch)?.lr; return lr != null ? lrText(lr) : ''; })()}</small></div></div>
    </div>
    <div className="scc-chart"><ResponsiveContainer width="100%" height="100%">
      <LineChart data={points} margin={{ top: 10, right: 20, bottom: 0, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="epoch" type="number" domain={['dataMin', 'dataMax']} allowDecimals={false} />
        <YAxis scale="log" domain={['auto', 'auto']} tickFormatter={(value: number) => value.toExponential(0)} width={56} />
        <Tooltip formatter={(value) => lrText(Number(value))} labelFormatter={(label) => `Época ${label}`} />
        <Legend />
        <Line dataKey="lr" name="Learning rate (escala log)" type="stepAfter" stroke="var(--ds-violet-500, #8b5cf6)" dot={{ r: 2 }} isAnimationActive={false} />
        {fine != null && <ReferenceLine x={fine - 0.5} strokeDasharray="2 4" stroke="var(--ds-border-strong, #94a3b8)" label="Inicio ajuste fino" />}
        {selectedEpoch != null && <ReferenceLine x={selectedEpoch} stroke="var(--ds-green-500, #22c55e)" label="Checkpoint" />}
      </LineChart>
    </ResponsiveContainer></div>
    {changes.length > 0 && <div className="report-table-scroll"><table className="report-data-table"><caption>Cambios de learning rate entre épocas consecutivas</caption>
      <thead><tr><th>Época</th><th>Fase</th><th>Antes</th><th>Después</th><th>Factor</th></tr></thead>
      <tbody>{changes.map(change => <tr key={change.epoch}><td>{change.epoch}</td><td>{PHASES[change.phase] ?? change.phase}{change.phaseStart ? ' (inicio)' : ''}</td>
        <td>{lrText(change.from)}</td><td>{lrText(change.to)}</td><td>×{Number(change.factor.toPrecision(3))}</td></tr>)}</tbody></table></div>}
    <p className="scc-meta">Valor leído del optimizador al cerrar cada época. La causa de cada cambio (ReduceLROnPlateau o nueva fase) no se registra por separado.</p>
  </>;
}

/* ── Trayectoria de células ───────────────────────────────────────────────── */

const CORRECT = [20, 158, 117], WRONG = [216, 90, 48], MID = [128, 128, 128];
function color(probability: number | null): [number, number, number] {
  if (probability == null) return [0, 0, 0];
  const [a, b, t] = probability >= 0.5 ? [MID, CORRECT, (probability - 0.5) * 2] : [WRONG, MID, probability * 2];
  return [0, 1, 2].map(i => Math.round(a[i] + (b[i] - a[i]) * t)) as [number, number, number];
}

const HEAT_H = 360;

function TrajectoryHeatmap({ data, order, selectedEpoch, highlight, onPick }: {
  data: TrainingTrajectories; order: SampleTrajectory[]; selectedEpoch: number | null; highlight: number | null; onPick: (index: number) => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<{ row: number; column: number } | null>(null);
  const columns = data.epochs.length;
  useEffect(() => {
    const target = canvas.current;
    if (!target) return;
    const width = target.clientWidth || 800;
    target.width = width;
    target.height = HEAT_H;
    // 1) Imagen completa (una fila por célula) → 2) reducción vertical con suavizado (promedia filas) → 3) ampliación horizontal nítida.
    const full = document.createElement('canvas');
    full.width = columns; full.height = order.length;
    const fullCtx = full.getContext('2d');
    const ctx = target.getContext('2d');
    if (!fullCtx || !ctx) return;
    const image = fullCtx.createImageData(columns, order.length);
    order.forEach((item, row) => data.scores[item.index].forEach((score, column) => {
      const [r, g, b] = color(trueClassProbability(item.label, score));
      const at = 4 * (row * columns + column);
      image.data.set([r, g, b, 255], at);
    }));
    fullCtx.putImageData(image, 0, 0);
    const reduced = document.createElement('canvas');
    reduced.width = columns; reduced.height = Math.min(order.length, HEAT_H);
    const reducedCtx = reduced.getContext('2d');
    if (!reducedCtx) return;
    reducedCtx.imageSmoothingEnabled = true;
    reducedCtx.drawImage(full, 0, 0, columns, reduced.height);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(reduced, 0, 0, width, HEAT_H);
    const x = (epoch: number) => (data.epochs.findIndex(item => item.epoch === epoch) + 0.5) * width / columns;
    const fine = fineTuneStart(data.epochs);
    ctx.lineWidth = 2;
    if (fine != null) { ctx.strokeStyle = 'rgba(255,255,255,.85)'; ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(x(fine) - width / columns / 2, 0); ctx.lineTo(x(fine) - width / columns / 2, HEAT_H); ctx.stroke(); }
    ctx.setLineDash([]);
    if (selectedEpoch != null && data.epochs.some(item => item.epoch === selectedEpoch)) { ctx.strokeStyle = 'rgba(255,255,255,.95)'; ctx.strokeRect(x(selectedEpoch) - width / columns / 2, 0, width / columns, HEAT_H); }
    const split = order.findIndex(item => item.label === 0);
    if (split > 0) { ctx.fillStyle = 'rgba(255,255,255,.9)'; ctx.fillRect(0, split * HEAT_H / order.length - 1, width, 2); }
    if (highlight != null) {
      const row = order.findIndex(item => item.index === highlight);
      if (row >= 0) { ctx.strokeStyle = '#fff'; ctx.strokeRect(0.5, row * HEAT_H / order.length - 2, width - 1, Math.max(4, HEAT_H / order.length + 2)); }
    }
  }, [data, order, columns, selectedEpoch, highlight]);
  const position = (event: MouseEvent<HTMLCanvasElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    return { row: Math.min(order.length - 1, Math.floor((event.clientY - box.top) / box.height * order.length)),
      column: Math.min(columns - 1, Math.floor((event.clientX - box.left) / box.width * columns)) };
  };
  const hovered = hover ? order[hover.row] : null;
  const hoveredScore = hover && hovered ? data.scores[hovered.index][hover.column] : null;
  return <figure className="mt-heat">
    <div className="mt-heat-axis"><span>Parasitadas</span><span>No parasitadas</span></div>
    <canvas ref={canvas} className="mt-heat-canvas" role="img" aria-label={`Mapa de ${order.length} células por ${columns} épocas: probabilidad asignada a la clase real`}
      onMouseMove={event => setHover(position(event))} onMouseLeave={() => setHover(null)} onClick={event => onPick(order[position(event).row].index)} />
    <figcaption className="mt-heat-caption">
      <span className="mt-heat-legend"><i data-tone="wrong" />0 · clase equivocada<i data-tone="mid" />0,5<i data-tone="right" />1 · clase real</span>
      <span aria-live="polite">{hovered && hover ? `Época ${data.epochs[hover.column].epoch} · ${hovered.sample.split('/').pop()} · P(clase real) ${pct(trueClassProbability(hovered.label, hoveredScore))}` : `Filas ordenadas por clase y época de aprendizaje (${order.length.toLocaleString('es-CL')} células; cada píxel promedia filas vecinas). Clic para ver una célula.`}</span>
    </figcaption>
  </figure>;
}

function TrajectoryPanel({ load, selectedEpoch, requestedSample }: { load: Load<TrainingTrajectories>; selectedEpoch: number | null; requestedSample: string | null }) {
  const data = load.data?.state === 'available' ? load.data : null;
  const items = useMemo(() => data ? sampleTrajectories(data) : [], [data]);
  const order = useMemo(() => orderTrajectories(items), [items]);
  const counts = useMemo(() => outcomeCounts(items), [items]);
  const accuracy = useMemo(() => data ? accuracyByEpoch(data) : [], [data]);
  const requested = useMemo(() => requestedSample ? items.find(item => item.sampleId === requestedSample)?.index ?? null : null, [items, requestedSample]);
  const [picked, setPicked] = useState<number | null>(null);
  const [filter, setFilter] = useState<TrajectoryOutcome | 'todas'>('todas');
  const current = picked ?? requested;
  if (load.state !== 'ready' || !load.data) return <><OriginTag origin="registrado" /><Status load={load} /></>;
  if (!data) return <><OriginTag origin="registrado" /><p className="mt-pending-note">{load.data.state === 'missing' ? 'Sin evidencia' : 'Trayectorias no publicables'}: {load.data.issues.join(' ')}</p></>;
  const final = accuracy.at(-1);
  const atCheckpoint = accuracy.find(item => item.epoch === selectedEpoch);
  const fine = fineTuneStart(data.epochs);
  const sample = current != null ? items[current] : null;
  const series = sample ? data.epochs.map((epoch, column) => ({ epoch: epoch.epoch, score: data.scores[sample.index][column] })) : [];
  const listed = order.filter(item => filter === 'todas' || item.outcome === filter).slice(0, 12);
  return <>
    <OriginTag origin="registrado" />
    <div className="mt-history-kpis">
      <div className="mt-fact"><div className="mt-k">Células VAL</div><div className="mt-v">{items.length.toLocaleString('es-CL')}<small>{data.epochs.length} épocas registradas</small></div></div>
      <div className="mt-fact"><div className="mt-k">Bien clasificadas · checkpoint</div><div className="mt-v">{pct(atCheckpoint?.all ?? null)}<small>{selectedEpoch != null ? `época ${selectedEpoch}` : 'sin checkpoint'}</small></div></div>
      <div className="mt-fact"><div className="mt-k">Bien clasificadas · última época</div><div className="mt-v">{pct(final?.all ?? null)}<small>época {final?.epoch}</small></div></div>
      {(Object.keys(OUTCOME_LABELS) as TrajectoryOutcome[]).map(outcome => <button key={outcome} type="button" className="mt-fact mt-fact-button" aria-pressed={filter === outcome}
        onClick={() => setFilter(value => value === outcome ? 'todas' : outcome)}><div className="mt-k">{OUTCOME_LABELS[outcome]}</div><div className="mt-v">{counts[outcome].toLocaleString('es-CL')}<small>{pct(counts[outcome] / items.length)}</small></div></button>)}
    </div>
    <TrajectoryHeatmap data={data} order={order} selectedEpoch={selectedEpoch} highlight={current} onPick={setPicked} />
    <div className="mt-history-grid">
      <section aria-label="Bien clasificadas por época">
        <div className="mt-sec-t">Bien clasificadas por época y clase</div>
        <div className="scc-chart"><ResponsiveContainer width="100%" height="100%">
          <LineChart data={accuracy} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="epoch" type="number" domain={['dataMin', 'dataMax']} allowDecimals={false} />
            <YAxis domain={[0, 1]} tickFormatter={(value: number) => `${Math.round(value * 100)}%`} width={44} />
            <Tooltip formatter={(value) => pct(Number(value))} labelFormatter={(label) => `Época ${label}`} />
            <Legend />
            <Line dataKey="parasitized" name="Parasitadas (sensibilidad)" stroke="var(--ds-red-500, #ef4444)" dot={false} isAnimationActive={false} />
            <Line dataKey="uninfected" name="No parasitadas (especificidad)" stroke="var(--ds-cyan-500, #06b6d4)" dot={false} isAnimationActive={false} />
            {fine != null && <ReferenceLine x={fine - 0.5} strokeDasharray="2 4" stroke="var(--ds-border-strong, #94a3b8)" label="Ajuste fino" />}
            {selectedEpoch != null && <ReferenceLine x={selectedEpoch} stroke="var(--ds-green-500, #22c55e)" label="Checkpoint" />}
          </LineChart>
        </ResponsiveContainer></div>
      </section>
      <section aria-label="Célula seleccionada">
        <div className="mt-sec-t">{sample ? `Célula · ${sample.sample.split('/').pop()}` : 'Célula'}</div>
        {sample ? <>
          <div className="scc-chart"><ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="epoch" type="number" domain={['dataMin', 'dataMax']} allowDecimals={false} />
              <YAxis domain={[0, 1]} width={36} />
              <Tooltip formatter={(value) => Number(value).toFixed(3)} labelFormatter={(label) => `Época ${label}`} />
              <Line dataKey="score" name="Score (P parasitada)" stroke="var(--ds-violet-500, #8b5cf6)" isAnimationActive={false} />
              <ReferenceLine y={data.training_threshold} strokeDasharray="4 4" stroke="var(--ds-border-strong, #94a3b8)" label={`Umbral TRAIN ${data.training_threshold}`} />
              {selectedEpoch != null && <ReferenceLine x={selectedEpoch} stroke="var(--ds-green-500, #22c55e)" />}
            </LineChart>
          </ResponsiveContainer></div>
          <p className="mt-cell-meta">Clase real {sample.label ? 'parasitada' : 'no parasitada'} · {OUTCOME_LABELS[sample.outcome]}{sample.learnedAt != null ? ` desde la época ${sample.learnedAt}` : ''} · {sample.flips} cambios de decisión · {sample.sampleId ? <code title={sample.sampleId}>{sample.sampleId.slice(0, 8)}</code> : 'sin sample_id gobernado'}</p>
        </> : <p className="mt-muted">Haz clic en una fila del mapa o en una célula de la lista.</p>}
        <div className="mt-sec-t">{filter === 'todas' ? 'Más inestables' : OUTCOME_LABELS[filter]} · primeras {listed.length}</div>
        <ul className="mt-cell-list">{(filter === 'todas' ? [...items].sort((a, b) => b.flips - a.flips).slice(0, 12) : listed).map(item => <li key={item.index}>
          <button type="button" aria-pressed={item.index === current} onClick={() => setPicked(item.index)}>
            <span data-label={item.label}>{item.label ? 'P' : 'N'}</span>{item.sample.split('/').pop()}<small>{item.flips} cambios</small></button></li>)}</ul>
      </section>
    </div>
    <p className="scc-meta">Scores de la pasada VAL que TRAIN ejecutó al cerrar cada época (umbral {data.training_threshold}, no el umbral clínico calibrado). VAL también se usó para elegir el checkpoint: no acredita desempeño en TEST.{load.data.issues.length ? ` ${load.data.issues.join(' ')}` : ''}</p>
  </>;
}

/* ── Análisis desde checkpoints ───────────────────────────────────────────── */

function CheckpointAnalyses() {
  return <>
    <p className="mt-history-lead">Estos análisis se calculan desde los checkpoints <code>.keras</code> que TRAIN guardó en cada época (pesos y estado del optimizador), sin volver a entrenar. Aún no hay resultados calculados para este TRAIN.</p>
    <div className="mt-analysis-grid">{CHECKPOINT_ANALYSES.map(item => <div key={item.title} className="mt-analysis" data-origin={item.origin}>
      <OriginTag origin={item.origin} />
      <h3>{item.title}</h3>
      <p>{item.question}</p>
      <p className="mt-muted">{item.source}</p>
      <span className="mt-analysis-state">{item.origin === 'sin_evidencia' ? 'No demostrable' : 'Pendiente de cálculo'}</span>
    </div>)}</div>
  </>;
}
