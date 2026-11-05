import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../../auth';
import { useComparisonSelection } from '../../hooks/useComparisonSelection';
import { withAllowedQuery, routes } from '../../router';
import { api } from '../../services/api';
import type { ActivationTrace, ActivationTraceCandidate, ActivationTraceCatalog, ActivationTraceStep, TraceCategory } from '../../types/activationTrace';
import type { ModelArchitecture } from '../../types/modelArchitecture';
import type { BlockActivity } from './ArchitectureChart';
import type { CurveEvidence } from '../../types/scientificReport';
import { CopyText } from '../reports/ComparisonPython';
import { GeneratedXAIComparison } from '../reports/GeneratedXAIComparison';
import { useCellComparison, useExpandRequest } from '../reports/useCellComparison';
import { layerOperations } from './mathOperations';
import { MiniCurves, ScoreBar, StepProfile, VectorHistogram } from './TraceCharts';
import { CIVIDIS_GRADIENT, paintMap, type MapScale } from './traceColor';
import { stepCode, stepLayers, stepTitle } from './traceCode';
import { megabytes, number, percent, points, stepChange, traceCategories } from './traceSteps';

const PLAY_MS = 1400;
const png = (data: string) => `data:image/png;base64,${data}`;
const message = (cause: unknown, fallback: string) => cause instanceof Error ? cause.message : fallback;
const shortId = (id: string) => `${id.slice(0, 8)}…`;
/** Two decimals for readable magnitudes; small values keep two significant digits instead of rounding to zero. */
const stat = (value: number) => Math.abs(value) > 0 && Math.abs(value) < 0.01 ? value.toLocaleString('es-CL', { maximumSignificantDigits: 2 }) : number(value, 2);
const shapeOf = (shape: number[]) => shape.join(' × ');
/** Drawn block of a step: the head is drawn layer by layer, so its steps answer to their own layer. */
const drawnBlock = (architecture: ModelArchitecture, step: ActivationTraceStep | null) =>
  !step ? 'input' : architecture.blocks.some(block => block.id === step.layer) ? step.layer : step.block;

type Outcome = TraceCategory | 'unknown';
const outcomeKey = ({ label, predicted }: { label: number | null; predicted: number | null }): Outcome =>
  label == null || predicted == null ? 'unknown' : label ? (predicted ? 'true_positive' : 'false_negative') : (predicted ? 'false_positive' : 'true_negative');
const outcomeLabel = (key: Outcome) => key === 'unknown' ? 'Sin evidencia' : traceCategories[key];
const tones: Record<Outcome, string> = { false_negative: 'wine', true_positive: 'green', false_positive: 'amber', true_negative: 'slate', unknown: 'slate' };

function Outcome({ value }: { value: { label: number | null; predicted: number | null } }) {
  const key = outcomeKey(value);
  return <span className="mx-outcome" data-tone={tones[key]}>{outcomeLabel(key)}</span>;
}

/** Native modal: focus trap, Escape and backdrop come from the browser. */
function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return <dialog ref={ref} className="mx-dialog" aria-label={title} onClose={onClose} onClick={event => { if (event.target === ref.current) onClose(); }}>
    <header><h4>{title}</h4><button type="button" className="ds-button" data-size="compact" aria-label="Cerrar" onClick={onClose}>×</button></header>
    <div className="mx-dialog-body">{children}</div>
  </dialog>;
}

function MapCanvas({ map, layer, scale, label }: { map: ActivationTraceStep['maps'][number]; layer: { min: number; max: number }; scale: MapScale; label: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => { if (ref.current) void paintMap(ref.current, map.png, map, layer, scale).catch(() => undefined); }, [map, layer, scale]);
  return <canvas ref={ref} role="img" aria-label={label} />;
}

function SpatialMaps({ step, scale, onScale, picked, onPick }: { step: ActivationTraceStep; scale: MapScale; onScale: (scale: MapScale) => void; picked: number | null; onPick: (channel: number | null) => void }) {
  // ViT: each map is one token dimension over the patch grid; a CNN map is one channel.
  const unit = step.tokens != null ? 'Dimensión' : 'Canal', units = step.tokens != null ? 'dimensiones' : 'canales';
  const attention = step.attention ? { channel: -1, mean: 0, png: step.attention.png, min: step.attention.min, max: step.attention.max } : null;
  const ranged = step.maps.every(map => map.min != null && map.max != null);
  const effective: MapScale = ranged ? scale : 'channel';
  const layer = useMemo(() => ranged ? { min: Math.min(...step.maps.map(map => map.min!)), max: Math.max(...step.maps.map(map => map.max!)) } : { min: 0, max: 1 }, [ranged, step.maps]);
  return <>
    {step.tokens != null && <div className="mx-vit-summary">
      {attention && <figure className="mx-attention"><MapCanvas map={attention} layer={{ min: attention.min, max: attention.max }} scale="channel" label="Atención del token de clase sobre los parches" />
        <figcaption>Atención del token de clase sobre los {step.shape[0]}×{step.shape[1]} parches (promedio de las cabezas): dónde mira, no qué causa la predicción.</figcaption></figure>}
      <dl className="mx-stats mx-stats--stack">
        <div><dt>Tokens</dt><dd>{step.tokens} × {step.shape[2]}</dd></div>
        {step.cls_similarity != null && <div><dt>CLS vs. último bloque</dt><dd>{number(step.cls_similarity, 3)}</dd></div>}
      </dl>
    </div>}
    <div className="mx-maps-toolbar">
      <div className="scc-segmented" role="group" aria-label="Escala de color">
        <button type="button" className="ds-button" data-size="compact" aria-pressed={effective === 'layer'} disabled={!ranged} onClick={() => onScale('layer')}>Escala común</button>
        <button type="button" className="ds-button" data-size="compact" aria-pressed={effective === 'channel'} onClick={() => onScale('channel')}>Por {unit.toLowerCase()}</button>
      </div>
      <div className="mx-colorbar" aria-label="Leyenda de color"><span>{effective === 'layer' ? stat(layer.min) : 'mín.'}</span>
        <i style={{ background: CIVIDIS_GRADIENT }} /><span>{effective === 'layer' ? stat(layer.max) : 'máx.'}</span></div>
    </div>
    <ol className="mx-maps">{step.maps.map((map, rank) => <li key={map.channel}>
      <button type="button" aria-pressed={picked === map.channel} title={`${unit} ${map.channel} · media ${stat(map.mean)}${map.max != null ? ` · máx. ${stat(map.max)}` : ''}`}
        onClick={() => onPick(picked === map.channel ? null : map.channel)}>
        <MapCanvas map={map} layer={layer} scale={effective} label={`${unit} ${map.channel}`} />
        <span className="mx-map-caption"><b>#{map.channel}</b><small>{rank + 1}º · μ {stat(map.mean)}</small></span>
      </button></li>)}</ol>
    <p className="scc-meta">{effective === 'layer' ? `Todas las ${units} comparten la escala de la capa: un mapa más claro es un valor mayor.` : `Cada mapa usa su propia escala: muestra dónde es alta una ${unit.toLowerCase()}, no cuánto respecto de otras.`}
      {!ranged && ' Este recorrido es anterior a la escala común; vuelve a calcularlo para habilitarla.'} Selecciona {step.tokens != null ? 'una dimensión' : 'un canal'} para proyectarla sobre la célula.</p>
  </>;
}

/** Where to compare this trace with the explanations: Grad-CAM weighs the last convolutional block; a ViT has none. */
function explainHint(architecture: ModelArchitecture): string {
  if (architecture.family === 'biomedclip') return 'En un ViT no aplica Grad-CAM: compara la atención del token de clase de los últimos bloques con LIME y SHAP de esta célula.';
  const last = [...architecture.blocks].reverse().find(block => ['convolution', 'dense', 'transition'].includes(block.kind));
  return `Grad-CAM pondera los mapas del último bloque convolucional. Compáralos con los canales de ${last?.label ?? 'ese bloque'} de esta célula.`;
}

/** The cell image as the access to «Vista ampliada» (rule: every cell image opens it, unless its EVALUATE context is missing). */
function CellImage({ trace, alt, onOpen, pending }: { trace: ActivationTrace; alt: string; onOpen?: () => void; pending?: boolean }) {
  const image = <img src={png(trace.input_image)} alt={alt} />;
  return onOpen ? <button type="button" className="mx-cell-open" onClick={onOpen} aria-busy={pending} aria-label="Ampliar Célula original"
    title={pending ? 'Abriendo «Vista ampliada»…' : 'Vista ampliada: célula original y explicabilidad'}>{image}</button> : image;
}

function StepBody({ trace, index, inputShape, scale, onScale, picked, onPick, onOpen, pending, vit }: { trace: ActivationTrace; index: number; inputShape: number[]; scale: MapScale; onScale: (scale: MapScale) => void; picked: number | null; onPick: (channel: number | null) => void; onOpen?: () => void; pending?: boolean; vit?: boolean }) {
  if (index === 0) return <div className="mx-input-body"><CellImage trace={trace} alt="Célula original a tamaño de entrada" onOpen={onOpen} pending={pending} />
    {vit
      ? <p>La imagen entra como un tensor de {shapeOf(inputShape)} y se corta en parches cuadrados: cada parche, más un token de clase, es un vector de la misma dimensión. Los bloques no cambian esa forma; cambian lo que representa cada token.</p>
      :     <p>La imagen entra como un tensor de {shapeOf(inputShape)}, uno por canal de color. Cada bloque siguiente reduce el tamaño a la mitad y multiplica los canales: el modelo cambia resolución espacial por cantidad de patrones.</p>}</div>;
  const step = trace.steps[index - 1];
  if (step.kind === 'spatial') return <SpatialMaps step={step} scale={scale} onScale={onScale} picked={picked} onPick={onPick} />;
  if (step.kind === 'output') return <div className="mx-output-body">
    <p className="mx-big-number"><span>p(parasitada)</span><strong>{number(trace.score, 3)}</strong></p>
    <ScoreBar score={trace.score} threshold={trace.threshold} tone={tones[outcomeKey(trace)]} />
    <dl className="mx-stats"><div><dt>Logit z</dt><dd>{stat(trace.logit)}</dd></div><div><dt>σ(z)</dt><dd>{number(trace.score, 4)}</dd></div>
      <div><dt>Umbral</dt><dd>{trace.threshold == null ? 'Sin evidencia' : number(trace.threshold, 3)}</dd></div><div><dt>Resultado</dt><dd><Outcome value={trace} /></dd></div></dl>
    {!trace.consistent && <p className="ds-callout" data-tone="warning" role="alert">El score recalculado ({number(trace.score)}) no coincide con el guardado en la evaluación ({number(trace.persisted_score)}).</p>}
  </div>;
  return <div className="mx-vector-body">
    {step.histogram ? <VectorHistogram histogram={step.histogram} /> : null}
    <div><h5>Neuronas con mayor |valor|</h5><ol className="mx-trace-top">{step.top.slice(0, 8).map(item => <li key={item.index}><span>#{item.index}</span><strong>{stat(item.value)}</strong></li>)}</ol></div>
  </div>;
}

/** Saved forward passes of one TRAIN. Opening it reads files only; the model runs when «Calcular» is pressed. */
export function ActivationTracePanel({ runId, datasource, onBlock, architecture, blockClick, onActivity, onSample }: { runId: string; datasource: string; onBlock: (id: string) => void;
  architecture: ModelArchitecture; blockClick?: { id: string; n: number } | null; onActivity?: (activity: BlockActivity | null) => void;
  /** Informa la célula abierta, para que otras vistas (Entrenamiento) muestren la misma. */
  onSample?: (sampleId: string | null) => void }) {
  const { user } = useAuth();
  const selection = useComparisonSelection();
  const canCalculate = Boolean(user?.permissions?.includes('scientific.cell_classification.explain'));
  const [catalog, setCatalog] = useState<ActivationTraceCatalog | null>(null);
  const [category, setCategory] = useState<TraceCategory>('false_negative');
  const [explainedOnly, setExplainedOnly] = useState(false);
  const [candidates, setCandidates] = useState<ActivationTraceCandidate[] | null>(null);
  const [trace, setTrace] = useState<ActivationTrace | null>(null);
  // «Vista ampliada» of the open cell: its EVALUATE context, read once per cell.
  const { comparison, contextError } = useCellComparison(runId, trace);
  const { signal: expandSignal, request: openExpanded, pending: expandPending } = useExpandRequest(Boolean(comparison));
  const openCell = trace && !contextError ? openExpanded : undefined;
  const [compare, setCompare] = useState<ActivationTrace | null>(null);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [scale, setScale] = useState<MapScale>('layer');
  const [picked, setPicked] = useState<number | null>(null);
  const [dialog, setDialog] = useState<'pick' | 'saved' | null>(null);
  const [calculating, setCalculating] = useState<string | null>(null);
  const [curve, setCurve] = useState<CurveEvidence | null | 'loading'>(null);
  const [context, setContext] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = useCallback(async (sampleId: string) => {
    setError(null); setPlaying(false);
    try { setTrace(await api.getActivationTrace(runId, sampleId)); setIndex(0); setPicked(null); setDialog(null); }
    catch (cause) { setError(message(cause, 'No fue posible abrir el recorrido.')); }
  }, [runId]);

  const refresh = useCallback(async () => {
    const next = await api.getActivationTraces(datasource, runId);
    setCatalog(next);
    return next;
  }, [datasource, runId]);

  useEffect(() => {
    let active = true;
    setTrace(null); setCompare(null); setCatalog(null); setPlaying(false); setCurve(null);
    // The latest saved trace opens by itself: returning to the RUN shows the work already done.
    refresh().then(next => { if (active && next.items[0]) void open(next.items[0].sample_id); })
      .catch(cause => { if (active) setError(message(cause, 'No fue posible consultar los recorridos.')); });
    return () => { active = false; };
  }, [refresh, open]);

  useEffect(() => { onSample?.(trace?.sample_id ?? null); }, [trace?.sample_id, onSample]);

  const available = catalog?.available;
  useEffect(() => {
    if (!available || dialog !== 'pick') return;
    const controller = new AbortController();
    setCandidates(null);
    api.getActivationTraceCandidates(datasource, runId, category, controller.signal, { limit: 24, explained: explainedOnly }).then(setCandidates)
      .catch(cause => { if (!controller.signal.aborted) { setCandidates([]); setError(message(cause, 'No fue posible listar células.')); } });
    return () => controller.abort();
  }, [available, category, explainedOnly, datasource, runId, dialog]);

  const total = trace ? trace.steps.length + 1 : 0;
  const step = trace && index > 0 ? trace.steps[index - 1] : null;
  useEffect(() => { if (trace) onBlock(drawnBlock(architecture, step)); }, [trace, step, onBlock, architecture]);
  useEffect(() => {
    if (!playing) return;
    if (index >= total - 1) { setPlaying(false); return; }
    const timer = window.setTimeout(() => setIndex(value => value + 1), PLAY_MS);
    return () => window.clearTimeout(timer);
  }, [playing, index, total]);
  // The open cell annotates the drawing: share of active values under each block, p under the output.
  useEffect(() => {
    if (!onActivity) return;
    onActivity(trace ? Object.fromEntries(trace.steps.map((item, position) => [drawnBlock(architecture, item), item.kind === 'output'
      ? { value: trace.score, label: `p ${number(trace.score, 3)}`, current: position + 1 === index }
      : { value: item.stats.active, label: `${percent(item.stats.active)} activos`, current: position + 1 === index }])) : null);
  }, [trace, index, architecture, onActivity]);
  useEffect(() => () => onActivity?.(null), [onActivity]);
  // The architecture drawing is the navigator: a block opens its first step; clicking it again walks the steps it holds.
  const handled = useRef(blockClick?.n ?? 0);
  useEffect(() => {
    if (!blockClick || blockClick.n === handled.current || !trace) return;
    handled.current = blockClick.n;
    const positions = [0, ...trace.steps.map((_, position) => position + 1)].filter(position => drawnBlock(architecture, position ? trace.steps[position - 1] : null) === blockClick.id);
    if (!positions.length) return;
    setPlaying(false);
    setIndex(current => positions.includes(current) ? positions[(positions.indexOf(current) + 1) % positions.length] : positions[0]);
  }, [blockClick, trace, architecture]);
  useEffect(() => { if (step?.kind !== 'spatial' || !step.maps.some(map => map.channel === picked)) setPicked(null); }, [step, picked]);

  const go = (next: number) => { setPlaying(false); setIndex(Math.min(total - 1, Math.max(0, next))); };
  const onKeys = (event: KeyboardEvent) => {
    if ((event.target as HTMLElement).closest('select, input, dialog, textarea')) return;
    if (event.key === 'ArrowRight') { event.preventDefault(); go(index + 1); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); go(index - 1); }
  };

  const calculate = async (sampleId: string) => {
    setCalculating(sampleId); setError(null);
    try {
      const created = await api.createActivationTrace(datasource, runId, sampleId);
      setTrace(created); setIndex(0); setPlaying(false); setPicked(null); setDialog(null);
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
      if (compare?.sample_id === sampleId) setCompare(null);
      await refresh();
    } catch (cause) { setError(message(cause, 'No fue posible eliminar el recorrido.')); }
  };
  const compareWith = async (sampleId: string) => {
    setError(null);
    try { setCompare(sampleId ? await api.getActivationTrace(runId, sampleId) : null); if (sampleId) setContext(true); }
    catch (cause) { setError(message(cause, 'No fue posible abrir el recorrido a comparar.')); }
  };
  const loadCurve = () => {
    if (curve) return;
    setCurve('loading');
    api.getComparisonReport<CurveEvidence[]>(datasource, { module: 'curves', selections: [{ training_run_id: runId }] })
      .then(response => setCurve(response.data[0] ?? null)).catch(() => setCurve(null));
  };
  // Analysis reads the RUN from the shared selection: add it before leaving so the destination opens on this model.
  const selectRun = () => { if (!selection.ids.includes(runId)) selection.add(runId, selection.ids.length + 1); };

  if (catalog && !catalog.available) return null;
  const saved = new Set(catalog?.items.map(item => item.sample_id));
  const labels = trace ? ['Entrada', ...trace.steps.map(item => stepTitle(architecture, item).replace('Bloque ', 'B'))] : [];
  const actives = (value: ActivationTrace) => [null, ...value.steps.map(item => item.kind === 'output' ? null : item.stats.active)];
  const change = trace && index > 0 ? stepChange(trace.steps, index - 1) : null;
  const inputShape = (architecture.input_shape ?? []).slice(1).filter((value): value is number => value != null);
  const previousShape = trace && index > 1 ? trace.steps[index - 2].shape : index === 1 ? inputShape : null;
  const operations = step ? layerOperations(architecture, stepLayers(architecture, step)) : [];
  const compareStep = compare && index > 0 ? compare.steps[index - 1] : null;
  const pickedMap = step?.maps.find(map => map.channel === picked);
  const blockId = drawnBlock(architecture, step);
  const blockLabel = architecture.blocks.find(item => item.id === blockId)?.label ?? stepTitle(architecture, step);
  const siblings = trace ? [0, ...trace.steps.map((_, position) => position + 1)].filter(position => drawnBlock(architecture, position ? trace.steps[position - 1] : null) === blockId) : [];

  return <section className="report-section mx-trace" aria-label="Recorrido de una célula" onKeyDown={onKeys}>
    <header className="mx-trace-head">
      <div><h3>Recorrido de una célula</h3>
        <p>Una célula de {catalog?.split?.toUpperCase() ?? 'VAL'} atraviesa el modelo bloque por bloque. Es una ilustración: muestra cómo este checkpoint procesa una imagen, no cómo aprendió.</p></div>
      <div className="mx-trace-actions">
        {canCalculate && <button type="button" className="ds-button" data-variant="primary" onClick={() => setDialog('pick')}>Elegir célula</button>}
        <button type="button" className="ds-button" onClick={() => setDialog('saved')} disabled={!catalog}>Guardados <span className="mx-count">{catalog?.items.length ?? 0}</span></button>
      </div>
    </header>
    <ul className="mx-chips" aria-label="Contexto del recorrido">
      <li>Split <b>{catalog?.split?.toUpperCase() ?? '—'}</b></li>
      <li>Checkpoint <b>{architecture.checkpoint.selected_epoch == null ? 'sin evidencia' : `época ${architecture.checkpoint.selected_epoch}`}</b></li>
      {trace?.threshold != null && <li>Umbral <b>{number(trace.threshold, 3)}</b></li>}
      {trace && <li>Célula <b title={trace.sample_id}>{shortId(trace.sample_id)}</b> <Outcome value={trace} /></li>}
    </ul>
    {error && <p className="ds-callout" data-tone="warning" role="alert">{error}</p>}

    {!trace && catalog && <div className="mx-empty"><p>{catalog.items.length ? 'Abre un recorrido guardado o elige una célula nueva.' : 'Aún no hay recorridos para este RUN.'}</p>
      {canCalculate && <button type="button" className="ds-button" data-variant="primary" onClick={() => setDialog('pick')}>Elegir célula</button>}</div>}

    {trace && <>
      <div className="mx-player" role="group" aria-label="Reproducción del recorrido">
        <button type="button" className="ds-button" data-size="compact" aria-label="Paso anterior" disabled={index === 0} onClick={() => go(index - 1)}>←</button>
        <button type="button" className="ds-button" data-size="compact" onClick={() => { if (index >= total - 1) setIndex(0); setPlaying(!playing); }}>{playing ? 'Pausar' : 'Reproducir'}</button>
        <button type="button" className="ds-button" data-size="compact" aria-label="Paso siguiente" disabled={index >= total - 1} onClick={() => go(index + 1)}>→</button>
        <span className="mx-player-step" aria-live="polite">Paso {index + 1} de {total} · <b>{blockLabel}</b>{siblings.length > 1 && <> · {siblings.indexOf(index) + 1} de {siblings.length}: {stepTitle(architecture, step)}</>}</span>
        <span className="scc-meta">Selecciona un bloque del diagrama para ir a su paso.</span>
        {playing && <span key={index} className="mx-player-progress" style={{ animationDuration: `${PLAY_MS}ms` }} aria-hidden="true" />}
      </div>

      <div className="mx-stage">
        <aside className="mx-specimen" aria-label="Célula">
          <figure>
            <div className="mx-specimen-frame">
              <CellImage trace={trace} alt={`Célula ${trace.sample_id}`} onOpen={openCell} pending={expandPending} />
              {pickedMap && step && <MapCanvas key={`${index}-${picked}`} map={pickedMap} scale={scale}
                layer={{ min: Math.min(...step.maps.map(map => map.min ?? 0)), max: Math.max(...step.maps.map(map => map.max ?? 1)) }} label={`Canal ${picked} sobre la célula`} />}
            </div>
            <figcaption>{pickedMap ? step?.tokens != null ? <>Dimensión #{picked} proyectada (aprox.: el preprocesamiento recorta y reescala)</> : <>Canal #{picked} proyectado (aprox.: el pooling recorta bordes)</> : <>{trace.split.toUpperCase()} · {shortId(trace.sample_id)}</>}
              {contextError ? <> · «Vista ampliada» no disponible: {contextError}</> : <> · clic en la imagen para la vista ampliada</>}</figcaption>
          </figure>
          {comparison && <GeneratedXAIComparison key={comparison.id} comparison={comparison} datasource={datasource} variant="modal" lazy
            image={png(trace.input_image)} expandSignal={expandSignal} />}
          <dl className="mx-stats mx-stats--stack">
            <div><dt>Etiqueta real</dt><dd>{trace.label == null ? 'Sin evidencia' : trace.label ? 'Parasitada' : 'No parasitada'}</dd></div>
            <div><dt>Predicción</dt><dd><Outcome value={trace} /></dd></div>
          </dl>
          <ScoreBar score={trace.score} threshold={trace.threshold} tone={tones[outcomeKey(trace)]} />
          {outcomeKey(trace) === 'false_negative' && trace.threshold != null && <p className="mx-note">Le faltaron {number(trace.threshold - trace.score, 3)} para ser detectada: es el error de mayor costo clínico.</p>}
        </aside>

        <div className="mx-step" key={index} aria-live="polite">
          <header>
            <h4>{stepTitle(architecture, step)} {step && <code>{step.layer}</code>}</h4>
            <p className="mx-shape">{previousShape && <>{shapeOf(previousShape)} <span aria-hidden="true">→</span> </>}<b>{step ? shapeOf(step.shape) : shapeOf(inputShape)}</b></p>
          </header>
          {step && step.kind !== 'output' && <dl className="mx-stats">
            <div><dt>Media</dt><dd>{stat(step.stats.mean)}</dd></div><div><dt>Máximo</dt><dd>{stat(step.stats.max)}</dd></div>
            <div><dt>Valores activos</dt><dd>{percent(step.stats.active)}</dd></div>
            {change && <div><dt>Δ activos vs. paso anterior</dt><dd data-trend={change.active >= 0 ? 'up' : 'down'}>{change.active >= 0 ? '+' : ''}{points(change.active)}</dd></div>}
            {compareStep && compareStep.kind !== 'output' && <div data-compare><dt>Activos · {outcomeLabel(outcomeKey(compare!))}</dt><dd>{percent(compareStep.stats.active)}</dd></div>}
          </dl>}
          <StepBody trace={trace} index={index} inputShape={inputShape} scale={scale} onScale={setScale} picked={picked} onPick={setPicked} onOpen={openCell} pending={expandPending} vit={architecture.family === 'biomedclip'} />
          <p className="scc-meta">{step?.kind === 'spatial' ? `${trace.selection} de ${step.shape[2]}.` : ''} Valores calculados con este checkpoint para una sola célula: lo observado es una hipótesis, no una conclusión sobre el modelo.</p>
        </div>

        <aside className="mx-explain" aria-label="Qué ocurre en este paso">
          <h5>Operación</h5>
          {index === 0 ? <p className="mx-explain-text">Sin pesos: el preprocesamiento del contrato de entrada deja la imagen lista para el primer bloque.</p>
            : operations.length ? <ol className="mx-operations">{operations.map(operation => <li key={operation.id}>
              <div><strong>{operation.title}{operation.count > 1 ? ` × ${operation.count}` : ''}</strong><small>{operation.detail}</small></div>{operation.formula}</li>)}</ol>
            : <p className="mx-explain-text">El TRAIN no registró la configuración de esta capa.</p>}
          <h5>Código Keras</h5>
          <pre className="mx-code"><code>{stepCode(architecture, step)}</code></pre>
          <CopyText text={stepCode(architecture, step)} label="Copiar código" />
        </aside>
      </div>

      <details className="mx-context" open={context} onToggle={event => { const opened = (event.target as HTMLDetailsElement).open; setContext(opened); if (opened) loadCurve(); }}>
        <summary>Comparar con otra célula y ver contexto del entrenamiento</summary>
        <div className="mx-context-grid">
          <section aria-label="Comparación"><h5>Valores activos por paso</h5>
            <label className="mx-filter">Comparar con<select className="ds-control" value={compare?.sample_id ?? ''} onChange={event => void compareWith(event.target.value)}>
              <option value="">Sin comparación</option>
              {catalog?.items.filter(item => item.sample_id !== trace.sample_id).map(item => <option key={item.sample_id} value={item.sample_id}>{outcomeLabel(outcomeKey(item))} · {number(item.score, 3)} · {shortId(item.sample_id)}</option>)}
            </select></label>
            <StepProfile labels={labels} index={index} onPick={go} series={[{ label: `${outcomeLabel(outcomeKey(trace))} · ${shortId(trace.sample_id)}`, values: actives(trace), tone: 'current' },
              ...(compare ? [{ label: `${outcomeLabel(outcomeKey(compare))} · ${shortId(compare.sample_id)}`, values: actives(compare), tone: 'compare' as const }] : [])]} />
            <p className="scc-meta">Un falso negativo junto a un verdadero positivo muestra en qué bloque se separan sus señales.</p>
          </section>
          <section aria-label="Aprendizaje"><h5>¿De qué época es este checkpoint?</h5>
            {architecture.zero_shot ? <p className="scc-meta">Modelo zero-shot: no hubo entrenamiento ni épocas; el checkpoint es la versión registrada.</p>
              : curve === 'loading' ? <p role="status">Consultando curvas…</p> : curve ? <MiniCurves curve={curve} /> : <p className="scc-meta">Sin curvas registradas para este TRAIN.</p>}
            <Link className="ds-button" data-size="compact" onClick={selectRun} to={withAllowedQuery(routes.comparison, { datasource, seccion: 'aprendizaje' })}>Abrir Curvas TRAIN / VAL</Link>
          </section>
          <section aria-label="Explicabilidad"><h5>¿Qué miró el modelo?</h5>
            <p className="mx-explain-text">{explainHint(architecture)}</p>
            <Link className="ds-button" data-size="compact" onClick={selectRun} to={withAllowedQuery(routes.comparison, { datasource, seccion: 'explicabilidad', muestra: trace.sample_id })}>Ver explicabilidad de esta célula</Link>
          </section>
        </div>
      </details>
    </>}

    <Modal open={dialog === 'pick'} onClose={() => setDialog(null)} title={`Elegir célula de ${catalog?.split?.toUpperCase() ?? 'VAL'}`}>
      <div className="scc-segmented" role="group" aria-label="Tipo de resultado">{(Object.keys(traceCategories) as TraceCategory[]).map(item =>
        <button key={item} type="button" className="ds-button" data-size="compact" data-tone={tones[item]} aria-pressed={item === category} onClick={() => setCategory(item)}>{traceCategories[item]}</button>)}</div>
      <label className="mx-check"><input type="checkbox" checked={explainedOnly} onChange={event => setExplainedOnly(event.target.checked)} />Solo células con explicabilidad (XAI) generada</label>
      <p className="scc-meta">Ordenadas por distancia al umbral: primero las predicciones más seguras de su tipo.</p>
      {candidates == null ? <p role="status">Buscando células…</p> : candidates.length ? <ul className="mx-rows">{candidates.map(item => {
        const busy = calculating === item.sample_id, done = saved.has(item.sample_id);
        return <li key={item.sample_id}>
          <span className="mx-row-score"><ScoreBar score={item.score} threshold={item.threshold} tone={tones[category]} /></span>
          <span className="mx-row-id" title={item.sample_id}><b>{number(item.score, 3)}</b> {shortId(item.sample_id)}</span>
          {item.explained && <span className="mx-badge">XAI</span>}
          <button type="button" className="ds-button" data-size="compact" data-variant={done ? undefined : 'primary'} disabled={Boolean(calculating)}
            onClick={() => void (done ? open(item.sample_id) : calculate(item.sample_id))}>{busy ? 'Calculando…' : done ? 'Ver' : 'Calcular'}</button>
        </li>;
      })}</ul> : <p className="scc-meta">Sin células de este tipo{explainedOnly ? ' con explicabilidad' : ''}.</p>}
      {calculating && <p className="scc-meta" role="status">Se carga el modelo y se ejecuta una pasada hacia adelante; puede tardar hasta dos minutos.</p>}
    </Modal>

    <Modal open={dialog === 'saved'} onClose={() => setDialog(null)} title="Recorridos guardados">
      {catalog && <div className="mx-storage"><span>{megabytes(catalog.used_bytes)} de {megabytes(catalog.max_bytes)}</span>
        <i><b style={{ width: `${Math.min(100, catalog.used_bytes / catalog.max_bytes * 100)}%` }} /></i></div>}
      {catalog?.items.length ? <ul className="mx-rows">{catalog.items.map(item => <li key={item.sample_id} data-active={item.sample_id === trace?.sample_id}>
        <Outcome value={item} />
        <span className="mx-row-id" title={item.sample_id}><b>{number(item.score, 3)}</b> {shortId(item.sample_id)}</span>
        <span className="scc-meta">{new Date(item.created_at).toLocaleDateString('es-CL')}</span>
        <button type="button" className="ds-button" data-size="compact" onClick={() => void open(item.sample_id)}>Abrir</button>
        {trace && item.sample_id !== trace.sample_id && <button type="button" className="ds-button" data-size="compact" onClick={() => { void compareWith(item.sample_id); setDialog(null); }}>Comparar</button>}
        {canCalculate && <button type="button" className="ds-button" data-size="compact" aria-label={`Eliminar recorrido ${shortId(item.sample_id)}`} onClick={() => void remove(item.sample_id)}>×</button>}
      </li>)}</ul> : <p className="scc-meta">Aún no hay recorridos para este RUN.</p>}
    </Modal>
  </section>;
}
