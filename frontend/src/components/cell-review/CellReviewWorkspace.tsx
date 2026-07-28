import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { ApiError, api } from '../../services/api';
import type {
  CellDetectionDetail,
  CellDetectionImage,
  CellDetectionRunDetail,
  CellDetectionSummary,
  CellReviewCounts,
  CellReviewDecision,
  CellReviewFilter,
  CellReviewStatus,
  ScientificCellReview,
} from '../../types/cellReview';
import { AuthenticatedCropImage } from './AuthenticatedCellImage';
import { CellImageViewer } from './CellImageViewer';

const PAGE_SIZE = 100;

const reviewStatusLabel: Record<CellReviewStatus, string> = {
  unreviewed: 'Sin revisar',
  accepted: 'Aceptada',
  rejected: 'Rechazada',
  needs_attention: 'Requiere atención',
};

const filterLabel: Record<CellReviewFilter, string> = {
  all: 'Todas',
  ...reviewStatusLabel,
};

const reviewStatusSymbol: Record<CellReviewStatus, string> = {
  unreviewed: '○',
  accepted: '✓',
  rejected: '×',
  needs_attention: '!',
};

const reviewDecisionLabel: Record<CellReviewDecision, string> = {
  accepted: 'Aceptada',
  rejected: 'Rechazada',
  needs_attention: 'Requiere atención',
  comment_only: 'Comentario',
};

const emptyCounts: CellReviewCounts = {
  unreviewed: 0,
  accepted: 0,
  rejected: 0,
  needs_attention: 0,
};

const safeDate = (value: string | null | undefined) => {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleString();
};

const optionalMetric = (value: number | null | undefined, digits = 4) =>
  value == null ? '—' : value.toFixed(digits);

const runCounts = (run: CellDetectionRunDetail | null): CellReviewCounts => ({
  ...emptyCounts,
  ...(run?.review_counts ?? {}),
  unreviewed:
    run?.review_counts?.unreviewed
    ?? run?.review_counts?.pending
    ?? run?.pending_review_count
    ?? 0,
});

type MobileTab = 'summary' | 'cells' | 'image' | 'detail';

type CellReviewWorkspaceProps = {
  detectionRunId: string;
  canReview: boolean;
  onClose: () => void;
  closeLabel?: string;
  initialMicroscopyImageId?: string | null;
  onMicroscopyImageChange?: (microscopyImageId: string | null) => void;
  initialSelectedDetectionId?: string | null;
  onSelectedDetectionChange?: (detectionId: string | null) => void;
};

export function CellReviewWorkspace({
  detectionRunId,
  canReview,
  onClose,
  closeLabel = 'Volver a ejecuciones',
  initialMicroscopyImageId = null,
  onMicroscopyImageChange,
  initialSelectedDetectionId = null,
  onSelectedDetectionChange,
}: CellReviewWorkspaceProps) {
  const [run, setRun] = useState<CellDetectionRunDetail | null>(null);
  const [images, setImages] = useState<CellDetectionImage[]>([]);
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [filter, setFilter] = useState<CellReviewFilter>('all');
  const [detections, setDetections] = useState<CellDetectionSummary[]>([]);
  const [overlayDetections, setOverlayDetections] = useState<CellDetectionSummary[]>([]);
  const [detectionTotal, setDetectionTotal] = useState(0);
  const [galleryOffset, setGalleryOffset] = useState(0);
  const [selectedDetectionId, setSelectedDetectionId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<CellDetectionDetail | null>(null);
  const [reviewHistory, setReviewHistory] = useState<ScientificCellReview[]>([]);
  const [workspaceLoading, setWorkspaceLoading] = useState(true);
  const [galleryLoading, setGalleryLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [workspaceError, setWorkspaceError] = useState('');
  const [galleryError, setGalleryError] = useState('');
  const [detailError, setDetailError] = useState('');
  const [reviewError, setReviewError] = useState('');
  const [reviewComment, setReviewComment] = useState('');
  const [reviewSaving, setReviewSaving] = useState(false);
  const [liveMessage, setLiveMessage] = useState('');
  const [focusRequest, setFocusRequest] = useState(0);
  const [summaryCollapsed, setSummaryCollapsed] = useState(false);
  const [mobileTab, setMobileTab] = useState<MobileTab>('image');
  const [selectionResolved, setSelectionResolved] = useState(false);
  const cardRefs = useRef(new Map<string, HTMLButtonElement>());
  const galleryRequest = useRef(0);
  const selectFirstUnreviewed = useRef(false);
  const selectedDetectionIdRef = useRef<string | null>(null);
  const pendingInitialSelection = useRef<string | null>(initialSelectedDetectionId);
  const pendingInitialImage = useRef<string | null>(initialMicroscopyImageId);
  const initialSelectionAttempted = useRef(false);
  const selectionDetectionRunId = useRef(detectionRunId);
  const lastNotifiedImage = useRef<string | null | undefined>(undefined);
  const lastNotifiedSelection = useRef<string | null | undefined>(undefined);

  const commitSelectedDetectionId = useCallback((detectionId: string | null) => {
    selectedDetectionIdRef.current = detectionId;
    setSelectedDetectionId(detectionId);
  }, []);

  useEffect(() => {
    if (selectionDetectionRunId.current === detectionRunId) {
      if (!initialSelectionAttempted.current && !selectionResolved) {
        pendingInitialSelection.current = initialSelectedDetectionId;
      }
      return;
    }
    selectionDetectionRunId.current = detectionRunId;
    pendingInitialImage.current = initialMicroscopyImageId;
    pendingInitialSelection.current = initialSelectedDetectionId;
    initialSelectionAttempted.current = false;
    lastNotifiedImage.current = undefined;
    lastNotifiedSelection.current = undefined;
    setSelectionResolved(false);
    commitSelectedDetectionId(null);
  }, [
    commitSelectedDetectionId,
    detectionRunId,
    initialMicroscopyImageId,
    initialSelectedDetectionId,
    selectionResolved,
  ]);

  useEffect(() => {
    if (workspaceLoading || !onMicroscopyImageChange) return;
    if (lastNotifiedImage.current === selectedImageId) return;
    lastNotifiedImage.current = selectedImageId;
    onMicroscopyImageChange(selectedImageId);
  }, [
    onMicroscopyImageChange,
    selectedImageId,
    workspaceLoading,
  ]);

  useEffect(() => {
    if (!selectionResolved || !onSelectedDetectionChange) return;
    if (lastNotifiedSelection.current === selectedDetectionId) return;
    lastNotifiedSelection.current = selectedDetectionId;
    onSelectedDetectionChange(selectedDetectionId);
  }, [onSelectedDetectionChange, selectedDetectionId, selectionResolved]);

  const selectedImage = useMemo(
    () => images.find((item) => item.microscopy_image_id === selectedImageId) ?? null,
    [images, selectedImageId],
  );
  const selectedDetection = useMemo(
    () => detections.find((item) => item.id === selectedDetectionId) ?? null,
    [detections, selectedDetectionId],
  );
  const counts = runCounts(run);

  const loadWorkspace = useCallback(async () => {
    setWorkspaceLoading(true);
    setWorkspaceError('');
    try {
      const [nextRun, imagePage] = await Promise.all([
        api.getCellDetectionRun(detectionRunId),
        api.getCellDetectionImages(detectionRunId),
      ]);
      setRun(nextRun);
      setImages(imagePage.items);
      setSelectedImageId((current) => (
        imagePage.items.some((item) => item.microscopy_image_id === current)
          ? current
          : imagePage.items.some(
            (item) => item.microscopy_image_id === pendingInitialImage.current,
          )
            ? pendingInitialImage.current
            : imagePage.items[0]?.microscopy_image_id ?? null
      ));
    } catch {
      setWorkspaceError('No fue posible cargar esta ejecución de detección.');
    } finally {
      setWorkspaceLoading(false);
    }
  }, [detectionRunId]);

  useEffect(() => {
    void loadWorkspace();
  }, [loadWorkspace]);

  useEffect(() => {
    if (workspaceLoading) return;
    if (!selectedImageId) {
      setDetections([]);
      setOverlayDetections([]);
      setDetectionTotal(0);
      setGalleryOffset(0);
      commitSelectedDetectionId(null);
      setSelectionResolved(true);
      return;
    }
    const requestId = ++galleryRequest.current;
    setGalleryLoading(true);
    setGalleryError('');
    setSelectionResolved(false);
    const query = { review_status: filter === 'all' ? undefined : filter };
    Promise.all([
      api.getCellDetections(detectionRunId, selectedImageId, {
        ...query,
        limit: PAGE_SIZE,
        offset: 0,
      }),
      api.getCellDetections(detectionRunId, selectedImageId, {
        ...query,
        limit: 500,
        offset: 0,
      }),
    ])
      .then(([page, overlayPage]) => {
        if (galleryRequest.current !== requestId) return;
        setDetections(page.items);
        setOverlayDetections(overlayPage.items);
        setDetectionTotal(page.total);
        setGalleryOffset(page.items.length);
        const selectRequestedFirst = selectFirstUnreviewed.current;
        selectFirstUnreviewed.current = false;
        const initialCandidate = initialSelectionAttempted.current
          ? null
          : pendingInitialSelection.current;
        initialSelectionAttempted.current = true;
        pendingInitialSelection.current = null;
        const nextSelection = selectRequestedFirst
          ? page.items[0]?.id ?? null
          : initialCandidate && overlayPage.items.some((item) => item.id === initialCandidate)
            ? initialCandidate
            : overlayPage.items.some((item) => item.id === selectedDetectionIdRef.current)
              ? selectedDetectionIdRef.current
              : page.items[0]?.id ?? null;
        commitSelectedDetectionId(nextSelection);
        setSelectionResolved(true);
        if (selectRequestedFirst && page.items[0]) {
          setFocusRequest((value) => value + 1);
        }
      })
      .catch(() => {
        if (galleryRequest.current !== requestId) return;
        setGalleryError('No fue posible cargar las detecciones de esta imagen.');
        setDetections([]);
        setOverlayDetections([]);
        setDetectionTotal(0);
        setGalleryOffset(0);
        commitSelectedDetectionId(null);
        setSelectionResolved(true);
      })
      .finally(() => {
        if (galleryRequest.current === requestId) setGalleryLoading(false);
      });
  }, [
    commitSelectedDetectionId,
    detectionRunId,
    filter,
    selectedImageId,
    workspaceLoading,
  ]);

  useEffect(() => {
    if (!selectedDetectionId) {
      setSelectedDetail(null);
      setReviewHistory([]);
      setDetailError('');
      return;
    }
    let active = true;
    setDetailLoading(true);
    setDetailError('');
    Promise.all([
      api.getCellDetection(selectedDetectionId),
      api.getCellReviews(selectedDetectionId),
    ])
      .then(([detail, reviews]) => {
        if (!active) return;
        setSelectedDetail(detail);
        setReviewHistory(reviews.items);
      })
      .catch(() => {
        if (active) setDetailError('No fue posible cargar el detalle o su historial.');
      })
      .finally(() => {
        if (active) setDetailLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedDetectionId]);

  useEffect(() => {
    setReviewComment('');
    setReviewError('');
  }, [selectedDetectionId]);

  useEffect(() => {
    if (!selectedDetectionId) return;
    window.requestAnimationFrame(() => {
      cardRefs.current.get(selectedDetectionId)?.scrollIntoView({
        block: 'nearest',
        inline: 'nearest',
      });
    });
  }, [selectedDetectionId]);

  function selectDetection(detection: CellDetectionSummary, focusViewer: boolean) {
    setDetections((items) => (
      items.some((item) => item.id === detection.id)
        ? items
        : [...items, detection].sort((left, right) => left.cell_index - right.cell_index)
    ));
    commitSelectedDetectionId(detection.id);
    if (focusViewer) {
      setFocusRequest((value) => value + 1);
      setMobileTab('image');
    }
  }

  async function loadMore(selectFirstNew = false) {
    if (!selectedImageId || galleryLoading || galleryOffset >= detectionTotal) return;
    setGalleryLoading(true);
    setGalleryError('');
    try {
      const page = await api.getCellDetections(detectionRunId, selectedImageId, {
        review_status: filter === 'all' ? undefined : filter,
        limit: PAGE_SIZE,
        offset: galleryOffset,
      });
      setDetections((current) => {
        const ids = new Set(current.map((item) => item.id));
        return [...current, ...page.items.filter((item) => !ids.has(item.id))]
          .sort((left, right) => left.cell_index - right.cell_index);
      });
      setGalleryOffset((current) => current + page.items.length);
      setDetectionTotal(page.total);
      if (selectFirstNew && page.items[0]) selectDetection(page.items[0], true);
    } catch {
      setGalleryError('No fue posible cargar más detecciones.');
    } finally {
      setGalleryLoading(false);
    }
  }

  function selectRelative(direction: -1 | 1) {
    if (!detections.length) return;
    const currentIndex = detections.findIndex((item) => item.id === selectedDetectionId);
    if (direction === 1 && currentIndex === detections.length - 1 && detections.length < detectionTotal) {
      void loadMore(true);
      return;
    }
    const nextIndex = currentIndex < 0
      ? 0
      : (currentIndex + direction + detections.length) % detections.length;
    selectDetection(detections[nextIndex], true);
  }

  function nextUnreviewed() {
    const currentIndex = detections.findIndex((item) => item.id === selectedDetectionId);
    const ordered = [
      ...detections.slice(Math.max(0, currentIndex + 1)),
      ...detections.slice(0, Math.max(0, currentIndex + 1)),
    ];
    const next = ordered.find((item) => (
      item.review_status === 'unreviewed' && item.id !== selectedDetectionId
    ));
    if (next) {
      selectDetection(next, true);
      return;
    }
    if (filter !== 'unreviewed') {
      selectFirstUnreviewed.current = true;
      setFilter('unreviewed');
      return;
    }
    if (galleryOffset < detectionTotal) {
      void loadMore(true);
      return;
    }
    setLiveMessage('No quedan detecciones sin revisar en esta imagen.');
  }

  async function submitReview(decision: CellReviewDecision) {
    const reviewTarget = selectedDetail ?? selectedDetection;
    if (!reviewTarget || !canReview) return;
    const comment = reviewComment.trim();
    if (decision !== 'accepted' && !comment) {
      setReviewError('Esta decisión requiere un comentario.');
      return;
    }
    if (
      decision === 'rejected'
      && !window.confirm('¿Confirmas el rechazo de esta detección candidata? La caja y el crop no se modificarán.')
    ) {
      return;
    }
    setReviewSaving(true);
    setReviewError('');
    try {
      const result = await api.createCellReview(reviewTarget.id, decision, comment || undefined);
      const createdReview: ScientificCellReview = result;
      const oldStatus = reviewTarget.review_status;
      const nextStatus = result.effective_review_status;
      const remainsVisible = filter === 'all' || filter === nextStatus;
      const selectedLoadedIndex = detections.findIndex((item) => item.id === reviewTarget.id);
      const countedInPageOffset = selectedLoadedIndex >= 0 && selectedLoadedIndex < galleryOffset;
      setDetections((items) => remainsVisible
        ? items.map((item) => (
          item.id === reviewTarget.id ? { ...item, review_status: nextStatus } : item
        ))
        : items.filter((item) => item.id !== reviewTarget.id));
      setOverlayDetections((items) => remainsVisible
        ? items.map((item) => (
          item.id === reviewTarget.id ? { ...item, review_status: nextStatus } : item
        ))
        : items.filter((item) => item.id !== reviewTarget.id));
      if (!remainsVisible) {
        setDetectionTotal((total) => Math.max(0, total - 1));
        if (countedInPageOffset) {
          setGalleryOffset((current) => Math.max(0, current - 1));
        }
      }
      setSelectedDetail((detail) => detail ? {
        ...detail,
        review_status: nextStatus,
        latest_review: createdReview,
        review_history: [...detail.review_history, createdReview],
      } : detail);
      setReviewHistory((items) => [...items, createdReview]);
      setRun((current) => {
        if (!current || oldStatus === nextStatus) return current;
        const nextCounts = { ...runCounts(current) };
        nextCounts[oldStatus] = Math.max(0, nextCounts[oldStatus] - 1);
        nextCounts[nextStatus] += 1;
        const reviewedDelta = oldStatus === 'unreviewed' && nextStatus !== 'unreviewed'
          ? 1
          : oldStatus !== 'unreviewed' && nextStatus === 'unreviewed' ? -1 : 0;
        return {
          ...current,
          review_counts: nextCounts,
          reviewed_count: Math.max(0, current.reviewed_count + reviewedDelta),
          pending_review_count: nextCounts.unreviewed,
        };
      });
      if (oldStatus === 'unreviewed' && nextStatus !== 'unreviewed') {
        setImages((items) => items.map((item) => (
          item.microscopy_image_id === selectedImageId
            ? { ...item, reviewed_count: item.reviewed_count + 1 }
            : item
        )));
      }
      setReviewComment('');
      setLiveMessage(`Revisión guardada para ${reviewTarget.cell_code}. Puedes continuar con la siguiente sin revisar.`);
    } catch (error) {
      setReviewError(
        error instanceof ApiError && error.status === 403
          ? 'Tu rol no tiene permiso para revisar detecciones.'
          : 'No fue posible guardar la revisión.',
      );
    } finally {
      setReviewSaving(false);
    }
  }

  if (workspaceLoading) {
    return (
      <section className="cell-workspace-loading" aria-live="polite">
        <p>Cargando estación de revisión…</p>
      </section>
    );
  }

  if (workspaceError || !run) {
    return (
      <section className="cell-workspace-loading cell-error" role="alert">
        <p>{workspaceError || 'La ejecución no está disponible.'}</p>
        <div>
          <button type="button" onClick={() => void loadWorkspace()}>Reintentar</button>
          <button type="button" onClick={onClose}>{closeLabel}</button>
        </div>
      </section>
    );
  }

  if (run.status === 'failed') {
    return (
      <section className="cell-workspace-loading cell-error" role="alert">
        <h2>{run.detection_run_code}: detección fallida</h2>
        <p>{run.error_message || 'La ejecución terminó con un error seguro. No hay reintento automático.'}</p>
        <button type="button" onClick={onClose}>{closeLabel}</button>
      </section>
    );
  }

  return (
    <section className="cell-workspace-shell" aria-label="Estación visual de revisión celular">
      <header className="cell-workspace-actions">
        <div>
          <p className="cell-workspace-kicker">Estación visual científica</p>
          <strong>{run.detection_run_code}</strong>
          <span>{run.subject_code} · {run.sample_code} · {run.slide_code}</span>
        </div>
        <div>
          <button
            type="button"
            aria-pressed={summaryCollapsed}
            onClick={() => setSummaryCollapsed((value) => !value)}
          >
            {summaryCollapsed ? 'Mostrar resumen' : 'Ocultar resumen'}
          </button>
          <button type="button" onClick={onClose}>{closeLabel}</button>
        </div>
      </header>

      <div className="cell-review-mobile-tabs" role="tablist" aria-label="Paneles de revisión">
        {([
          ['summary', 'Resumen', 'cell-summary-panel'],
          ['cells', 'Células', 'cell-gallery-panel'],
          ['image', 'Imagen', 'cell-image-panel'],
          ['detail', 'Detalle', 'cell-detail-panel'],
        ] as const).map(([id, label, controls]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={mobileTab === id}
            aria-controls={controls}
            onClick={() => setMobileTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <div
        className={`cell-review-workspace${summaryCollapsed ? ' is-summary-collapsed' : ''}`}
        data-mobile-tab={mobileTab}
      >
        <aside id="cell-summary-panel" className="cell-summary-panel" role="tabpanel" aria-labelledby="cell-summary-heading">
          <header className="cell-panel-heading">
            <div>
              <h2 id="cell-summary-heading">Revisión de detecciones</h2>
              <p>{run.detection_run_code}</p>
            </div>
          </header>
          <dl className="cell-run-facts">
            <div><dt>Paciente</dt><dd>{run.subject_code}</dd></div>
            <div><dt>Muestra</dt><dd>{run.sample_code}</dd></div>
            <div><dt>Imágenes</dt><dd>{run.image_count}</dd></div>
            <div><dt>Detecciones</dt><dd>{run.detection_count}</dd></div>
            <div><dt>Revisadas</dt><dd>{run.reviewed_count}</dd></div>
            <div><dt>Pendientes</dt><dd>{counts.unreviewed}</dd></div>
          </dl>

          <nav className="cell-status-filters" aria-label="Filtrar por estado de revisión">
            {(['all', 'unreviewed', 'accepted', 'rejected', 'needs_attention'] as CellReviewFilter[]).map((status) => {
              const count = status === 'all' ? run.detection_count : counts[status];
              const percentage = run.detection_count ? count / run.detection_count * 100 : 0;
              return (
                <button
                  key={status}
                  type="button"
                  className={`status-${status}`}
                  aria-pressed={filter === status}
                  onClick={() => setFilter(status)}
                >
                  <span className="cell-filter-name">
                    <span aria-hidden="true">{status === 'all' ? '∑' : reviewStatusSymbol[status]}</span>
                    {filterLabel[status]}
                  </span>
                  <strong>{count}</strong>
                  <small>{percentage.toFixed(1)}%</small>
                  <span className="cell-filter-progress" aria-hidden="true">
                    <span style={{ width: `${percentage}%` }} />
                  </span>
                </button>
              );
            })}
          </nav>

          <section className="cell-image-list" aria-labelledby="cell-image-list-heading">
            <h3 id="cell-image-list-heading">Imágenes del frotis</h3>
            {images.map((item) => (
              <button
                key={item.microscopy_image_id}
                type="button"
                aria-pressed={item.microscopy_image_id === selectedImageId}
                onClick={() => {
                  setSelectedImageId(item.microscopy_image_id);
                  setSelectionResolved(false);
                  commitSelectedDetectionId(null);
                  setMobileTab('cells');
                }}
              >
                <span><strong>{item.sequence_number}. {item.safe_name}</strong>
                  <small>{item.detection_count} detecciones · {item.reviewed_count} revisadas</small></span>
                {item.warning_count ? <span aria-label={`${item.warning_count} advertencias`}>⚠ {item.warning_count}</span> : <span>Sin alertas</span>}
              </button>
            ))}
            {!images.length ? <p className="cell-empty-state">Esta ejecución no contiene imágenes.</p> : null}
          </section>
        </aside>

        <section id="cell-gallery-panel" className="cell-gallery-panel" role="tabpanel" aria-labelledby="cell-gallery-heading">
          <header className="cell-panel-heading">
            <div>
              <h2 id="cell-gallery-heading">Detecciones candidatas</h2>
              <p>{selectedImage ? `${selectedImage.sequence_number}. ${selectedImage.safe_name}` : 'Sin imagen seleccionada'}</p>
            </div>
            <span>{detectionTotal} filtradas · {selectedImage?.detection_count ?? 0} totales · {filterLabel[filter]}</span>
          </header>
          <div className="cell-gallery-scroll">
            {galleryError ? <p className="cell-error" role="alert">{galleryError}</p> : null}
            <div className="cell-crop-gallery" aria-busy={galleryLoading}>
              {detections.map((detection) => (
                <DetectionCard
                  key={detection.id}
                  detection={detection}
                  selected={detection.id === selectedDetectionId}
                  register={(node) => {
                    if (node) cardRefs.current.set(detection.id, node);
                    else cardRefs.current.delete(detection.id);
                  }}
                  onSelect={() => selectDetection(detection, true)}
                />
              ))}
            </div>
            {galleryLoading ? <p className="cell-panel-state" aria-live="polite">Cargando detecciones…</p> : null}
            {!galleryLoading && !galleryError && selectedImage && !detections.length ? (
              <p className="cell-empty-state">
                {selectedImage.detection_count === 0
                  ? 'Esta imagen no contiene detecciones candidatas.'
                  : 'No hay detecciones para el filtro seleccionado.'}
              </p>
            ) : null}
            {galleryOffset < detectionTotal ? (
              <button className="cell-load-more" type="button" disabled={galleryLoading} onClick={() => void loadMore()}>
                Cargar más ({Math.min(galleryOffset, detectionTotal)} de {detectionTotal})
              </button>
            ) : null}
          </div>
        </section>

        <div className="cell-review-right">
          <div id="cell-image-panel" role="tabpanel">
            {selectedImage ? (
              <CellImageViewer
                detectionRunId={detectionRunId}
                images={images}
                image={selectedImage}
                detections={overlayDetections}
                selectedDetectionId={selectedDetectionId}
                focusRequest={focusRequest}
                onImageChange={(id) => {
                  setSelectedImageId(id);
                  setSelectionResolved(false);
                  commitSelectedDetectionId(null);
                }}
                onDetectionSelect={selectDetection}
                onPrevious={() => selectRelative(-1)}
                onNext={() => selectRelative(1)}
                onNextUnreviewed={nextUnreviewed}
              />
            ) : (
              <section className="cell-viewer-section cell-empty-state">
                <h2>Imagen original</h2>
                <p>No hay una imagen disponible para mostrar.</p>
              </section>
            )}
          </div>
          <CellDetailPanel
            selected={selectedDetection}
            detail={selectedDetail}
            history={reviewHistory}
            loading={detailLoading}
            error={detailError}
            canReview={canReview}
            comment={reviewComment}
            saving={reviewSaving}
            reviewError={reviewError}
            run={run}
            image={selectedImage}
            onCommentChange={(value) => {
              setReviewComment(value);
              setReviewError('');
            }}
            onReview={submitReview}
            onNextUnreviewed={nextUnreviewed}
          />
        </div>
      </div>
      <p className="cell-review-live" aria-live="polite">{liveMessage}</p>
    </section>
  );
}

const DetectionCard = memo(function DetectionCard({
  detection,
  selected,
  register,
  onSelect,
}: {
  detection: CellDetectionSummary;
  selected: boolean;
  register: (node: HTMLButtonElement | null) => void;
  onSelect: () => void;
}) {
  const hasWarning = Boolean(
    detection.component.touches_border || detection.technical_warnings?.length,
  );
  return (
    <article className={`cell-detection-card status-${detection.review_status}${selected ? ' is-selected' : ''}`}>
      <button
        ref={register}
        type="button"
        aria-pressed={selected}
        aria-label={`${detection.cell_code}, ${reviewStatusLabel[detection.review_status]}`}
        onClick={onSelect}
      >
        <AuthenticatedCropImage
          crop={detection.crop}
          alt={`Crop técnico de la detección ${detection.cell_code}`}
          eager={selected}
        />
        <span className="cell-card-caption">
          <strong>{detection.cell_code}</strong>
          <span className={`cell-review-status status-${detection.review_status}`}>
            <span aria-hidden="true">{reviewStatusSymbol[detection.review_status]}</span>
            {reviewStatusLabel[detection.review_status]}
          </span>
        </span>
        {hasWarning ? <span className="cell-card-warning" aria-label="Advertencia técnica">⚠</span> : null}
      </button>
    </article>
  );
});

function CellDetailPanel({
  selected,
  detail,
  history,
  loading,
  error,
  canReview,
  comment,
  saving,
  reviewError,
  run,
  image,
  onCommentChange,
  onReview,
  onNextUnreviewed,
}: {
  selected: CellDetectionSummary | null;
  detail: CellDetectionDetail | null;
  history: ScientificCellReview[];
  loading: boolean;
  error: string;
  canReview: boolean;
  comment: string;
  saving: boolean;
  reviewError: string;
  run: CellDetectionRunDetail;
  image: CellDetectionImage | null;
  onCommentChange: (value: string) => void;
  onReview: (decision: CellReviewDecision) => void;
  onNextUnreviewed: () => void;
}) {
  const detection = detail ?? selected;
  return (
    <section id="cell-detail-panel" className="cell-detail-panel" role="tabpanel" aria-labelledby="cell-detail-heading">
      <header className="cell-panel-heading">
        <div>
          <h2 id="cell-detail-heading">Detalle de la detección candidata</h2>
          <p>{detection?.cell_code ?? 'Sin selección'}</p>
        </div>
        {detection ? (
          <span className={`cell-review-status status-${detection.review_status}`}>
            {reviewStatusSymbol[detection.review_status]} {reviewStatusLabel[detection.review_status]}
          </span>
        ) : null}
      </header>
      {!detection ? <p className="cell-empty-state">Selecciona un crop o una bounding box para ver su detalle.</p> : null}
      {detection ? (
        <div className="cell-detail-content">
          <div className="cell-detail-crop">
            <AuthenticatedCropImage
              crop={detection.crop}
              alt={`Crop ampliado de la detección ${detection.cell_code}`}
              eager
            />
          </div>
          <dl className="cell-detail-facts">
            <div><dt>Código</dt><dd>{detection.cell_code}</dd></div>
            <div><dt>Detection run</dt><dd>{detail?.detection_run_code ?? run.detection_run_code}</dd></div>
            <div><dt>Imagen de origen</dt><dd>{detail?.source_image?.safe_name ?? detail?.safe_name ?? image?.safe_name ?? '—'}</dd></div>
            <div><dt>Detector</dt><dd>{detail?.detector?.key ?? detail?.detector_key ?? run.detector_key}</dd></div>
            <div><dt>Versión</dt><dd>{detail?.detector?.version ?? detail?.detector_version ?? run.detector_version}</dd></div>
            <div><dt>Resultado automático</dt><dd>{detection.automated_status}</dd></div>
            <div><dt>Score geométrico</dt><dd>{optionalMetric(detection.detector_score)}</dd></div>
            <div><dt>Bounding box (xywh)</dt><dd>{detection.bbox_x}, {detection.bbox_y}, {detection.bbox_width}, {detection.bbox_height}</dd></div>
            <div><dt>Coordinate space</dt><dd>{detection.coordinate_space}</dd></div>
            <div><dt>Área</dt><dd>{detection.component.area_px} px²</dd></div>
            <div><dt>Perímetro</dt><dd>{optionalMetric(detection.component.perimeter_px, 2)}</dd></div>
            <div><dt>Circularidad</dt><dd>{optionalMetric(detection.component.circularity)}</dd></div>
            <div><dt>Solidity</dt><dd>{optionalMetric(detection.component.solidity)}</dd></div>
            <div><dt>Contacto con borde</dt><dd>{detection.component.touches_border ? 'Sí' : 'No'}</dd></div>
            <div><dt>Checksum crop</dt><dd>{detection.crop ? `${detection.crop.sha256.slice(0, 12)}…` : '—'}</dd></div>
          </dl>
          {loading ? <p className="cell-panel-state">Cargando historial…</p> : null}
          {error ? <p className="cell-error" role="alert">{error}</p> : null}

          <section className="cell-human-review" aria-labelledby="cell-human-review-heading">
            <h3 id="cell-human-review-heading">Revisión humana</h3>
            {detail?.latest_review ? (
              <p>
                Última revisión: <strong>{reviewDecisionLabel[detail.latest_review.decision]}</strong> ·{' '}
                {safeDate(detail.latest_review.created_at)}
              </p>
            ) : <p>Sin revisión humana registrada.</p>}
            {canReview ? (
              <div className="cell-review-form">
                <label>
                  Comentario
                  <textarea
                    value={comment}
                    maxLength={4000}
                    placeholder="Obligatorio para rechazo, atención y comentario."
                    onChange={(event) => onCommentChange(event.target.value)}
                  />
                </label>
                <div className="cell-review-actions">
                  <button type="button" disabled={saving} onClick={() => onReview('accepted')}>Aceptar detección</button>
                  <button type="button" className="danger" disabled={saving} onClick={() => onReview('rejected')}>Rechazar detección</button>
                  <button type="button" disabled={saving} onClick={() => onReview('needs_attention')}>Requiere atención</button>
                  <button type="button" disabled={saving} onClick={() => onReview('comment_only')}>Agregar comentario</button>
                  <button type="button" disabled={saving} onClick={onNextUnreviewed}>Siguiente sin revisar</button>
                </div>
                {reviewError ? <p className="cell-error" role="alert">{reviewError}</p> : null}
              </div>
            ) : (
              <p className="cell-readonly-note">
                Vista de solo lectura: tu rol no incluye scientific.cell_detection.review.
              </p>
            )}
          </section>

          <section className="cell-review-history" aria-labelledby="cell-review-history-heading">
            <h3 id="cell-review-history-heading">Historial de revisión</h3>
            {history.length ? (
              <ol>
                {history.map((review) => (
                  <li key={review.id}>
                    <div>
                <strong>{reviewDecisionLabel[review.decision]}</strong>
                      <span>{safeDate(review.created_at)} · {review.actor_username ?? review.actor_user_id}</span>
                    </div>
                    <p>{review.comment || 'Sin comentario.'}</p>
                  </li>
                ))}
              </ol>
            ) : <p>No existen decisiones ni comentarios para esta detección.</p>}
          </section>
        </div>
      ) : null}
    </section>
  );
}
