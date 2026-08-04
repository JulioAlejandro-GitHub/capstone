import { useCallback, useEffect, useState } from 'react';

import { api } from '../../services/api';
import type {
  CellExplanation,
  CellPredictionDetail,
  CellPredictionSummary,
} from '../../types/cellClassification';
import { AuthenticatedCropImage, useAuthenticatedObjectUrl } from './AuthenticatedCellImage';

type GradCamMode = 'original' | 'heatmap' | 'overlay';

function GradCamAsset({
  explanation,
  mode,
}: {
  explanation: CellExplanation;
  mode: Exclude<GradCamMode, 'original'>;
}) {
  const load = useCallback(
    (signal: AbortSignal) => (
      mode === 'heatmap'
        ? api.getCellExplanationHeatmapBlob(explanation.id, signal)
        : api.getCellExplanationOverlayBlob(explanation.id, signal)
    ),
    [explanation.id, mode],
  );
  const image = useAuthenticatedObjectUrl(
    load,
    explanation.status === 'generated',
    `${explanation.id}:${mode}`,
  );

  if (image.loading) return <span className="cell-gradcam-state">Cargando artefacto autenticado…</span>;
  if (!image.url || image.error) return <span className="cell-gradcam-state">Artefacto no disponible.</span>;
  return (
    <img
      src={image.url}
      alt={mode === 'heatmap' ? 'Heatmap Grad-CAM de la célula' : 'Overlay Grad-CAM de la célula'}
      loading="lazy"
      decoding="async"
    />
  );
}

export function CellGradCamPreview({
  prediction,
}: {
  prediction: CellPredictionSummary | CellPredictionDetail;
}) {
  const [mode, setMode] = useState<GradCamMode>('original');
  const explanation = prediction.explanation;
  const crop = prediction.detection?.crop
    ?? ('detection_detail' in prediction ? prediction.detection_detail?.crop : null)
    ?? prediction.crop
    ?? null;
  const generated = explanation?.status === 'generated';

  useEffect(() => {
    setMode('original');
  }, [prediction.id]);

  return (
    <section className="cell-gradcam-preview" aria-labelledby="cell-gradcam-preview-heading">
      <header>
        <h4 id="cell-gradcam-preview-heading">Visualización Grad-CAM</h4>
        <div role="tablist" aria-label="Capa de explicabilidad">
          {([
            ['original', 'Crop original'],
            ['heatmap', 'Heatmap'],
            ['overlay', 'Overlay'],
          ] as const).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={mode === id}
              disabled={id !== 'original' && !generated}
              onClick={() => setMode(id)}
            >
              {label}
            </button>
          ))}
        </div>
      </header>
      <div className="cell-gradcam-image" role="tabpanel">
        {mode === 'original' ? (
          <AuthenticatedCropImage crop={crop} alt={`Crop original ${prediction.cell_code}`} eager />
        ) : generated && explanation ? (
          <GradCamAsset explanation={explanation} mode={mode} />
        ) : (
          <span className="cell-gradcam-state">Grad-CAM no disponible.</span>
        )}
      </div>
    </section>
  );
}
