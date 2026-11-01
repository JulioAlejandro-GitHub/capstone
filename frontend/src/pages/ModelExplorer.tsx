import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { ArchitectureChart } from '../components/model-architecture/ArchitectureChart';
import { architectureViews, countText, phaseLabels, resolveView, shapeText, viewsFor, type ArchitectureView } from '../components/model-architecture/architectureViews';
import { Kpi, SectionAnswer, TraceabilityProvider, EvidenceButton } from '../components/reports/AnalysisWorkspace';
import { CopyText } from '../components/reports/ComparisonPython';
import { RunSelectorDialog } from '../components/reports/RunSelectorDialog';
import { useComparisonTrainingSummaries } from '../hooks/useComparisonTrainingSummaries';
import { useModelArchitecture } from '../hooks/useModelArchitecture';
import { buildShareableUrl, isValidPublicId, routes, withAllowedQuery } from '../router';
import type { ModelArchitecture } from '../types/modelArchitecture';
import '../styles/ds-primitives.css';
import '../styles/report-components.css';
import '../styles/scc-comparison.css';
import '../styles/model-explorer.css';

function ArchitectureDetail({ data, view, onView, phase, onPhase, datasource }: { data: ModelArchitecture; view: ArchitectureView; onView: (view: ArchitectureView) => void;
  phase: string; onPhase: (phase: string) => void; datasource: string }) {
  const current = data.phases.find(item => item.phase === phase);
  const reference = data.blocks.some(block => block.origin === 'reference');
  return <>
    <SectionAnswer indicators={<>
      <Kpi label="Entrada" value={shapeText(data.input_shape)} detail={data.framework ?? undefined} />
      <Kpi label="Parámetros totales" value={countText(data.total_parameters)} detail={data.total_parameters == null ? 'El TRAIN no los registró' : 'Calculados desde la configuración'} />
      <Kpi label={`Entrenables · ${phaseLabels[phase] ?? phase}`} value={countText(current?.trainable_parameters)} detail={current?.encoder ? `Encoder: ${current.encoder}` : undefined} />
      <Kpi label="Checkpoint" value={data.checkpoint.selected_epoch == null ? 'Sin evidencia' : `Época ${data.checkpoint.selected_epoch}`} detail={data.checkpoint.phase ? phaseLabels[data.checkpoint.phase] ?? data.checkpoint.phase : undefined} />
    </>}>
      {data.model_name ?? 'Modelo sin nombre'} · arquitectura {data.architecture ?? 'sin evidencia'}. {reference
        ? 'El TRAIN registra la entrada, la cabeza y la cantidad de parámetros entrenados; los bloques ViT son la estructura de referencia del encoder.'
        : 'Capas y conexiones registradas por este TRAIN; dimensiones y parámetros calculados desde esa configuración.'}
    </SectionAnswer>
    <div className="scc-chart-toolbar">
      <div className="scc-segmented" role="group" aria-label="Tipo de gráfico">{viewsFor(data.family).map(item => <button key={item} type="button" className="ds-button" data-size="compact"
        aria-pressed={item === view} onClick={() => onView(item)}>{architectureViews[item]}</button>)}</div>
      {data.phases.length > 1 && <div className="scc-segmented" role="group" aria-label="Fase de entrenamiento">{data.phases.map(item => <button key={item.phase} type="button" className="ds-button" data-size="compact"
        aria-pressed={item.phase === phase} onClick={() => onPhase(item.phase)}>{phaseLabels[item.phase] ?? item.phase}</button>)}</div>}
    </div>
    <ArchitectureChart data={data} view={view} phase={phase} />
    <p className="mx-legend"><span data-trained="true" />Se entrena en esta fase<span data-trained="false" />Congelado o sin pesos</p>
    <EvidenceButton title="Identidad del modelo" label="Identidad del modelo">
      <p className="report-identifier">TRAIN: {data.training_run_id}<br />Checkpoint: {data.checkpoint.artifact_id ?? 'Sin evidencia'}</p>
      <CopyText text={buildShareableUrl(routes.modelExplorer, { datasource, run: data.training_run_id, grafico: view })} label="Copiar enlace" />
      {' '}<Link className="ds-button" to={withAllowedQuery(routes.runDetail(data.training_run_id), { datasource })}>Abrir ficha del TRAIN</Link>
    </EvidenceButton>
  </>;
}

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
      <div className="scc-heading-copy"><h1 className="report-heading">Explorador de Modelos</h1>
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
