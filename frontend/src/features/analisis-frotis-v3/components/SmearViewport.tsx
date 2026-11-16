import { ImageOff, LoaderCircle } from 'lucide-react';
import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from 'react';

import type { MicroscopeImage } from '../adapters/analysisModel';
import { cellKind, KIND_LABEL, type MicroscopeCell } from '../adapters/cellLayer';
import { useElementSize } from '../hooks/useElementSize';
import { useSmearImage } from '../hooks/useSmearImage';
import type { OpticsSettings } from '../state/presentationStorage';
import {
  fitViewport,
  panBy,
  rotateBy,
  zoomAt,
  type Size,
  type ViewportState,
} from '../state/viewportMath';

export type ViewportGeometry = { image: Size | null; stage: Size; url: string | null };

const DRAG_THRESHOLD = 4;
const KEY_PAN = 48;

/**
 * Viewport del frotis: imagen real con zoom digital, pan, rotación y ajustes
 * visuales reversibles. Los ajustes son filtros de presentación: nunca
 * modifican la imagen original ni las entradas de inferencia.
 */
export function SmearViewport({
  image,
  localUrl,
  scanning,
  scanLabel,
  viewport,
  onViewportChange,
  onGeometry,
  optics,
  cells,
  showCells,
  contour,
  selectedDetectionId,
  onSelectCell,
}: {
  image: MicroscopeImage | null;
  localUrl: string | null;
  scanning: boolean;
  scanLabel: string;
  /** `null` = ajustado a pantalla. */
  viewport: ViewportState | null;
  onViewportChange: (viewport: ViewportState | null) => void;
  onGeometry: (geometry: ViewportGeometry) => void;
  optics: OpticsSettings;
  cells: readonly MicroscopeCell[];
  showCells: boolean;
  contour: 'light' | 'dark';
  selectedDetectionId: string | null;
  onSelectCell: (cell: MicroscopeCell) => void;
}) {
  const source = useSmearImage(image?.id ?? null, localUrl);
  const url = source.status === 'ready' ? source.url : null;
  const { ref, size: stage } = useElementSize<HTMLDivElement>();
  const [imageSize, setImageSize] = useState<Size | null>(null);
  const [undecodable, setUndecodable] = useState(false);
  const filterId = `frotis-v3-gamma-${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  const drag = useRef<{ x: number; y: number; moved: boolean } | null>(null);

  useEffect(() => {
    setUndecodable(false);
    setImageSize(null);
  }, [url]);
  useEffect(() => {
    onGeometry({ image: imageSize, stage, url: undecodable ? null : url });
  }, [imageSize, onGeometry, stage, undecodable, url]);

  const ready = Boolean(url && imageSize && stage.width && stage.height && !undecodable);
  const current = ready ? viewport ?? fitViewport(imageSize!, stage) : null;
  const latest = useRef({ current, imageSize, stage, onViewportChange });
  latest.current = { current, imageSize, stage, onViewportChange };

  // La rueda necesita un listener no pasivo para no desplazar la página.
  useEffect(() => {
    const element = ref.current;
    if (!element) return undefined;
    const onWheel = (event: WheelEvent) => {
      const state = latest.current;
      if (!state.current || !state.imageSize) return;
      event.preventDefault();
      const bounds = element.getBoundingClientRect();
      state.onViewportChange(zoomAt(
        state.current,
        Math.exp(-event.deltaY * 0.0016),
        { x: event.clientX - bounds.left, y: event.clientY - bounds.top },
        state.imageSize,
        state.stage,
      ));
    };
    element.addEventListener('wheel', onWheel, { passive: false });
    return () => element.removeEventListener('wheel', onWheel);
  }, [ref]);

  const pointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!current || event.button !== 0) return;
    drag.current = { x: event.clientX, y: event.clientY, moved: false };
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const pointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const state = drag.current;
    if (!state || !current || !imageSize) return;
    const dx = event.clientX - state.x;
    const dy = event.clientY - state.y;
    if (!state.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
    drag.current = { x: event.clientX, y: event.clientY, moved: true };
    onViewportChange(panBy(current, dx, dy, imageSize));
  };
  const pointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    const state = drag.current;
    drag.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (!state || state.moved || !showCells) return;
    // Clic sin arrastre: selecciona la célula bajo el cursor.
    const target = document.elementFromPoint(event.clientX, event.clientY);
    const id = target instanceof SVGElement ? target.getAttribute('data-detection') : null;
    const cell = id ? cells.find((item) => item.detectionId === id) : null;
    if (cell) onSelectCell(cell);
  };
  const keyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!current || !imageSize) return;
    const center = { x: stage.width / 2, y: stage.height / 2 };
    const actions: Record<string, () => ViewportState | null> = {
      ArrowLeft: () => panBy(current, KEY_PAN, 0, imageSize),
      ArrowRight: () => panBy(current, -KEY_PAN, 0, imageSize),
      ArrowUp: () => panBy(current, 0, KEY_PAN, imageSize),
      ArrowDown: () => panBy(current, 0, -KEY_PAN, imageSize),
      '+': () => zoomAt(current, 1.25, center, imageSize, stage),
      '=': () => zoomAt(current, 1.25, center, imageSize, stage),
      '-': () => zoomAt(current, 0.8, center, imageSize, stage),
      0: () => null,
      r: () => rotateBy(current, 90),
    };
    const action = actions[event.key];
    if (!action) return;
    event.preventDefault();
    onViewportChange(action());
  };

  const filters = [
    optics.gamma !== 1 ? `url(#${filterId})` : '',
    optics.brightness !== 100 ? `brightness(${optics.brightness}%)` : '',
    optics.contrast !== 100 ? `contrast(${optics.contrast}%)` : '',
    optics.saturation !== 100 ? `saturate(${optics.saturation}%)` : '',
  ].filter(Boolean).join(' ');
  const name = image?.name ?? 'imagen incorporada';

  return (
    <div
      ref={ref}
      className="frotis-v3-viewport"
      data-scanning={scanning ? 'true' : 'false'}
      data-contour={contour}
      data-interactive={current ? 'true' : 'false'}
      tabIndex={0}
      role="application"
      aria-label={`Visor del frotis: ${name}. Flechas desplazan, más y menos cambian el zoom, cero ajusta a pantalla, R rota.`}
      onPointerDown={pointerDown}
      onPointerMove={pointerMove}
      onPointerUp={pointerUp}
      onPointerCancel={pointerUp}
      onKeyDown={keyDown}
    >
      {optics.gamma !== 1 ? (
        <svg className="frotis-v3-filter-defs" aria-hidden="true" focusable="false">
          <filter id={filterId} colorInterpolationFilters="sRGB">
            <feComponentTransfer>
              <feFuncR type="gamma" exponent={1 / optics.gamma} />
              <feFuncG type="gamma" exponent={1 / optics.gamma} />
              <feFuncB type="gamma" exponent={1 / optics.gamma} />
            </feComponentTransfer>
          </filter>
        </svg>
      ) : null}

      {url && !undecodable ? (
        <div
          className="frotis-v3-world"
          style={current && imageSize ? {
            width: imageSize.width,
            height: imageSize.height,
            transform: `rotate(${current.rotation}deg) scale(${current.scale}) translate(${-current.cx}px, ${-current.cy}px)`,
          } : { visibility: 'hidden' }}
        >
          <img
            className="frotis-v3-smear"
            src={url}
            alt={`Frotis: ${name}`}
            draggable={false}
            style={filters ? { filter: filters } : undefined}
            onLoad={(event) => setImageSize({
              width: event.currentTarget.naturalWidth,
              height: event.currentTarget.naturalHeight,
            })}
            onError={() => setUndecodable(true)}
          />
          {showCells && imageSize && cells.length ? (
            <svg
              className="frotis-v3-cells"
              viewBox={`0 0 ${imageSize.width} ${imageSize.height}`}
              aria-label={`${cells.length} células detectadas en esta imagen`}
            >
              {cells.map((cell) => {
                const kind = cellKind(cell);
                return (
                  <rect
                    key={cell.detectionId}
                    data-detection={cell.detectionId}
                    data-kind={kind}
                    data-near={cell.prediction?.nearThreshold ? 'true' : undefined}
                    data-selected={cell.detectionId === selectedDetectionId ? 'true' : undefined}
                    x={cell.bbox.x}
                    y={cell.bbox.y}
                    width={cell.bbox.width}
                    height={cell.bbox.height}
                  >
                    <title>{`${cell.cellCode} · ${KIND_LABEL[kind]}`}</title>
                  </rect>
                );
              })}
            </svg>
          ) : null}
        </div>
      ) : null}

      {url && undecodable ? (
        <div className="frotis-v3-viewport-message" role="status">
          <ImageOff aria-hidden="true" />
          <strong>El navegador no puede mostrar este formato</strong>
          <span>
            {name} se conserva sin cambios para el análisis; la visualización de este formato
            aún no está soportada en el microscopio.
          </span>
        </div>
      ) : null}

      {source.status === 'loading' ? (
        <div className="frotis-v3-viewport-message" role="status">
          <LoaderCircle className="frotis-v3-spin" aria-hidden="true" />
          <strong>Cargando imagen del frotis…</strong>
        </div>
      ) : null}

      {source.status === 'unavailable' ? (
        <div className="frotis-v3-viewport-message" role="alert">
          <ImageOff aria-hidden="true" />
          <strong>Imagen no disponible</strong>
          <span>{source.message}</span>
        </div>
      ) : null}

      {source.status === 'idle' && !url ? (
        <div className="frotis-v3-viewport-message" role="status">
          <ImageOff aria-hidden="true" />
          <strong>Este análisis no tiene imágenes disponibles</strong>
        </div>
      ) : null}

      {scanning ? (
        <div className="frotis-v3-scan" role="status" aria-live="polite">
          <span className="frotis-v3-scanline" aria-hidden="true" />
          <span className="frotis-v3-scan-label">{scanLabel}</span>
        </div>
      ) : null}
    </div>
  );
}
