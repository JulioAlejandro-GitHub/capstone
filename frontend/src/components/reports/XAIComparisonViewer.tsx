import { useEffect, useId, useRef, useState } from 'react';
import { useScientificArtifact, type XAIImageResource } from '../../hooks/useScientificArtifact';
import { XAI_LABELS, XAI_METHODS, type XAIComparison, type XAIEvidence, type XAIMethod } from './xai/comparison';
import '../../styles/ds-primitives.css';
import '../../styles/report-components.css';

export interface XAIGenerationAction {
  authorized: boolean;
  execute: (comparison: XAIComparison, method: XAIMethod) => Promise<void>;
}
type Resources = Record<XAIMethod | 'original', XAIImageResource>;
const availabilityLabels = { available: 'Disponible', no_evidence: 'Sin evidencia', missing: 'Archivo no disponible',
  denied: 'Acceso denegado', integrity_failed: 'Integridad fallida', not_comparable: 'No comparable', error: 'Error de recuperación' };

function EvidencePanel({evidence, method, resource, sample, onExpand, generation}: {
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
  return <section className="xai-panel" aria-label={XAI_LABELS[method]}>
    <h4 className="ds-subsection-title">{XAI_LABELS[method]}</h4>
    <div className="xai-image-frame">
      {image ? onExpand ? <button className="xai-image-button" type="button" onClick={() => onExpand(method)} aria-label={`Ampliar ${XAI_LABELS[method]}`}>{image}</button> : image
        : <p role={error ? 'alert' : 'status'}>{state}</p>}
    </div>
    <div className="xai-panel-status">
      <span className="ds-status" data-tone={error ? 'rejected' : resource.url ? 'approved' : 'neutral'}>{state}</span>
      {evidence && method !== 'original' && <small>Ejecución: {evidence.execution === 'completed' ? 'Completada' : evidence.execution === 'running' ? 'Ejecutándose' : evidence.execution === 'failed' ? 'Fallida' : evidence.execution === 'pending' ? 'Pendiente' : 'No ejecutado'}</small>}
      {resource.failure?.message && <p>{resource.failure.message}</p>}
      {evidence?.message && <p>{evidence.message}</p>}
      {!evidence && <p>{method === 'original' ? 'No hay una imagen original autorizada y trazable registrada.' : 'Sin evidencia en esta selección.'}</p>}
      {resource.url && <a className="ds-button" href={resource.url} download={`${evidence?.originalSource?.sampleId ?? evidence?.artifact?.artifactId}${resource.extension}`}>Descargar {XAI_LABELS[method]}</a>}
      {!evidence?.artifact && method !== 'original' && <button className="ds-button" type="button" disabled={!generation?.authorized || generating} onClick={async () => {
        if (!generation?.authorized) return;
        setGenerating(true); setGenerationError(null);
        try { await generation.execute(sample, method); }
        catch (error: unknown) { setGenerationError(error instanceof Error ? error.message : 'No fue posible solicitar la generación.'); }
        finally { setGenerating(false); }
      }}>Generar {XAI_LABELS[method]}</button>}
      {!evidence?.artifact && method !== 'original' && !generation?.authorized && <small>La generación todavía no está disponible.</small>}
      {generationError && <p role="alert">{generationError}</p>}
    </div>
  </section>;
}

/** Pure shared presentation: neither modal nor inline starts a second image request. */
export function XAIComparisonContent({comparison, resources, onExpand, generation, density = 'compact'}: {
  density?: 'compact' | 'expanded';
  comparison: XAIComparison; resources: Resources; onExpand?: (method: XAIMethod | 'original') => void;
  generation?: Partial<Record<XAIMethod, XAIGenerationAction>>;
}) {
  const scrollHint = useId();
  return <div className="xai-content" data-density={density}>
    {onExpand && <button className="ds-button xai-expand" type="button" onClick={() => onExpand('original')}>Ampliar comparación</button>}
    {comparison.comparabilityIssue && <p className="ds-callout" data-tone="warning">No comparable: {comparison.comparabilityIssue}</p>}
    <div className="xai-scroll" tabIndex={0} role="region" aria-label="Comparación de cuatro cuadros" aria-describedby={scrollHint}>
      <div className="xai-grid">
        {(['original', ...XAI_METHODS] as const).map(method => <EvidencePanel key={method} method={method} sample={comparison}
          evidence={method === 'original' ? comparison.original : comparison.methods[method]} resource={resources[method]}
          onExpand={onExpand} generation={method === 'original' ? undefined : generation?.[method]} />)}
      </div>
    </div>
    <details className="ds-accordion"><summary>Trazabilidad y metadatos (identificadores completos seleccionables)</summary>
      <div className="xai-context">
        <h3 className="ds-subsection-title">Muestra <code className="report-identifier">{comparison.sampleId ?? 'No identificada'}</code></h3>
        <dl className="ds-dl">
          <div><dt>Modelo</dt><dd className="report-identifier">{comparison.modelVersionId ?? 'No registrado'}</dd></div>
          <div><dt>TRAIN</dt><dd className="report-identifier">{comparison.trainingRunId}</dd></div>
          <div><dt>Predicción / Clase real</dt><dd>{comparison.prediction ?? 'No registrada'} / {comparison.trueClass ?? 'No registrada'}</dd></div>
        </dl>
        <p className="report-copy" id={scrollHint}>Original → Grad-CAM → LIME → SHAP. En pantallas estrechas, desplaza horizontalmente la comparación; con teclado, enfoca la fila y usa las flechas.</p>
      </div>
      <dl className="ds-dl">
        <div><dt>Checkpoint</dt><dd className="report-identifier">{comparison.checkpointArtifactId ?? 'No registrado'}</dd></div>
        <div><dt>Dataset / split / propósito</dt><dd className="report-identifier">{comparison.datasetVersionId ?? 'No registrado'} / {comparison.split ?? 'No registrado'} / {comparison.purpose ?? 'No registrado'}</dd></div>
        {([comparison.original, ...XAI_METHODS.map(method => comparison.methods[method])]).filter((entry): entry is XAIEvidence => Boolean(entry)).map(entry => <div key={entry.method}>
          <dt>{XAI_LABELS[entry.method]}</dt><dd>
            <p>Intento: <code className="report-identifier">{entry.attemptId ?? 'No registrado'}</code></p>
            <p>Identidad: <code className="report-identifier">{entry.assessmentIdentityId ?? 'No registrada'}</code></p>
            <p>Artefacto: <code className="report-identifier">{entry.originalSource ? 'No aplica: muestra del dataset gobernado' : entry.artifact?.artifactId ?? 'No registrado'}</code></p>
            {entry.method === 'shap' && <p>Referencia SHAP (background, distinta de la muestra explicada): <code className="report-identifier">{entry.referenceSampleIds?.join(', ') || 'No registrada'}</code></p>}
            <pre className="report-identifier xai-metadata">{JSON.stringify({artifact: entry.artifact, originalSource: entry.originalSource, metadata: entry.metadata}, null, 2)}</pre>
          </dd>
        </div>)}
      </dl>
    </details>
  </div>;
}

export function XAIComparisonViewer({comparison, datasource, generation}: {
  comparison: XAIComparison; datasource: string; generation?: Partial<Record<XAIMethod, XAIGenerationAction>>;
}) {
  const host = useRef<HTMLElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);
  const [expanded, setExpanded] = useState<XAIMethod | 'original' | null>(null);
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
  const resources: Resources = {
    original: useScientificArtifact(comparison.original?.originalSource ?? comparison.original?.artifact, datasource, visible),
    gradcam: useScientificArtifact(comparison.methods.gradcam?.artifact, datasource, visible),
    lime: useScientificArtifact(comparison.methods.lime?.artifact, datasource, visible),
    shap: useScientificArtifact(comparison.methods.shap?.artifact, datasource, visible),
  };
  useEffect(() => {
    if (expanded !== null) dialog.current?.showModal();
  }, [expanded]);
  return <section ref={host} className="ds-report xai-viewer" data-surface="workbench">
    <div className="report-section"><XAIComparisonContent comparison={comparison} resources={resources} generation={generation} onExpand={method => {
      trigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      setExpanded(method);
    }} /></div>
    <dialog ref={dialog} className="report-viewer xai-modal" aria-labelledby={titleId} onClose={() => { setExpanded(null); trigger.current?.focus(); }}>
      <h2 id={titleId}>{expanded ? `Vista ampliada · ${XAI_LABELS[expanded]}` : 'Comparación XAI'}</h2>
      <form method="dialog"><button className="ds-button" autoFocus>Cerrar comparación</button></form>
      {expanded !== null && <XAIComparisonContent comparison={comparison} resources={resources} density="expanded" />}
    </dialog>
  </section>;
}
