import { groupXAIComparisons } from './xai/comparison';
import { XAIComparisonViewer } from './XAIComparisonViewer';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, BarChart, Bar } from 'recharts';
import { api } from '../../services/api';
import { useComparisonEvidence } from '../../hooks/useComparisonEvidence';
import { createComparisonCache, type ComparisonCache } from '../../utils/comparisonCache';
import type { RequestedSelection } from '../../types/scientificPreflight';
import type { CatalogEvidence, CurveEvidence, MetricsEvidence, ConsensusEvidence, ReportModule, EvaluationChoice } from '../../types/scientificReport';
import { CopyText } from './ComparisonPython';

const runLabel = (index: number) => `RUN ${String.fromCharCode(65 + index)}`;
const value = (n: number | null | undefined) => n == null ? 'Sin evidencia' : n.toLocaleString('es-CL', {maximumFractionDigits: 6});
const colors = ['var(--ds-blue-500)', 'var(--ds-green-700)', 'var(--ds-violet-700)', 'var(--ds-amber-700)'];
export function evaluationSelection(item: EvaluationChoice): RequestedSelection {
  return { training_run_id: item.training_run_id, split: item.split,
    ...(item.checkpoint_artifact_id ? {checkpoint_artifact_id: item.checkpoint_artifact_id} : {}),
    ...(item.evaluation_id ? {evaluation: {source: 'evaluations' as const, evaluation_id: item.evaluation_id}}
      : item.attempt_id && item.identity_id ? {evaluation: {source: 'assessment' as const, attempt_id: item.attempt_id, identity_id: item.identity_id}} : {}) };
}
export function EvaluationNavigation({id, datasource, onChange}: {id: string; datasource: string; onChange: (selection: RequestedSelection) => void}) {
  const cache = useMemo(createComparisonCache, [id, datasource]);
  const [revision, setRevision] = useState(0);
  const [index, setIndex] = useState(0);
  const {data, error, loading} = useComparisonEvidence(cache, JSON.stringify(['catalog', id, datasource, revision]), () => api.getComparisonReport<CatalogEvidence[]>(datasource, {module: 'catalog', selections: [{training_run_id: id}]}));
  const catalog = data?.data[0];
  const selected = catalog?.evaluations[index];
  useEffect(() => { if (selected) onChange(evaluationSelection(selected)); }, [selected, onChange]);
  return <div className="scc-evaluation-nav">
    {loading && <p role="status">Consultando evaluaciones…</p>}
    {error ? <p role="alert">Error al consultar evaluaciones. <button className="ds-button" onClick={() => setRevision(n => n+1)}>Reintentar</button></p> : null}
    {catalog && <>
      <p><strong>{catalog.governance.name ?? 'Dataset sin evidencia'}</strong><br />{catalog.governance.status} · {catalog.governance.grouping_strategy}</p>
      {selected ? <><strong>{selected.split.toUpperCase()} · {selected.evaluation_role === 'training_validation_final' ? 'VALIDATION final del checkpoint' : 'Evaluación independiente'}</strong>
        <p>{new Date(selected.created_at).toLocaleString('es-CL')} · {selected.purpose}</p>
        {catalog.evaluations.length > 1 && <nav aria-label="Evaluaciones del RUN">{catalog.evaluations.map((item, i) => <button className="ds-button" type="button" key={item.evaluation_id ?? item.attempt_id} aria-current={i === index ? 'true' : undefined} title={`${item.split} · ${item.evaluation_role} · ${item.created_at}`} onClick={() => setIndex(i)}>{i+1}</button>)}</nav>}
        <small>Inicio: la más reciente; el orden no indica superioridad científica.</small>
        <details><summary>Identidad de evaluación</summary><p className="report-identifier">Evaluación: {selected.evaluation_id ?? 'No registrada'}<br />Intento: {selected.attempt_id ?? 'No aplica a VAL histórica'}<br />Checkpoint: {selected.checkpoint_artifact_id ?? 'Sin evidencia'}</p><CopyText text={JSON.stringify(evaluationSelection(selected))} label="Copiar identidad" /></details>
      </> : <p>Sin evaluaciones persistidas para este RUN.</p>}
      <details><summary>Dataset y partición gobernada</summary>
        <p>{catalog.governance.split_algorithm} · Semilla {catalog.governance.random_seed} · {value(catalog.governance.source_record_count)} registros</p>
        <p>{Object.entries(catalog.governance.counts).map(([split, count]) => `${split.toUpperCase()}: ${value(count)}`).join(' · ')}</p>
        <p>Controles PASS: {catalog.governance.checks.filter(c => c.status === 'PASS').length} / {catalog.governance.checks.length}</p>
        <p>Materialización: {catalog.governance.materialization_status ?? 'Sin evidencia'} · Reconciliación: {catalog.governance.reconciliation_status ?? 'Sin evidencia'} · {value(catalog.governance.record_count)} registros</p>
        <p>Coincidencia de versión: {catalog.governance.materialization_dataset_matches === true ? 'Sí' : 'No acreditada'}. Consumo individual TRAIN: {catalog.governance.consumed_images ? `${catalog.governance.consumed_images} imágenes registradas` : 'Sin evidencia individual; el snapshot acredita la referencia de campaña.'}</p>
        <details><summary>Controles y snapshot de campaña</summary><pre>{JSON.stringify({checks: catalog.governance.checks, snapshot: catalog.governance.campaign_snapshot}, null, 2)}</pre></details>
      </details>
    </>}
  </div>;
}

type ModuleProps = {cache: ComparisonCache; datasource: string; selections: RequestedSelection[]; evidenceRevision?: number};
// Consensus verifies every governed sample of each attempt (3 x 2.685 TEST rows took 22 s before the
// population query fix); the default 15 s would report a query error for a valid answer.
const MODULE_TIMEOUT_MS: Partial<Record<ReportModule, number>> = {consensus: 60000, questions: 60000};
export function LazyScientificModule<T>({title, module, cache, datasource, selections, evidenceRevision = 0, children, params = {}}: ModuleProps & {title: string; module: ReportModule; params?: {offset?: number; category?: string}; children: (data: T) => ReactNode}) {
  const [open, setOpen] = useState(false);
  const [revision, setRevision] = useState(0);
  const key = selections.length ? JSON.stringify([module, datasource, selections, params, revision, evidenceRevision]) : null;
  const result = useComparisonEvidence(cache, key, () => api.getComparisonReport<T>(datasource, {module, selections, ...params}, MODULE_TIMEOUT_MS[module]), open);
  return <details className="ds-accordion scc-science-module" onToggle={event => setOpen(event.currentTarget.open)}><summary>{title}</summary>
    {open && <>{!selections.length && <p>Selecciona RUN para consultar este módulo.</p>}{result.loading && <p role="status">Consultando resultados…</p>}
      {result.error ? <p role="alert">Error de consulta. <button className="ds-button" onClick={() => setRevision(n => n+1)}>Reintentar</button></p> : null}
      {result.data && <>{result.data.warnings.map(w => <p className="ds-callout" data-tone="warning" key={w}>{w}</p>)}{children(result.data.data)}</>}
    </>}
  </details>;
}

export function TrainingCurves({data}: {data: CurveEvidence[]}) {
  const [hidden, setHidden] = useState<string[]>([]);
  const [reference, setReference] = useState('');
  const toggle = (key: string) => setHidden(old => old.includes(key) ? old.filter(v => v !== key) : [...old, key]);
  const optional = ['auc', 'pr_auc', 'recall', 'specificity', 'f2_parasitized'].filter(metric => data.some(r => r.metrics_definition && r.epochs.some(e => e.values[metric] != null || e.values[`val_${metric}`] != null)));
  const metrics = ['loss', 'accuracy', ...optional];
  const epochs = [...new Set(data.flatMap(r => r.epochs.map(e => e.epoch)))].sort((a,b) => a-b);
  // Explicit gaps keep Recharts from joining epochs absent from every run.
  const axis = epochs.length ? Array.from({length: epochs[epochs.length-1] - epochs[0] + 1}, (_, i) => epochs[0]+i) : [];
  const rows = axis.map(epoch => Object.fromEntries([['epoch', epoch], ...data.flatMap((r,i) => Object.entries(r.epochs.find(e => e.epoch === epoch)?.values ?? {}).map(([k,v]) => [`r${i}_${k}`, v]))]));
  if (!epochs.length) return <p>No hay eventos de época válidos para esta selección. {data.flatMap(r => r.issues).join(' ')}</p>;
  return <>
    <div className="report-table-scroll"><table className="report-data-table"><caption>Épocas ejecutadas y checkpoint</caption><thead><tr><th>RUN</th><th>Ejecutadas</th><th>Máximo configurado</th><th>Final</th><th>Seleccionada</th><th>Política / métrica</th></tr></thead><tbody>{data.map((r,i) => <tr key={r.training_run_id}><th scope="row">{runLabel(i)}</th><td>{r.executed_epochs}</td><td>{value(r.max_epochs)}</td><td>{value(r.final_epoch)}</td><td>{value(r.checkpoint.selected_epoch)}</td><td>{r.checkpoint.policy ?? 'Sin evidencia'} / {r.checkpoint.metric ?? 'Sin evidencia'}</td></tr>)}</tbody></table></div>
    <label>Referencia de checkpoint<select className="ds-control" value={reference} onChange={e => setReference(e.target.value)}><option value="">Sin referencia vertical</option>{data.map((r,i) => <option key={r.training_run_id} value={i}>{runLabel(i)} · época {r.checkpoint.selected_epoch ?? 'sin evidencia'}</option>)}</select></label>
    {metrics.map(metric => {
      const series = data.flatMap((r,i) => ['', 'val_'].flatMap(prefix => r.epochs.some(e => e.values[`${prefix}${metric}`] != null) ? [{key: `r${i}_${prefix}${metric}`, name: `${runLabel(i)} ${prefix ? 'VAL' : 'TRAIN'}`, i, prefix}] : []));
      if (!series.length) return null;
      return <section key={metric}><h3>{metric === 'loss' ? 'Loss' : metric === 'accuracy' ? 'Accuracy' : metric}</h3>
        <div className="scc-series-controls">{series.map(s => <label key={s.key}><input type="checkbox" checked={!hidden.includes(s.key)} onChange={() => toggle(s.key)} />{s.name}</label>)}</div>
        <div className="scc-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={rows}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="epoch" type="number" domain={['dataMin', 'dataMax']} allowDecimals={false} /><YAxis /><Tooltip /><Legend />
          {series.filter(s => !hidden.includes(s.key)).map(s => <Line key={s.key} dataKey={s.key} name={s.name} stroke={colors[s.i % colors.length]} strokeDasharray={s.prefix ? '6 3' : undefined} type="linear" dot={false} connectNulls={false} isAnimationActive={false} />)}
          {reference !== '' && data[Number(reference)]?.checkpoint.logical_lineage && data[Number(reference)].checkpoint.selected_epoch != null && <ReferenceLine x={data[Number(reference)].checkpoint.selected_epoch!} stroke={colors[Number(reference) % colors.length]} label={`Checkpoint ${runLabel(Number(reference))}`} />}
        </LineChart></ResponsiveContainer></div>
      </section>;
    })}
    <p>TRAIN: línea continua. VAL: discontinua. Valores originales, sin rellenar épocas ausentes.</p>
    <details><summary>Definiciones y linaje</summary>{data.map((r,i) => <div key={r.training_run_id}><p>{runLabel(i)} · Loss: {r.loss_definition ?? 'Sin evidencia'} · Métricas: {r.metrics_definition ?? 'Sin evidencia'}</p>{r.issues.map(issue => <p key={issue}>{issue}</p>)}<pre>{JSON.stringify(r.checkpoint, null, 2)}</pre></div>)}</details>
  </>;
}
const metricLabels: Record<string,string> = {accuracy:'Accuracy', precision:'Precision', recall:'Sensibilidad', specificity:'Especificidad', f1:'F1', f2:'F2', roc_auc:'ROC-AUC', pr_auc:'PR-AUC', balanced_accuracy:'Balanced accuracy'};
export function ClinicalMetrics({data}: {data: MetricsEvidence}) {
  return <>
    <div className="scc-highlights">{data.highlights.map(h => <div className="report-metric" key={h.label}><span>{h.label}</span><strong>{value(h.value)}</strong><span>{h.runs.map(runLabel).join(', ')}</span></div>)}</div>
    <div className="report-table-scroll" tabIndex={0}><table className="report-data-table"><caption>Métricas persistidas de la evaluación seleccionada</caption><thead><tr><th>Métrica</th>{data.runs.map((r,i) => <th key={r.training_run_id}>{runLabel(i)} · {r.evaluation?.split.toUpperCase() ?? 'Sin evaluación'}</th>)}</tr></thead><tbody>
      {Object.entries(metricLabels).map(([key,label]) => <tr key={key}><th scope="row">{label}</th>{data.runs.map(r => <td key={r.training_run_id}>{r.state === 'available' ? value(r.clinical?.metrics[key]?.value) : 'Sin evidencia atribuible'}</td>)}</tr>)}
      {(['sample_count','threshold_used'] as const).map(key => <tr key={key}><th scope="row">{key === 'sample_count' ? 'Muestras' : 'Umbral'}</th>{data.runs.map(r => <td key={r.training_run_id}>{value(r.clinical?.[key])}</td>)}</tr>)}
    </tbody></table></div>
    <div className="scc-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.runs.filter(r => r.state === 'available').map(r => ({name: `${runLabel(data.runs.indexOf(r))} ${r.evaluation?.split.toUpperCase()}`, ...Object.fromEntries(Object.entries(r.clinical?.metrics ?? {}).map(([k,v]) => [k,v.value]))}))}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis domain={[0,1]} /><Tooltip /><Legend />{['recall','specificity','f2'].map((k,i) => <Bar key={k} dataKey={k} name={metricLabels[k]} fill={colors[i]} isAnimationActive={false} />)}</BarChart></ResponsiveContainer></div>
    <h3>Matrices de confusión</h3><div className="report-comparison">{data.runs.map((r,i) => <section key={r.training_run_id} className="report-evidence"><h4>{runLabel(i)} · {r.evaluation?.split.toUpperCase()}</h4>{r.state === 'available' && r.clinical ? <table className="report-data-table"><caption>Filas reales / columnas predichas</caption><thead><tr><th>Real</th><th>No parasitada</th><th>Parasitada</th></tr></thead><tbody><tr><th>No parasitada</th><td>TN {r.clinical.tn}</td><td>FP {r.clinical.fp}</td></tr><tr><th>Parasitada</th><td>FN {r.clinical.fn}</td><td>TP {r.clinical.tp}</td></tr></tbody></table> : <p>{r.issues.join(' ') || 'Sin métricas clínicas para esta evaluación.'}</p>}<details><summary>Protocolo y atribución</summary><pre>{JSON.stringify(r.evaluation, null, 2)}</pre><pre>{JSON.stringify(r.checkpoint, null, 2)}</pre></details></section>)}</div>
    <p>Los valores describen esta población y este umbral; no identifican un ganador clínico universal.</p>
  </>;
}
export function ConsensusResults({data}: {data: ConsensusEvidence}) {
  if (data.state !== 'available') return <p>{data.state === 'incompatible' ? 'Incompatibilidad metodológica. ' : 'Sin evidencia suficiente para este análisis. '}{data.issues?.join(' ')}</p>;
  return <>
    <p>{data.common_count} muestras comunes de {data.union_count} distintas · {data.label_conflicts} conflictos de etiquetas.</p>
    <div className="scc-highlights"><div className="report-metric"><span>Oracle descriptivo</span><strong>{value((data.oracle?.ratio ?? 0)*100)} %</strong><span>{data.oracle?.numerator} / {data.oracle?.denominator}; no desplegable</span></div><div className="report-metric"><span>Todos fallan</span><strong>{data.all_wrong}</strong></div><div className="report-metric"><span>Errores de alta confianza</span><strong>{data.high_confidence_errors}</strong></div><div className="report-metric"><span>Cerca del umbral</span><strong>{data.low_confidence}</strong></div></div>
    <div className="scc-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={Object.entries(data.distribution ?? {}).map(([category,count]) => ({category,count}))}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="category" tick={{fontSize: 11}} /><YAxis /><Tooltip /><Bar dataKey="count" name="Muestras" fill={colors[0]} isAnimationActive={false} /></BarChart></ResponsiveContainer></div>
    {([['Acuerdo: predicciones iguales / N común', data.agreement], ['Solapamiento de errores: conteos sobre N común', data.error_overlap]] as const).map(([title, matrix]) => <div className="report-table-scroll" key={title}><table className="report-data-table"><caption>{title}; N = {data.common_count}</caption><thead><tr><th>RUN</th>{matrix?.map((_,i) => <th key={i}>{runLabel(i)}</th>)}</tr></thead><tbody>{matrix?.map((row,i) => <tr key={i}><th scope="row">{runLabel(i)}</th>{row.map((n,j) => <td key={j}>{n} / {data.common_count}</td>)}</tr>)}</tbody></table></div>)}
    <div className="report-table-scroll"><table className="report-data-table"><caption>Cobertura y complementariedad por RUN</caption><thead><tr><th>RUN</th><th>Población</th><th>Comunes</th><th>Faltantes</th><th>Exclusivas</th><th>Errores exclusivos</th><th>Aciertos exclusivos</th></tr></thead><tbody>{data.coverage?.map((c,i) => <tr key={i}><th>{runLabel(i)}</th><td>{c.population}</td><td>{c.common}</td><td>{c.missing}</td><td>{c.exclusive}</td><td>{data.exclusive_errors?.[i]}</td><td>{data.exclusive_correct?.[i]}</td></tr>)}</tbody></table></div>
    <details><summary>Fórmulas y denominadores</summary>{Object.entries(data.definitions ?? {}).map(([k,v]) => <p key={k}>{v}</p>)}</details>
    <div className="report-table-scroll" tabIndex={0}><table className="report-data-table"><caption>Muestras · {data.total} resultados del filtro</caption><thead><tr><th>Muestra</th><th>Clase real</th><th>Categoría</th>{data.coverage?.map((_,i) => <th key={i}>{runLabel(i)}</th>)}</tr></thead><tbody>{data.samples?.map(s => <tr key={s.sample}><th scope="row"><details><summary>{s.sample.split('/').pop()}</summary><code>{s.sample}</code><CopyText text={s.sample} label="Copiar muestra" /></details></th><td>{s.label === 1 ? 'Parasitada' : 'No parasitada'}</td><td>{s.category}</td>{s.runs.map((r,i) => <td key={i}>{value(r.score)} · {r.correct ? 'Acierto' : 'Error'} · clase {r.prediction}</td>)}</tr>)}</tbody></table></div>
  </>;
}
export function ScientificResults(props: ModuleProps) {
  const [offset, setOffset] = useState(0);
  const [category, setCategory] = useState('disagreement');
  return <>
    <LazyScientificModule<CurveEvidence[]> {...props} selections={props.selections.map(s => ({training_run_id: s.training_run_id}))} title="Curvas TRAIN / VAL" module="curves">{data => <TrainingCurves data={data} />}</LazyScientificModule>
    <LazyScientificModule<MetricsEvidence> {...props} title="Métricas clínicas y matrices de confusión" module="metrics">{data => <ClinicalMetrics data={data} />}</LazyScientificModule>
    <LazyScientificModule<ConsensusEvidence> {...props} title="Consenso y desacuerdos" module="consensus" params={{offset, category}}>{data => <><label>Filtrar muestras<select className="ds-control" value={category} onChange={e => {setCategory(e.target.value); setOffset(0);}}>{['all','disagreement','CONSENSUS_TP','CONSENSUS_TN','CONSENSUS_FP','CONSENSUS_FN','high_confidence_error','low_confidence'].map(c => <option key={c}>{c}</option>)}</select></label><ConsensusResults data={data} />{data.state === 'available' && <nav aria-label="Páginas de muestras"><button className="ds-button" disabled={offset === 0} onClick={() => setOffset(n => Math.max(0,n-25))}>Anterior</button><span>Página {Math.floor(offset/25)+1}</span><button className="ds-button" disabled={offset+25 >= (data.total ?? 0)} onClick={() => setOffset(n => n+25)}>Siguiente</button></nav>}</>}</LazyScientificModule>
  </>;
}
export function ScientificQuestions(props: ModuleProps) {
  return <section><h2>Preguntas científicas</h2>{['¿Dónde se complementan los modelos?', '¿Podemos inferir superioridad clínica?', '¿Qué evidencia explica las predicciones?'].map((q,i) => <LazyScientificModule<{answers: string[]}> key={q} {...props} title={q} module="questions">{data => <p>{data.answers[i]}</p>}</LazyScientificModule>)}</section>;
}

export function ScientificRepresentations(props: ModuleProps) {
  return <LazyScientificModule<{training_run_id: string; artifacts: {id: string; artifact_type: string; metadata: unknown}[]}[]> {...props} title="Embeddings y representaciones · PCA / UMAP / CKA" module="representations">{data => <>
    {data.map((r,i) => <div key={r.training_run_id}>{r.artifacts.length > 0 && <h3>{runLabel(i)}</h3>}{r.artifacts.map(a => <details key={a.id}><summary>{a.artifact_type} · referencia persistida</summary><p>La referencia requiere un contrato de capa, dimensionalidad y población para acreditar una comparación.</p><pre>{JSON.stringify(a, null, 2)}</pre></details>)}</div>)}
    <section aria-label="Sin evidencia"><h3>Sin evidencia</h3>
    {data.map((r,i) => <p key={r.training_run_id}>{runLabel(i)}: {r.artifacts.length === 0 ? 'No hay embeddings disponibles para esta selección. ' : ''}PCA / UMAP: sin proyección atribuible; CKA: sin análisis acreditado por el contrato actual.</p>)}
    <p>EXPLAIN no acredita automáticamente embeddings ni CKA.</p></section>
    <p>No se ejecutan cálculos al abrir este módulo.</p>
  </>}</LazyScientificModule>;
}

export function PersistedXAI({selection, datasource, active}: {selection: RequestedSelection; datasource: string; active: boolean}) {
  const cache = useMemo(createComparisonCache, [datasource, selection.training_run_id]);
  const [revision, setRevision] = useState(0);
  const [attempt, setAttempt] = useState('');
  const [offset, setOffset] = useState(0);
  const [rowPage, setRowPage] = useState(0);
  const visible = useRef(active);
  visible.current = active;
  const choices = useComparisonEvidence(cache, JSON.stringify(['xai-list', datasource, selection, revision]), async () => {
    const all: import('../../types/api').AssessmentChoice[] = [];
    for (let page = 0; ; page += 100) {
      if (!visible.current) throw new Error('Consulta pausada al cerrar XAI.');
      const response = await api.getTrainingAssessments(selection.training_run_id, page);
      if (response.items.some(r => r.training_run_id !== selection.training_run_id)) throw new Error('Linaje incompatible');
      all.push(...response.items.filter(r => r.kind === 'explain' && r.checkpoint_artifact_id === selection.checkpoint_artifact_id && (!selection.split || r.split === selection.split)));
      if (response.items.length < 100) return all;
    }
  }, active);
  const selected = choices.data?.find(r => r.attempt_id === attempt) ?? choices.data?.[0];
  const detail = useComparisonEvidence(cache, selected ? JSON.stringify(['xai-detail', selected.attempt_id, revision]) : null, async () => {
    const response = await api.getAssessment(selected!.attempt_id);
    if (response.training_run_id !== selection.training_run_id || response.id !== selected!.attempt_id || response.kind !== 'explain' || response.identity.model.checkpoint_artifact_id !== selection.checkpoint_artifact_id) throw new Error('Linaje incompatible');
    return response;
  }, active);
  const artifacts = useComparisonEvidence(cache, detail.data ? JSON.stringify(['xai-artifacts', detail.data.id, offset, revision]) : null,
    () => api.getAssessmentArtifacts(detail.data!.id, offset), active);
  const rows = useMemo(() => detail.data && artifacts.data ? groupXAIComparisons([{detail: detail.data, artifacts: artifacts.data.items}], selection.training_run_id) : [], [detail.data, artifacts.data, selection.training_run_id]);
  return <section>
    {choices.loading || detail.loading || artifacts.loading ? <p role="status">Consultando explicaciones persistidas…</p> : null}
    {choices.error || detail.error || artifacts.error ? <p role="alert">Error al consultar explicaciones. <button className="ds-button" onClick={() => setRevision(n => n+1)}>Reintentar</button></p> : null}
    {choices.data?.length === 0 && <p>No hay explicaciones compatibles para esta selección.</p>}
    {choices.data && choices.data.length > 0 && <label>Explicación persistida<select className="ds-control" value={selected?.attempt_id ?? ''} onChange={e => {setAttempt(e.target.value); setOffset(0); setRowPage(0);}}>{choices.data.map((c,i) => <option value={c.attempt_id} key={c.attempt_id}>{i+1} · {c.split.toUpperCase()} · {c.state} · {new Date(c.started_at).toLocaleString('es-CL')}</option>)}</select></label>}
    {active && rows.slice(rowPage*5,rowPage*5+5).map(row => <XAIComparisonViewer key={row.id} comparison={row} datasource={datasource} />)}
    {rows.length > 5 && <nav aria-label="Muestras XAI"><button className="ds-button" disabled={!rowPage} onClick={() => setRowPage(n => n-1)}>Muestras anteriores</button><button className="ds-button" disabled={(rowPage+1)*5 >= rows.length} onClick={() => setRowPage(n => n+1)}>Muestras siguientes</button></nav>}
    {artifacts.data && (offset > 0 || artifacts.data.items.length === 100) && <nav aria-label="Páginas de explicaciones"><button className="ds-button" disabled={offset === 0} onClick={() => {setOffset(n => n-100); setRowPage(0);}}>Anterior</button><span>Página {offset/100+1}</span><button className="ds-button" disabled={artifacts.data.items.length < 100} onClick={() => {setOffset(n => n+100); setRowPage(0);}}>Siguiente</button></nav>}
  </section>;
}
