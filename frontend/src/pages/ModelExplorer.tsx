import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { ArchitectureDetail } from '../components/model-architecture/ArchitectureDetail';
import { resolveView } from '../components/model-architecture/architectureViews';
import { TraceabilityProvider } from '../components/reports/AnalysisWorkspace';
import { RunSelectorDialog } from '../components/reports/RunSelectorDialog';
import { useComparisonTrainingSummaries } from '../hooks/useComparisonTrainingSummaries';
import { useModelArchitecture } from '../hooks/useModelArchitecture';
import { isValidPublicId } from '../router';
import '../styles/ds-primitives.css';
import '../styles/report-components.css';
import '../styles/scc-comparison.css';
import '../styles/model-explorer.css';

export function ModelExplorer({ datasource }: { datasource: string }) {
  const [search, setSearch] = useSearchParams();
  const requested = search.get('run');
  const run = isValidPublicId(requested) ? requested : null;
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const [selectorLoaded, setSelectorLoaded] = useState(false);
  const [draft, setDraft] = useState<string | null>(run);
  useEffect(() => setDraft(run), [run]);
  const { summaries, error: summariesError, retry: retrySummaries } = useComparisonTrainingSummaries(datasource, selectorLoaded);
  const { data, error, loading, retry } = useModelArchitecture(datasource, run);
  const update = useCallback((values: Record<string, string | null>) => setSearch(previous => {
    const params = new URLSearchParams(previous);
    Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, value); else params.delete(key); });
    return params;
  }, { replace: true }), [setSearch]);
  const open = (button: HTMLButtonElement) => { trigger.current = button; setDraft(run); setSelectorLoaded(true); dialog.current?.showModal(); };
  const view = data ? resolveView(data.family, search.get('grafico')) : null;
  const phases = data?.phases ?? [];
  const phase = phases.find(item => item.phase === search.get('fase'))?.phase ?? phases.at(-1)?.phase ?? '';
  const runLabel = (id: string) => summaries?.items.find(item => item.run_id === id)?.model_name || id;
  return <TraceabilityProvider><section className="ds-page ds-report scc-page mx-page">
    <header className="ds-page-header">
      <div className="scc-heading-copy"><h1 className="report-heading">Arquitectura del modelo</h1>
        <p className="report-copy">Selecciona un RUN para ver la arquitectura del modelo que entrenó.</p></div>
      <button type="button" className="ds-button" data-variant="primary" onClick={event => open(event.currentTarget)}>{run ? 'Cambiar RUN' : '＋ Seleccionar RUN'}</button>
    </header>
    {requested && !run && <p className="ds-callout" data-tone="warning" role="alert">El identificador de RUN de la URL no es válido.</p>}
    {!run && <button type="button" className="ds-button scc-empty-slot" onClick={event => open(event.currentTarget)}><strong>＋ Seleccionar RUN</strong><span>Aún no hay un modelo seleccionado</span></button>}
    {loading && <p role="status">Consultando la arquitectura registrada…</p>}
    {error && <div className="ds-callout" role="alert"><p>{error}</p><button type="button" className="ds-button" onClick={retry}>Reintentar</button></div>}
    {data?.state === 'missing' && <p className="ds-callout" data-tone="warning" role="status">{data.issues.join(' ')}</p>}
    {data?.state === 'available' && view && <ArchitectureDetail data={data} view={view} phase={phase} datasource={datasource}
      onView={next => update({ grafico: next })} onPhase={next => update({ fase: next })} />}
    <RunSelectorDialog dialog={dialog} ids={draft ? [draft] : []} summaries={summaries} error={summariesError} retry={retrySummaries}
      counter={draft ? 'RUN seleccionado' : 'Ningún RUN seleccionado'} emptyHint="Marca el TRAIN cuyo modelo quieres ver." submitLabel="Ver modelo" runLabel={runLabel}
      onRemove={() => setDraft(null)} onClose={() => trigger.current?.focus()} onSubmit={() => update({ run: draft, grafico: null, fase: null })}
      canSelect={() => true} onChange={(id, selected) => setDraft(selected ? id : null)} />
  </section></TraceabilityProvider>;
}
