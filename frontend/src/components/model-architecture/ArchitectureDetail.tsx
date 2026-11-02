import { useState, type MouseEvent } from 'react';
import { Link } from 'react-router-dom';

import { buildShareableUrl, routes, withAllowedQuery } from '../../router';
import type { ModelArchitecture } from '../../types/modelArchitecture';
import { EvidenceButton, Kpi, SectionAnswer } from '../reports/AnalysisWorkspace';
import { CopyText } from '../reports/ComparisonPython';
import { ActivationTracePanel } from './ActivationTracePanel';
import { ArchitectureChart } from './ArchitectureChart';
import { MathFunctionPanel } from './MathFunctionPanel';
import { architectureViews, countText, lossText, outputText, phaseLabels, shapeText, viewsFor, type ArchitectureView } from './architectureViews';

/** One model's architecture; Arquitectura del modelo and Análisis de Modelos differ only in who owns the view and the phase. */
export function ArchitectureDetail({ data, view, onView, phase, onPhase, datasource, explorerLink = false }: { data: ModelArchitecture; view: ArchitectureView; onView: (view: ArchitectureView) => void;
  phase: string; onPhase: (phase: string) => void; datasource: string; explorerLink?: boolean }) {
  const [requestedBlock, setRequestedBlock] = useState<string | null>(null);
  const block = data.blocks.find(item => item.id === requestedBlock) ?? data.blocks.find(item => item.kind !== 'input') ?? data.blocks[0];
  // Every drawn block carries data-block, so one listener serves all the chart types.
  const pickBlock = (event: MouseEvent<HTMLDivElement>) => {
    const id = (event.target as Element).closest('[data-block]')?.getAttribute('data-block');
    if (id) setRequestedBlock(id);
  };
  const current = data.phases.find(item => item.phase === phase);
  const reference = data.blocks.some(block => block.origin === 'reference');
  return <>
    <SectionAnswer indicators={<>
      <Kpi label="Entrada" value={shapeText(data.input_shape)} detail={data.framework ?? undefined} />
      <Kpi label="Parámetros totales" value={countText(data.total_parameters)} detail={data.total_parameters == null ? 'El TRAIN no los registró' : 'Calculados desde la configuración'} />
      <Kpi label={`Entrenables · ${phaseLabels[phase] ?? phase}`} value={countText(current?.trainable_parameters)} detail={current?.encoder ? `Encoder: ${current.encoder}` : undefined} />
      <Kpi label="Capa de salida" value={outputText(data.output)} detail={lossText(data.output)} />
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
    <div className="mx-selectable" onClick={pickBlock}>
      {block && <style>{`.mx-selectable [data-block="${block.id}"] rect, .mx-selectable [data-block="${block.id}"] polygon { stroke-width: 3; }`}</style>}
      <ArchitectureChart data={data} view={view} phase={phase} />
    </div>
    {explorerLink && <Link className="ds-button" data-size="compact" to={withAllowedQuery(routes.modelExplorer, { datasource, run: data.training_run_id, grafico: view, fase: phase })}>Abrir vista completa</Link>}
    <p className="mx-legend"><span data-trained="true" />Se entrena en esta fase<span data-trained="false" />Congelado o sin pesos</p>
    {data.family === 'vgg16' && <ActivationTracePanel runId={data.training_run_id} datasource={datasource} onBlock={setRequestedBlock} architecture={data} />}
    {block && <MathFunctionPanel data={data} block={block} onBlock={setRequestedBlock} />}
    <EvidenceButton title="Identidad del modelo" label="Identidad del modelo">
      <p className="report-identifier">TRAIN: {data.training_run_id}<br />Checkpoint: {data.checkpoint.artifact_id ?? 'Sin evidencia'}</p>
      <CopyText text={buildShareableUrl(routes.modelExplorer, { datasource, run: data.training_run_id, grafico: view })} label="Copiar enlace" />
      {' '}<Link className="ds-button" to={withAllowedQuery(routes.runDetail(data.training_run_id), { datasource })}>Abrir ficha del TRAIN</Link>
    </EvidenceButton>
  </>;
}
