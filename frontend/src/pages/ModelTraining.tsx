import { Fragment, useCallback, useMemo, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { phaseLabels } from '../components/model-architecture/architectureViews';
import { TrainingScene } from '../components/model-training/TrainingScene';
import { TrainingHistoryCard, TrainingTabs } from '../components/model-training/TrainingHistory';
import { viewFrom } from '../components/model-training/trainingHistoryModel';
import { useTrainingHistory } from '../components/model-training/useTrainingHistory';
import {
  PARAMETER_GROUP_LABELS, buildTrainingLayers, formatCount, kindLabel, parametersFor, pendingItems,
  resolveTrainingParameters, trainingChecks, trainingRegime, tuningGuide, type ParameterGroup, type TrainingCheck, type TrainingLayer,
} from '../components/model-training/trainingModel';
import { CELL_CATEGORY_LABELS, cellCategory, classText, useTrainingCell } from '../components/model-training/useTrainingCell';
import { GeneratedXAIComparison } from '../components/reports/GeneratedXAIComparison';
import { useExpandRequest } from '../components/reports/useCellComparison';
import { CellOutcome } from '../components/reports/XAIComparisonViewer';
import { useComparisonRun } from '../hooks/useComparisonRun';
import { useModelArchitecture } from '../hooks/useModelArchitecture';
import { isValidPublicId, routes, withAllowedQuery } from '../router';
import '../styles/ds-primitives.css';
import '../styles/report-components.css';
import '../styles/scc-comparison.css';
import '../styles/model-training.css';

/** Texto con `código` entre acentos graves. */
const rich = (text: string): ReactNode => text.split('`').map((part, i) => i % 2 ? <code key={i}>{part}</code> : <Fragment key={i}>{part}</Fragment>);
const factor = (value: number | null, up: string, down: string) => value == null || value === 1 ? '—'
  : value > 1 ? `${up} ${Number(value.toFixed(2))}×` : `${down} ${Number((1 / value).toFixed(2))}×`;

/** Estado del bloque en la fase: una capa sin pesos no «se congela», simplemente no tiene nada que entrenar. */
const stateText = (layer: TrainingLayer) => layer.trainable ? 'Se entrena' : layer.parameters === 0 ? 'Sin pesos' : 'Congelado';

const categoryText = (item: { label: number | null; predicted: number | null }) => {
  const category = cellCategory(item);
  return category ? CELL_CATEGORY_LABELS[category] : 'Sin evidencia';
};

const CHECK_ICON: Record<TrainingCheck['level'], string> = { warn: '!', ok: '✓', info: 'i', pending: '…' };

function Bar({ pct, tone, label }: { pct: number | null; tone: string; label: string }) {
  return <div className="mt-bar"><div className="mt-track">{pct != null && <div className={`mt-fill mt-${tone}`} style={{ width: `${Math.max(pct, 1.5)}%` }} />}</div><span className="mt-num">{label}</span></div>;
}

/**
 * «Entrenamiento»: vista inmersiva de un TRAIN, abierta en pestaña nueva desde Arquitectura del modelo.
 * Pestañas: «Flujo de tensores» (GET /runs/{id}/architecture y GET /runs/{id}) y la historia del TRAIN
 * (curvas, learning rate y trayectorias VAL registradas); lo que falta se muestra como pendiente.
 */
export function ModelTraining({ datasource }: { datasource: string }) {
  const [search] = useSearchParams();
  const requested = search.get('run');
  if (isValidPublicId(requested)) return <ModelTrainingView datasource={datasource} run={requested} />;
  return <main className="mt-page" data-surface="lab"><div className="mt-wrap">
    <p className="mt-callout" role="alert">{requested ? 'El identificador de RUN de la URL no es válido.' : 'Falta el parámetro run en la URL.'}</p>
    <Link className="mt-link" to={withAllowedQuery(routes.modelExplorer, { datasource })}>Ir a Arquitectura del modelo</Link>
  </div></main>;
}

function ModelTrainingView({ datasource, run }: { datasource: string; run: string }) {
  const [search, setSearch] = useSearchParams();
  const { data, error, loading, retry } = useModelArchitecture(datasource, run);
  const { run: record, error: runError } = useComparisonRun(datasource, run);
  const cellState = useTrainingCell(datasource, run, search.get('muestra'));
  const view = viewFrom(search.get('vista'));
  const history = useTrainingHistory(datasource, run, view);
  const { cell } = cellState;
  // La imagen de la célula (en la tarjeta o en el diagrama) es el acceso a «Vista ampliada»; sin contexto no hay modal que abrir.
  // Regla: toda imagen de célula abre «Vista ampliada». Un clic antes de que llegue el contexto EVALUATE se conserva.
  const { signal: expandSignal, request: openExpanded, pending: expandPending } = useExpandRequest(Boolean(cellState.comparison));
  const openCell = cell && !cellState.contextError ? openExpanded : undefined;
  const phases = data?.phases ?? [];
  const phase = phases.find(item => item.phase === search.get('fase'))?.phase ?? phases.at(-1)?.phase ?? '';
  const layers = useMemo(() => data?.state === 'available' ? buildTrainingLayers(data, phase) : [], [data, phase]);
  const parameters = useMemo(() => resolveTrainingParameters(record, data?.phases ?? []), [record, data]);
  const regime = useMemo(() => trainingRegime(data, parameters), [data, parameters]);
  const checks = useMemo(() => data?.state === 'available' ? trainingChecks(data, layers, parameters, phase) : [], [data, layers, parameters, phase]);
  const pending = useMemo(() => pendingItems(data, layers, parameters, Boolean(record)), [data, layers, parameters, record]);
  const requestedBlock = search.get('bloque');
  const selected = Math.max(0, layers.findIndex(layer => layer.id === requestedBlock));
  const update = useCallback((values: Record<string, string | null>) => setSearch(previous => {
    const params = new URLSearchParams(previous);
    Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, value); else params.delete(key); });
    return params;
  }, { replace: true }), [setSearch]);
  const select = useCallback((index: number) => { const layer = layers[index]; if (layer) update({ bloque: layer.id }); }, [layers, update]);
  const layer: TrainingLayer | undefined = layers[selected];

  const maxH = Math.max(1, ...layers.map(item => item.h ?? 0));
  const maxD = Math.max(1, ...layers.map(item => item.d ?? 0));
  const maxVol = Math.max(1, ...layers.map(item => item.volume ?? 0));
  const maxParams = Math.max(1, ...layers.map(item => item.parameters ?? 0));
  const convs = layers.filter(item => item.kind === 'convolution');
  const input = layers.find(item => item.kind === 'input');
  const lastConv = convs.at(-1);
  const biggest = layers.reduce<TrainingLayer | null>((best, item) => item.volume != null && (!best || item.volume > (best.volume ?? 0)) ? item : best, null);
  const current = phases.find(item => item.phase === phase);
  const phaseLabel = phaseLabels[phase] ?? (phase || 'sin fase');
  const groups = Object.keys(PARAMETER_GROUP_LABELS) as ParameterGroup[];
  const tabs = <TrainingTabs view={view} onChange={next => update({ vista: next === 'flujo' ? null : next })} />;

  return <main className="mt-page" data-surface="lab">
    <div className="mt-wrap">
      <header className="mt-header">
        <div>
          <div className="mt-eyebrow"><span>XAI · Entrenamiento</span>{data?.architecture && <span className="mt-tag">{data.architecture}</span>}</div>
          <h1>{data?.model_name ?? 'Modelo'} <span>· anatomía del modelo entrenado</span></h1>
          <p className="mt-sub">Cómo se transforma una imagen de frotis a lo largo de los bloques del modelo y qué parámetros del entrenamiento gobiernan cada uno. Selecciona un bloque para ver su entrada, salida y qué ajustar en un nuevo entrenamiento.</p>
        </div>
        <div className="mt-actions">
          {phases.length > 1 && <div className="mt-tb-group" role="group" aria-label="Fase de entrenamiento">{phases.map(item => <button key={item.phase} type="button" className="mt-tb"
            aria-pressed={item.phase === phase} onClick={() => update({ fase: item.phase })}>{phaseLabels[item.phase] ?? item.phase}</button>)}</div>}
          <Link className="mt-link" to={withAllowedQuery(routes.modelExplorer, { datasource, run })}>Arquitectura del modelo</Link>
          <Link className="mt-link" to={withAllowedQuery(routes.runDetail(run), { datasource })}>Ficha del TRAIN</Link>
        </div>
      </header>

      {loading && <p className="mt-callout" role="status">Consultando la arquitectura registrada…</p>}
      {error && <div className="mt-callout" role="alert"><p>{error}</p><button type="button" className="mt-tb" onClick={retry}>Reintentar</button></div>}
      {data?.state === 'missing' && <p className="mt-callout" role="status">Pendiente: {data.issues.join(' ') || 'el TRAIN no registró su arquitectura.'}</p>}
      {data?.zero_shot && <p className="mt-callout mt-callout-info" role="note">Modelo zero-shot: TRAIN lógico, sin entrenamiento ni épocas. La arquitectura es la de la base registrada; las curvas, el learning rate y las trayectorias no tienen evidencia porque no hubo optimización. Su desempeño está en EVALUATE, TEST y EXPLAIN.</p>}

      {layers.length > 0 && layer && <>
        <section className="mt-kpis" aria-label="Resumen del modelo">
          <div className="mt-kpi"><div className="mt-k">Bloques</div><div className="mt-v">{layers.length}</div><div className="mt-h">{convs.length ? `${convs.reduce((s, item) => s + item.convolutions, 0)} conv. en ${convs.length} bloques` : data?.structure ? `${data.structure.vit_blocks ?? '—'} bloques Transformer` : `${data?.layers.length ?? 0} capas registradas`}</div></div>
          {data?.structure ? <>
            <div className="mt-kpi"><div className="mt-k">Imagen → parches</div><div className="mt-v">{input?.h ?? '—'}<small> → </small>{data.structure.patches != null ? `${Math.round(Math.sqrt(data.structure.patches))}×${Math.round(Math.sqrt(data.structure.patches))}` : '—'}</div><div className="mt-h">{data.structure.patch_size ? `parches de ${data.structure.patch_size[0]} px; la forma no cambia entre bloques` : 'Pendiente'}</div></div>
            <div className="mt-kpi"><div className="mt-k">Tokens</div><div className="mt-v">{data.structure.tokens ?? '—'}<small> × </small>{data.structure.width ?? '—'}</div><div className="mt-h">{data.structure.patches != null ? `${data.structure.patches} parches + token de clase` : 'Pendiente'}</div></div>
          </> : <>
            <div className="mt-kpi"><div className="mt-k">Resolución espacial</div><div className="mt-v">{input?.h ?? '—'}<small> → </small>{lastConv?.h ?? '—'}</div><div className="mt-h">{input?.h && lastConv?.h ? `${(input.h / lastConv.h).toFixed(1)}× menos por lado al final del backbone` : 'Pendiente'}</div></div>
            <div className="mt-kpi"><div className="mt-k">Canales</div><div className="mt-v">{input?.d ?? '—'}<small> → </small>{lastConv?.d ?? '—'}</div><div className="mt-h">{input?.d && lastConv?.d ? `${Math.round(lastConv.d / input.d)}× más profundidad` : 'Pendiente'}</div></div>
          </>}
          <div className="mt-kpi"><div className="mt-k">Parámetros totales</div><div className="mt-v">{formatCount(data?.total_parameters)}</div><div className="mt-h">{current?.trainable_parameters != null ? `${formatCount(current.trainable_parameters)} entrenables · ${phaseLabel}` : data?.zero_shot ? 'Ninguno entrenado: modelo zero-shot' : 'Entrenables: pendiente'}</div></div>
          <div className="mt-kpi"><div className="mt-k">Tensor más grande</div><div className="mt-v">{formatCount(biggest?.volume)}</div><div className="mt-h">{biggest ? `${biggest.label} · ${biggest.outputText}` : 'Pendiente'}</div></div>
        </section>

        <section className="mt-card mt-cell-card" aria-label="Célula seleccionada">
          <div className="mt-card-h"><h2>Célula seleccionada</h2>
            <span className="mt-hint">{cell ? 'su imagen aparece en la entrada y, con el resultado, en la salida del diagrama' : 'recorridos de activación guardados del TRAIN'}</span></div>
          <div className="mt-cell-body">
            {!cell && <div className="mt-cell-thumb mt-cell-empty" aria-hidden="true">?</div>}
            {cell && !cellState.comparison && (openCell
              ? <button type="button" className="mt-cell-thumb-button" onClick={openCell} aria-busy={expandPending}
                  title={expandPending ? 'Abriendo «Vista ampliada»…' : 'Vista ampliada: célula original y explicabilidad'} aria-label="Ampliar Célula original">
                  <img className="mt-cell-thumb" src={cell.image} alt={`Célula ${cell.sampleId}`} data-category={cell.category ?? 'unknown'} /></button>
              : <img className="mt-cell-thumb" src={cell.image} alt={`Célula ${cell.sampleId}`} data-category={cell.category ?? 'unknown'} />)}
            <div className="mt-cell-info" data-category={cell?.category ?? 'unknown'}>
              {cellState.catalog && cellState.catalog.items.length > 0 && <label className="mt-cell-select">Célula
                <select value={cellState.sampleId ?? ''} onChange={event => update({ muestra: event.target.value })}>
                  {cellState.catalog.items.map(item => <option key={item.sample_id} value={item.sample_id}>
                    {`${categoryText(item)} · ${item.score.toFixed(3)} · ${item.sample_id.slice(0, 8)}`}
                  </option>)}
                </select></label>}
              {cellState.loading && <p className="mt-muted" role="status">Consultando células…</p>}
              {cellState.error && <p className="mt-muted" role="alert">{cellState.error}</p>}
              {cellState.catalog && !cellState.catalog.items.length && <p className="mt-pending-note">{cellState.catalog.available
                ? 'Pendiente: este TRAIN no tiene recorridos de células guardados. Calcúlalos en «Recorrido de una célula» de Arquitectura del modelo.'
                : `Sin evidencia: ${cellState.catalog.reason ?? 'el recorrido por capas no está disponible para este modelo.'}`}</p>}
              {cell && (cellState.comparison
                ? <GeneratedXAIComparison key={cellState.comparison.id} comparison={cellState.comparison} datasource={datasource} variant="toolbar" lazy image={cell.image} expandSignal={expandSignal} />
                : <div className="ds-report xai-viewer" data-surface="workbench" data-variant="toolbar"><div className="xai-toolbar">
                    <CellOutcome comparison={{ id: cell.sampleId, trainingRunId: run, sampleId: cell.sampleId, methods: {},
                      sampleRecord: cell.label != null ? { label: cell.label } : undefined,
                      outcome: cell.label != null && cell.predicted != null && cell.threshold != null ? { label: cell.label, predicted: cell.predicted, score: cell.score, threshold: cell.threshold, split: cell.split, attemptId: cell.attemptId } : undefined }} />
                  </div></div>)}
              {cell && <p className="mt-cell-meta">Clase real {classText(cell.label)} · {cell.split.toUpperCase()} · <code title={cell.sampleId}>{cell.sampleId.slice(0, 8)}</code>{cellState.contextError ? <> · «Vista ampliada» no disponible: {cellState.contextError}</> : cellState.comparison ? ' · haz clic en la imagen para la vista ampliada' : ''}</p>}
            </div>
          </div>
        </section>

        {view !== 'flujo' && <section className="mt-wide">
          <TrainingHistoryCard view={view} tabs={tabs} curve={history.curve} trajectories={history.trajectories}
            selectedEpoch={data?.checkpoint.selected_epoch ?? null} requestedSample={search.get('muestra')} phases={data?.phases ?? []} />
        </section>}
        {view === 'flujo' && <section className="mt-main">
          <TrainingScene layers={layers} selected={selected} onSelect={select} phaseLabel={phaseLabel} cell={cell} onCellOpen={openCell} tabs={tabs} />

          <aside className="mt-card mt-detail" aria-live="polite">
            <div className="mt-card-h"><h2>Bloque seleccionado</h2><span className="mt-hint">{selected + 1} / {layers.length}</span></div>
            <div className="mt-d-body">
              <div className="mt-d-title"><i style={{ background: `rgb(${layer.color})` }} /><h3>{layer.label}</h3><span className="mt-kind">{kindLabel(layer.kind)}</span></div>
              <div className="mt-d-desc">{layer.description}{layer.origin !== 'recorded' && <> · <em>{layer.origin === 'reference' ? 'estructura de referencia' : 'derivado'}</em></>}</div>
              <div className="mt-flow">
                <div className="mt-flow-in"><div className="mt-lab">ENTRADA</div><div className="mt-val">{layer.inputText}</div></div>
                <div className="mt-arrow">→</div>
                <div className="mt-flow-out"><div className="mt-lab">SALIDA</div><div className="mt-val">{layer.outputText}</div></div>
              </div>
              <div className="mt-facts">
                <div className="mt-fact"><div className="mt-k">Activaciones (h·w·d)</div><div className="mt-v">{formatCount(layer.volume)}<small>{layer.volume != null ? `${(100 * layer.volume / maxVol).toFixed(1)} % del máx.` : ''}</small></div></div>
                <div className="mt-fact"><div className="mt-k">Parámetros</div><div className="mt-v">{formatCount(layer.parameters)}<small>{layer.parameters != null && data?.total_parameters ? `${(100 * layer.parameters / data.total_parameters).toFixed(1)} % del total` : ''}</small></div></div>
                <div className="mt-fact"><div className="mt-k">Factor espacial · canales</div><div className="mt-v">{factor(layer.spatialFactor, '↓', '↑')}<small>{factor(layer.channelFactor, '↑', '↓')} canales</small></div></div>
                <div className="mt-fact"><div className="mt-k">En {phaseLabel}</div><div className="mt-v">{stateText(layer)}<small>{layer.innerLayers} capas internas</small></div></div>
              </div>
              {checks.some(check => check.layer === selected) && <div><div className="mt-sec-t">Observaciones</div>
                <div className="mt-flags">{checks.filter(check => check.layer === selected).map((check, i) => <div key={i} className="mt-flag" data-level={check.level}><span className="mt-ic">{CHECK_ICON[check.level]}</span><div>{rich(check.text)}</div></div>)}</div></div>}
              <div>
                <div className="mt-sec-t">Parámetros del TRAIN que gobiernan este bloque</div>
                <dl className="mt-params">{parametersFor(layer, layers, parameters, regime).map(item => <Fragment key={item.key}><dt><code>{item.key}</code> {item.label}</dt>
                  <dd data-pending={item.value == null}>{item.value ?? 'Pendiente'}</dd></Fragment>)}</dl>
              </div>
              <div>
                <div className="mt-sec-t">Qué ajustar en un nuevo entrenamiento</div>
                <ul className="mt-tune">{tuningGuide(layer, layers, regime).map((line, i) => <li key={i}>{rich(line)}</li>)}</ul>
                <div className="mt-note">Guía orientativa por tipo de bloque; los valores vienen del TRAIN.</div>
              </div>
            </div>
          </aside>
        </section>}

        <section className="mt-lower">
          <div className="mt-card">
            <div className="mt-card-h"><h2>Tabla de bloques</h2><span className="mt-hint">Vista tabular equivalente al diagrama</span></div>
            <div className="mt-table-wrap"><table className="mt-table">
              <thead><tr><th>#</th><th>Bloque</th><th>Operación</th><th>Entrada</th><th>Salida</th><th>Resolución (h)</th><th>Canales (d)</th><th>Activaciones (log)</th><th>Parámetros</th><th>{phaseLabel}</th></tr></thead>
              <tbody>{layers.map(item => <tr key={item.id} className={item.index === selected ? 'sel' : undefined} onClick={() => select(item.index)}>
                <td className="mt-mono mt-muted">{String(item.index).padStart(2, '0')}</td>
                <td><span className="mt-sw" style={{ background: `rgb(${item.color})` }} />{item.label}</td>
                <td className="mt-muted">{item.description}</td>
                <td className="mt-mono mt-muted">{item.index ? item.inputText : '—'}</td>
                <td className="mt-mono">{item.outputText}</td>
                <td><Bar pct={item.h != null ? 100 * item.h / maxH : null} tone="hw" label={item.h != null ? String(item.h) : 'Pend.'} /></td>
                <td><Bar pct={item.d != null ? 100 * item.d / maxD : null} tone="d" label={item.d != null ? formatCount(item.d) : 'Pend.'} /></td>
                <td><Bar pct={item.volume != null ? 100 * Math.log10(Math.max(item.volume, 1)) / Math.log10(Math.max(maxVol, 10)) : null} tone="vol" label={item.volume != null ? formatCount(item.volume) : 'Pend.'} /></td>
                <td><Bar pct={item.parameters != null ? 100 * item.parameters / maxParams : null} tone="par" label={item.parameters != null ? formatCount(item.parameters) : 'Pend.'} /></td>
                <td><span className="mt-chip" data-trained={item.trainable}>{stateText(item)}</span></td>
              </tr>)}</tbody>
            </table></div>
          </div>
          <div className="mt-side">
            <div className="mt-card">
              <div className="mt-card-h"><h2>Chequeos de coherencia</h2><span className="mt-hint">calculados desde el TRAIN</span></div>
              <div className="mt-checks">
                {checks.length === 0 && <p className="mt-muted">Sin chequeos aplicables con los datos registrados.</p>}
                {checks.map((check, i) => <button key={i} type="button" className="mt-flag" data-level={check.level} disabled={check.layer == null}
                  onClick={() => check.layer != null && select(check.layer)}><span className="mt-ic">{CHECK_ICON[check.level]}</span><div>{rich(check.text)}</div></button>)}
              </div>
            </div>
            <div className="mt-card">
              <div className="mt-card-h"><h2>Configuración del entrenamiento</h2><span className="mt-hint">{runError ? 'no disponible' : record ? 'registrada en el TRAIN' : 'cargando…'}</span></div>
              <div className="mt-config">{groups.map(group => <div key={group}><div className="mt-sec-t">{PARAMETER_GROUP_LABELS[group]}</div>
                {!regime.trained && group !== 'entrada' && group !== 'decision' ? <p className="mt-muted mt-na">No aplica: modelo zero-shot, sin entrenamiento.</p>
                  : group === 'ajuste' && !regime.fineTuning ? <p className="mt-muted mt-na">No aplica: este TRAIN no tuvo fase de ajuste fino{regime.pretrained ? '' : '; es un solo entrenamiento desde cero'}.</p> :
                <dl className="mt-params">{parameters.filter(item => item.group === group).map(item => <Fragment key={item.key}><dt><code>{item.key}</code> {item.label}</dt>
                  <dd data-pending={item.value == null}>{item.value ?? 'Pendiente'}</dd></Fragment>)}</dl>}</div>)}</div>
            </div>
            {pending.length > 0 && <div className="mt-card">
              <div className="mt-card-h"><h2>Datos pendientes</h2><span className="mt-hint">se mostrarán cuando el TRAIN los registre</span></div>
              <ul className="mt-pending">{pending.map(item => <li key={item}>{item}</li>)}</ul>
            </div>}
          </div>
        </section>
      </>}

      <footer className="mt-footer">
        <span>Fuente: <code>GET /runs/{'{id}'}/architecture</code>, <code>GET /runs/{'{id}'}</code>, curvas del reporte científico y <code>GET /runs/{'{id}'}/training-trajectories</code>. Entrada = salida del bloque previo; activaciones = h·w·d.</span>
        <span>TRAIN {run}{data?.checkpoint.selected_epoch != null ? ` · checkpoint época ${data.checkpoint.selected_epoch}` : ''}</span>
      </footer>
    </div>
  </main>;
}
