import { groupXAIComparisons, type XAIComparison } from './xai/comparison';
import { GeneratedXAIComparison } from './GeneratedXAIComparison';
import { cellComparison } from './AssessmentXAI';
import { ConsensusSamplesTable } from './ConsensusSamplesTable';
import type { MRT_ColumnFiltersState, MRT_PaginationState, MRT_SortingState } from 'material-react-table';
import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, BarChart, Bar, ScatterChart, Scatter, LabelList, Cell } from 'recharts';
import { api } from '../../services/api';
import { useComparisonEvidence } from '../../hooks/useComparisonEvidence';
import { createComparisonCache, type ComparisonCache } from '../../utils/comparisonCache';
import type { RequestedSelection } from '../../types/scientificPreflight';
import type { CatalogEvidence, ClinicalEvidence, CurveEvidence, MetricsEvidence, ConsensusEvidence, ReportModule, ReportRequest, ReportResponse, EvaluationChoice } from '../../types/scientificReport';
import { CopyText } from './ComparisonPython';
import { useExplainExecutor } from '../../hooks/useExplainExecutor';
import { EvidenceButton, Kpi, SectionAnswer } from './AnalysisWorkspace';
import { consensusSummary, curveSummary, intensity, metricRange } from '../../utils/analysisSummaries';
import { choiceKey, defaultEvaluationSlot, effectiveSlot, evaluationSlots, explainMethods, groupEvaluations, groupExplanations, isAssessmentExplanation, roleLabels, splitExplanations, type EvaluationSlot } from '../../utils/lineageSlots';
import type { AssessmentExplanationChild } from '../../types/api';

const runLabel = (index: number) => `RUN ${String.fromCharCode(65 + index)}`;
const value = (n: number | null | undefined) => n == null ? 'Sin evidencia' : n.toLocaleString('es-CL', {maximumFractionDigits: 6});
const colors = ['var(--ds-blue-500)', 'var(--ds-green-700)', 'var(--ds-violet-700)', 'var(--ds-amber-700)'];
const percent = (n: number | null | undefined) => n == null ? 'Sin evidencia' : `${(n * 100).toLocaleString('es-CL', {maximumFractionDigits: 1})} %`;
const listText = (items: string[]) => items.length > 1 ? `${items.slice(0, -1).join(', ')} y ${items.at(-1)}` : items[0] ?? '';
const short = (n: number | null | undefined) => n == null ? '—' : n.toLocaleString('es-CL', {maximumFractionDigits: 3});
export function evaluationSelection(item: EvaluationChoice): RequestedSelection {
  return { training_run_id: item.training_run_id, split: item.split,
    ...(item.checkpoint_artifact_id ? {checkpoint_artifact_id: item.checkpoint_artifact_id} : {}),
    ...(item.evaluation_id ? {evaluation: {source: 'evaluations' as const, evaluation_id: item.evaluation_id}}
      : item.attempt_id && item.identity_id ? {evaluation: {source: 'assessment' as const, attempt_id: item.attempt_id, identity_id: item.identity_id}} : {}) };
}
const when = (iso: string) => new Date(iso).toLocaleString('es-CL', {dateStyle: 'short', timeStyle: 'short'});
const choiceText = (choice: EvaluationChoice, index: number) => choice.evaluation_role === 'independent_evaluate'
  ? `#${index + 1} · ${when(choice.created_at)} · ${choice.purpose}` : `${roleLabels[choice.evaluation_role] ?? choice.evaluation_role} · ${when(choice.created_at)}`;
const explanationText = (child: AssessmentExplanationChild) => `#${child.ordinal} · ${child.split.toUpperCase()} · ${when(child.started_at)} · ${child.state}${child.result_count != null ? ` · ${value(child.result_count)} ${child.result_count === 1 ? 'resultado' : 'resultados'}` : ''}`;
function SlotChoice<T>({label, items, current, keyOf, text, onPick}: {label: string; items: T[]; current?: T; keyOf: (item: T) => string; text: (item: T, index: number) => string; onPick: (key: string) => void}) {
  if (!items.length) return <span className="scc-meta">Sin ejecución</span>;
  if (items.length === 1) return <span className="scc-slot-value">{text(items[0], 0)}</span>;
  return <select className="ds-control" aria-label={`${label}: ejecución`} value={current ? keyOf(current) : ''} onChange={event => onPick(event.target.value)}>
    {items.map((item, index) => <option key={keyOf(item)} value={keyOf(item)}>{text(item, index)}</option>)}
  </select>;
}
export function EvaluationNavigation({id, datasource, protocol = defaultEvaluationSlot, lineageRevision = 0, onChange, onExplainChange}: {id: string; datasource: string; protocol?: EvaluationSlot; lineageRevision?: number; onChange: (selection: RequestedSelection) => void; onExplainChange?: (id: string, attemptIds: string[]) => void}) {
  const cache = useMemo(createComparisonCache, [id, datasource]);
  const [revision, setRevision] = useState(0);
  const [override, setOverride] = useState<EvaluationSlot | null>(null);
  const [picked, setPicked] = useState<Partial<Record<EvaluationSlot, string>>>({});
  const [explainPicked, setExplainPicked] = useState<Record<string, string>>({});
  const {data, error, loading} = useComparisonEvidence(cache, JSON.stringify(['catalog', id, datasource, revision]), () => api.getComparisonReport<CatalogEvidence[]>(datasource, {module: 'catalog', selections: [{training_run_id: id}]}));
  const lineage = useComparisonEvidence(cache, JSON.stringify(['lineage', id, datasource, revision, lineageRevision]), async () => api.getTrainingLineageChildren({trainingRunId: id, datasource}));
  const catalog = data?.data[0];
  const groups = useMemo(() => groupEvaluations(catalog?.evaluations ?? []), [catalog]);
  // A new analysis protocol resets per-card overrides.
  useEffect(() => { setOverride(null); }, [protocol]);
  const slot = effectiveSlot(groups, protocol, override);
  const currentOf = (target: EvaluationSlot) => groups[target].find(choice => choiceKey(choice) === picked[target]) ?? groups[target][0];
  const selected = slot ? currentOf(slot) : undefined;
  useEffect(() => { if (selected) onChange(evaluationSelection(selected)); }, [selected, onChange]);
  const explanations = useMemo(() => groupExplanations((lineage.data?.explainabilities ?? []).filter(isAssessmentExplanation)), [lineage.data]);
  const explainParts = (method: string) => splitExplanations(explanations[method]);
  const explainOf = (method: string) => { const {population} = explainParts(method); return population.find(child => child.attempt_id === explainPicked[method]) ?? population[0]; };
  const explainIds = explainMethods.flatMap(method => [...(explainOf(method.id) ? [explainOf(method.id)!.attempt_id] : []), ...explainParts(method.id).cells.map(child => child.attempt_id)]).join(',');
  useEffect(() => { if (lineage.data) onExplainChange?.(id, explainIds ? explainIds.split(',') : []); }, [id, explainIds, lineage.data, onExplainChange]);
  return <div className="scc-evaluation-nav">
    {loading && <p role="status">Consultando evaluaciones…</p>}
    {error ? <p role="alert">Error al consultar evaluaciones. <button className="ds-button" onClick={() => setRevision(n => n+1)}>Reintentar</button></p> : null}
    {catalog && <>
      <p><strong>{catalog.governance.name ?? 'Dataset sin evidencia'}</strong><br />{catalog.governance.status} · {catalog.governance.grouping_strategy}</p>
      <ol className="scc-lineage-slots" aria-label="Linaje del TRAIN">
        {evaluationSlots.map(meta => <li key={meta.id} data-active={slot === meta.id} data-empty={!groups[meta.id].length}>
          <label className="scc-slot-use" title={meta.detail}><input type="radio" name={`scc-evaluation-${id}`} checked={slot === meta.id} disabled={!groups[meta.id].length} onChange={() => setOverride(meta.id)} /><strong>{meta.label}</strong></label>
          <SlotChoice label={meta.label} items={groups[meta.id]} current={currentOf(meta.id)} keyOf={choiceKey} text={choiceText} onPick={key => { setPicked(old => ({...old, [meta.id]: key})); setOverride(meta.id); }} />
        </li>)}
        <li data-slot="explain"><strong>EXPLAIN</strong>
          {lineage.loading && <span className="scc-meta" role="status">Consultando EXPLAIN…</span>}
          {lineage.error ? <span role="alert">Error al consultar EXPLAIN. <button className="ds-button" data-size="compact" onClick={() => setRevision(n => n+1)}>Reintentar</button></span> : null}
          {lineage.data && <ul>{explainMethods.map(method => <li key={method.id} data-empty={!explanations[method.id]?.length}><span>{method.label}</span>
            <span className="scc-slot-explain">{explainParts(method.id).population.length > 0 || !explainParts(method.id).cells.length
              ? <SlotChoice label={`EXPLAIN ${method.label}`} items={explainParts(method.id).population} current={explainOf(method.id)} keyOf={child => child.attempt_id} text={explanationText} onPick={key => setExplainPicked(old => ({...old, [method.id]: key}))} /> : null}
              {explainParts(method.id).cells.length > 0 && <small className="scc-meta">{explainParts(method.id).population.length ? '+ ' : ''}{explainParts(method.id).cells.length} {explainParts(method.id).cells.length === 1 ? 'célula generada' : 'células generadas'} desde el reporte</small>}</span>
          </li>)}</ul>}
        </li>
      </ol>
      {slot && slot !== protocol && <p className="scc-slot-warning" role="note">Distinta al análisis: este RUN usa {evaluationSlots.find(item => item.id === slot)!.label}{groups[protocol].length ? '' : ` porque no tiene ${evaluationSlots.find(item => item.id === protocol)!.label}`}.</p>}
      {selected ? <EvidenceButton title="Identidad de evaluación" label="Identidad de evaluación"><p className="report-identifier">Evaluación: {selected.evaluation_id ?? 'No registrada'}<br />Intento: {selected.attempt_id ?? 'No aplica a VAL histórica'}<br />Checkpoint: {selected.checkpoint_artifact_id ?? 'Sin evidencia'}</p><CopyText text={JSON.stringify(evaluationSelection(selected))} label="Copiar identidad" /></EvidenceButton>
        : <p>Sin evaluaciones persistidas para este RUN.</p>}
      <EvidenceButton title="Dataset y partición gobernada" label="Dataset y partición">
        <p>{catalog.governance.split_algorithm} · Semilla {catalog.governance.random_seed} · {value(catalog.governance.source_record_count)} registros</p>
        <p>{Object.entries(catalog.governance.counts).map(([split, count]) => `${split.toUpperCase()}: ${value(count)}`).join(' · ')}</p>
        <p>Controles PASS: {catalog.governance.checks.filter(c => c.status === 'PASS').length} / {catalog.governance.checks.length}</p>
        <p>Materialización: {catalog.governance.materialization_status ?? 'Sin evidencia'} · Reconciliación: {catalog.governance.reconciliation_status ?? 'Sin evidencia'} · {value(catalog.governance.record_count)} registros</p>
        <p>Coincidencia de versión: {catalog.governance.materialization_dataset_matches === true ? 'Sí' : 'No acreditada'}. Consumo individual TRAIN: {catalog.governance.consumed_images ? `${catalog.governance.consumed_images} imágenes registradas` : 'Sin evidencia individual; el snapshot acredita la referencia de campaña.'}</p>
        <details><summary>Controles y snapshot de campaña</summary><pre>{JSON.stringify({checks: catalog.governance.checks, snapshot: catalog.governance.campaign_snapshot}, null, 2)}</pre></details>
      </EvidenceButton>
    </>}
  </div>;
}

// active: section mode (Análisis de Modelos); omitted: standalone disclosure opened by the reader.
export type ModuleProps = {cache: ComparisonCache; datasource: string; selections: RequestedSelection[]; evidenceRevision?: number; active?: boolean};
// Consensus verifies every governed sample of each attempt (3 x 2.685 TEST rows took 22 s before the
// population query fix); the default 15 s would report a query error for a valid answer.
const MODULE_TIMEOUT_MS: Partial<Record<ReportModule, number>> = {consensus: 60000, questions: 60000};
export function LazyScientificModule<T>({title, module, cache, datasource, selections, evidenceRevision = 0, active, children, params = {}}: ModuleProps & {title: string; module: ReportModule; params?: Omit<ReportRequest, 'module' | 'selections'>; children: (data: T, loading: boolean) => ReactNode}) {
  const [open, setOpen] = useState(false);
  const [revision, setRevision] = useState(0);
  const key = selections.length ? JSON.stringify([module, datasource, selections, params, revision, evidenceRevision]) : null;
  const enabled = active ?? open;
  const result = useComparisonEvidence(cache, key, () => api.getComparisonReport<T>(datasource, {module, selections, ...params}, MODULE_TIMEOUT_MS[module]), enabled);
  // While a new page or filter loads, the previous answer stays on screen (no flicker, table state kept).
  const previous = useRef<{key: string; data: ReportResponse<T>} | null>(null);
  if (result.data && key) previous.current = {key, data: result.data};
  const shown = result.data ?? (result.loading && previous.current && JSON.stringify(JSON.parse(previous.current.key).slice(0, 3)) === JSON.stringify(key ? JSON.parse(key).slice(0, 3) : null) ? previous.current.data : undefined);
  const body = <>{!selections.length && <p>Selecciona RUN para consultar este módulo.</p>}{result.loading && !shown && <p role="status">Consultando resultados…</p>}
    {result.error ? <p role="alert">Error de consulta. <button className="ds-button" onClick={() => setRevision(n => n+1)}>Reintentar</button></p> : null}
    {shown && <>{shown.warnings.map(w => <p className="ds-callout" data-tone="warning" key={w}>{w}</p>)}{children(shown.data, result.loading)}</>}
  </>;
  if (active !== undefined) return <section className="scc-science-module" aria-label={title} aria-busy={result.loading}><h3>{title}</h3>{body}</section>;
  return <details className="ds-accordion scc-science-module" onToggle={event => setOpen(event.currentTarget.open)}><summary>{title}</summary>
    {open && body}
  </details>;
}

const curveMetricLabels: Record<string, string> = {loss: 'Loss', accuracy: 'Accuracy', auc: 'ROC-AUC', pr_auc: 'PR-AUC', recall: 'Sensibilidad', specificity: 'Especificidad', f2_parasitized: 'F2 parasitada'};
const epochsText = (executed: number, configured: number | null) => `${executed} / ${configured ?? '—'}`;
export function TrainingCurves({data}: {data: CurveEvidence[]}) {
  const [hidden, setHidden] = useState<string[]>([]);
  const [reference, setReference] = useState('');
  const [metric, setMetric] = useState('loss');
  const toggle = (key: string) => setHidden(old => old.includes(key) ? old.filter(v => v !== key) : [...old, key]);
  const optional = ['auc', 'pr_auc', 'recall', 'specificity', 'f2_parasitized'].filter(metric => data.some(r => r.metrics_definition && r.epochs.some(e => e.values[metric] != null || e.values[`val_${metric}`] != null)));
  const metrics = ['loss', 'accuracy', ...optional].filter(m => data.some(r => r.epochs.some(e => e.values[m] != null || e.values[`val_${m}`] != null)));
  const shown = metrics.includes(metric) ? metric : metrics[0];
  const epochs = [...new Set(data.flatMap(r => r.epochs.map(e => e.epoch)))].sort((a,b) => a-b);
  // Explicit gaps keep Recharts from joining epochs absent from every run.
  const axis = epochs.length ? Array.from({length: epochs[epochs.length-1] - epochs[0] + 1}, (_, i) => epochs[0]+i) : [];
  const rows = axis.map(epoch => Object.fromEntries([['epoch', epoch], ...data.flatMap((r,i) => Object.entries(r.epochs.find(e => e.epoch === epoch)?.values ?? {}).map(([k,v]) => [`r${i}_${k}`, v]))]));
  if (!epochs.length) return <p>No hay eventos de época válidos para esta selección. {data.flatMap(r => r.issues).join(' ')}</p>;
  const summaries = data.map(curveSummary);
  const series = shown ? data.flatMap((r,i) => ['', 'val_'].flatMap(prefix => r.epochs.some(e => e.values[`${prefix}${shown}`] != null) ? [{key: `r${i}_${prefix}${shown}`, name: `${runLabel(i)} ${prefix ? 'VAL' : 'TRAIN'}`, i, prefix}] : [])) : [];
  const fineTuneStart = data.map(r => r.epochs.find(e => e.phase === 'fine_tuning')?.epoch).find(epoch => epoch != null);
  return <>
    <SectionAnswer indicators={summaries.map((s, i) => <Kpi key={data[i].training_run_id} run={i} label={`${runLabel(i)} · checkpoint`}
      value={s.checkpointEpoch == null ? 'Sin evidencia' : `Época ${s.checkpointEpoch} de ${s.baseExecuted + s.fineExecuted}`}
      detail={<>{s.checkpointPhase === 'fine_tuning' ? 'Ajuste fino' : s.checkpointPhase ? 'Fase base' : 'Fase sin evidencia'} · VAL loss {short(s.valLoss)}{s.gap != null && <> · VAL−TRAIN loss {short(s.gap)}</>}</>} />)}>
      {summaries.some(s => s.baseCheckpointAfterFineTuning)
        ? `En ${summaries.every(s => s.baseCheckpointAfterFineTuning) ? 'todos los RUN' : listText(summaries.flatMap((s, i) => s.baseCheckpointAfterFineTuning ? [runLabel(i)] : []))} el checkpoint quedó en la fase base: las épocas de ajuste fino no superaron la política de selección.`
        : 'El checkpoint de cada RUN corresponde a la época que maximizó su política de selección sobre VAL.'}
    </SectionAnswer>
    <div className="report-table-scroll"><table className="report-data-table"><caption>Épocas ejecutadas / configuradas y checkpoint</caption><thead><tr><th>RUN</th><th>Base</th><th>Ajuste fino</th><th>Total</th><th>Checkpoint</th><th>Política / métrica</th></tr></thead><tbody>{data.map((r,i) => { const s = summaries[i]; return <tr key={r.training_run_id}><th scope="row">{runLabel(i)}</th><td>{epochsText(s.baseExecuted, s.baseConfigured)}</td><td>{s.fineExecuted || s.fineConfigured ? epochsText(s.fineExecuted, s.fineConfigured) : 'No aplica'}</td><td>{epochsText(s.baseExecuted + s.fineExecuted, s.configuredTotal)}</td><td>{value(r.checkpoint.selected_epoch)}{r.checkpoint.phase ? ` · ${r.checkpoint.phase === 'fine_tuning' ? 'ajuste fino' : 'base'}` : ''}</td><td>{r.checkpoint.policy ?? 'Sin evidencia'} / {r.checkpoint.metric ?? 'Sin evidencia'}</td></tr>; })}</tbody></table></div>
    <div className="scc-chart-toolbar">
      <div role="tablist" aria-label="Métrica de la curva" className="scc-segmented">{metrics.map(m => <button key={m} type="button" role="tab" aria-selected={m === shown} className="ds-button" data-size="compact" onClick={() => setMetric(m)}>{curveMetricLabels[m] ?? m}</button>)}</div>
      <label>Referencia de checkpoint<select className="ds-control" value={reference} onChange={e => setReference(e.target.value)}><option value="">Sin referencia vertical</option>{data.map((r,i) => <option key={r.training_run_id} value={i}>{runLabel(i)} · época {r.checkpoint.selected_epoch ?? 'sin evidencia'}</option>)}</select></label>
    </div>
    {shown && <section aria-label={`Curva ${curveMetricLabels[shown] ?? shown}`}>
      <div className="scc-series-controls">{series.map(s => <label key={s.key}><input type="checkbox" checked={!hidden.includes(s.key)} onChange={() => toggle(s.key)} />{s.name}</label>)}</div>
      <div className="scc-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={rows}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="epoch" type="number" domain={['dataMin', 'dataMax']} allowDecimals={false} /><YAxis /><Tooltip /><Legend />
        {series.filter(s => !hidden.includes(s.key)).map(s => <Line key={s.key} dataKey={s.key} name={s.name} stroke={colors[s.i % colors.length]} strokeDasharray={s.prefix ? '6 3' : undefined} type="linear" dot={false} connectNulls={false} isAnimationActive={false} />)}
        {fineTuneStart != null && <ReferenceLine x={fineTuneStart - 0.5} stroke="var(--ds-border-strong, #94a3b8)" strokeDasharray="2 4" label="Inicio ajuste fino" />}
        {reference !== '' && data[Number(reference)]?.checkpoint.logical_lineage && data[Number(reference)].checkpoint.selected_epoch != null && <ReferenceLine x={data[Number(reference)].checkpoint.selected_epoch!} stroke={colors[Number(reference) % colors.length]} label={`Checkpoint ${runLabel(Number(reference))}`} />}
      </LineChart></ResponsiveContainer></div>
    </section>}
    <p className="scc-meta">TRAIN: línea continua. VAL: discontinua. Valores originales, sin rellenar épocas ausentes.</p>
    <EvidenceButton title="Definiciones y linaje de las curvas" label="Definiciones y linaje">{data.map((r,i) => <div key={r.training_run_id}><p>{runLabel(i)} · Loss: {r.loss_definition ?? 'Sin evidencia'} · Métricas: {r.metrics_definition ?? 'Sin evidencia'}</p>{r.issues.map(issue => <p key={issue}>{issue}</p>)}<pre>{JSON.stringify(r.checkpoint, null, 2)}</pre></div>)}</EvidenceButton>
  </>;
}
const metricLabels: Record<string,string> = {accuracy:'Accuracy', precision:'Precision', recall:'Sensibilidad', specificity:'Especificidad', f1:'F1', f2:'F2', roc_auc:'ROC-AUC', pr_auc:'PR-AUC', balanced_accuracy:'Balanced accuracy'};
function ConfusionHeatmap({clinical}: {clinical: NonNullable<ClinicalEvidence['clinical']>}) {
  const negatives = clinical.tn + clinical.fp, positives = clinical.fn + clinical.tp;
  const cell = (label: string, count: number, total: number, correct: boolean) => <td data-correct={correct} style={{'--scc-heat': intensity(count, total)} as CSSProperties} title={`${count} de ${total} (${percent(total ? count / total : null)} de la fila)`}>{label} {count}<small>{percent(total ? count / total : null)}</small></td>;
  return <table className="report-data-table scc-confusion"><caption>Filas reales / columnas predichas</caption><thead><tr><th>Real</th><th>No parasitada</th><th>Parasitada</th></tr></thead><tbody>
    <tr><th>No parasitada</th>{cell('TN', clinical.tn, negatives, true)}{cell('FP', clinical.fp, negatives, false)}</tr>
    <tr><th>Parasitada</th>{cell('FN', clinical.fn, positives, false)}{cell('TP', clinical.tp, positives, true)}</tr>
  </tbody></table>;
}
export function ClinicalMetrics({data}: {data: MetricsEvidence}) {
  const available = data.runs.filter(r => r.state === 'available' && r.clinical);
  const recall = metricRange(data.runs, 'recall'), specificity = metricRange(data.runs, 'specificity');
  const thresholds = [...new Set(available.map(r => r.clinical!.threshold_used))];
  const tradeoff = available.map(r => ({name: runLabel(data.runs.indexOf(r)), index: data.runs.indexOf(r), fpr: 1 - (r.clinical!.metrics.specificity?.value ?? NaN), recall: r.clinical!.metrics.recall?.value ?? null})).filter(p => Number.isFinite(p.fpr) && p.recall != null);
  return <>
    <SectionAnswer indicators={data.runs.map((r,i) => r.state === 'available' && r.clinical ? <Kpi key={r.training_run_id} run={i} label={`${runLabel(i)} · ${r.evaluation?.split.toUpperCase() ?? ''}`}
      value={<>{percent(r.clinical.metrics.recall?.value)} <small>sens.</small> · {percent(r.clinical.metrics.specificity?.value)} <small>espec.</small></>}
      detail={`FN ${r.clinical.fn} · FP ${r.clinical.fp} · umbral ${short(r.clinical.threshold_used)}`} /> : <Kpi key={r.training_run_id} run={i} label={runLabel(i)} value="Sin evidencia" detail={r.issues.join(' ')} />)}>
      {available.length ? <>Sensibilidad {recall && recall.min !== recall.max ? `entre ${percent(recall.min)} y ${percent(recall.max)}` : percent(recall?.min)} y especificidad {specificity && specificity.min !== specificity.max ? `entre ${percent(specificity.min)} y ${percent(specificity.max)}` : percent(specificity?.min)} sobre {value(available[0].clinical!.sample_count)} muestras{thresholds.length > 1 ? '; cada RUN decide con su propio umbral calibrado, por lo que las métricas dependientes del umbral no son una comparación a igual punto de operación.' : '.'}</> : 'Sin métricas clínicas atribuibles en esta selección.'}
    </SectionAnswer>
    {data.highlights.length > 0 && <div className="scc-highlights">{data.highlights.map(h => <div className="report-metric" key={h.label}><span>{h.label}</span><strong>{value(h.value)}</strong><span>{h.runs.map(runLabel).join(', ')}</span></div>)}</div>}
    <div className="scc-chart-grid">
      <section aria-label="Punto de operación"><h4>Punto de operación: sensibilidad vs falsos positivos</h4>
        <div className="scc-chart scc-chart--compact"><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{top: 16, right: 24, bottom: 8, left: 0}}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" dataKey="fpr" name="1 − especificidad" domain={[0, 'auto']} tickFormatter={v => percent(v)} /><YAxis type="number" dataKey="recall" name="Sensibilidad" domain={['auto', 1]} tickFormatter={v => percent(v)} /><Tooltip formatter={v => percent(typeof v === 'number' ? v : null)} />
          <Scatter data={tradeoff} isAnimationActive={false}>{tradeoff.map(p => <Cell key={p.name} fill={colors[p.index % colors.length]} />)}<LabelList dataKey="name" position="top" /></Scatter>
        </ScatterChart></ResponsiveContainer></div>
        <p className="scc-meta">Arriba a la izquierda: más sensibilidad con menos falsos positivos. Cada punto usa el umbral de su RUN.</p></section>
      <section aria-label="Sensibilidad, especificidad y F2"><h4>Sensibilidad, especificidad y F2</h4>
        <div className="scc-chart scc-chart--compact"><ResponsiveContainer width="100%" height="100%"><BarChart data={available.map(r => ({name: `${runLabel(data.runs.indexOf(r))} ${r.evaluation?.split.toUpperCase()}`, ...Object.fromEntries(Object.entries(r.clinical?.metrics ?? {}).map(([k,v]) => [k,v.value]))}))}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis domain={[0,1]} /><Tooltip /><Legend />{['recall','specificity','f2'].map((k,i) => <Bar key={k} dataKey={k} name={metricLabels[k]} fill={colors[i]} isAnimationActive={false} />)}</BarChart></ResponsiveContainer></div></section>
    </div>
    <h4>Matrices de confusión</h4><div className="report-comparison scc-confusion-grid">{data.runs.map((r,i) => <section key={r.training_run_id} className="report-evidence"><h5>{runLabel(i)} · {r.evaluation?.split.toUpperCase()}</h5>{r.state === 'available' && r.clinical ? <ConfusionHeatmap clinical={r.clinical} /> : <p>{r.issues.join(' ') || 'Sin métricas clínicas para esta evaluación.'}</p>}<EvidenceButton title={`Protocolo y atribución · ${runLabel(i)}`} label="Protocolo y atribución"><pre>{JSON.stringify(r.evaluation, null, 2)}</pre><pre>{JSON.stringify(r.checkpoint, null, 2)}</pre></EvidenceButton></section>)}</div>
    <details className="ds-accordion"><summary>Tabla completa de métricas persistidas</summary>
      <div className="report-table-scroll" tabIndex={0}><table className="report-data-table"><caption>Métricas persistidas de la evaluación seleccionada</caption><thead><tr><th>Métrica</th>{data.runs.map((r,i) => <th key={r.training_run_id}>{runLabel(i)} · {r.evaluation?.split.toUpperCase() ?? 'Sin evaluación'}</th>)}</tr></thead><tbody>
        {Object.entries(metricLabels).map(([key,label]) => <tr key={key}><th scope="row">{label}</th>{data.runs.map(r => <td key={r.training_run_id}>{r.state === 'available' ? value(r.clinical?.metrics[key]?.value) : 'Sin evidencia atribuible'}</td>)}</tr>)}
        {(['sample_count','threshold_used'] as const).map(key => <tr key={key}><th scope="row">{key === 'sample_count' ? 'Muestras' : 'Umbral'}</th>{data.runs.map(r => <td key={r.training_run_id}>{value(r.clinical?.[key])}</td>)}</tr>)}
      </tbody></table></div>
    </details>
    <p className="scc-meta">Los valores describen esta población y este umbral; no identifican un ganador clínico universal.</p>
  </>;
}
// One RUN: the same categories are that model's own confusion cells; there is nothing to disagree with.
const singleRunCategories: Record<string, string> = {all: 'Todas', CONSENSUS_TP: 'Verdadero positivo', CONSENSUS_TN: 'Verdadero negativo', CONSENSUS_FP: 'Falso positivo', CONSENSUS_FN: 'Falso negativo', high_confidence_error: 'Error de alta confianza', low_confidence: 'Cerca del umbral'};
const consensusCategories: Record<string, string> = {all: 'Todas', disagreement: 'Desacuerdo', CONSENSUS_TP: 'Todos aciertan · parasitada', CONSENSUS_TN: 'Todos aciertan · no parasitada', CONSENSUS_FP: 'Todos fallan · FP', CONSENSUS_FN: 'Todos fallan · FN', high_confidence_error: 'Error de alta confianza', low_confidence: 'Cerca del umbral'};
function PairHeatmap({title, matrix, n, diagonalTotal}: {title: string; matrix: number[][]; n: number; diagonalTotal?: boolean}) {
  return <div className="report-table-scroll"><table className="report-data-table scc-heatmap"><caption>{title}; N = {n}</caption><thead><tr><th>RUN</th>{matrix.map((_,i) => <th key={i}>{runLabel(i)}</th>)}</tr></thead><tbody>{matrix.map((row,i) => <tr key={i}><th scope="row">{runLabel(i)}</th>{row.map((count,j) => <td key={j} data-diagonal={i === j} style={{'--scc-heat': intensity(count, diagonalTotal ? Math.max(...matrix.map((r, k) => r[k])) : n)} as CSSProperties}>{count} / {n}<small>{percent(n ? count / n : null)}</small></td>)}</tr>)}</tbody></table></div>;
}
// onExplain opens the cell (its original image is the table's XAI column) in the «Vista ampliada».
export function ConsensusResults({data, datasource, onExplain, pagination, onPagination, sorting, onSorting, columnFilters, onColumnFilters, loading}: {data: ConsensusEvidence; datasource?: string; onExplain?: (sample: string) => void;
  pagination?: MRT_PaginationState; onPagination?: (next: MRT_PaginationState) => void; sorting?: MRT_SortingState; onSorting?: (next: MRT_SortingState) => void;
  columnFilters?: MRT_ColumnFiltersState; onColumnFilters?: (next: MRT_ColumnFiltersState) => void; loading?: boolean}) {
  if (data.state !== 'available') return <p>{data.state === 'incompatible' ? 'Incompatibilidad metodológica. ' : 'Sin evidencia suficiente para este análisis. '}{data.issues?.join(' ')}</p>;
  const summary = consensusSummary(data);
  const runs = data.coverage?.length ?? 0;
  const labels = runs === 1 ? singleRunCategories : consensusCategories;
  const distribution = Object.entries(data.distribution ?? {}).filter(([category]) => labels[category]);
  return <>
    {runs === 1 ? <SectionAnswer indicators={<>
      <Kpi label="Aciertos" value={percent(data.oracle?.ratio)} detail={`${data.oracle?.numerator} / ${data.oracle?.denominator} muestras`} />
      <Kpi label="Falsos negativos" value={data.distribution?.CONSENSUS_FN ?? 0} detail="Parasitadas no detectadas" />
      <Kpi label="Falsos positivos" value={data.distribution?.CONSENSUS_FP ?? 0} detail="Sanas marcadas como parasitadas" />
      <Kpi label="Errores de alta confianza" value={data.high_confidence_errors} detail={`${data.low_confidence} cerca del umbral`} />
    </>}>
      N = {data.common_count} muestras evaluadas. El modelo falla en {data.all_wrong} ({percent(data.common_count ? (data.all_wrong ?? 0) / data.common_count : null)}); los errores de alta confianza y los cercanos al umbral son los primeros candidatos a revisar en Explicabilidad.
    </SectionAnswer> : <SectionAnswer indicators={<>
      <Kpi label="Oracle descriptivo" value={percent(data.oracle?.ratio)} detail={`${data.oracle?.numerator} / ${data.oracle?.denominator}; no desplegable`} />
      <Kpi label="Todos fallan" value={data.all_wrong} detail="Candidatas a revisión de etiqueta o imagen" />
      <Kpi label="Errores de alta confianza" value={data.high_confidence_errors} />
      <Kpi label="Cerca del umbral" value={data.low_confidence} />
    </>}>
      N común = {data.common_count} muestras de {data.union_count} distintas · {data.label_conflicts} conflictos de etiquetas.{runs > 1 && summary.agreementRange && <> Los RUN coinciden en {percent(summary.agreementRange.min)}–{percent(summary.agreementRange.max)} de las predicciones.</>}{summary.fewestSharedErrors && <> El par con menos errores compartidos es {runLabel(summary.fewestSharedErrors.i)}–{runLabel(summary.fewestSharedErrors.j)} ({summary.fewestSharedErrors.count} muestras): es el par más complementario.</>}
    </SectionAnswer>}
    <div className="scc-chart-grid">
      <section aria-label="Distribución por categoría"><h4>Distribución por categoría</h4>
        <div className="scc-chart scc-chart--compact"><ResponsiveContainer width="100%" height="100%"><BarChart data={distribution.map(([category,count]) => ({category, label: labels[category], count}))}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" tick={{fontSize: 11}} interval={0} /><YAxis /><Tooltip /><Bar dataKey="count" name="Muestras" fill={colors[0]} isAnimationActive={false} /></BarChart></ResponsiveContainer></div></section>
      {runs > 1 && <section aria-label="Aciertos y errores exclusivos"><h4>Aciertos y errores exclusivos por RUN</h4>
        <div className="scc-chart scc-chart--compact"><ResponsiveContainer width="100%" height="100%"><BarChart data={(data.coverage ?? []).map((_, i) => ({name: runLabel(i), correct: data.exclusive_correct?.[i] ?? 0, errors: data.exclusive_errors?.[i] ?? 0}))}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Legend /><Bar dataKey="correct" name="Aciertos exclusivos" fill={colors[1]} isAnimationActive={false} /><Bar dataKey="errors" name="Errores exclusivos" fill={colors[3]} isAnimationActive={false} /></BarChart></ResponsiveContainer></div>
        <p className="scc-meta">Acierto exclusivo: solo ese RUN acierta. Error exclusivo: solo ese RUN falla.</p></section>}
    </div>
    {runs > 1 && <div className="scc-chart-grid">
      {data.agreement && <PairHeatmap title="Acuerdo: predicciones iguales / N común" matrix={data.agreement} n={data.common_count ?? 0} />}
      {data.error_overlap && <PairHeatmap title="Solapamiento de errores: conteos sobre N común" matrix={data.error_overlap} n={data.common_count ?? 0} diagonalTotal />}
    </div>}
    {runs > 1 && <EvidenceButton title="Cobertura y complementariedad por RUN" label="Cobertura por RUN"><div className="report-table-scroll"><table className="report-data-table"><caption>Cobertura y complementariedad por RUN</caption><thead><tr><th>RUN</th><th>Población</th><th>Comunes</th><th>Faltantes</th><th>Exclusivas</th><th>Errores exclusivos</th><th>Aciertos exclusivos</th></tr></thead><tbody>{data.coverage?.map((c,i) => <tr key={i}><th>{runLabel(i)}</th><td>{c.population}</td><td>{c.common}</td><td>{c.missing}</td><td>{c.exclusive}</td><td>{data.exclusive_errors?.[i]}</td><td>{data.exclusive_correct?.[i]}</td></tr>)}</tbody></table></div></EvidenceButton>}
    <EvidenceButton title="Fórmulas y denominadores del consenso" label="Fórmulas y denominadores">{Object.entries(data.definitions ?? {}).map(([k,v]) => <p key={k}>{v}</p>)}</EvidenceButton>
    <ConsensusSamplesTable data={data} labels={labels} loading={loading} datasource={datasource}
      pagination={pagination ?? {pageIndex: Math.floor((data.offset ?? 0) / (data.limit || 10)), pageSize: data.limit || 10}}
      onPagination={onPagination ?? (() => {})} sorting={sorting ?? []} onSorting={onSorting ?? (() => {})}
      columnFilters={columnFilters ?? []} onColumnFilters={onColumnFilters ?? (() => {})} onExplain={onExplain} />
  </>;
}
export function CurvesModule(props: ModuleProps) {
  return <LazyScientificModule<CurveEvidence[]> {...props} selections={props.selections.map(s => ({training_run_id: s.training_run_id}))} title="Curvas TRAIN / VAL" module="curves">{data => <TrainingCurves data={data} />}</LazyScientificModule>;
}
export function MetricsModule(props: ModuleProps) {
  return <LazyScientificModule<MetricsEvidence> {...props} title="Métricas clínicas y matrices de confusión" module="metrics">{data => <ClinicalMetrics data={data} />}</LazyScientificModule>;
}
const filterNumber = (value: unknown) => value === '' || value == null || !Number.isFinite(Number(value)) ? null : Number(value);
// MRT column filters → request fields: Muestra (contains), Clase real (0/1), Categoría (key), RUN n ([min, max] score).
function consensusFilterParams(filters: MRT_ColumnFiltersState): Omit<ReportRequest, 'module' | 'selections'> {
  const value = (id: string) => filters.find(f => f.id === id)?.value;
  const sample = String(value('sample') ?? '').trim(), label = filterNumber(value('label')), category = value('category');
  const score_ranges = Object.fromEntries(filters.filter(f => f.id.startsWith('run-') && Array.isArray(f.value))
    .map(f => [f.id.slice(4), (f.value as unknown[]).slice(0, 2).map(filterNumber) as [number | null, number | null]])
    .filter(([, [lo, hi]]) => lo != null || hi != null));
  return {category: typeof category === 'string' && category ? category : 'all', ...(sample ? {sample_query: sample} : {}),
    ...(label === 0 || label === 1 ? {label} : {}), ...(Object.keys(score_ranges).length ? {score_ranges} : {})};
}
const shortId = (sample: string) => /^[0-9a-f-]{36}$/i.test(sample) ? `${sample.slice(0, 8)}…` : sample.split('/').pop() ?? sample;
export type XAIAccess = {explains?: Record<string, string[]>; canGenerate?: boolean; onGenerated?: () => void};
// The «Vista ampliada» of a table cell: one RUN at a time, with the same generation and views as Explicabilidad.
export function ConsensusCellModal({sample, selections, datasource, explains, canGenerate, onGenerated, onClose, onExplain, initialRun = 0}: XAIAccess & {
  sample: string; selections: RequestedSelection[]; datasource: string; onClose: () => void; onExplain?: (sample: string) => void; initialRun?: number}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [run, setRun] = useState(initialRun);
  const {blocked} = useExplainExecutor(Boolean(canGenerate));
  useEffect(() => { dialog.current?.showModal(); }, []);
  const selection = selections[run];
  return <dialog ref={dialog} className="report-viewer xai-modal" aria-label={`Vista ampliada · célula ${sample}`} onClose={onClose}>
    <form method="dialog" className="xai-modal-close"><button type="submit" className="ds-button" aria-label="Cerrar vista ampliada" title="Cerrar" autoFocus>
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
    </button></form>
    <h2>Vista ampliada · célula <code title={sample}>{shortId(sample)}</code></h2>
    <div className="xai-modal-bar">
      {selections.length > 1 && <div role="tablist" aria-label="RUN" className="xai-view-tabs">{selections.map((s, i) => <button key={s.training_run_id} type="button" role="tab"
        className="ds-button" aria-selected={run === i} onClick={() => setRun(i)}>{runLabel(i)}</button>)}</div>}
      <CopyText text={sample} label="Copiar muestra" />
      {onExplain && <button type="button" className="ds-button" onClick={() => { dialog.current?.close(); onExplain(sample); }}>Abrir en Explicabilidad</button>}
    </div>
    {selection && <PersistedXAI key={JSON.stringify(selection)} selection={selection} datasource={datasource} active attemptIds={explains?.[selection.training_run_id]}
      canGenerate={canGenerate} blocked={blocked} onGenerated={onGenerated} focusSample={sample} variant="expanded" />}
  </dialog>;
}
export function ConsensusModule({onExplain, explains, canGenerate, onGenerated, ...props}: ModuleProps & XAIAccess & {onExplain?: (sample: string) => void}) {
  const single = props.selections.length === 1;
  const [pagination, setPagination] = useState<MRT_PaginationState>({pageIndex: 0, pageSize: 10});
  const [sorting, setSorting] = useState<MRT_SortingState>([]);
  const sorted = (next: MRT_SortingState) => { setSorting(next); setPagination(old => ({...old, pageIndex: 0})); };
  // The table starts on the whole population; its column filters are applied server-side before sorting and paging.
  const [columnFilters, setColumnFilters] = useState<MRT_ColumnFiltersState>([]);
  const filtered = (next: MRT_ColumnFiltersState) => { setColumnFilters(next); setPagination(old => ({...old, pageIndex: 0})); };
  const [opened, setOpened] = useState<string | null>(null);
  return <><LazyScientificModule<ConsensusEvidence> {...props} title={single ? 'Errores del modelo' : 'Consenso y desacuerdos'} module="consensus"
    params={{offset: pagination.pageIndex * pagination.pageSize, limit: pagination.pageSize, ...consensusFilterParams(columnFilters),
      ...(sorting[0] ? {sort_by: sorting[0].id, sort_desc: sorting[0].desc} : {})}}>{(data, loading) =>
      <ConsensusResults data={data} datasource={props.datasource} onExplain={setOpened} pagination={pagination} onPagination={setPagination} sorting={sorting} onSorting={sorted}
        columnFilters={columnFilters} onColumnFilters={filtered} loading={loading} />}</LazyScientificModule>
    {opened && <ConsensusCellModal key={opened} sample={opened} selections={props.selections} datasource={props.datasource} explains={explains}
      canGenerate={canGenerate} onGenerated={onGenerated} onClose={() => setOpened(null)} onExplain={onExplain} />}
  </>;
}
export function ScientificResults(props: ModuleProps) {
  return <><CurvesModule {...props} /><MetricsModule {...props} /><ConsensusModule {...props} /></>;
}
export function ScientificQuestions(props: ModuleProps) {
  return <section className="scc-questions"><h3>Preguntas científicas</h3><div className="scc-question-grid">{['¿Dónde se complementan los modelos?', '¿Podemos inferir superioridad clínica?', '¿Qué evidencia explica las predicciones?'].map((q,i) => <LazyScientificModule<{answers: string[]}> key={q} {...props} title={q} module="questions">{data => <p>{data.answers[i]}</p>}</LazyScientificModule>)}</div></section>;
}

// attemptIds: EXPLAIN chosen in the RUN card (one per method). They are combined per cell, shown even when their
// split or checkpoint identifier differs (with a notice), and kept on screen while a refresh is in flight.
// focusSample: one cell chosen in Errores (or searched); its explanations are read across every chosen EXPLAIN, and
// when none exists yet the cell is built from a VAL context containing it so it can be generated.
export function PersistedXAI({selection, datasource, active, attemptIds, canGenerate = false, blocked, onGenerated, focusSample, variant}: {selection: RequestedSelection; datasource: string; active: boolean; attemptIds?: string[]; canGenerate?: boolean; blocked?: string | null; onGenerated?: () => void; focusSample?: string | null; variant?: 'inline' | 'expanded'}) {
  const cache = useMemo(createComparisonCache, [datasource, selection.training_run_id]);
  const [revision, setRevision] = useState(0);
  const [attempt, setAttempt] = useState('');
  const [offset, setOffset] = useState(0);
  const [rowPage, setRowPage] = useState(0);
  const visible = useRef(active);
  visible.current = active;
  const choices = useComparisonEvidence(cache, JSON.stringify(['xai-list', datasource, selection, attemptIds, revision]), async () => {
    const all: import('../../types/api').AssessmentChoice[] = [];
    for (let page = 0; ; page += 100) {
      if (!visible.current) throw new Error('Consulta pausada al cerrar XAI.');
      const response = await api.getTrainingAssessments(selection.training_run_id, page);
      if (response.items.some(r => r.training_run_id !== selection.training_run_id)) throw new Error('Linaje incompatible');
      all.push(...response.items.filter(r => r.kind === 'explain' && (attemptIds ? attemptIds.includes(r.attempt_id) : r.checkpoint_artifact_id === selection.checkpoint_artifact_id && (!selection.split || r.split === selection.split))));
      if (response.items.length < 100) return all;
    }
  }, active);
  const lastChoices = useRef<import('../../types/api').AssessmentChoice[] | undefined>(undefined);
  if (choices.data) lastChoices.current = choices.data;
  const listed = choices.data ?? (choices.loading ? lastChoices.current : undefined);
  const selected = listed?.find(r => r.attempt_id === attempt) ?? listed?.[0];
  const picked = attemptIds ? listed ?? [] : selected ? [selected] : [];
  const composed = useComparisonEvidence(cache, picked.length || (focusSample && listed) ? JSON.stringify(['xai-composed', picked.map(c => c.attempt_id), offset, focusSample, revision]) : null, async () => {
    const details = await Promise.all(picked.map(async choice => {
      const response = await api.getAssessment(choice.attempt_id);
      if (response.training_run_id !== selection.training_run_id || response.id !== choice.attempt_id || response.kind !== 'explain' || (!attemptIds && response.identity.model.checkpoint_artifact_id !== selection.checkpoint_artifact_id)) throw new Error('Linaje incompatible');
      return response;
    }));
    const size = (detail: typeof details[number]) => detail.identity.samples?.length ?? 0;
    if (focusSample) {
      const pages = await Promise.all(details.map(async detail => ({detail, artifacts: (await api.getAssessmentArtifacts(detail.id, 0, undefined, [focusSample])).items})));
      const contains = (detail: typeof details[number]) => Boolean(detail.identity.samples?.some(item => item.sample_id === focusSample));
      let source = details.find(contains);
      // No EXPLAIN lists the cell: the selected EVALUATE attempt (VAL or TEST) is its generation context.
      if (!source && selection.evaluation?.source === 'assessment') {
        const evaluation = await api.getAssessment(selection.evaluation.attempt_id);
        if (evaluation.training_run_id === selection.training_run_id && contains(evaluation)) source = evaluation;
      }
      return {pages, primaryCount: 0, focus: [focusSample], source: source ?? null};
    }
    // The largest attempt is paged; single-cell attempts are read whole and their cells are read from the large one.
    const [primary, ...others] = [...details].sort((a, b) => size(b) - size(a));
    const primaryPage = (await api.getAssessmentArtifacts(primary.id, offset)).items;
    const pageSamples = [...new Set(primaryPage.flatMap(item => item.sample_id ? [item.sample_id] : []))];
    const pages = [{detail: primary, artifacts: primaryPage}];
    const focus = new Set<string>();
    for (const other of others) {
      const items = (await api.getAssessmentArtifacts(other.id, 0, undefined, size(other) <= 50 ? undefined : pageSamples)).items;
      items.forEach(item => { if (item.sample_id && !pageSamples.includes(item.sample_id)) focus.add(item.sample_id); });
      pages.push({detail: other, artifacts: items});
    }
    if (focus.size) pages[0] = {detail: primary, artifacts: [...primaryPage, ...(await api.getAssessmentArtifacts(primary.id, 0, undefined, [...focus].slice(0, 100))).items]};
    return {pages, primaryCount: primaryPage.length, focus: [...focus], source: null};
  }, active);
  const fresh = useMemo(() => {
    if (!composed.data) return undefined;
    const grouped = groupXAIComparisons(composed.data.pages, selection.training_run_id);
    if (focusSample) {
      const rows = grouped.filter(row => row.sampleId === focusSample);
      return rows.length ? rows : composed.data.source ? [cellComparison(composed.data.source, focusSample)] : [];
    }
    const focus = new Set(composed.data.focus);
    // Cells explained outside the current page (recently generated) come first.
    return [...grouped.filter(row => row.sampleId && focus.has(row.sampleId)), ...grouped.filter(row => !row.sampleId || !focus.has(row.sampleId))];
  }, [composed.data, selection.training_run_id, focusSample]);
  const lastRows = useRef<XAIComparison[]>([]);
  if (fresh) lastRows.current = fresh;
  const rows = fresh ?? (composed.loading || choices.loading ? lastRows.current : []);
  // EVALUATE attempts of this TRAIN give each visible cell its real class, predicted class and score.
  const evaluations = useComparisonEvidence(cache, JSON.stringify(['xai-evaluations', datasource, selection.training_run_id, revision]), async () => {
    const all: import('../../types/api').AssessmentChoice[] = [];
    for (let page = 0; ; page += 100) {
      const response = await api.getTrainingAssessments(selection.training_run_id, page);
      all.push(...response.items.filter(r => r.kind === 'evaluate' && r.training_run_id === selection.training_run_id && r.state === 'verified'));
      if (response.items.length < 100) return all;
    }
  }, active);
  const visibleRows = rows.slice(rowPage*5, rowPage*5+5);
  const evaluateFor = (split?: string) => {
    if (!split) return undefined;
    if (selection.evaluation?.source === 'assessment' && selection.split === split) return selection.evaluation.attempt_id;
    return evaluations.data?.filter(choice => choice.split === split).sort((a, b) => b.started_at.localeCompare(a.started_at))[0]?.attempt_id;
  };
  const wanted = [...new Set(visibleRows.flatMap(row => row.sampleId && evaluateFor(row.split) ? [`${evaluateFor(row.split)}|${row.split}|${row.sampleId}`] : []))].sort();
  const outcomes = useComparisonEvidence(cache, wanted.length ? JSON.stringify(['xai-outcomes', wanted]) : null, async () => {
    const byAttempt = new Map<string, {split: string; samples: string[]}>();
    for (const item of wanted) {
      const [attempt, split, sample] = item.split('|');
      const entry = byAttempt.get(attempt) ?? {split, samples: []};
      entry.samples.push(sample); byAttempt.set(attempt, entry);
    }
    const found: Record<string, NonNullable<XAIComparison['outcome']>> = {};
    for (const [attempt, {split, samples}] of byAttempt) {
      for (const item of (await api.getAssessmentResults(attempt, samples)).items) {
        found[`${split}|${item.sample_id}`] = {label: item.label, predicted: item.predicted, score: item.raw_score, threshold: item.threshold, split, attemptId: attempt};
      }
    }
    return found;
  }, active);
  const withOutcome = (items: XAIComparison[]) => items.map(row => {
    const outcome = row.sampleId && row.split ? outcomes.data?.[`${row.split}|${row.sampleId}`] : undefined;
    return outcome ? {...row, outcome} : row;
  });
  // Compare the split of what is actually shown (a focused TEST cell comes from its TEST context, not from VAL EXPLAIN).
  const splits = [...new Set(rows.flatMap(row => row.split ? [row.split] : []))].filter(split => selection.split && split !== selection.split);
  return <section>
    {choices.loading || composed.loading ? <p role="status">Consultando explicaciones persistidas…</p> : null}
    {choices.error || composed.error ? <p role="alert">Error al consultar explicaciones. <button className="ds-button" onClick={() => setRevision(n => n+1)}>Reintentar</button></p> : null}
    {!focusSample && listed?.length === 0 && <p>{attemptIds ? 'Este RUN no tiene EXPLAIN registrado.' : 'No hay explicaciones compatibles para esta selección.'}</p>}
    {focusSample && composed.data && !rows.length && <p className="ds-callout" data-tone="warning">Ninguna evaluación ni explicación registrada de este RUN contiene la célula; selecciona en la tarjeta una EVALUATE que la incluya.</p>}
    {splits.length > 0 && <p className="ds-callout" data-tone="warning">EXPLAIN sobre {splits.map(split => split.toUpperCase()).join(', ')}; la evaluación del análisis es {selection.split!.toUpperCase()}. Las explicaciones describen el mismo TRAIN, pero no la población evaluada.</p>}
    {selection.checkpoint_artifact_id && picked.some(choice => choice.checkpoint_artifact_id !== selection.checkpoint_artifact_id) && <p className="ds-callout" data-tone="warning">El EXPLAIN registra otro identificador de checkpoint que la evaluación seleccionada; verifica el SHA-256 en Trazabilidad antes de atribuirlo al mismo archivo.</p>}
    {!attemptIds && !focusSample && listed && listed.length > 0 && <label>Explicación persistida<select className="ds-control" value={selected?.attempt_id ?? ''} onChange={e => {setAttempt(e.target.value); setOffset(0); setRowPage(0);}}>{listed.map((c,i) => <option value={c.attempt_id} key={c.attempt_id}>{i+1} · {c.split.toUpperCase()} · {c.state} · {new Date(c.started_at).toLocaleString('es-CL')}</option>)}</select></label>}
    {active && withOutcome(rows.slice(rowPage*5,rowPage*5+5)).map(row => <GeneratedXAIComparison key={row.id} comparison={row} datasource={datasource} active={active} lazy authorized={canGenerate} blocked={blocked} variant={variant} onEvidenceChange={() => { setRevision(n => n+1); onGenerated?.(); }} />)}
    {!focusSample && rows.length > 5 && <nav aria-label="Muestras XAI"><button className="ds-button" disabled={!rowPage} onClick={() => setRowPage(n => n-1)}>Muestras anteriores</button><button className="ds-button" disabled={(rowPage+1)*5 >= rows.length} onClick={() => setRowPage(n => n+1)}>Muestras siguientes</button></nav>}
    {!focusSample && composed.data && (offset > 0 || composed.data.primaryCount === 100) && <nav aria-label="Páginas de explicaciones"><button className="ds-button" disabled={offset === 0} onClick={() => {setOffset(n => n-100); setRowPage(0);}}>Anterior</button><span>Página {offset/100+1}</span><button className="ds-button" disabled={composed.data.primaryCount < 100} onClick={() => {setOffset(n => n+100); setRowPage(0);}}>Siguiente</button></nav>}
  </section>;
}
