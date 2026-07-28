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

const clamp = (value: number, minimum: number, maximum: number) =>
  Math.min(maximum, Math.max(minimum, value));

type CellImageViewerProps = {
  detectionRunId: string;
  images: CellDetectionImage[];
  image: CellDetectionImage;
  detections: CellDetectionSummary[];
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
  const original = useAuthenticatedObjectUrl(loadOriginal);
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
  const viewBox = `${viewCenter.x - viewWidth / 2} ${viewCenter.y - viewHeight / 2} ${viewWidth} ${viewHeight}`;
  const screenStroke = 2;
  const labelSize = Math.max(
    20,
    Math.min(48, Math.min(image.width_px, image.height_px) / 40),
  ) / zoom;
  const gridSize = Math.max(32, Math.min(image.width_px, image.height_px) / 20);

  function startPan(event: React.PointerEvent<HTMLDivElement>) {
    if (event.button !== 0 || zoom <= 1) return;
    const target = event.target as Element;
    if (target.closest('[data-detection-box]')) return;
    dragPoint.current = { x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
  }

  function movePan(event: React.PointerEvent<HTMLDivElement>) {
    if (!dragPoint.current || zoom <= 1) return;
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

  function selectBox(event: React.SyntheticEvent, detection: CellDetectionSummary) {
    event.stopPropagation();
    onDetectionSelect(detection, false);
  }

  return (
    <section className="cell-viewer-section" aria-labelledby="cell-viewer-heading">
      <header className="cell-panel-heading cell-viewer-heading">
        <div>
          <h2 id="cell-viewer-heading">Imagen original y bounding boxes</h2>
          <p>{image.sequence_number}. {image.safe_name}</p>
        </div>
        <span>Zoom digital: {Math.round(zoom * 100)}%</span>
      </header>

      <div className="cell-viewer-toolbar" role="toolbar" aria-label="Controles del visor">
        <label>
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
        <button type="button" onClick={fit}>Ajustar a pantalla</button>
        {[0.25, 0.5, 1, 2].map((level) => (
          <button
            key={level}
            type="button"
            aria-pressed={zoom === level}
            onClick={() => setZoomLevel(level)}
          >
            {level * 100}%
          </button>
        ))}
        <button type="button" aria-label="Acercar" onClick={() => setZoomLevel(zoom * 1.25)}>＋</button>
        <button type="button" aria-label="Alejar" onClick={() => setZoomLevel(zoom / 1.25)}>−</button>
        <button type="button" onClick={fit}>Restablecer vista</button>
        <button type="button" aria-pressed={showBoxes} onClick={() => setShowBoxes((value) => !value)}>
          Cajas
        </button>
        <button type="button" aria-pressed={showLabels} onClick={() => setShowLabels((value) => !value)}>
          Etiquetas
        </button>
        <button type="button" aria-pressed={showGrid} onClick={() => setShowGrid((value) => !value)}>
          Rejilla
        </button>
        <button type="button" onClick={onPrevious} aria-label="Detección anterior">← Anterior</button>
        <button type="button" onClick={onNext} aria-label="Detección siguiente">Siguiente →</button>
        <button type="button" onClick={onNextUnreviewed}>Siguiente sin revisar</button>
      </div>

      <div
        className={`cell-image-viewport${dragging ? ' is-dragging' : ''}${zoom > 1 ? ' can-pan' : ''}`}
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
          <svg
            className="cell-image-canvas"
            viewBox={viewBox}
            preserveAspectRatio="xMidYMid meet"
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
            {showBoxes || showLabels ? detections.map((detection) => {
              const isSelected = detection.id === selectedDetectionId;
              return (
                <g
                  key={detection.id}
                  className={`cell-box status-${detection.review_status}${isSelected ? ' is-selected' : ''}`}
                  data-detection-box
                  role="button"
                  tabIndex={0}
                  aria-label={`${detection.cell_code}, ${statusLabel[detection.review_status]}${isSelected ? ', seleccionada' : ''}`}
                  onClick={(event) => selectBox(event, detection)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      selectBox(event, detection);
                    }
                  }}
                >
                  <title>{detection.cell_code} · {statusLabel[detection.review_status]}</title>
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
                      {isSelected ? (
                        <circle
                          cx={detection.bbox_x}
                          cy={detection.bbox_y}
                          r={screenStroke * 3.2}
                          vectorEffect="non-scaling-stroke"
                        />
                      ) : null}
                    </>
                  ) : null}
                  {showLabels ? (
                    <text
                      x={detection.bbox_x}
                      y={Math.max(labelSize, detection.bbox_y - labelSize * 0.3)}
                      style={{ fontSize: labelSize }}
                    >
                      {statusSymbol[detection.review_status]} {detection.cell_code}
                    </text>
                  ) : null}
                </g>
              );
            }) : null}
          </svg>
        ) : null}
      </div>

      <div className="cell-viewer-footer">
        <ul className="cell-box-legend" aria-label="Leyenda de estados">
          {(Object.keys(statusLabel) as CellReviewStatus[]).map((status) => (
            <li key={status} className={`status-${status}`}>
              <span aria-hidden="true">{statusSymbol[status]}</span>{statusLabel[status]}
            </li>
          ))}
        </ul>
        {selected ? (
          <p aria-live="polite">
            <strong>{selected.cell_code}</strong> · bbox [{selected.bbox_x}, {selected.bbox_y},{' '}
            {selected.bbox_width}, {selected.bbox_height}] · área {selected.component.area_px} px² ·{' '}
            score geométrico {selected.detector_score == null ? '—' : selected.detector_score.toFixed(4)} ·{' '}
            {statusLabel[selected.review_status]}
          </p>
        ) : <p>Ninguna detección seleccionada.</p>}
      </div>
    </section>
  );
});
