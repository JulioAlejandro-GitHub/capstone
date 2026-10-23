import { ComparisonEligibilityStatus } from '../components/reports/ComparisonEligibilityStatus';
import { EvaluationNavigation } from '../components/reports/ScientificReport';
import type { RequestedSelection } from '../types/scientificPreflight';
import { useAuth } from '../auth';
import { ScientificPreflight } from '../components/reports/ScientificPreflight';
import { useCallback, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { defaultEvaluationSlot, evaluationSlots, type EvaluationSlot } from '../utils/lineageSlots';
const isEvaluationSlot = (value: string | null): value is EvaluationSlot => evaluationSlots.some(slot => slot.id === value);
import { TraceabilityProvider, defaultAnalysisSection, isAnalysisSection, type AnalysisSection } from '../components/reports/AnalysisWorkspace';
import { useComparisonCatalog } from '../hooks/useComparisonCatalog';
import { useComparisonSelection } from '../hooks/useComparisonSelection';
import { ComparisonRunCard } from '../components/reports/ComparisonRunCard';
import { RunSummaryRow } from '../components/reports/RunSummaryRow';
import { useComparisonTrainingSummaries } from '../hooks/useComparisonTrainingSummaries';
import '../styles/ds-primitives.css';
import '../styles/report-components.css';
import '../styles/scc-comparison.css';

function ComparisonPage({ datasource }: { datasource: string }) {
  const { catalog, error, retry } = useComparisonCatalog(datasource);
  const { ids, add, remove } = useComparisonSelection();
  const [evaluations, setEvaluations] = useState<Record<string, RequestedSelection>>({});
  const onEvaluation = useCallback((selection: RequestedSelection) => setEvaluations(previous =>
    JSON.stringify(previous[selection.training_run_id]) === JSON.stringify(selection) ? previous : { ...previous, [selection.training_run_id]: selection }), []);
  const selections = ids.map(id => evaluations[id] ?? { training_run_id: id });
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const [query, setQuery] = useState('');
  const [selectorLoaded, setSelectorLoaded] = useState(false);
  const [trayOpen, setTrayOpen] = useState(true);
  const [lineageRevision, setLineageRevision] = useState(0);
  const onGenerated = useCallback(() => setLineageRevision(value => value + 1), []);
  const [explains, setExplains] = useState<Record<string, string[]>>({});
  const onExplain = useCallback((id: string, attemptIds: string[]) => setExplains(previous =>
    previous[id]?.join(',') === attemptIds.join(',') ? previous : { ...previous, [id]: attemptIds }), []);
  const [search, setSearch] = useSearchParams();
  const requested = search.get('seccion');
  const section: AnalysisSection = isAnalysisSection(requested) ? requested : defaultAnalysisSection;
  const focusSample = search.get('muestra');
  const onFocusSample = useCallback((sample: string | null, next?: AnalysisSection) => setSearch(previous => {
    const params = new URLSearchParams(previous);
    if (sample) params.set('muestra', sample); else params.delete('muestra');
    if (next) { if (next === defaultAnalysisSection) params.delete('seccion'); else params.set('seccion', next); }
    return params;
  }, { replace: true }), [setSearch]);
  const requestedProtocol = search.get('evaluacion');
  const protocol: EvaluationSlot = isEvaluationSlot(requestedProtocol) ? requestedProtocol : defaultEvaluationSlot;
  const setProtocol = useCallback((next: EvaluationSlot) => setSearch(previous => {
    const params = new URLSearchParams(previous);
    if (next === defaultEvaluationSlot) params.delete('evaluacion'); else params.set('evaluacion', next);
    return params;
  }, { replace: true }), [setSearch]);
  // Only the section is written; datasource and any other allowed query value are preserved.
  const selectSection = useCallback((next: AnalysisSection) => setSearch(previous => {
    const params = new URLSearchParams(previous);
    if (next === defaultAnalysisSection) params.delete('seccion'); else params.set('seccion', next);
    return params;
  }, { replace: true }), [setSearch]);
  const { summaries, error: summariesError, retry: retrySummaries } = useComparisonTrainingSummaries(datasource, selectorLoaded);
  const maximum = catalog?.comparison.scc_max_comparison_runs;
  const available = maximum === undefined ? 0 : Math.max(0, maximum - ids.length);
  const choices = catalog?.items.flatMap(model => model.training_runs.map(run => ({ model, run }))) ?? [];
  const filtered = summaries?.items.filter(run => {
    const model = choices.find(choice => choice.run.training_run_id === run.run_id)?.model;
    return `${run.model_name ?? ''} ${model?.architecture ?? ''} ${run.run_id} ${run.run_name ?? ''}`.toLowerCase().includes(query.toLowerCase());
  }) ?? [];
  const openSelector = (button: HTMLButtonElement) => {
    trigger.current = button;
    setQuery('');
    setSelectorLoaded(true);
    dialog.current?.showModal();
  };
  return <TraceabilityProvider><section className="ds-page ds-report scc-page">
    <header className="ds-page-header">
      <div className="scc-heading-copy"><h1 className="report-heading">Análisis de Modelos</h1><p className="report-copy">{ids.length === 1
        ? '¿Qué aprendió el modelo? Dinámica de aprendizaje, desempeño clínico, errores y explicabilidad de un TRAIN.'
        : ids.length > 1 ? 'Comparación científica: dinámica de aprendizaje, desempeño, complementariedad de errores y explicabilidad entre TRAIN.'
          : 'Selecciona un TRAIN para analizar qué aprendió el modelo, o varios para compararlos científicamente.'}</p></div>
      <div className="report-metric" aria-live="polite"><span>Capacidad utilizada / máxima</span><strong>{ids.length} / {maximum ?? '—'}</strong></div>
    </header>
    {error && <div className="ds-callout" role="alert"><p>{error}</p><button className="ds-button" onClick={retry}>Reintentar consulta</button></div>}
    {!catalog && !error && <p role="status">Cargando catálogo de TRAIN y capacidad…</p>}
    <div className="ds-page-header"><h2>Ejecuciones seleccionadas</h2>
      <div className="scc-tray-actions">{ids.length > 0 && <button type="button" className="ds-button" aria-expanded={trayOpen} aria-controls="scc-run-tray" onClick={() => setTrayOpen(open => !open)}>{trayOpen ? 'Ocultar tarjetas' : 'Mostrar tarjetas'}</button>}
        <button className="ds-button" data-variant="primary" disabled={!available} onClick={event => openSelector(event.currentTarget)}>Añadir RUN</button></div>
    </div>
    <p role="status">{ids.length < 2 ? ids.length === 1 ? 'Todavía no existe una comparación configurada: con un TRAIN se analiza qué aprendió el modelo; añade otro para comparar.' : 'Todavía no existe una comparación configurada. Selecciona al menos dos TRAIN.' : 'Selección preparada para consultar evidencia científica.'}
      {maximum !== undefined && !available ? ' Capacidad máxima alcanzada.' : ''}
      {maximum !== undefined && ids.length > maximum ? ' La configuración cambió: quita ejecuciones para respetar el máximo actual.' : ''}</p>
    {ids.length > 0 && <fieldset className="scc-protocol"><legend>Evaluación del análisis</legend>
      {evaluationSlots.map(slot => <label key={slot.id}><input type="radio" name="scc-protocol" checked={protocol === slot.id} onChange={() => setProtocol(slot.id)} /><span><strong>{slot.label}</strong><small>{slot.detail}</small></span></label>)}
      <p className="scc-meta">Se aplica a todos los RUN; en cada tarjeta puedes elegir otra ejecución, que queda marcada como distinta al análisis.</p>
    </fieldset>}
    <div className="report-comparison" id="scc-run-tray" hidden={!trayOpen}>
      {ids.map((id, index) => {
        const choice = choices.find(item => item.run.training_run_id === id);
        return <ComparisonRunCard key={`${datasource}:${id}`} id={id} index={index} datasource={datasource}
          modelName={choice?.model.model_name} architecture={choice?.model.architecture} onRemove={() => remove(id)}><EvaluationNavigation id={id} datasource={datasource} protocol={protocol} lineageRevision={lineageRevision} onChange={onEvaluation} onExplainChange={onExplain} /></ComparisonRunCard>;
      })}
      {Array.from({ length: available }, (_, index) => <button key={index} className="ds-button scc-empty-slot"
        onClick={event => openSelector(event.currentTarget)}><strong>＋ Añadir RUN</strong><span>Espacio {ids.length + index + 1} disponible</span></button>)}
    </div>
    <ScientificPreflight selections={selections} ids={ids} datasource={datasource} maximum={maximum} section={section} onSectionChange={selectSection} explains={explains} onGenerated={onGenerated} focusSample={focusSample} onFocusSample={onFocusSample} />
    <dialog ref={dialog} className="report-viewer scc-run-selector" aria-labelledby="scc-selector-title" onClose={() => trigger.current?.focus()}>
      <div className="ds-page-header"><h2 id="scc-selector-title">Seleccionar ejecuciones TRAIN</h2>
        <button className="ds-button" onClick={() => dialog.current?.close()}>Cerrar</button></div>
      <p>Seleccionadas: {ids.length} / {maximum ?? '—'}. Cada identificador corresponde a un TRAIN concreto.</p>
      <label>Buscar modelo, arquitectura o identificador<input autoFocus className="ds-control" value={query} onChange={event => setQuery(event.target.value)} /></label>
      {summariesError && <div role="alert"><p>{summariesError}</p><button className="ds-button" onClick={retrySummaries}>Reintentar carga</button></div>}
      {!summaries && !summariesError && <p role="status">Cargando resúmenes de Ejecuciones…</p>}
      <ul className="scc-choices">{filtered.map(run => {
        const eligibility = choices.find(choice => choice.run.training_run_id === run.run_id)?.run.eligibility;
        return <li key={run.run_id} data-selected={ids.includes(run.run_id)}>
        <label><input type="checkbox" checked={ids.includes(run.run_id)} disabled={!ids.includes(run.run_id) && (!available || !eligibility?.eligible)}
          onChange={event => event.target.checked && eligibility?.eligible && maximum !== undefined ? add(run.run_id, maximum) : remove(run.run_id)} />
          {ids.includes(run.run_id) ? 'Seleccionado' : 'Seleccionar'}: {run.model_name || run.run_name || run.run_id}
        </label>
        <ComparisonEligibilityStatus eligibility={eligibility} />
        {eligibility?.reasons.some(reason => reason.code === 'ERROR_DE_CONSULTA') &&
          <button className="ds-button" onClick={retry}>Reintentar elegibilidad</button>}
        <RunSummaryRow run={run} processKind="training" variant="compact" onRunSelect={() => {}} />
      </li>; })}</ul>
      {summaries && !filtered.length && <p>Sin ejecuciones TRAIN disponibles para esta búsqueda.</p>}
      {summaries && summaries.count >= summaries.limit && <p role="status">Se muestran hasta {summaries.limit} entrenamientos recientes.</p>}
    </dialog>
  </section></TraceabilityProvider>;
}

export function ModelComparison({ datasource }: { datasource: string }) {
  const { user, status } = useAuth();
  return <ComparisonPage key={JSON.stringify([user, status, datasource])} datasource={datasource} />;
}
