import {
  Circle,
  CircleCheck,
  LoaderCircle,
  Microscope,
  OctagonAlert,
  SlidersHorizontal,
  Sparkles,
  TriangleAlert,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';

import { buildShareableUrl, routes, withAllowedQuery } from '../../../router';
import { api } from '../../../services/api';
import type { MicroscopeAnalysis } from '../adapters/analysisModel';
import { filterCells, type MicroscopeCell } from '../adapters/cellLayer';
import { useCellLayer } from '../hooks/useCellLayer';
import { useReportFindings, type ReportFinding } from '../hooks/useReportFindings';
import { useViewportFill } from '../hooks/useViewportFill';
import { MICROSCOPE_VIEWS, type MicroscopeViewId } from '../routes';
import { computeFloatingLayout, type FloatingRequest } from '../state/floatingLayout';
import {
  readPreferences,
  writePreferences,
  type WorkspacePreferences,
} from '../state/presentationStorage';
import {
  centerOn,
  fitScale,
  fitViewport,
  focusRegion,
  rotateBy,
  setScale,
  visibleQuad,
  zoomAt,
  type ViewportState,
} from '../state/viewportMath';
import { CellInspector } from './CellInspector';
import { Minimap } from './Minimap';
import { ReportView } from './ReportView';
import { SmearViewport, type ViewportGeometry } from './SmearViewport';
import { AiPanel } from './panels/AiPanel';
import { FloatingPanel } from './panels/FloatingPanel';
import { OpticsPanel } from './panels/OpticsPanel';

export type WorkspaceTone = 'idle' | 'progress' | 'ok' | 'warning' | 'blocked';
export type WorkspaceNotice = { id: string; tone: 'info' | 'warning' | 'blocked'; text: string };
export type CellSelection = { detectionId: string | null; predictionId: string | null };

const TONE_ICON: Record<WorkspaceTone, typeof Circle> = {
  idle: Circle,
  progress: LoaderCircle,
  ok: CircleCheck,
  warning: TriangleAlert,
  blocked: OctagonAlert,
};

const NO_SELECTION: CellSelection = { detectionId: null, predictionId: null };
const EMPTY_GEOMETRY: ViewportGeometry = { image: null, stage: { width: 0, height: 0 }, url: null };
const PANEL_WIDTH = { notices: 400, optics: 264, minimap: 188, actions: 320, ai: 280 } as const;

const count = (value: number, singular: string, plural: string) =>
  `${value.toLocaleString('es-CL')} ${value === 1 ? singular : plural}`;

/**
 * Workspace único del Microscopio Digital. Carga, revisión técnica y
 * microscopio son estados del mismo instrumento: el contenedor, el header y
 * el viewport permanecen montados entre ellos y entre las tres vistas.
 */
export function MicroscopeWorkspace({
  analysis,
  status,
  takeover = null,
  activeImageId = null,
  onImageSelect,
  localPreview = null,
  scanning = false,
  notices = [],
  actions = null,
  headerActions = null,
  selection = NO_SELECTION,
  onSelectCell,
}: {
  analysis: MicroscopeAnalysis | null;
  status: { label: string; tone: WorkspaceTone };
  /** Ocupa el lugar del viewport: carga de imágenes, recuperación o análisis no disponible. */
  takeover?: ReactNode;
  activeImageId?: string | null;
  onImageSelect?: (imageId: string) => void;
  /** Vista previa local del archivo recién incorporado y la imagen a la que corresponde. */
  localPreview?: { imageId: string | null; url: string } | null;
  scanning?: boolean;
  notices?: WorkspaceNotice[];
  actions?: ReactNode;
  headerActions?: ReactNode;
  /** Célula seleccionada según el contexto de la sesión (URL). */
  selection?: CellSelection;
  onSelectCell?: (selection: CellSelection) => void;
}) {
  const { ref, height } = useViewportFill<HTMLElement>();
  const [searchParams] = useSearchParams();
  const datasource = searchParams.get('datasource');
  const images = analysis?.images ?? [];
  const activeIndex = images.findIndex((image) => image.id === activeImageId);
  const activeImage = activeIndex >= 0 ? images[activeIndex] : images[0] ?? null;
  const localUrl = localPreview && (!activeImage || localPreview.imageId === activeImage.id || localPreview.imageId === null)
    ? localPreview.url
    : null;
  const StatusIcon = TONE_ICON[status.tone];
  const classification = analysis?.classification ?? null;
  const showingSmear = Boolean(analysis) && !takeover;

  // ---- Preferencias de presentación (namespace propio de v3)
  const [preferences, setPreferences] = useState<WorkspacePreferences>(readPreferences);
  const update = useCallback((patch: Partial<WorkspacePreferences>) => {
    setPreferences((current) => {
      const next = { ...current, ...patch };
      writePreferences(next);
      return next;
    });
  }, []);
  const { optics, layers, panels } = preferences;

  // ---- Vistas: una vista sin datos reales se declara no disponible
  const viewAvailability: Record<MicroscopeViewId, string | null> = {
    'full-field': null,
    'review-cells': !showingSmear
      ? 'Disponible cuando haya un frotis en el visor'
      : analysis?.detection ? null : 'Disponible cuando exista detección celular',
    report: showingSmear ? null : 'Disponible cuando haya un análisis abierto',
  };
  const view: MicroscopeViewId = viewAvailability[preferences.view] ? 'full-field' : preferences.view;

  // ---- Visor
  const [viewport, setViewport] = useState<ViewportState | null>(null);
  const [geometry, setGeometry] = useState<ViewportGeometry>(EMPTY_GEOMETRY);
  const imageKey = activeImage?.id ?? null;
  useEffect(() => setViewport(null), [imageKey]);
  const { image: imageSize, stage } = geometry;
  const visible = Boolean(imageSize && stage.width && stage.height && geometry.url);
  const effective = visible ? viewport ?? fitViewport(imageSize!, stage) : null;
  const change = (compute: (current: ViewportState) => ViewportState) => {
    if (effective) setViewport(compute(effective));
  };
  const stageCenter = { x: stage.width / 2, y: stage.height / 2 };

  // ---- Capa celular real de la imagen activa
  const { state: layer } = useCellLayer(
    showingSmear ? analysis?.detection?.runId ?? null : null,
    showingSmear ? classification?.runId ?? null : null,
    showingSmear ? imageKey : null,
  );
  const shownCells = useMemo(() => filterCells(layer.cells, layers.filter), [layer.cells, layers.filter]);
  const selected = layer.cells.find((cell) => cell.detectionId === selection.detectionId)
    ?? (selection.predictionId && !selection.detectionId
      ? layer.cells.find((cell) => cell.prediction?.id === selection.predictionId)
      : undefined)
    ?? null;

  // Una selección pedida desde fuera del visor (enlace, inspector, reporte) se centra una vez.
  const pendingFocus = useRef<string | null>(selection.detectionId ?? selection.predictionId);
  useEffect(() => {
    if (!selected || !effective || !imageSize) return;
    const wanted = pendingFocus.current;
    if (wanted !== selected.detectionId && wanted !== selected.prediction?.id) return;
    pendingFocus.current = null;
    setViewport(focusRegion(effective, selected.bbox, imageSize, stage));
  }, [effective, imageSize, selected, stage]);

  const select = useCallback((cell: MicroscopeCell, focus: boolean) => {
    if (focus) pendingFocus.current = cell.detectionId;
    onSelectCell?.({ detectionId: cell.detectionId, predictionId: cell.prediction?.id ?? null });
  }, [onSelectCell]);

  // ---- Validación de pertenencia de un enlace profundo a detección o predicción
  const [linkIssue, setLinkIssue] = useState<string | null>(null);
  const resolved = useRef('');
  const imageIds = useMemo(() => images.map((image) => image.id), [images]);
  const classificationRunId = classification?.runId ?? null;
  useEffect(() => {
    const wanted = selection.detectionId ?? selection.predictionId;
    if (!wanted || layer.status !== 'ready' || !showingSmear) return;
    if (selected) {
      // Un enlace solo con predicción se completa con su detección real.
      if (!selection.detectionId) onSelectCell?.({ detectionId: selected.detectionId, predictionId: selected.prediction?.id ?? null });
      return;
    }
    const key = `${wanted}@${imageKey}`;
    if (resolved.current === key) return;
    resolved.current = key;
    let active = true;
    const locate = selection.detectionId
      ? api.getCellDetection(selection.detectionId).then((detection) => ({
        imageId: detection.microscopy_image_id ?? detection.source_image?.microscopy_image_id ?? null,
        detectionId: detection.id,
        foreign: false,
      }))
      : api.getCellPrediction(selection.predictionId!).then((prediction) => ({
        imageId: prediction.microscopy_image_id,
        detectionId: prediction.cell_detection_id,
        foreign: prediction.classification_run_id !== classificationRunId,
      }));
    locate.then((found) => {
      if (!active) return;
      if (!found.foreign && found.imageId && found.imageId !== imageKey && imageIds.includes(found.imageId)) {
        // Cambiar de imagen limpia la selección: se vuelve a fijar la célula localizada.
        pendingFocus.current = found.detectionId;
        onImageSelect?.(found.imageId);
        onSelectCell?.({ detectionId: found.detectionId, predictionId: selection.predictionId });
        return;
      }
      setLinkIssue('La célula indicada en el enlace no pertenece a este análisis; no se seleccionó ninguna.');
    }).catch(() => {
      if (active) setLinkIssue('La célula indicada en el enlace no existe o no es accesible; no se seleccionó ninguna.');
    });
    return () => {
      active = false;
    };
  }, [classificationRunId, imageIds, imageKey, layer.status, onImageSelect, onSelectCell, selected, selection.detectionId, selection.predictionId, showingSmear]);
  useEffect(() => {
    if (selected || !(selection.detectionId ?? selection.predictionId)) setLinkIssue(null);
  }, [selected, selection.detectionId, selection.predictionId]);

  // ---- Reporte
  const findings = useReportFindings(classificationRunId, view === 'report' && showingSmear);
  const openFinding = (finding: ReportFinding) => {
    pendingFocus.current = finding.detectionId;
    if (finding.imageId !== imageKey) onImageSelect?.(finding.imageId);
    onSelectCell?.({ detectionId: finding.detectionId, predictionId: finding.predictionId });
    update({ view: analysis?.detection ? 'review-cells' : 'full-field', layers: { ...layers, cells: true, filter: 'all' } });
  };

  // ---- Enlaces del hallazgo seleccionado
  const linkQuery = {
    datasource,
    image: imageKey,
    selected_detection: selected?.detectionId ?? null,
    selected_prediction: selected?.prediction?.id ?? null,
  };
  const shareUrl = selected && analysis?.analysisRunId
    ? buildShareableUrl(routes.smearMicroscopeAnalysis(analysis.analysisRunId), linkQuery)
    : null;
  const reviewHref = selected && analysis?.analysisRunId
    ? withAllowedQuery(routes.smearHistoryDetail(analysis.analysisRunId), linkQuery)
    : null;

  // ---- Layout Manager de instrumentos flotantes
  const allNotices = linkIssue ? [...notices, { id: 'cell-link', tone: 'warning' as const, text: linkIssue }] : notices;
  const floatingVisible = view !== 'report';
  const showMinimap = floatingVisible && showingSmear && layers.minimap && Boolean(effective && geometry.url);
  const [heights, setHeights] = useState<Record<string, number>>({});
  const measure = useCallback((id: string, value: number) => {
    setHeights((current) => (current[id] === value ? current : { ...current, [id]: value }));
  }, []);
  const requests: FloatingRequest[] = [];
  const request = (id: keyof typeof PANEL_WIDTH, side: 'left' | 'right', anchor: 'top' | 'bottom' = 'top') => {
    requests.push({ id, side, anchor, width: PANEL_WIDTH[id], height: heights[id] ?? 120 });
  };
  if (floatingVisible && allNotices.length) request('notices', 'left');
  if (floatingVisible && showingSmear && panels.optics) request('optics', 'left');
  if (showMinimap) request('minimap', 'left', 'bottom');
  if (floatingVisible && actions) request('actions', 'right');
  if (floatingVisible && showingSmear && panels.ai) request('ai', 'right');
  // La capa flotante solo existe cuando hay un frotis en el visor (no durante la
  // carga o la recuperación): se observa el elemento cada vez que se monta.
  const [layerSize, setLayerSize] = useState({ width: 0, height: 0 });
  const [layerElement, setLayerElement] = useState<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!layerElement) return undefined;
    const measureLayer = () => {
      setLayerSize((current) => (
        current.width === layerElement.clientWidth && current.height === layerElement.clientHeight
          ? current
          : { width: layerElement.clientWidth, height: layerElement.clientHeight }
      ));
    };
    measureLayer();
    if (typeof ResizeObserver !== 'function') return undefined;
    const observer = new ResizeObserver(measureLayer);
    observer.observe(layerElement);
    return () => observer.disconnect();
  }, [layerElement]);
  const placements = computeFloatingLayout({
    stage: layerSize,
    // La etiqueta de la línea de escaneo ocupa la franja inferior mientras hay procesamiento.
    reserved: { bottom: scanning ? 44 : 0 },
    panels: requests,
  });
  const placementOf = (id: string) => placements.find((placement) => placement.id === id);

  const zoomPercent = effective ? effective.scale * 100 : null;
  const fitted = Boolean(effective && imageSize
    && Math.abs(effective.scale - fitScale(imageSize, stage, effective.rotation)) < 1e-6
    && Math.abs(effective.cx - imageSize.width / 2) < 0.5
    && Math.abs(effective.cy - imageSize.height / 2) < 0.5);

  return (
    <section
      ref={ref}
      className="frotis-v3"
      data-phase={takeover ? 'takeover' : analysis?.phase ?? 'empty'}
      data-view={view}
      style={height ? { height: `${height}px` } : undefined}
      aria-label="Microscopio Digital"
    >
      <header className="frotis-v3-header">
        <div className="frotis-v3-identity">
          <Microscope className="frotis-v3-identity-mark" aria-hidden="true" />
          <h1>Microscopio Digital</h1>
          {analysis ? (
            <dl className="frotis-v3-case">
              {analysis.runCode ? <div><dt>Análisis</dt><dd>{analysis.runCode}</dd></div> : null}
              {analysis.subjectCode ? <div><dt>Paciente</dt><dd>{analysis.subjectCode}</dd></div> : null}
              {analysis.sampleCode ? <div><dt>Muestra</dt><dd>{analysis.sampleCode}</dd></div> : null}
              {analysis.slideCode ? <div><dt>Frotis</dt><dd>{analysis.slideCode}</dd></div> : null}
            </dl>
          ) : null}
        </div>

        <nav className="frotis-v3-views" aria-label="Vistas del microscopio">
          {MICROSCOPE_VIEWS.map((item) => {
            const reason = viewAvailability[item.id];
            return (
              <button
                key={item.id}
                type="button"
                className="frotis-v3-view"
                aria-current={item.id === view ? 'page' : undefined}
                aria-disabled={reason ? 'true' : undefined}
                title={reason ?? undefined}
                onClick={() => { if (!reason) update({ view: item.id }); }}
              >
                {item.label}
                {reason ? <span className="frotis-v3-visually-hidden"> ({reason})</span> : null}
              </button>
            );
          })}
        </nav>

        <div className="frotis-v3-header-tools">
          {([
            ['optics', 'Imagen y Óptica', SlidersHorizontal],
            ['ai', 'IA y Revisión', Sparkles],
          ] as const).map(([id, label, Icon]) => {
            const usable = showingSmear && floatingVisible;
            return (
              <button
                key={id}
                type="button"
                className="frotis-v3-instrument-toggle"
                aria-pressed={usable && panels[id]}
                aria-disabled={usable ? undefined : 'true'}
                aria-label={`Mostrar u ocultar ${label}`}
                title={usable ? label : `${label}: disponible con un frotis en el visor`}
                onClick={() => { if (usable) update({ panels: { ...panels, [id]: !panels[id] } }); }}
              >
                <Icon aria-hidden="true" />
              </button>
            );
          })}
          <span className="frotis-v3-status" data-tone={status.tone} role="status">
            <StatusIcon className={status.tone === 'progress' ? 'frotis-v3-spin' : undefined} aria-hidden="true" />
            {status.label}
          </span>
          {headerActions}
        </div>
      </header>

      <div className="frotis-v3-stage">
        {takeover}

        {showingSmear ? (
          // El visor permanece montado en REPORT: solo se oculta, para conservar su estado.
          <div className="frotis-v3-optical" hidden={view === 'report'}>
            <SmearViewport
              image={activeImage}
              localUrl={localUrl}
              scanning={scanning}
              scanLabel={status.label}
              viewport={viewport}
              onViewportChange={setViewport}
              onGeometry={setGeometry}
              optics={optics}
              cells={shownCells}
              showCells={layers.cells}
              contour={layers.contour}
              selectedDetectionId={selected?.detectionId ?? null}
              onSelectCell={(cell) => select(cell, false)}
            />
            <div ref={setLayerElement} className="frotis-v3-floating-layer">
              {floatingVisible && allNotices.length ? (
                <FloatingPanel id="notices" placement={placementOf('notices')} onMeasure={measure}>
                  <ul className="frotis-v3-notices">
                    {allNotices.map((notice) => (
                      <li key={notice.id} data-tone={notice.tone} role={notice.tone === 'info' ? 'status' : 'alert'}>
                        {notice.tone === 'info' ? null : <TriangleAlert aria-hidden="true" />}
                        <span>{notice.text}</span>
                      </li>
                    ))}
                  </ul>
                </FloatingPanel>
              ) : null}
              {floatingVisible && panels.optics ? (
                <FloatingPanel
                  id="optics"
                  title="Imagen y Óptica"
                  placement={placementOf('optics')}
                  onMeasure={measure}
                  onClose={() => update({ panels: { ...panels, optics: false } })}
                >
                  <OpticsPanel
                    available={Boolean(effective)}
                    zoomPercent={zoomPercent}
                    rotation={effective?.rotation ?? 0}
                    fitted={fitted}
                    optics={optics}
                    minimap={layers.minimap}
                    onZoom={(factor) => change((current) => zoomAt(current, factor, stageCenter, imageSize!, stage))}
                    onFit={() => setViewport(effective && effective.rotation ? fitViewport(imageSize!, stage, effective.rotation) : null)}
                    onActualSize={() => change((current) => setScale(current, 1, imageSize!, stage))}
                    onRotate={(delta) => change((current) => {
                      const rotated = rotateBy(current, delta);
                      return viewport ? rotated : fitViewport(imageSize!, stage, rotated.rotation);
                    })}
                    onOpticsChange={(next) => update({ optics: next })}
                    onMinimapChange={(value) => update({ layers: { ...layers, minimap: value } })}
                  />
                </FloatingPanel>
              ) : null}
              {showMinimap && effective && imageSize && geometry.url ? (
                <FloatingPanel id="minimap" placement={placementOf('minimap')} onMeasure={measure}>
                  <Minimap
                    url={geometry.url}
                    image={imageSize}
                    quad={visibleQuad(effective, stage)}
                    onCenter={(point) => change((current) => centerOn(current, point, imageSize))}
                  />
                </FloatingPanel>
              ) : null}
              {floatingVisible && actions ? (
                <FloatingPanel id="actions" placement={placementOf('actions')} onMeasure={measure}>
                  {actions}
                </FloatingPanel>
              ) : null}
              {floatingVisible && panels.ai ? (
                <FloatingPanel
                  id="ai"
                  title="IA y Revisión"
                  placement={placementOf('ai')}
                  onMeasure={measure}
                  onClose={() => update({ panels: { ...panels, ai: false } })}
                >
                  <AiPanel
                    layer={layer}
                    hasDetection={Boolean(analysis?.detection)}
                    layers={layers}
                    onLayersChange={(next) => update({ layers: next })}
                    onOpenReview={view === 'full-field' && analysis?.detection ? () => update({ view: 'review-cells' }) : null}
                  />
                </FloatingPanel>
              ) : null}
            </div>
          </div>
        ) : null}

        {showingSmear && view === 'review-cells' ? (
          <CellInspector
            layer={layer}
            cells={shownCells}
            filter={layers.filter}
            onFilterChange={(filter) => update({ layers: { ...layers, filter } })}
            selected={selected}
            onSelect={(cell) => select(cell, true)}
            onFocus={(cell) => change((current) => focusRegion(current, cell.bbox, imageSize!, stage))}
            shareUrl={shareUrl}
            reviewHref={reviewHref}
          />
        ) : null}

        {showingSmear && view === 'report' && analysis ? (
          <ReportView analysis={analysis} findings={findings} onOpenFinding={openFinding} />
        ) : null}

        {analysis && showingSmear && view !== 'report' ? (
          <footer className="frotis-v3-readout">
            {images.length > 1 ? (
              <nav className="frotis-v3-rail" aria-label="Imágenes del análisis">
                {images.map((image, index) => (
                  <button
                    key={image.id}
                    type="button"
                    aria-current={image.id === activeImage?.id ? 'true' : undefined}
                    aria-label={`Imagen ${index + 1} de ${images.length}: ${image.name}`}
                    title={image.name}
                    onClick={() => onImageSelect?.(image.id)}
                  >
                    {index + 1}
                  </button>
                ))}
              </nav>
            ) : null}
            <dl className="frotis-v3-facts">
              {activeImage ? (
                <div>
                  <dt>Imagen{images.length > 1 ? ` ${Math.max(activeIndex, 0) + 1} de ${images.length}` : ''}</dt>
                  <dd>
                    {activeImage.name}
                    {activeImage.widthPx && activeImage.heightPx
                      ? ` · ${activeImage.widthPx} × ${activeImage.heightPx} px`
                      : ''}
                  </dd>
                </div>
              ) : null}
              {zoomPercent != null ? <div><dt>Zoom digital</dt><dd>{Math.round(zoomPercent)} %</dd></div> : null}
              {analysis.detection ? (
                <div>
                  <dt>Detección</dt>
                  <dd>
                    {count(analysis.detection.detectionCount, 'célula detectada', 'células detectadas')}
                    {activeImage?.detectionCount != null && images.length > 1
                      ? ` (${activeImage.detectionCount.toLocaleString('es-CL')} en esta imagen)`
                      : ''}
                    {` · ${count(analysis.detection.pendingReviewCount, 'pendiente de revisión', 'pendientes de revisión')}`}
                  </dd>
                </div>
              ) : null}
              {classification && classification.classifiedCount != null ? (
                <div>
                  <dt>Clasificación{classification.modelName ? ` · ${classification.modelName}${classification.modelVersion ? ` ${classification.modelVersion}` : ''}` : ''}</dt>
                  <dd>
                    {count(classification.classifiedCount, 'célula clasificada', 'células clasificadas')}
                    {classification.parasitizedCandidateCount != null
                      ? ` · ${count(classification.parasitizedCandidateCount, 'candidata parasitada', 'candidatas parasitadas')}`
                      : ''}
                    {classification.nearThresholdCount
                      ? ` · ${count(classification.nearThresholdCount, 'cercana al umbral', 'cercanas al umbral')}`
                      : ''}
                  </dd>
                </div>
              ) : null}
            </dl>
            {analysis.detection ? (
              <p className="frotis-v3-disclaimer" role="note">
                Resultado experimental: requiere revisión experta y no constituye un diagnóstico clínico.
              </p>
            ) : null}
          </footer>
        ) : null}
      </div>
    </section>
  );
}
