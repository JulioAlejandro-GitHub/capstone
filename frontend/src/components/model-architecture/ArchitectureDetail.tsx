import { useMemo, useState, type MouseEvent } from 'react';
import { Link } from 'react-router-dom';

import { buildShareableUrl, routes, withAllowedQuery } from '../../router';
import type { ModelArchitecture } from '../../types/modelArchitecture';
import { EvidenceButton, Kpi, SectionAnswer } from '../reports/AnalysisWorkspace';
import { CopyText } from '../reports/ComparisonPython';
import { ActivationTracePanel } from './ActivationTracePanel';
import { ArchitectureChart, type BlockActivity } from './ArchitectureChart';
import { MathFunctionPanel } from './MathFunctionPanel';
import { architectureViews, countText, isTraceable, lossText, outputText, phaseLabels, shapeText, splitHead, viewsFor, type ArchitectureView } from './architectureViews';

/** One model's architecture; Arquitectura del modelo and Análisis de Modelos differ only in who owns the view and the phase. */
export function ArchitectureDetail({ data: source, view, onView, phase, onPhase, datasource, explorerLink = false, trainingLink = false }: { data: ModelArchitecture; view: ArchitectureView; onView: (view: ArchitectureView) => void;
  phase: string; onPhase: (phase: string) => void; datasource: string; explorerLink?: boolean; trainingLink?: boolean }) {
  // VGG16 draws its head layer by layer: the drawing then has one element per step of a cell's trace.
  const data = useMemo(() => source.family === 'vgg16' ? splitHead(source) : source, [source]);
  const [requestedBlock, setRequestedBlock] = useState<string | null>(null);
  // A click on the drawing is also a request to the cell trace; the counter tells a new click from the trace's own echo.
  const [blockClick, setBlockClick] = useState<{ id: string; n: number } | null>(null);
  const [activity, setActivity] = useState<BlockActivity | null>(null);
  const [traceSample, setTraceSample] = useState<string | null>(null);
  const block = data.blocks.find(item => item.id === requestedBlock) ?? data.blocks.find(item => item.kind !== 'input') ?? data.blocks[0];
  // Every drawn block carries data-block, so one listener serves all the chart types.
  const pickBlock = (event: MouseEvent<HTMLDivElement>) => {
    const id = (event.target as Element).closest('[data-block]')?.getAttribute('data-block');
    if (id) { setRequestedBlock(id); setBlockClick(previous => ({ id, n: (previous?.n ?? 0) + 1 })); }
  };
  const current = data.phases.find(item => item.phase === phase);
  const reference = data.blocks.some(block => block.origin === 'reference');
  return <>
    <SectionAnswer indicators={<>
      <Kpi label="Entrada" value={shapeText(data.input_shape)} detail={data.framework ?? undefined} />
      <Kpi label="Parámetros totales" value={countText(data.total_parameters)} detail={data.total_parameters == null ? 'El TRAIN no los registró' : data.structure ? 'Derivados de la base registrada' : 'Calculados desde la configuración'} />
      {data.zero_shot
        ? <Kpi label="Entrenables" value="0" detail="Modelo zero-shot: no hubo entrenamiento" />
        : <Kpi label={`Entrenables · ${phaseLabels[phase] ?? phase}`} value={countText(current?.trainable_parameters)} detail={current?.encoder ? `Encoder: ${current.encoder}` : undefined} />}
      <Kpi label="Capa de salida" value={outputText(data.output)} detail={lossText(data.output)} />
      {data.zero_shot
        ? <Kpi label="Checkpoint" value="Versión registrada" detail={`Sin épocas · ${data.zero_shot.model_version_id.slice(0, 8)}`} />
        : <Kpi label="Checkpoint" value={data.checkpoint.selected_epoch == null ? 'Sin evidencia' : `Época ${data.checkpoint.selected_epoch}`} detail={data.checkpoint.phase ? phaseLabels[data.checkpoint.phase] ?? data.checkpoint.phase : undefined} />}
    </>}>
      {data.model_name ?? 'Modelo sin nombre'} · arquitectura {data.architecture ?? 'sin evidencia'}. {data.zero_shot
        ? <>TRAIN lógico: no hubo entrenamiento. La imagen pasa por el encoder ViT de la base registrada{data.structure ? ` (${data.structure.patches ?? '—'} parches + CLS = ${data.structure.tokens ?? '—'} tokens)` : ''} y su embedding se compara con los de {data.zero_shot.prompts.length} prompts; softmax da el score relativo, que no es una probabilidad calibrada.
          {data.zero_shot.prompts.length > 0 && <span className="mx-prompts">{data.zero_shot.prompts.map((prompt, i) => <span key={prompt}><b>{data.zero_shot!.class_order[i] ?? `clase ${i}`}</b> «{prompt}»</span>)}</span>}</>
        : data.structure
        ? `El TRAIN registra la entrada, la cabeza y el conjunto entrenable de cada fase; formas y parámetros de los bloques ViT se derivan de la base registrada (${data.structure.patches ?? '—'} parches + CLS = ${data.structure.tokens ?? '—'} tokens de ${data.structure.width ?? '—'} dimensiones).`
        : reference
        ? 'El TRAIN registra la entrada, la cabeza y la cantidad de parámetros entrenados; los bloques ViT son la estructura de referencia del encoder.'
        : 'Capas y conexiones registradas por este TRAIN; dimensiones y parámetros calculados desde esa configuración.'}
    </SectionAnswer>
    <div className="scc-chart-toolbar">
      <div className="mx-view-actions">
        <div className="scc-segmented" role="group" aria-label="Tipo de gráfico">{viewsFor(data.family).map(item => <button key={item} type="button" className="ds-button" data-size="compact"
          aria-pressed={item === view} onClick={() => onView(item)}>{architectureViews[item]}</button>)}</div>
        {trainingLink && <a className="ds-button" data-size="compact" href={withAllowedQuery(routes.modelTraining, { datasource, run: data.training_run_id, fase: phase, muestra: traceSample })}
          target="_blank" rel="noopener noreferrer" title="Abre la vista Entrenamiento en una pestaña nueva">Entrenamiento ↗</a>}
      </div>
      {data.phases.length > 1 && <div className="scc-segmented" role="group" aria-label="Fase de entrenamiento">{data.phases.map(item => <button key={item.phase} type="button" className="ds-button" data-size="compact"
        aria-pressed={item.phase === phase} onClick={() => onPhase(item.phase)}>{phaseLabels[item.phase] ?? item.phase}</button>)}</div>}
    </div>
    <div className="mx-selectable" onClick={pickBlock}>
      {block && <style>{`.mx-selectable [data-block="${block.id}"] rect, .mx-selectable [data-block="${block.id}"] polygon { stroke-width: 3; }`}</style>}
      <ArchitectureChart data={data} view={view} phase={phase} activity={isTraceable(data.family) ? activity : null} />
    </div>
    {explorerLink && <Link className="ds-button" data-size="compact" to={withAllowedQuery(routes.modelExplorer, { datasource, run: data.training_run_id, grafico: view, fase: phase })}>Abrir vista completa</Link>}
    <p className="mx-legend"><span data-trained="true" />Se entrena en esta fase<span data-trained="false" />Congelado o sin pesos</p>
    {isTraceable(data.family) && <ActivationTracePanel runId={data.training_run_id} datasource={datasource} onBlock={setRequestedBlock} architecture={data} blockClick={blockClick} onActivity={setActivity} onSample={setTraceSample} />}
    {block && <MathFunctionPanel data={data} block={block} onBlock={setRequestedBlock} />}
    <EvidenceButton title="Identidad del modelo" label="Identidad del modelo">
      <p className="report-identifier">TRAIN: {data.training_run_id}<br />Checkpoint: {data.checkpoint.artifact_id ?? 'Sin evidencia'}</p>
      <CopyText text={buildShareableUrl(routes.modelExplorer, { datasource, run: data.training_run_id, grafico: view })} label="Copiar enlace" />
      {' '}<Link className="ds-button" to={withAllowedQuery(routes.runDetail(data.training_run_id), { datasource })}>Abrir ficha del TRAIN</Link>
    </EvidenceButton>
  </>;
}
