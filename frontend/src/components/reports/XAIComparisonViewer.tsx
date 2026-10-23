import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { useScientificArtifact, type XAIImageResource } from '../../hooks/useScientificArtifact';
import { XAI_LABELS, XAI_METHODS, type XAIComparison, type XAIEvidence, type XAIMethod } from './xai/comparison';
import { XAIOverlayView } from './XAIOverlayView';
import '../../styles/ds-primitives.css';
import '../../styles/report-components.css';

export interface XAIGenerationAction {
  authorized: boolean;
  reason?: string;
  execute: (comparison: XAIComparison, method: XAIMethod) => Promise<void>;
}
type Resources = Record<XAIMethod | 'original', XAIImageResource>;
const record = (value: unknown): Record<string, unknown> | undefined => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : undefined;
const classLabel = (value: unknown) => value === 1 || value === '1' ? 'Parasitada (1)' : value === 0 || value === '0' ? 'No parasitada (0)' : 'No registrada';
const identityOf = (entry?: XAIEvidence) => record(record(entry?.metadata)?.identity);
// The identity repeats the whole population (thousands of samples) for every method; only its size is informative here.
export function compactMetadata(metadata: XAIEvidence['metadata']) {
  const identity = record(record(metadata)?.identity);
  if (!identity || !Array.isArray(identity.samples)) return metadata;
  return { ...record(metadata), identity: { ...identity, samples: `${identity.samples.length} muestras en la identidad (lista omitida)` } };
}
function downloadJson(name: string, value: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
// Only the inputs that change the attribution map, in words; identifiers and hashes stay in Identificadores.
export function methodSettings(entry: XAIEvidence): string[] {
  const explanation = record(identityOf(entry)?.explanation) ?? {};
  // const lines = [`Clase explicada: ${classLabel(explanation.class)}${explanation.class === 1 ? ': resalta lo que aumenta la probabilidad de parásito.' : '.'}`];
  const lines: string[] = [];
  if (entry.method === 'gradcam') lines.push(`Capa: ${typeof explanation.layer === 'string' && explanation.layer ? explanation.layer : 'última capa convolucional (por defecto)'}.`);
  if (explanation.score_explained) lines.push(`Puntaje explicado: ${explanation.score_explained === 'raw' ? 'salida del modelo sin calibrar (sigmoide)' : String(explanation.score_explained)}.`);
  if (explanation.num_samples != null) lines.push(`Perturbaciones: ${Number(explanation.num_samples).toLocaleString('es-CL')} muestras.`);
  if (entry.method === 'shap') lines.push(`Referencia (background): ${entry.referenceSampleIds?.join(', ') || 'No registrada'}, distinta de la célula explicada.`);
  const seed = identityOf(entry)?.seed;
  if (entry.method !== 'gradcam' && seed != null) lines.push(`Semilla: ${String(seed)}.`);
  if (explanation.version) lines.push(`Versión del método: ${String(explanation.version)}.`);
  return lines;
}
const methodPurpose: Record<XAIMethod, string> = {
  gradcam: 'Grad-CAM pondera los mapas de activación de una capa convolucional por el gradiente de la clase explicada.',
  lime: 'LIME perturba superpíxeles de la célula y ajusta un modelo lineal local.',
  shap: 'SHAP reparte la predicción entre regiones comparándola con una imagen de referencia.',
};
function CellTrace({ comparison }: { comparison: XAIComparison }) {
  const generated = XAI_METHODS.flatMap(method => comparison.methods[method] ? [comparison.methods[method]!] : []);
  // Any method's identity carries the cell record; single-cell and population attempts share the same fields.
  const samplesOf = (entry: XAIEvidence) => { const value = identityOf(entry)?.samples; return Array.isArray(value) ? value as Record<string, unknown>[] : []; };
  const source = generated.find(entry => samplesOf(entry).some(item => item.sample_id === comparison.sampleId)) ?? generated[0];
  const identity = identityOf(source);
  const listed = source ? samplesOf(source).find(item => item.sample_id === comparison.sampleId) : undefined;
  const sample = { relative_path: comparison.sampleRecord?.relativePath ?? listed?.relative_path, label: comparison.sampleRecord?.label ?? listed?.label };
  const model = record(identity?.model);
  const input = record(model?.input_contract);
  const external = record(input?.external);
  const epoch = record(model?.source)?.epoch;
  const shape = Array.isArray(input?.shape) ? input!.shape.slice(1, 3).join('×') : null;
  return <details className="ds-accordion xai-trace"><summary>Trazabilidad de la célula</summary>
    <dl className="xai-trace-facts">
      <div><dt>Célula original</dt><dd><code>{String(sample?.relative_path ?? 'Ruta no registrada')}</code><small>Ruta relativa en la versión del dataset: partición / clase / archivo.</small></dd></div>
      <div><dt>Clase real</dt><dd>{classLabel(sample?.label)}</dd></div>
      <div><dt>Modelo</dt><dd>{String(input?.architecture ?? 'Arquitectura no registrada')} · checkpoint de la época {epoch != null ? String(epoch) : 'sin registro'}</dd></div>
      <div><dt>Entrada del modelo</dt><dd>{shape ? `${shape} px` : 'Tamaño no registrado'} · {String(input?.source_order ?? 'RGB')}{external?.output_order && external.output_order !== input?.source_order ? `→${String(external.output_order)}` : ''} · preprocesamiento {String(external?.mode ?? 'no registrado')}</dd></div>
    </dl>
    {generated.map(entry => <section key={entry.method} className="xai-trace-method"><h4 className="ds-subsection-title">{XAI_LABELS[entry.method]}</h4>
      <p className="scc-meta">{methodPurpose[entry.method as XAIMethod]}</p>
      <ul>{methodSettings(entry).map(line => <li key={line}>{line}</li>)}</ul>
      <button type="button" className="ds-button" data-size="compact" onClick={() => downloadJson(`${entry.method}-${comparison.sampleId ?? 'muestra'}.json`, { artifact: entry.artifact, metadata: entry.metadata })}>Descargar JSON completo</button>
    </section>)}
    <details className="xai-trace-raw"><summary>Identificadores</summary><dl className="ds-dl">
      <div><dt>Muestra</dt><dd><code className="report-identifier">{comparison.sampleId ?? 'No identificada'}</code></dd></div>
      <div><dt>TRAIN · versión de modelo · checkpoint</dt><dd><code className="report-identifier">{comparison.trainingRunId}</code> · <code className="report-identifier">{comparison.modelVersionId ?? 'No registrada'}</code> · <code className="report-identifier">{comparison.checkpointArtifactId ?? 'No registrado'}</code></dd></div>
      <div><dt>Dataset · partición · propósito</dt><dd><code className="report-identifier">{comparison.datasetVersionId ?? 'No registrado'}</code> · {comparison.split ?? '—'} · {comparison.purpose ?? '—'}</dd></div>
      {generated.map(entry => <div key={entry.method}><dt>{XAI_LABELS[entry.method]}</dt><dd>Intento <code className="report-identifier" title={entry.attemptId}>{entry.attemptId ?? 'No registrado'}</code> · identidad <code className="report-identifier">{entry.assessmentIdentityId ?? 'No registrada'}</code> · artefacto <code className="report-identifier">{entry.artifact?.artifactId ?? 'No registrado'}</code>{entry.artifact?.sha256 && <> · SHA-256 <code className="report-identifier">{entry.artifact.sha256}</code></>}{entry.attemptId === comparison.original?.attemptId && <small> · la célula original proviene del mismo intento</small>}</dd></div>)}
    </dl></details>
  </details>;
}
const availabilityLabels = {
  available: 'Disponible', no_evidence: 'Sin evidencia', missing: 'Archivo no disponible',
  denied: 'Acceso denegado', integrity_failed: 'Integridad fallida', not_comparable: 'No comparable', error: 'Error de recuperación'
};

function EvidencePanel({ evidence, method, resource, sample, onExpand, generation }: {
  evidence?: XAIEvidence; method: XAIMethod | 'original'; resource: XAIImageResource; sample: XAIComparison;
  onExpand?: (method: XAIMethod | 'original') => void; generation?: XAIGenerationAction;
}) {
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [decodeError, setDecodeError] = useState<string | null>(null);
  const failedDecode = Boolean(resource.url && decodeError === resource.url);
  const availability = resource.failure?.availability ?? (resource.error ? 'error' : evidence?.availability ?? 'no_evidence');
  const state = resource.loading ? 'Cargando imagen…' : failedDecode ? 'Imagen no decodificable' : resource.url ? 'Disponible'
    : availability !== 'no_evidence' && availability !== 'available' ? availabilityLabels[availability]
      : evidence?.execution === 'running' ? 'Ejecutándose' : evidence?.execution === 'pending' ? 'Pendiente'
        : evidence?.execution === 'failed' ? 'Fallido' : availability === 'available' ? 'Imagen pendiente de carga' : 'Sin evidencia';
  const error = resource.error || failedDecode || evidence?.execution === 'failed' || ['missing', 'denied', 'integrity_failed', 'error', 'not_comparable'].includes(availability);
  const image = resource.url && !failedDecode ? <img className="report-scientific-image" src={resource.url}
    alt={`${XAI_LABELS[method]} · muestra ${sample.sampleId ?? 'no identificada'}`} onError={() => setDecodeError(resource.url)} /> : null;
  // A visible image is its own status; only loading, running, pending and failures need words.
  const notice = !image && (resource.loading || evidence?.artifact || evidence?.originalSource || evidence?.execution === 'running' || evidence?.execution === 'pending' || error) ? state : null;
  return <section className="xai-panel" aria-label={XAI_LABELS[method]} data-state={image ? 'available' : notice ? (error ? 'error' : 'busy') : 'empty'}>
    <h4 className="ds-subsection-title">{XAI_LABELS[method]}</h4>
    <div className="xai-image-frame">
      {image ? onExpand ? <button className="xai-image-button" type="button" onClick={() => onExpand(method)} aria-label={`Ampliar ${XAI_LABELS[method]}`}>{image}</button> : image
        : notice ? <p role={error ? 'alert' : 'status'}>{notice}</p> : <span className="xai-sr-only">{method === 'original' ? 'Sin imagen original trazable' : 'No generada'}</span>}
    </div>
    <div className="xai-panel-status">
      {notice && !image && error && <span className="ds-status" data-tone="rejected">{notice}</span>}
      {resource.failure?.message && <p>{resource.failure.message}</p>}
      {evidence?.message && error && <p>{evidence.message}</p>}
      {!evidence && method === 'original' && <p>No hay una imagen original autorizada y trazable registrada.</p>}
      {resource.url && <a className="ds-button" href={resource.url} download={`${evidence?.originalSource?.sampleId ?? evidence?.artifact?.artifactId}${resource.extension}`}>Descargar {XAI_LABELS[method]}</a>}
      {!evidence?.artifact && method !== 'original' && <button className="ds-button" type="button" disabled={!generation?.authorized || generating}
        title={generation?.authorized ? undefined : generation?.reason ?? 'La generación todavía no está disponible.'} onClick={async () => {
          if (!generation?.authorized) return;
          setGenerating(true); setGenerationError(null);
          try { await generation.execute(sample, method); }
          catch (error: unknown) { setGenerationError(error instanceof Error ? error.message : 'No fue posible solicitar la generación.'); }
          finally { setGenerating(false); }
        }}>Generar {XAI_LABELS[method]}</button>}
      {generationError && <p role="alert">{generationError}</p>}
    </div>
  </section>;
}

const outcomeCategory = (label: number, predicted: number) =>
  label === 1 ? (predicted === 1 ? 'Verdadero positivo' : 'Falso negativo') : (predicted === 1 ? 'Falso positivo' : 'Verdadero negativo');
const decimal = (value: number) => value.toLocaleString('es-CL', { maximumFractionDigits: 4 });
/** Real class, the model's category for this cell and its score against the decision threshold. */
export function CellOutcome({ comparison }: { comparison: XAIComparison }) {
  const outcome = comparison.outcome;
  const label = outcome?.label ?? comparison.sampleRecord?.label;
  if (label == null && !outcome) return null;
  return <dl className="xai-outcome" aria-label="Resultado del modelo en esta célula">
    <div><dt>Clase real</dt><dd>{label === 1 ? 'Parasitada' : label === 0 ? 'No parasitada' : 'No registrada'}</dd></div>
    {outcome && <div data-correct={outcome.label === outcome.predicted}><dt>Categoría</dt><dd>{outcomeCategory(outcome.label, outcome.predicted)}</dd></div>}
    {outcome && <div><dt>Score</dt><dd title={`EVALUATE ${outcome.split.toUpperCase()} · intento ${outcome.attemptId}`}>{decimal(outcome.score)} <small>umbral {decimal(outcome.threshold)}</small></dd></div>}
  </dl>;
}

/** Pure shared presentation: neither modal nor inline starts a second image request. */
export function XAIComparisonContent({ comparison, resources, onExpand, generation, actions, density = 'compact' }: {
  density?: 'compact' | 'expanded'; actions?: ReactNode;
  comparison: XAIComparison; resources: Resources; onExpand?: (method: XAIMethod | 'original') => void;
  generation?: Partial<Record<XAIMethod, XAIGenerationAction>>;
}) {
  return <div className="xai-content" data-density={density}>
    {(onExpand || actions) && <div className="xai-toolbar">{onExpand && <button className="ds-button xai-expand" type="button" onClick={() => onExpand('original')}>Ampliar comparación</button>}<CellOutcome comparison={comparison} />{actions}</div>}
    {comparison.comparabilityIssue && <p className="ds-callout" data-tone="warning">No comparable: {comparison.comparabilityIssue}</p>}
    <div className="xai-scroll" tabIndex={0} role="region" aria-label="Comparación de cuatro cuadros: original, Grad-CAM, LIME y SHAP">
      <div className="xai-grid">
        {(['original', ...XAI_METHODS] as const).map(method => <EvidencePanel key={method} method={method} sample={comparison}
          evidence={method === 'original' ? comparison.original : comparison.methods[method]} resource={resources[method]}
          onExpand={onExpand} generation={method === 'original' ? undefined : generation?.[method]} />)}
      </div>
    </div>
    <CellTrace comparison={comparison} />
  </div>;
}

/** Expanded view body (Comparación / Superposición); the viewer's own modal and hosts with their own modal share it. */
function XAIExpandedView({ comparison, resources, datasource, generation, actions, onView }: {
  comparison: XAIComparison; resources: Resources; datasource: string; generation?: Partial<Record<XAIMethod, XAIGenerationAction>>; actions?: ReactNode;
  onView?: (view: 'comparison' | 'overlay') => void;
}) {
  // Alternative expanded view: layers over the original cell. Candidate main view pending specialist review.
  const [view, setView] = useState<'comparison' | 'overlay'>('comparison');
  useEffect(() => onView?.(view), [view, onView]);
  return <>
    <div className="xai-modal-bar">
      <div role="tablist" aria-label="Tipo de vista" className="xai-view-tabs">
        {(['comparison', 'overlay'] as const).map(item => <button key={item} type="button" role="tab" className="ds-button" aria-selected={view === item}
          onClick={() => setView(item)}>{item === 'comparison' ? 'Comparación' : 'Superposición'}</button>)}
      </div>
      <CellOutcome comparison={comparison} />
      {actions}
    </div>
    {view === 'overlay'
      ? <XAIOverlayView comparison={comparison} resources={resources} datasource={datasource} generation={generation} />
      : <XAIComparisonContent comparison={comparison} resources={resources} density="expanded" generation={generation} />}
  </>;
}

/** variant="expanded" renders only the expanded view, for a host that already is a modal (Errores y consenso). */
export function XAIComparisonViewer({ comparison, datasource, generation, actions, variant = 'inline' }: {
  comparison: XAIComparison; datasource: string; generation?: Partial<Record<XAIMethod, XAIGenerationAction>>; actions?: ReactNode;
  variant?: 'inline' | 'expanded';
}) {
  const host = useRef<HTMLElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);
  const [expanded, setExpanded] = useState<XAIMethod | 'original' | null>(null);
  const [overlay, setOverlay] = useState(false);
  const titleId = useId();
  useEffect(() => {
    if (!host.current) return;
    if (typeof IntersectionObserver === 'undefined') { setVisible(true); return; }
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { setVisible(true); observer.disconnect(); }
    });
    observer.observe(host.current);
    return () => observer.disconnect();
  }, []);
  // Opening the expanded view also loads the images, even if the row never scrolled into view.
  const load = visible || expanded !== null || variant === 'expanded';
  const resources: Resources = {
    original: useScientificArtifact(comparison.original?.originalSource ?? comparison.original?.artifact, datasource, load),
    gradcam: useScientificArtifact(comparison.methods.gradcam?.artifact, datasource, load),
    lime: useScientificArtifact(comparison.methods.lime?.artifact, datasource, load),
    shap: useScientificArtifact(comparison.methods.shap?.artifact, datasource, load),
  };
  useEffect(() => {
    if (expanded !== null) dialog.current?.showModal();
  }, [expanded]);
  if (variant === 'expanded') return <section ref={host} className="ds-report xai-viewer" data-surface="workbench">
    <XAIExpandedView comparison={comparison} resources={resources} datasource={datasource} generation={generation} actions={actions} />
  </section>;
  return <section ref={host} className="ds-report xai-viewer" data-surface="workbench">
    <div className="report-section"><XAIComparisonContent comparison={comparison} resources={resources} generation={generation} actions={actions} onExpand={method => {
      trigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      setExpanded(method);
    }} /></div>
    <dialog ref={dialog} className="report-viewer xai-modal" aria-labelledby={titleId} onClose={() => { setExpanded(null); trigger.current?.focus(); }}>
      <form method="dialog" className="xai-modal-close"><button type="submit" className="ds-button" aria-label="Cerrar vista ampliada" title="Cerrar" autoFocus>
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
      </button></form>
      <h2 id={titleId}>{overlay ? 'Vista ampliada · Superposición' : expanded ? `Vista ampliada · ${XAI_LABELS[expanded]}` : 'Comparación XAI'}</h2>
      {expanded !== null && <XAIExpandedView comparison={comparison} resources={resources} datasource={datasource} generation={generation} onView={view => setOverlay(view === 'overlay')} />}
    </dialog>
  </section>;
}
