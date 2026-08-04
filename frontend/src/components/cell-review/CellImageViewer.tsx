import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { api } from '../../services/api';
import type {
  CellDetectionImage,
  CellDetectionSummary,
  CellReviewStatus,
} from '../../types/cellReview';
import { useAuthenticatedObjectUrl } from './AuthenticatedCellImage';
import type { CellPredictionSummary } from '../../types/cellClassification';

const statusLabel: Record<CellReviewStatus, string> = {
  unreviewed: 'Sin revisar',
  accepted: 'Aceptada',
  rejected: 'Rechazada',
  needs_attention: 'Requiere atención',
};

const statusSymbol: Record<CellReviewStatus, string> = {
  unreviewed: '○',
  accepted: '✓',
  rejected: '×',
  needs_attention: '!',
};

type OverlayColorMode = 'detection' | 'prediction' | 'classification_review';
type ViewerTool = 'select' | 'pan';

type ViewerIconName =
  | 'select'
  | 'pan'
  | 'zoom-in'
  | 'zoom-out'
  | 'fit'
  | 'reset'
  | 'boxes'
  | 'labels'
  | 'grid'
  | 'previous'
  | 'next'
  | 'unreviewed';

const ZOOM_STEPS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 3, 4] as const;

function ViewerIcon({ name }: { name: ViewerIconName }) {
  const common = {
    width: 20,
    height: 20,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
  };

  switch (name) {
    case 'select':
      return (
        <svg {...common}>
          <path d="M5 3.5 18.5 12l-6.1 1.2-3.2 5.3L5 3.5Z" />
        </svg>
      );
    case 'pan':
      return (
        <svg {...common}>
          <path d="M7.5 11V6.5a1.5 1.5 0 0 1 3 0V10" />
          <path d="M10.5 9V5a1.5 1.5 0 0 1 3 0v5" />
          <path d="M13.5 9V6.5a1.5 1.5 0 0 1 3 0V11" />
          <path d="M16.5 10a1.5 1.5 0 0 1 3 0v3.4c0 4.4-2.6 7.1-6.7 7.1h-.6c-2.2 0-3.5-.9-4.8-2.4L4.8 15a1.5 1.5 0 0 1 2.1-2.1l.6.6V11" />
        </svg>
      );
    case 'zoom-in':
    case 'zoom-out':
      return (
        <svg {...common}>
          <circle cx="10.5" cy="10.5" r="6.5" />
          <path d="m15.5 15.5 4.5 4.5M7.5 10.5h6" />
          {name === 'zoom-in' ? <path d="M10.5 7.5v6" /> : null}
        </svg>
      );
    case 'fit':
      return (
        <svg {...common}>
          <path d="M8.5 4H4v4.5M15.5 4H20v4.5M20 15.5V20h-4.5M8.5 20H4v-4.5" />
          <rect x="8" y="8" width="8" height="8" rx="1" />
        </svg>
      );
    case 'reset':
      return (
        <svg {...common}>
          <path d="M4.6 8.1A8 8 0 1 1 4 15M4 4v4.5h4.5" />
          <path d="M12 8v4l2.7 1.7" />
        </svg>
      );
    case 'boxes':
      return (
        <svg {...common}>
          <rect x="4" y="5" width="11" height="10" rx="1" />
          <path d="M9 9h11v10H9z" />
        </svg>
      );
    case 'labels':
      return (
        <svg {...common}>
          <path d="M4 5h10l6 7-6 7H4V5Z" />
          <circle cx="8" cy="12" r="1.4" />
        </svg>
      );
    case 'grid':
      return (
        <svg {...common}>
          <rect x="4" y="4" width="16" height="16" rx="1" />
          <path d="M9.3 4v16M14.7 4v16M4 9.3h16M4 14.7h16" />
        </svg>
      );
    case 'previous':
      return (
        <svg {...common}>
          <path d="m14.5 6-6 6 6 6" />
        </svg>
      );
    case 'next':
      return (
        <svg {...common}>
          <path d="m9.5 6 6 6-6 6" />
        </svg>
      );
    case 'unreviewed':
      return (
        <svg {...common}>
          <circle cx="9" cy="12" r="5" />
          <path d="M14 8h5v5M19 8l-5 5" />
        </svg>
      );
  }
}

const overlayModeLabel: Record<OverlayColorMode, string> = {
  detection: 'Estado de detección',
  prediction: 'Predicción IA',
  classification_review: 'Revisión humana',
};

function classificationVisual(
  detection: CellDetectionSummary,
  prediction: CellPredictionSummary | undefined,
  mode: OverlayColorMode,
) {
  if (mode === 'detection') {
    return {
      className: `status-${detection.review_status}`,
      label: statusLabel[detection.review_status],
      symbol: statusSymbol[detection.review_status],
    };
  }
  if (!prediction) {
    return { className: 'classification-missing', label: 'Sin predicción', symbol: '—' };
  }
  if (mode === 'prediction') {
    if (prediction.prediction_status === 'failed') {
      return { className: 'prediction-failed', label: 'Predicción fallida', symbol: '×' };
    }
    return {
      className: `prediction-${prediction.predicted_label}`,
      label: `${prediction.predicted_label}${prediction.near_threshold ? ', próxima al threshold' : ''}`,
      symbol: prediction.near_threshold
        ? '≈'
        : prediction.predicted_label === 'parasitized' ? 'P' : 'U',
    };
  }
  const symbols = {
    unreviewed: '○',
    confirmed: '✓',
    corrected: '↺',
    needs_attention: '!',
  } as const;
  const labels = {
    unreviewed: 'Sin revisión',
    confirmed: 'Confirmada',
    corrected: 'Corregida',
    needs_attention: 'Requiere atención',
  } as const;
  return {
    className: `classification-review-${prediction.review_status}`,
    label: labels[prediction.review_status],
    symbol: symbols[prediction.review_status],
  };
}

const clamp = (value: number, minimum: number, maximum: number) =>
  Math.min(maximum, Math.max(minimum, value));

type CellImageViewerProps = {
  detectionRunId: string;
  images: CellDetectionImage[];
  image: CellDetectionImage;
  detections: CellDetectionSummary[];
  classificationAnnotations?: ReadonlyMap<string, CellPredictionSummary>;
  selectedDetectionId: string | null;
  focusRequest: number;
  onImageChange: (microscopyImageId: string) => void;
  onDetectionSelect: (detection: CellDetectionSummary, focusViewer: boolean) => void;
  onPrevious: () => void;
  onNext: () => void;
  onNextUnreviewed: () => void;
};

export const CellImageViewer = memo(function CellImageViewer({
  detectionRunId,
  images,
  image,
  detections,
  classificationAnnotations = new Map(),
  selectedDetectionId,
  focusRequest,
  onImageChange,
  onDetectionSelect,
  onPrevious,
  onNext,
  onNextUnreviewed,
}: CellImageViewerProps) {
  const [zoom, setZoom] = useState(1);
  const [viewCenter, setViewCenter] = useState({
    x: image.width_px / 2,
    y: image.height_px / 2,
  });
  const [showBoxes, setShowBoxes] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [showGrid, setShowGrid] = useState(false);
  const [overlayMode, setOverlayMode] = useState<OverlayColorMode>('detection');
  const [activeTool, setActiveTool] = useState<ViewerTool>('select');
  const [dragging, setDragging] = useState(false);
  const dragPoint = useRef<{ x: number; y: number } | null>(null);

  const loadOriginal = useCallback(
    (signal: AbortSignal) => api.getCellOriginalImageBlob(
      detectionRunId,
      image.microscopy_image_id,
      image.content_url,
      signal,
    ),
    [detectionRunId, image.content_url, image.microscopy_image_id],
  );
  const original = useAuthenticatedObjectUrl(
    loadOriginal,
    true,
    `${detectionRunId}:${image.microscopy_image_id}`,
  );
  const selected = useMemo(
    () => detections.find((item) => item.id === selectedDetectionId) ?? null,
    [detections, selectedDetectionId],
  );

  const constrainCenter = useCallback(
    (center: { x: number; y: number }, nextZoom = zoom) => {
      if (nextZoom <= 1) {
        return { x: image.width_px / 2, y: image.height_px / 2 };
      }
      const halfWidth = image.width_px / (2 * nextZoom);
      const halfHeight = image.height_px / (2 * nextZoom);
      return {
        x: clamp(center.x, halfWidth, image.width_px - halfWidth),
        y: clamp(center.y, halfHeight, image.height_px - halfHeight),
      };
    },
    [image.height_px, image.width_px, zoom],
  );

  const setZoomLevel = useCallback((value: number) => {
    const next = clamp(value, 0.25, 4);
    setZoom(next);
    setViewCenter((center) => constrainCenter(center, next));
  }, [constrainCenter]);

  const fit = useCallback(() => {
    setZoom(1);
    setViewCenter({ x: image.width_px / 2, y: image.height_px / 2 });
  }, [image.height_px, image.width_px]);

  useEffect(() => {
    fit();
  }, [fit, image.microscopy_image_id]);

  useEffect(() => {
    if (!focusRequest || !selected) return;
    const nextZoom = Math.max(zoom, 2);
    setZoom(nextZoom);
    setViewCenter(constrainCenter({
      x: selected.bbox_x + selected.bbox_width / 2,
      y: selected.bbox_y + selected.bbox_height / 2,
    }, nextZoom));
    // focusRequest intentionally makes repeated "focus" commands observable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusRequest]);

  const viewWidth = image.width_px / zoom;
  const viewHeight = image.height_px / zoom;
  const viewX = viewCenter.x - viewWidth / 2;
  const viewY = viewCenter.y - viewHeight / 2;
  const viewBox = `${viewX} ${viewY} ${viewWidth} ${viewHeight}`;
  const minimapViewportX = clamp(viewX, 0, image.width_px);
  const minimapViewportY = clamp(viewY, 0, image.height_px);
  const minimapViewportWidth = Math.max(
    0,
    clamp(viewX + viewWidth, 0, image.width_px) - minimapViewportX,
  );
  const minimapViewportHeight = Math.max(
    0,
    clamp(viewY + viewHeight, 0, image.height_px) - minimapViewportY,
  );
  const selectedIndex = selected
    ? detections.findIndex((detection) => detection.id === selected.id)
    : -1;
  const screenStroke = 2;
  const labelSize = Math.max(
    4,
    Math.min(32, Math.min(image.width_px, image.height_px) / 150),
  ) / zoom;
  const gridSize = Math.max(32, Math.min(image.width_px, image.height_px) / 20);

  function changeZoom(direction: 1 | -1) {
    const next = direction > 0
      ? ZOOM_STEPS.find((level) => level > zoom + 0.001) ?? ZOOM_STEPS.at(-1)!
      : [...ZOOM_STEPS].reverse().find((level) => level < zoom - 0.001) ?? ZOOM_STEPS[0];
    setZoomLevel(next);
  }

  function startPan(event: React.PointerEvent<HTMLDivElement>) {
    if (activeTool !== 'pan' || event.button !== 0 || zoom <= 1) return;
    event.preventDefault();
    dragPoint.current = { x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
  }

  function movePan(event: React.PointerEvent<HTMLDivElement>) {
    if (activeTool !== 'pan' || !dragPoint.current || zoom <= 1) return;
    event.preventDefault();
    const rect = event.currentTarget.getBoundingClientRect();
    const dx = event.clientX - dragPoint.current.x;
    const dy = event.clientY - dragPoint.current.y;
    dragPoint.current = { x: event.clientX, y: event.clientY };
    setViewCenter((center) => constrainCenter({
      x: center.x - dx * (viewWidth / Math.max(rect.width, 1)),
      y: center.y - dy * (viewHeight / Math.max(rect.height, 1)),
    }));
  }

  function stopPan(event: React.PointerEvent<HTMLDivElement>) {
    dragPoint.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setDragging(false);
  }

  function chooseTool(tool: ViewerTool) {
    dragPoint.current = null;
    setDragging(false);
    setActiveTool(tool);
  }

  function selectBox(event: React.SyntheticEvent, detection: CellDetectionSummary) {
    event.stopPropagation();
    if (event.type === 'click' && activeTool !== 'select') return;
    onDetectionSelect(detection, false);
  }

  return (
    <section
      className="cell-viewer-section"
      aria-labelledby="cell-viewer-heading"
      data-active-tool={activeTool}
    >
      <header className="cell-panel-heading cell-viewer-heading cell-viewer-overlay-heading">
        <div>
          <h2 id="cell-viewer-heading">Imagen original y bounding boxes</h2>
          <p>{image.sequence_number}. {image.safe_name}</p>
        </div>
        <output className="cell-viewer-zoom-readout" aria-live="polite">
          Zoom digital: {Math.round(zoom * 100)}%
        </output>
      </header>

      <div
        className="cell-viewer-toolbar cell-viewer-controls"
        role="toolbar"
        aria-label="Controles del visor"
      >
        <div className="cell-viewer-selectors">
          <label className="cell-viewer-selector">
            <span>Imagen</span>
            <select
              aria-label="Seleccionar imagen del frotis"
              value={image.microscopy_image_id}
              onChange={(event) => onImageChange(event.target.value)}
            >
              {images.map((item) => (
                <option key={item.microscopy_image_id} value={item.microscopy_image_id}>
                  {item.sequence_number}. {item.safe_name}
                </option>
              ))}
            </select>
          </label>
          {classificationAnnotations.size ? (
            <label className="cell-viewer-selector">
              <span>Color de cajas</span>
              <select
                aria-label="Colorear bounding boxes por"
                value={overlayMode}
                onChange={(event) => setOverlayMode(event.target.value as OverlayColorMode)}
              >
                {(Object.keys(overlayModeLabel) as OverlayColorMode[]).map((mode) => (
                  <option key={mode} value={mode}>{overlayModeLabel[mode]}</option>
                ))}
              </select>
            </label>
          ) : null}
        </div>

        <div className="cell-viewer-tool-group" role="group" aria-label="Herramienta activa">
          <button
            type="button"
            className="cell-viewer-icon-button"
            aria-label="Seleccionar bounding boxes"
            title="Seleccionar bounding boxes"
            aria-pressed={activeTool === 'select'}
            onClick={() => chooseTool('select')}
          >
            <ViewerIcon name="select" />
          </button>
          <button
            type="button"
            className="cell-viewer-icon-button"
            aria-label="Desplazar imagen (pan)"
            title="Desplazar imagen (pan)"
            aria-pressed={activeTool === 'pan'}
            onClick={() => chooseTool('pan')}
          >
            <ViewerIcon name="pan" />
          </button>
          <span className="cell-viewer-tool-separator" aria-hidden="true" />
          <button
            type="button"
            className="cell-viewer-icon-button"
            aria-label="Acercar"
            title="Acercar"
            onClick={() => changeZoom(1)}
          >
            <ViewerIcon name="zoom-in" />
          </button>
          <button
            type="button"
            className="cell-viewer-icon-button"
            aria-label="Alejar"
            title="Alejar"
            onClick={() => changeZoom(-1)}
          >
            <ViewerIcon name="zoom-out" />
          </button>
          <button
            type="button"
            className="cell-viewer-icon-button"
            aria-label="Ajustar a pantalla"
            title="Ajustar a pantalla"
            onClick={fit}
          >
            <ViewerIcon name="fit" />
          </button>
          <button
            type="button"
            className="cell-viewer-icon-button"
            aria-label="Restablecer vista"
            title="Restablecer vista"
            onClick={fit}
          >
            <ViewerIcon name="reset" />
          </button>
          <span className="cell-viewer-tool-separator" aria-hidden="true" />
          <button
            type="button"
            className="cell-viewer-icon-button"
            aria-label="Mostrar u ocultar bounding boxes"
            title="Mostrar u ocultar bounding boxes"
            aria-pressed={showBoxes}
            onClick={() => setShowBoxes((value) => !value)}
          >
            <ViewerIcon name="boxes" />
          </button>
          <button
            type="button"
            className="cell-viewer-icon-button"
            aria-label="Mostrar u ocultar etiquetas"
            title="Mostrar u ocultar etiquetas"
            aria-pressed={showLabels}
            onClick={() => setShowLabels((value) => !value)}
          >
            <ViewerIcon name="labels" />
          </button>
          <button
            type="button"
            className="cell-viewer-icon-button"
            aria-label="Mostrar u ocultar rejilla"
            title="Mostrar u ocultar rejilla"
            aria-pressed={showGrid}
            onClick={() => setShowGrid((value) => !value)}
          >
            <ViewerIcon name="grid" />
          </button>
        </div>
      </div>

      <div
        className={`cell-image-viewport cell-image-tool-${activeTool}${dragging ? ' is-dragging' : ''}${activeTool === 'pan' && zoom > 1 ? ' can-pan' : ''}`}
        data-tool={activeTool}
        onPointerDown={startPan}
        onPointerMove={movePan}
        onPointerUp={stopPan}
        onPointerCancel={stopPan}
      >
        {original.loading ? <p className="cell-viewer-state">Cargando imagen original autenticada…</p> : null}
        {original.error ? (
          <p className="cell-viewer-state cell-error" role="alert">
            Imagen original no disponible.
          </p>
        ) : null}
        {original.url ? (
          <>
            <img
              className="cell-image-backdrop"
              src={original.url}
              alt=""
              aria-hidden="true"
              draggable={false}
            />
            <svg
              className="cell-image-canvas"
              viewBox={viewBox}
              preserveAspectRatio="xMidYMid meet"
              role="listbox"
              aria-label={`Imagen microscópica ${image.safe_name} con ${detections.length} bounding boxes cargadas`}
            >
            <defs>
              <pattern id={`cell-grid-${image.microscopy_image_id}`} width={gridSize} height={gridSize} patternUnits="userSpaceOnUse">
                <path d={`M ${gridSize} 0 L 0 0 0 ${gridSize}`} className="cell-grid-line" />
              </pattern>
            </defs>
            <image
              href={original.url}
              x="0"
              y="0"
              width={image.width_px}
              height={image.height_px}
              preserveAspectRatio="none"
            />
            {showGrid ? (
              <rect
                x="0"
                y="0"
                width={image.width_px}
                height={image.height_px}
                fill={`url(#cell-grid-${image.microscopy_image_id})`}
                pointerEvents="none"
              />
            ) : null}
            {detections.map((detection) => {
              const isSelected = detection.id === selectedDetectionId;
              const shouldRenderLabel = isSelected || (showLabels && zoom > 1);
              if (!showBoxes && !shouldRenderLabel && !isSelected) return null;
              const visual = classificationVisual(
                detection,
                classificationAnnotations.get(detection.id),
                overlayMode,
              );
              return (
                <g
                  key={detection.id}
                  className={`cell-box ${visual.className}${isSelected ? ' is-selected' : ''}`}
                  data-detection-box
                  role="option"
                  tabIndex={isSelected || (!selectedDetectionId && detection === detections[0]) ? 0 : -1}
                  aria-selected={isSelected}
                  aria-label={`${detection.cell_code}, ${visual.label}${isSelected ? ', seleccionada' : ''}`}
                  onClick={(event) => selectBox(event, detection)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      selectBox(event, detection);
                    }
                    if (
                      event.key === 'ArrowRight'
                      || event.key === 'ArrowDown'
                      || event.key === 'ArrowLeft'
                      || event.key === 'ArrowUp'
                    ) {
                      event.preventDefault();
                      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') onNext();
                      else onPrevious();
                      window.requestAnimationFrame(() => {
                        document.querySelector<SVGElement>(
                          '.cell-image-canvas .cell-box[aria-selected="true"]',
                        )?.focus();
                      });
                    }
                  }}
                >
                  <title>{detection.cell_code} · {visual.label}</title>
                  {showBoxes ? (
                    <>
                      <rect
                        x={detection.bbox_x}
                        y={detection.bbox_y}
                        width={detection.bbox_width}
                        height={detection.bbox_height}
                        vectorEffect="non-scaling-stroke"
                        style={{ strokeWidth: isSelected ? screenStroke * 2.2 : screenStroke }}
                      />
                    </>
                  ) : null}
                  {isSelected ? (
                    <>
                      <rect
                        className="cell-image-selection-outline"
                        x={detection.bbox_x}
                        y={detection.bbox_y}
                        width={detection.bbox_width}
                        height={detection.bbox_height}
                        vectorEffect="non-scaling-stroke"
                        pointerEvents="none"
                        style={{ fill: 'none', stroke: '#a4e6ff', strokeWidth: screenStroke * 3 }}
                      />
                      <circle
                        className="cell-image-selection-anchor"
                        cx={detection.bbox_x}
                        cy={detection.bbox_y}
                        r={screenStroke * 3.2}
                        vectorEffect="non-scaling-stroke"
                        pointerEvents="none"
                      />
                    </>
                  ) : null}
                  {shouldRenderLabel ? (
                    <text
                      className={isSelected ? 'cell-image-selected-label' : undefined}
                      x={detection.bbox_x}
                      y={Math.max(labelSize, detection.bbox_y - labelSize * 0.3)}
                      style={{ fontSize: labelSize }}
                    >
                      {visual.symbol} {detection.cell_code}
                    </text>
                  ) : null}
                </g>
              );
            })}
            </svg>
          </>
        ) : null}

        <nav
          className="cell-viewer-navigation"
          aria-label="Navegación entre detecciones"
          onPointerDown={(event) => event.stopPropagation()}
        >
          <button
            type="button"
            className="cell-viewer-navigation-button"
            onClick={onPrevious}
            disabled={!detections.length}
            aria-label="Detección anterior"
            title="Detección anterior"
          >
            <ViewerIcon name="previous" />
          </button>
          <output className="cell-viewer-navigation-position" aria-live="polite">
            {selectedIndex >= 0 ? `${selectedIndex + 1}/${detections.length}` : `—/${detections.length}`}
          </output>
          <button
            type="button"
            className="cell-viewer-navigation-button"
            onClick={onNext}
            disabled={!detections.length}
            aria-label="Detección siguiente"
            title="Detección siguiente"
          >
            <ViewerIcon name="next" />
          </button>
          <button
            type="button"
            className="cell-viewer-navigation-button cell-viewer-navigation-unreviewed"
            onClick={onNextUnreviewed}
            disabled={!detections.length}
            aria-label="Siguiente sin revisar"
            title="Siguiente sin revisar"
          >
            <ViewerIcon name="unreviewed" />
          </button>
        </nav>

        {original.url ? (
          <aside
            className="cell-viewer-minimap"
            aria-label="Minimapa de la imagen original"
            onPointerDown={(event) => event.stopPropagation()}
          >
            <header className="cell-viewer-minimap-heading">
              <span>Minimapa</span>
              <output>Centro {Math.round(viewCenter.x)}, {Math.round(viewCenter.y)}</output>
            </header>
            <svg
              className="cell-viewer-minimap-canvas"
              viewBox={`0 0 ${image.width_px} ${image.height_px}`}
              preserveAspectRatio="xMidYMid meet"
              role="img"
              aria-label={`Vista general de ${image.safe_name}; el rectángulo indica el área visible`}
            >
              <image
                className="cell-viewer-minimap-image"
                href={original.url}
                x="0"
                y="0"
                width={image.width_px}
                height={image.height_px}
                preserveAspectRatio="none"
              />
              {detections.map((detection) => {
                const visual = classificationVisual(
                  detection,
                  classificationAnnotations.get(detection.id),
                  overlayMode,
                );
                return (
                  <rect
                    key={detection.id}
                    className={`cell-viewer-minimap-box ${visual.className}`}
                    x={detection.bbox_x}
                    y={detection.bbox_y}
                    width={detection.bbox_width}
                    height={detection.bbox_height}
                    fill="none"
                    stroke="rgba(164, 230, 255, .58)"
                    strokeWidth="1"
                    vectorEffect="non-scaling-stroke"
                  />
                );
              })}
              <rect
                className="cell-viewer-minimap-viewport"
                x={minimapViewportX}
                y={minimapViewportY}
                width={minimapViewportWidth}
                height={minimapViewportHeight}
                fill="rgba(164, 230, 255, .08)"
                stroke="#a4e6ff"
                strokeWidth="2"
                vectorEffect="non-scaling-stroke"
              />
              {selected ? (
                <>
                  <rect
                    className="cell-viewer-minimap-selection"
                    x={selected.bbox_x}
                    y={selected.bbox_y}
                    width={selected.bbox_width}
                    height={selected.bbox_height}
                    fill="none"
                    stroke="#4edea3"
                    strokeWidth="3"
                    vectorEffect="non-scaling-stroke"
                  />
                  <circle
                    className="cell-viewer-minimap-selection-point"
                    cx={selected.bbox_x + selected.bbox_width / 2}
                    cy={selected.bbox_y + selected.bbox_height / 2}
                    r={Math.max(selected.bbox_width, selected.bbox_height) * 0.16}
                    fill="#4edea3"
                    stroke="#061020"
                    strokeWidth="1.5"
                    vectorEffect="non-scaling-stroke"
                  />
                </>
              ) : null}
            </svg>
          </aside>
        ) : null}
      </div>

      <div className="cell-viewer-footer cell-viewer-overlay-footer">
        <ul className="cell-box-legend" aria-label={`Leyenda: ${overlayModeLabel[overlayMode]}`}>
          {overlayMode === 'detection'
            ? (Object.keys(statusLabel) as CellReviewStatus[]).map((status) => (
              <li key={status} className={`status-${status}`}>
                <span aria-hidden="true">{statusSymbol[status]}</span>{statusLabel[status]}
              </li>
            ))
            : Array.from(new Map(detections.map((detection) => {
              const visual = classificationVisual(
                detection,
                classificationAnnotations.get(detection.id),
                overlayMode,
              );
              return [visual.className, visual] as const;
            })).values()).map((visual) => (
              <li key={visual.className} className={visual.className}>
                <span aria-hidden="true">{visual.symbol}</span>{visual.label}
              </li>
            ))}
        </ul>
        {selected ? (
          <p aria-live="polite">
            <strong>{selected.cell_code}</strong> · bbox [{selected.bbox_x}, {selected.bbox_y},{' '}
            {selected.bbox_width}, {selected.bbox_height}] · área {selected.component.area_px} px² ·{' '}
            score geométrico {selected.detector_score == null ? '—' : selected.detector_score.toFixed(4)} ·{' '}
            {classificationVisual(
              selected,
              classificationAnnotations.get(selected.id),
              overlayMode,
            ).label}
          </p>
        ) : <p>Ninguna detección seleccionada.</p>}
      </div>
    </section>
  );
});
