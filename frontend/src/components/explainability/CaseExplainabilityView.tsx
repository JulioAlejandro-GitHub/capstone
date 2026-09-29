import { useCallback, useEffect, useState } from 'react';

import { api } from '../../services/api';
import type { CellCropSummary } from '../../types/cellReview';
import type { CellExplanation } from '../../types/cellClassification';
import { AuthenticatedCropImage, useAuthenticatedObjectUrl } from '../cell-review/AuthenticatedCellImage';

export type ExplainabilityStatus = 'not_requested' | 'generating' | 'generated' | 'artifact_missing' | 'failed' | 'unsupported';

export type ExplainabilityMedia =
  | { kind: 'url'; url: string | null; path?: string | null; alt: string }
  | { kind: 'cell_crop'; crop: CellCropSummary | null; alt: string }
  | { kind: 'cell_explanation'; explanation: CellExplanation; variant: 'heatmap' | 'overlay'; alt: string };

export type ExplainabilityMethodPanel = {
  status: ExplainabilityStatus;
  media: ExplainabilityMedia[];
  createdAt: string | null;
  error: string | null;
};

export type ExplainabilityCaseViewModel = {
  sourceContext: 'model_execution' | 'smear_analysis';
  caseCode: string;
  comparison?: { lime: ExplainabilityMethodPanel; shap: ExplainabilityMethodPanel };
  input: {
    media: ExplainabilityMedia;
    displayCode: string;
    id: string | null;
    checksum: string | null;
    facts?: Array<{ label: string; value: string | number | null }>;
  };
  prediction: {
    id: string | null;
    predictedLabel: string | null;
    probabilityParasitized: string;
    probabilityUninfected: string;
    threshold: string;
    thresholdSource: string | null;
    margin: string;
    nearThreshold: string;
    modelName: string | null;
    modelVersion: string | null;
    facts?: Array<{ label: string; value: string | number | null }>;
  };
  explanation: {
    status: ExplainabilityStatus;
    method: string;
    methodVersion: string | null;
    lastConvLayer: string | null;
    media: ExplainabilityMedia[];
    parameters: unknown;
    createdAt: string | null;
    error: string | null;
    otherMethods?: string[];
  };
  associatedRunId?: string | null;
};

function CellExplanationImage({ media, onUnavailable }: { media: Extract<ExplainabilityMedia, { kind: 'cell_explanation' }>; onUnavailable?: () => void }) {
  const load = useCallback((signal: AbortSignal) => (
    media.variant === 'heatmap'
      ? api.getCellExplanationHeatmapBlob(media.explanation.id, signal)
      : api.getCellExplanationOverlayBlob(media.explanation.id, signal)
  ), [media.explanation.id, media.variant]);
  const image = useAuthenticatedObjectUrl(load, true, `${media.explanation.id}:${media.variant}`);
  useEffect(() => { if (image.error) onUnavailable?.(); }, [image.error, onUnavailable]);
  if (image.loading) return <div className="image-placeholder">Cargando artefacto autenticado…</div>;
  if (!image.url || image.error) return <div className="image-placeholder">Artefacto no disponible.</div>;
  return <img src={image.url} alt={media.alt} loading="lazy" decoding="async" />;
}

function CaseMedia({ media, onUnavailable }: { media: ExplainabilityMedia; onUnavailable?: () => void }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [media]);
  if (media.kind === 'cell_crop') return <AuthenticatedCropImage crop={media.crop} alt={media.alt} eager />;
  if (media.kind === 'cell_explanation') return <CellExplanationImage media={media} onUnavailable={onUnavailable} />;
  if (!media.url || failed) return <div className="image-placeholder">Imagen no disponible.</div>;
  return <img src={media.url} alt={media.alt} loading="lazy" decoding="async" onError={() => { setFailed(true); onUnavailable?.(); }} />;
}

function Fact({ label, value }: { label: string; value: string | number | null | undefined }) {
  return <span>{label}<strong>{value === null || value === undefined || value === '' ? '—' : value}</strong></span>;
}

const PENDING_CONTROL_TITLE = 'Control pendiente de implementación.';

function gradCamPlaceholder(status: ExplainabilityStatus) {
  return status === 'unsupported'
    ? 'Grad-CAM no está disponible para este modelo.'
    : status === 'artifact_missing'
      ? 'El artefacto Grad-CAM ya no está disponible.'
      : status === 'failed'
        ? 'No fue posible generar Grad-CAM para este caso.'
        : status === 'generating'
          ? 'Generando explicación…'
          : 'La explicación visual Grad-CAM no está generada.';
}

function limeShapPlaceholder(status: ExplainabilityStatus, methodLabel: 'LIME' | 'SHAP') {
  return status === 'unsupported'
    ? `${methodLabel} no está disponible para este contexto.`
    : status === 'artifact_missing'
      ? `El artefacto ${methodLabel} ya no está disponible.`
      : status === 'failed'
        ? `No fue posible generar ${methodLabel} para este caso.`
        : status === 'generating'
          ? 'Generando explicación…'
          : `La explicación visual ${methodLabel} no está generada.`;
}

function MethodPanelImages({ status, media, onUnavailable, methodLabel }: { status: ExplainabilityStatus; media: ExplainabilityMedia[]; onUnavailable?: () => void; methodLabel: 'Grad-CAM' | 'LIME' | 'SHAP' }) {
  if (status !== 'artifact_missing' && media.length) {
    return <>{media.map((item, index) => <div className="audit-detail-image" key={`${item.kind}-${index}`}><CaseMedia media={item} onUnavailable={onUnavailable} /></div>)}</>;
  }
  const placeholder = methodLabel === 'Grad-CAM' ? gradCamPlaceholder(status) : limeShapPlaceholder(status, methodLabel);
  return <div className="audit-detail-image"><div className="image-placeholder">{placeholder}</div></div>;
}

export function CaseExplainabilityView({
  case: caseView,
  onClose,
  onRunSelect,
  canGenerate = false,
  onGenerate,
}: {
  case: ExplainabilityCaseViewModel;
  onClose: () => void;
  onRunSelect?: (runId: string) => void;
  canGenerate?: boolean;
  onGenerate?: (regenerate: boolean) => Promise<ExplainabilityCaseViewModel>;
}) {
  const [generatedCase, setGeneratedCase] = useState<ExplainabilityCaseViewModel | null>(null);
  const [generationPending, setGenerationPending] = useState(false);
  const [generationError, setGenerationError] = useState('');
  const activeCase = generatedCase ?? caseView;
  const [runtimeArtifactMissing, setRuntimeArtifactMissing] = useState(false);
  const [sidebarTab, setSidebarTab] = useState<'decision' | 'traceability'>('decision');
  useEffect(() => { setGeneratedCase(null); setGenerationError(''); }, [caseView.caseCode, caseView.explanation.createdAt]);
  useEffect(() => setRuntimeArtifactMissing(false), [activeCase.caseCode, activeCase.explanation.status, activeCase.explanation.method, activeCase.explanation.createdAt]);
  const explanationStatus = generationPending ? 'generating' : runtimeArtifactMissing && activeCase.explanation.status === 'generated'
    ? 'artifact_missing'
    : activeCase.explanation.status;
  const generationAllowed = Boolean(canGenerate && onGenerate && ['not_requested', 'artifact_missing', 'failed'].includes(explanationStatus));
  const generationButtonLabel = generationPending
    ? 'Generando…'
    : explanationStatus === 'generated'
      ? 'Grad-CAM generada'
      : explanationStatus === 'unsupported'
        ? 'Grad-CAM no disponible'
        : explanationStatus === 'artifact_missing'
          ? 'Regenerar Grad-CAM'
          : explanationStatus === 'failed'
            ? 'Reintentar Grad-CAM'
            : 'Generar Grad-CAM';
  const generationDisabledReason = !canGenerate
    ? 'No cuenta con permiso para generar explicaciones Grad-CAM.'
    : !onGenerate
      ? 'La generación Grad-CAM no está disponible en este contexto.'
      : explanationStatus === 'generated'
        ? 'La explicación Grad-CAM ya fue generada.'
        : explanationStatus === 'unsupported'
          ? 'El modelo de esta predicción no admite Grad-CAM.'
          : '';
  async function generate() {
    if (!onGenerate || generationPending) return;
    setGenerationPending(true);
    setGenerationError('');
    try {
      setGeneratedCase(await onGenerate(explanationStatus === 'artifact_missing'));
    } catch {
      setGenerationError('No fue posible generar Grad-CAM para este caso.');
    } finally {
      setGenerationPending(false);
    }
  }
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);

  const prediction = activeCase.prediction;
  const explanation = activeCase.explanation;
  const comparison = activeCase.comparison;
  const limePanel = comparison?.lime ?? { status: 'unsupported' as ExplainabilityStatus, media: [], createdAt: null, error: null };
  const shapPanel = comparison?.shap ?? { status: 'unsupported' as ExplainabilityStatus, media: [], createdAt: null, error: null };
  const methodsAvailable = [explanationStatus, limePanel.status, shapPanel.status].filter((status) => status === 'generated').length;
  const probabilityParasitizedValue = Number.parseFloat(prediction.probabilityParasitized);
  const thresholdValue = Number.parseFloat(prediction.threshold);
  const canPlotThreshold = Number.isFinite(probabilityParasitizedValue) && Number.isFinite(thresholdValue);
  const modelVersionShort = prediction.modelVersion ? prediction.modelVersion.slice(0, 8) : null;

  return (
    <div className="audit-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="audit-modal case-explainability-view" role="dialog" aria-modal="true" aria-labelledby="case-explainability-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="audit-modal-header">
          <div><p>Tríada XAI · Auditoría comparativa</p><h2 id="case-explainability-title">Clasificación de {activeCase.caseCode}</h2></div>
          <div className="path-actions">
            <span className="case-badge">Modelo: {prediction.modelName ?? '—'}{modelVersionShort ? ` · v: ${modelVersionShort}` : ''}</span>
            <span className="case-badge">Métodos XAI disponibles: {methodsAvailable}/3</span>
            <button className="modal-close" type="button" onClick={onClose} aria-label="Cerrar auditoría">×</button>
          </div>
        </header>

        <div className="page">
          <div className="run-detail-analysis-grid">
            <section className="panel" aria-label="Visor comparativo Tríada XAI">
              <div className="tabs" role="group" aria-label="Modo de vista">
                <button className="active" type="button" aria-pressed="true">Tríada XAI (4 paneles)</button>
                <button type="button" disabled title={PENDING_CONTROL_TITLE}>Detalle + Cortina</button>
                <button type="button" disabled title={PENDING_CONTROL_TITLE}>Matriz correlación</button>
              </div>
              <div className="path-actions" aria-label="Controles globales del visor (pendientes de implementación)">
                <span className="muted-text">Método: Todos (tríada)</span>
                <button type="button" disabled title={PENDING_CONTROL_TITLE} aria-label="Reducir zoom">−</button>
                <span className="muted-text">1.0x</span>
                <button type="button" disabled title={PENDING_CONTROL_TITLE} aria-label="Aumentar zoom">+</button>
              </div>

              <div className="production-steps">
                <div className="path-actions" aria-label="Controles crop fuente (pendientes de implementación)">
                  <label className="muted-text" title={PENDING_CONTROL_TITLE}><input type="checkbox" disabled aria-label="Isolíneas Grad-CAM" /> Isolíneas Grad-CAM</label>
                </div>
                <div className="path-actions" aria-label="Controles Grad-CAM (pendientes de implementación)">
                  <span className="muted-text">Paleta:</span>
                  <button type="button" disabled title={PENDING_CONTROL_TITLE}>Viridis</button>
                  <button type="button" disabled title={PENDING_CONTROL_TITLE}>Turbo</button>
                  <label className="muted-text" title={PENDING_CONTROL_TITLE}><input type="checkbox" disabled aria-label="Filtro Grad-CAM mayor a 30 por ciento" /> Filtro &gt; 30%</label>
                  <span className="muted-text">Alpha 55%:</span>
                  <input type="range" min={0} max={100} defaultValue={55} disabled aria-label="Alpha Grad-CAM" title={PENDING_CONTROL_TITLE} />
                </div>
                <div className="path-actions" aria-label="Controles LIME (pendientes de implementación)">
                  <span className="muted-text">Superpíxeles K 8:</span>
                  <input type="range" min={2} max={32} defaultValue={8} disabled aria-label="Superpíxeles K LIME" title={PENDING_CONTROL_TITLE} />
                  <label className="muted-text" title={PENDING_CONTROL_TITLE}><input type="checkbox" disabled aria-label="Solo positivos LIME" /> Solo positivos</label>
                  <span className="muted-text">Alpha 55%:</span>
                  <input type="range" min={0} max={100} defaultValue={55} disabled aria-label="Alpha LIME" title={PENDING_CONTROL_TITLE} />
                </div>
                <div className="path-actions" aria-label="Controles SHAP (pendientes de implementación)">
                  <span className="muted-text">Paleta:</span>
                  <button type="button" disabled title={PENDING_CONTROL_TITLE}>Divergente ±</button>
                  <label className="muted-text" title={PENDING_CONTROL_TITLE}><input type="checkbox" disabled aria-label="Filtro SHAP magnitud phi mayor a 30 por ciento" /> Filtro |φ| &gt; 30%</label>
                  <span className="muted-text">Alpha 55%:</span>
                  <input type="range" min={0} max={100} defaultValue={55} disabled aria-label="Alpha SHAP" title={PENDING_CONTROL_TITLE} />
                </div>

                <article className="audit-detail-panel">
                  <div className="audit-panel-heading"><span>01</span><div><strong>Crop fuente</strong><small>Entrada inmutable de inferencia</small></div></div>
                  <div className="audit-detail-image"><CaseMedia media={activeCase.input.media} /></div>
                </article>
                <article className="audit-detail-panel">
                  <div className="audit-panel-heading"><span>02</span><div><strong>Grad-CAM</strong><small>{explanation.lastConvLayer ?? '—'} · {explanationStatus}</small></div></div>
                  <MethodPanelImages status={explanationStatus} media={explanationStatus !== 'artifact_missing' ? explanation.media : []} onUnavailable={() => setRuntimeArtifactMissing(true)} methodLabel="Grad-CAM" />
                </article>
                <article className="audit-detail-panel">
                  <div className="audit-panel-heading"><span>03</span><div><strong>LIME</strong><small>Superpíxeles SLIC</small></div></div>
                  <MethodPanelImages status={limePanel.status} media={limePanel.media} methodLabel="LIME" />
                </article>
                <article className="audit-detail-panel">
                  <div className="audit-panel-heading"><span>04</span><div><strong>SHAP</strong><small>Atribución con signo ±</small></div></div>
                  <MethodPanelImages status={shapPanel.status} media={shapPanel.media} methodLabel="SHAP" />
                </article>
              </div>

              <div className="filter-actions">
                <span>
                  <span className="case-badge">Grad-CAM · {explanationStatus}</span>
                  {!generationAllowed && generationDisabledReason ? <span id="gradcam-action-status" className="detail-secondary"> {generationDisabledReason}</span> : null}
                </span>
                <button
                  className="audit-action-button"
                  type="button"
                  disabled={!generationAllowed || generationPending}
                  title={!generationAllowed ? generationDisabledReason : undefined}
                  aria-describedby={!generationAllowed && generationDisabledReason ? 'gradcam-action-status' : undefined}
                  onClick={() => void generate()}
                >
                  {generationButtonLabel}
                </button>
              </div>
              {generationError ? <p className="detail-error" aria-live="polite">{generationError}</p> : <span aria-live="polite" className="sr-only" />}
            </section>

            <aside className="panel" aria-label="Decisión y trazabilidad">
              <div className="tabs" role="tablist" aria-label="Información del caso">
                <button type="button" role="tab" id="case-tab-decision" aria-controls="case-tabpanel-decision" aria-selected={sidebarTab === 'decision'} className={sidebarTab === 'decision' ? 'active' : undefined} onClick={() => setSidebarTab('decision')}>Decisión clínica</button>
                <button type="button" role="tab" id="case-tab-traceability" aria-controls="case-tabpanel-traceability" aria-selected={sidebarTab === 'traceability'} className={sidebarTab === 'traceability' ? 'active' : undefined} onClick={() => setSidebarTab('traceability')}>Trazabilidad &amp; XAI</button>
              </div>

              {sidebarTab === 'decision' ? (
                <div className="audit-detail-panel prediction-panel" role="tabpanel" id="case-tabpanel-decision" aria-labelledby="case-tab-decision">
                  <div className="section-heading">
                    <span>Predicción · decisión de inferencia</span>
                    <span className={`cell-prediction-label large prediction-${prediction.predictedLabel ?? 'failed'}`}>{prediction.predictedLabel ?? 'predicción fallida'}</span>
                  </div>
                  <div className="metrics-grid">
                    <div className="metric-card"><span>P(uninfected)</span><strong>{prediction.probabilityUninfected}</strong></div>
                    <div className="metric-card"><span>P(parasitized)</span><strong>{prediction.probabilityParasitized}</strong></div>
                  </div>
                  <div className="detail-facts">
                    <Fact label="Threshold calibrado" value={prediction.threshold} />
                    <Fact label="Fuente threshold" value={prediction.thresholdSource} />
                    <Fact label="Margen al umbral" value={prediction.margin} />
                    <Fact label="Próxima al threshold" value={prediction.nearThreshold} />
                  </div>
                  {canPlotThreshold ? (
                    <div className="detail-facts prediction-facts">
                      <span>
                        P(parasitized) respecto al corte calibrado (0.000 sano · {prediction.threshold} corte · 1.000 infectado)
                        <meter min={0} max={1} low={thresholdValue} high={thresholdValue} optimum={0} value={probabilityParasitizedValue} aria-label="P(parasitized) respecto al threshold">{prediction.probabilityParasitized}</meter>
                      </span>
                    </div>
                  ) : null}
                  <div className="section-heading"><span>Métricas de concordancia XAI</span></div>
                  <div className="detail-facts">
                    <Fact label="IoU Grad-CAM vs. LIME" value="—" />
                    <Fact label="Spearman Grad-CAM vs. SHAP" value="—" />
                    <Fact label="Métodos generados" value={`${methodsAvailable}/3`} />
                    <Fact label="Estado LIME" value={limePanel.status} />
                    <Fact label="Estado SHAP" value={shapPanel.status} />
                  </div>
                  <p className="muted-text">El cálculo de concordancia requiere los mapas crudos y no está disponible en esta versión.</p>
                  {prediction.nearThreshold === 'Sí' ? (
                    <div className="clinical-mini-disclaimer"><strong>Caso límite (low-confidence).</strong> Margen de {prediction.margin} respecto al umbral{prediction.thresholdSource ? ` ${prediction.thresholdSource}` : ''}. Se recomienda confirmación por revisión experta.</div>
                  ) : null}
                  <div className="clinical-mini-disclaimer">Resultado experimental de cribado. Requiere revisión experta y no constituye un diagnóstico clínico.</div>
                  <span className="muted-text">Acciones de auditoría médica</span>
                  <div className="path-actions">
                    <button type="button" disabled title={PENDING_CONTROL_TITLE}>Validar</button>
                    <button type="button" disabled title={PENDING_CONTROL_TITLE}>Reclasificar</button>
                    <button type="button" disabled title={PENDING_CONTROL_TITLE}>Exportar reporte Multi-XAI</button>
                  </div>
                  {activeCase.associatedRunId && onRunSelect ? <button className="audit-action-button" type="button" onClick={() => onRunSelect(activeCase.associatedRunId!)}>Abrir run asociado</button> : null}
                </div>
              ) : (
                <div className="audit-detail-panel" role="tabpanel" id="case-tabpanel-traceability" aria-labelledby="case-tab-traceability">
                  <div className="section-heading"><span>Metadatos de inferencia</span></div>
                  <div className="detail-facts">
                    <Fact label="Código" value={activeCase.input.displayCode} />
                    <Fact label="Identificador" value={activeCase.input.id} />
                    <Fact label="Checksum" value={activeCase.input.checksum} />
                    {activeCase.input.facts?.map((fact) => <Fact key={fact.label} {...fact} />)}
                    <Fact label="Modelo" value={prediction.modelName} />
                    <Fact label="Versión" value={prediction.modelVersion} />
                    {prediction.facts?.map((fact) => <Fact key={fact.label} {...fact} />)}
                  </div>
                  <div className="section-heading"><span>Explicación Grad-CAM</span></div>
                  <div className="detail-facts">
                    <Fact label="Método" value={explanation.method} />
                    <Fact label="Versión" value={explanation.methodVersion} />
                    <Fact label="Capa convolucional" value={explanation.lastConvLayer} />
                    <Fact label="Estado" value={explanationStatus} />
                    <Fact label="Fecha" value={explanation.createdAt} />
                  </div>
                  {explanation.error ? <p className="detail-error">{explanation.error}</p> : null}
                  {explanation.otherMethods?.length ? <p className="detail-secondary">Otras explicaciones disponibles: {explanation.otherMethods.join(', ')}</p> : null}
                  <div className="section-heading"><span>LIME y SHAP</span></div>
                  <div className="detail-facts">
                    <Fact label="Estado LIME" value={limePanel.status} />
                    <Fact label="Fecha LIME" value={limePanel.createdAt} />
                    <Fact label="Estado SHAP" value={shapPanel.status} />
                    <Fact label="Fecha SHAP" value={shapPanel.createdAt} />
                  </div>
                  {limePanel.error ? <p className="detail-error">LIME: {limePanel.error}</p> : null}
                  {shapPanel.error ? <p className="detail-error">SHAP: {shapPanel.error}</p> : null}
                  <details className="parameters-details"><summary>Parámetros de explicación</summary><pre>{JSON.stringify(explanation.parameters ?? {}, null, 2)}</pre></details>
                </div>
              )}
            </aside>
          </div>
        </div>
      </section>
    </div>
  );
}
