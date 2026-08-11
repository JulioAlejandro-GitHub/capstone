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

export type ExplainabilityCaseViewModel = {
  sourceContext: 'model_execution' | 'smear_analysis';
  caseCode: string;
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

  return (
    <div className="audit-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="audit-modal case-explainability-view" role="dialog" aria-modal="true" aria-labelledby="case-explainability-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="audit-modal-header">
          <div><p>Auditoría visual · Grad-CAM</p><h2 id="case-explainability-title">Clasificación de {activeCase.caseCode}</h2></div>
          <button className="modal-close" type="button" onClick={onClose} aria-label="Cerrar auditoría">×</button>
        </header>
        <div className="audit-detail-grid">
          <article className="audit-detail-panel">
            <div className="audit-panel-heading"><span>01</span><div><strong>Crop fuente</strong><small>Entrada inmutable de inferencia</small></div></div>
            <div className="audit-detail-image"><CaseMedia media={activeCase.input.media} /></div>
            <div className="detail-facts">
              <Fact label="Código" value={activeCase.input.displayCode} />
              <Fact label="Identificador" value={activeCase.input.id} />
              <Fact label="Checksum" value={activeCase.input.checksum} />
              {activeCase.input.facts?.map((fact) => <Fact key={fact.label} {...fact} />)}
            </div>
          </article>
          <article className="audit-detail-panel prediction-panel">
            <div className="audit-panel-heading"><span>02</span><div><strong>Predicción</strong><small>Decisión automática inmutable</small></div></div>
            <span className={`cell-prediction-label large prediction-${activeCase.prediction.predictedLabel ?? 'failed'}`}>{activeCase.prediction.predictedLabel ?? 'predicción fallida'}</span>
            <div className="detail-facts">
              <Fact label="P(parasitized)" value={activeCase.prediction.probabilityParasitized} />
              <Fact label="P(uninfected)" value={activeCase.prediction.probabilityUninfected} />
              <Fact label="Threshold" value={activeCase.prediction.threshold} />
              <Fact label="Fuente threshold" value={activeCase.prediction.thresholdSource} />
              <Fact label="Margen" value={activeCase.prediction.margin} />
              <Fact label="Próxima al threshold" value={activeCase.prediction.nearThreshold} />
              <Fact label="Modelo" value={activeCase.prediction.modelName} />
              <Fact label="Versión" value={activeCase.prediction.modelVersion} />
              {activeCase.prediction.facts?.map((fact) => <Fact key={fact.label} {...fact} />)}
            </div>
            <div className="clinical-mini-disclaimer">Resultado experimental de cribado. Requiere revisión experta y no constituye un diagnóstico clínico.</div>
            {activeCase.associatedRunId && onRunSelect ? <button className="audit-action-button" type="button" onClick={() => onRunSelect(activeCase.associatedRunId!)}>Abrir run asociado</button> : null}
          </article>
          <article className="audit-detail-panel">
            <div className="audit-panel-heading"><span>03</span><div><strong>Explicación Grad-CAM</strong><small>Heatmap y overlay derivados</small></div></div>
            {explanationStatus !== 'artifact_missing' && activeCase.explanation.media.length ? activeCase.explanation.media.map((media, index) => <div className="audit-detail-image" key={`${media.kind}-${index}`}><CaseMedia media={media} onUnavailable={() => setRuntimeArtifactMissing(true)} /></div>) : <div className="image-placeholder">{explanationStatus === 'unsupported' ? 'Grad-CAM no está disponible para este modelo.' : explanationStatus === 'artifact_missing' ? 'El artefacto Grad-CAM ya no está disponible.' : explanationStatus === 'failed' ? 'No fue posible generar Grad-CAM para este caso.' : explanationStatus === 'generating' ? 'Generando explicación…' : 'La explicación visual Grad-CAM no está generada.'}</div>}
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
            {!generationAllowed && generationDisabledReason ? <p id="gradcam-action-status" className="detail-secondary">{generationDisabledReason}</p> : null}
            {generationError ? <p className="detail-error" aria-live="polite">{generationError}</p> : <span aria-live="polite" className="sr-only" />}
            <div className="detail-facts">
              <Fact label="Método" value={activeCase.explanation.method} />
              <Fact label="Versión" value={activeCase.explanation.methodVersion} />
              <Fact label="Capa convolucional" value={activeCase.explanation.lastConvLayer} />
              <Fact label="Estado" value={explanationStatus} />
              <Fact label="Fecha" value={activeCase.explanation.createdAt} />
            </div>
            {activeCase.explanation.error ? <p className="detail-error">{activeCase.explanation.error}</p> : null}
            {activeCase.explanation.otherMethods?.length ? <p className="detail-secondary">Otras explicaciones disponibles: {activeCase.explanation.otherMethods.join(', ')}</p> : null}
            <details className="parameters-details"><summary>Parámetros de explicación</summary><pre>{JSON.stringify(activeCase.explanation.parameters ?? {}, null, 2)}</pre></details>
          </article>
        </div>
      </section>
    </div>
  );
}
