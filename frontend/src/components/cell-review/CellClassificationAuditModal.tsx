import { useCallback, useEffect } from 'react';

import { api } from '../../services/api';
import type {
  CellClassificationRunDetail,
  CellExplanation,
  CellPredictionDetail,
  CellPredictionSummary,
} from '../../types/cellClassification';
import { AuthenticatedCropImage, useAuthenticatedObjectUrl } from './AuthenticatedCellImage';

function ExplanationImage({
  explanation,
  kind,
}: {
  explanation: CellExplanation;
  kind: 'heatmap' | 'overlay';
}) {
  const load = useCallback(
    (signal: AbortSignal) => (
      kind === 'heatmap'
        ? api.getCellExplanationHeatmapBlob(explanation.id, signal)
        : api.getCellExplanationOverlayBlob(explanation.id, signal)
    ),
    [explanation.id, kind],
  );
  const image = useAuthenticatedObjectUrl(
    load,
    explanation.status === 'generated',
  );
  if (image.loading) return <div className="image-placeholder">Cargando artefacto autenticado…</div>;
  if (!image.url || image.error) return <div className="image-placeholder">Artefacto no disponible.</div>;
  return (
    <img
      src={image.url}
      alt={kind === 'heatmap' ? 'Heatmap Grad-CAM de la célula' : 'Overlay Grad-CAM de la célula'}
      loading="lazy"
      decoding="async"
    />
  );
}

function AuditFact({ label, value }: { label: string; value: string | number | null | undefined }) {
  return <span>{label}<strong>{value ?? '—'}</strong></span>;
}

export function CellClassificationAuditModal({
  prediction,
  run,
  onClose,
}: {
  prediction: CellPredictionSummary | CellPredictionDetail;
  run: CellClassificationRunDetail | null;
  onClose: () => void;
}) {
  const explanation = prediction.explanation;
  const crop = prediction.detection?.crop ?? prediction.crop ?? null;

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);

  return (
    <div className="audit-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="audit-modal cell-classification-audit"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cell-classification-audit-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="audit-modal-header">
          <div>
            <p>Auditoría visual · Grad-CAM</p>
            <h2 id="cell-classification-audit-title">Clasificación de {prediction.cell_code}</h2>
          </div>
          <button className="modal-close" type="button" onClick={onClose} aria-label="Cerrar auditoría">×</button>
        </header>

        <div className="audit-detail-grid">
          <article className="audit-detail-panel">
            <div className="audit-panel-heading">
              <span>01</span>
              <div><strong>Crop fuente</strong><small>Entrada inmutable de inferencia</small></div>
            </div>
            <div className="audit-detail-image cell-audit-crop">
              <AuthenticatedCropImage crop={crop} alt={`Crop fuente ${prediction.cell_code}`} eager />
            </div>
            <div className="detail-facts">
              <AuditFact label="Código" value={prediction.cell_code} />
              <AuditFact label="Detection ID" value={prediction.cell_detection_id} />
              <AuditFact label="Crop checksum" value={crop ? `${crop.sha256.slice(0, 12)}…` : null} />
            </div>
          </article>

          <article className="audit-detail-panel prediction-panel">
            <div className="audit-panel-heading">
              <span>02</span>
              <div><strong>Predicción</strong><small>Decisión automática inmutable</small></div>
            </div>
            <span className={`cell-prediction-label large prediction-${prediction.predicted_label ?? 'failed'}`}>
              {prediction.predicted_label ?? 'predicción fallida'}
            </span>
            <div className="detail-facts">
              <AuditFact label="P(parasitized)" value={prediction.probability_parasitized?.toFixed(6)} />
              <AuditFact label="P(uninfected)" value={prediction.probability_uninfected?.toFixed(6)} />
              <AuditFact label="Threshold" value={prediction.threshold_used.toFixed(6)} />
              <AuditFact label="Fuente threshold" value={prediction.threshold_source} />
              <AuditFact label="Margen" value={prediction.decision_margin?.toFixed(6)} />
              <AuditFact label="Próxima al threshold" value={prediction.near_threshold ? 'Sí' : 'No'} />
              <AuditFact label="Modelo" value={run?.model_name} />
              <AuditFact label="Versión" value={run?.model_version} />
            </div>
            <div className="clinical-mini-disclaimer">
              Resultado experimental de cribado. Requiere revisión experta y no constituye un diagnóstico clínico.
            </div>
          </article>

          <article className="audit-detail-panel">
            <div className="audit-panel-heading">
              <span>03</span>
              <div><strong>Explicación Grad-CAM</strong><small>Heatmap y overlay derivados</small></div>
            </div>
            {explanation?.status === 'generated' ? (
              <>
                <div className="audit-detail-image"><ExplanationImage explanation={explanation} kind="heatmap" /></div>
                <div className="audit-detail-image"><ExplanationImage explanation={explanation} kind="overlay" /></div>
                <div className="detail-facts">
                  <AuditFact label="Método" value={explanation.method} />
                  <AuditFact label="Versión" value={explanation.method_version} />
                  <AuditFact label="Capa convolucional" value={explanation.last_conv_layer} />
                  <AuditFact label="Estado" value={explanation.status} />
                </div>
                <details className="parameters-details">
                  <summary>Parámetros de explicación</summary>
                  <pre>{JSON.stringify(explanation.parameters_json, null, 2)}</pre>
                </details>
              </>
            ) : (
              <div className="image-placeholder">
                {explanation?.status === 'unsupported'
                  ? 'El modelo productivo no admite Grad-CAM con la configuración registrada.'
                  : 'La explicación visual no está generada.'}
              </div>
            )}
          </article>
        </div>
      </section>
    </div>
  );
}
