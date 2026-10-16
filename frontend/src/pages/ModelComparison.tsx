import { ScientificPreflight } from '../components/reports/ScientificPreflight';
import { useRef, useState } from 'react';
import { useComparisonCatalog } from '../hooks/useComparisonCatalog';
import { useComparisonSelection } from '../hooks/useComparisonSelection';
import { ComparisonRunCard } from '../components/reports/ComparisonRunCard';
import { formatDate } from '../utils/format';
import '../styles/ds-primitives.css';
import '../styles/report-components.css';
import '../styles/scc-comparison.css';

export function ModelComparison({ datasource }: { datasource: string }) {
  const { catalog, error, retry } = useComparisonCatalog(datasource);
  const { ids, add, remove } = useComparisonSelection();
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const [query, setQuery] = useState('');
  const maximum = catalog?.comparison.scc_max_comparison_runs;
  const available = maximum === undefined ? 0 : Math.max(0, maximum - ids.length);
  const choices = catalog?.items.flatMap(model => model.training_runs.map(run => ({ model, run }))) ?? [];
  const filtered = choices.filter(({ model, run }) =>
    `${model.model_name} ${model.architecture ?? ''} ${run.training_run_id} ${run.run_name ?? ''}`.toLowerCase().includes(query.toLowerCase()));
  const openSelector = (button: HTMLButtonElement) => {
    trigger.current = button;
    setQuery('');
    dialog.current?.showModal();
  };
  return <section className="ds-page ds-report scc-page">
    <header className="ds-page-header">
      <div className="scc-heading-copy"><h1 className="report-heading">Comparación Científica</h1><p className="report-copy">Análisis comparativo de ejecuciones, dinámica de aprendizaje, topología de representaciones y complementariedad de errores.</p></div>
      <div className="report-metric" aria-live="polite"><span>Capacidad utilizada / máxima</span><strong>{ids.length} / {maximum ?? '—'}</strong></div>
    </header>
    {error && <div className="ds-callout" role="alert"><p>{error}</p><button className="ds-button" onClick={retry}>Reintentar consulta</button></div>}
    {!catalog && !error && <p role="status">Cargando catálogo de TRAIN y capacidad…</p>}
    <div className="ds-page-header"><h2>Ejecuciones seleccionadas</h2>
      <button className="ds-button" data-variant="primary" disabled={!available} onClick={event => openSelector(event.currentTarget)}>Añadir RUN</button>
    </div>
    <p role="status">{ids.length < 2 ? 'Todavía no existe una comparación configurada. Selecciona al menos dos TRAIN.' : 'Selección preparada para consultar evidencia científica.'}
      {maximum !== undefined && !available ? ' Capacidad máxima alcanzada.' : ''}
      {maximum !== undefined && ids.length > maximum ? ' La configuración cambió: quita ejecuciones para respetar el máximo actual.' : ''}</p>
    <div className="report-comparison">
      {ids.map((id, index) => {
        const choice = choices.find(item => item.run.training_run_id === id);
        return <ComparisonRunCard key={`${datasource}:${id}`} id={id} index={index} datasource={datasource}
          modelName={choice?.model.model_name} architecture={choice?.model.architecture} onRemove={() => remove(id)} />;
      })}
      {Array.from({ length: available }, (_, index) => <button key={index} className="ds-button scc-empty-slot"
        onClick={event => openSelector(event.currentTarget)}><strong>＋ Añadir RUN</strong><span>Espacio {ids.length + index + 1} disponible</span></button>)}
    </div>
    <ScientificPreflight ids={ids} datasource={datasource} maximum={maximum} />
    <dialog ref={dialog} className="report-viewer" aria-labelledby="scc-selector-title" onClose={() => trigger.current?.focus()}>
      <div className="ds-page-header"><h2 id="scc-selector-title">Seleccionar ejecuciones TRAIN</h2>
        <button className="ds-button" onClick={() => dialog.current?.close()}>Cerrar</button></div>
      <p>Seleccionadas: {ids.length} / {maximum ?? '—'}. Cada identificador corresponde a un TRAIN concreto.</p>
      <label>Buscar modelo, arquitectura o identificador<input autoFocus className="ds-control" value={query} onChange={event => setQuery(event.target.value)} /></label>
      <ul className="scc-choices">{filtered.map(({ model, run }) => <li key={run.training_run_id}>
        <label><input type="checkbox" checked={ids.includes(run.training_run_id)} disabled={!ids.includes(run.training_run_id) && !available}
          onChange={event => event.target.checked && maximum !== undefined ? add(run.training_run_id, maximum) : remove(run.training_run_id)} />
          <span><strong>{model.model_name}</strong> · Arquitectura: {model.architecture ?? 'Sin evidencia'}<br />
            <code className="report-identifier">{run.training_run_id}</code><br />
            {run.run_name ?? 'Sin nombre'} · {run.status} · {formatDate(run.started_at)}</span>
        </label></li>)}</ul>
      {!filtered.length && <p>Sin ejecuciones TRAIN disponibles para esta búsqueda.</p>}
    </dialog>
  </section>;
}
