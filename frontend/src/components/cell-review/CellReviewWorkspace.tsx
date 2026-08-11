import {
  memo,
  type FormEvent,
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
import {
  AuthenticatedCropImage,
  AuthenticatedImageCacheProvider,
} from './AuthenticatedCellImage';
import { CellGradCamPreview } from './CellGradCamPreview';
import { CellImageViewer } from './CellImageViewer';
import { CellClassificationAuditModal } from './CellClassificationAuditModal';
import { ScientificAnnotations } from './ScientificAnnotations';
import type {
  CanonicalCellLabel,
  CellClassificationReview,
  CellClassificationRunDetail,
  CellPredictionDetail,
  CellPredictionSummary,
  SmearAnalysisSummary,
  HumanCellClassification,
} from '../../types/cellClassification';

const PAGE_SIZE = 100;
const RAIL_RENDER_BATCH = 80;

type ClassificationFilter =
  | 'all'
  | 'parasitized'
  | 'uninfected'
  | 'near_threshold'
  | 'failed'
  | 'unreviewed'
  | 'confirmed'
  | 'corrected'
  | 'needs_attention';

const classificationFilterLabel: Record<ClassificationFilter, string> = {
  all: 'Todas',
  parasitized: 'Predichas parasitized',
  uninfected: 'Predichas uninfected',
  near_threshold: 'Próximas al threshold',
  failed: 'Sin clasificar o fallidas',
  unreviewed: 'Sin revisión',
  confirmed: 'Confirmadas',
  corrected: 'Corregidas',
  needs_attention: 'Requieren atención',
};

const classificationFilterSymbol: Record<ClassificationFilter, string> = {
  all: '∑',
  parasitized: 'P',
  uninfected: 'U',
  near_threshold: '≈',
  failed: '×',
  unreviewed: '○',
  confirmed: '✓',
  corrected: '↺',
  needs_attention: '!',
};

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

const inferredHumanLabel = (prediction: CellPredictionSummary | null) => {
  const review = prediction?.latest_review;
  if (!prediction || !review || review.decision === 'needs_attention' || review.decision === 'comment_only') return null;
  return review.reviewed_label ?? (review.decision === 'confirmed' ? prediction.predicted_label : null);
};

const normalizedSearch = (value: string) => value.trim().toLocaleLowerCase();

const coordinateSearch = (value: string) => {
  const match = value.trim().match(
    /^\[?\s*(\d+)\s*[,;x]\s*(\d+)(?:\s*[,;x]\s*(\d+)\s*[,;x]\s*(\d+))?\s*\]?$/i,
  );
  if (!match) return null;
  return match.slice(1).map((part) => part == null ? null : Number(part));
};

const detectionMatchesSearch = (
  detection: CellDetectionSummary,
  search: string,
) => {
  const query = normalizedSearch(search);
  if (!query) return true;
  if (
    detection.cell_code.toLocaleLowerCase().includes(query)
    || detection.id.toLocaleLowerCase().includes(query)
  ) return true;
  const coordinates = coordinateSearch(query);
  if (!coordinates) return false;
  const [x, y, width, height] = coordinates;
  if (x == null || y == null) return false;
  if (width != null && height != null) {
    return detection.bbox_x === x
      && detection.bbox_y === y
      && detection.bbox_width === width
      && detection.bbox_height === height;
  }
  return x >= detection.bbox_x
    && x <= detection.bbox_x + detection.bbox_width
    && y >= detection.bbox_y
    && y <= detection.bbox_y + detection.bbox_height;
};

const runCounts = (run: CellDetectionRunDetail | null): CellReviewCounts => ({
  ...emptyCounts,
  ...(run?.review_counts ?? {}),
  unreviewed:
    run?.review_counts?.unreviewed
    ?? run?.review_counts?.pending
    ?? run?.pending_review_count
    ?? 0,
});

function ReviewProgressRing({
  run,
  classificationRun,
}: {
  run: CellDetectionRunDetail;
  classificationRun: CellClassificationRunDetail | null;
}) {
  const isClassifying = classificationRun?.status === 'created'
    || classificationRun?.status === 'processing';
  const classificationReviews = classificationRun?.review_counts ?? {};
  const reviewedClassifications = (
    (classificationReviews.confirmed ?? 0)
    + (classificationReviews.corrected ?? 0)
    + (classificationReviews.needs_attention ?? 0)
  );
  const current = classificationRun
    ? isClassifying ? classificationRun.processed_count : reviewedClassifications
    : run.reviewed_count;
  const total = classificationRun?.eligible_count ?? run.detection_count;
  const safeCurrent = Math.min(total, Math.max(0, current));
  const progress = total ? safeCurrent / total : 0;
  const radius = 43;
  const label = isClassifying
    ? 'Clasificando'
    : total > 0 && safeCurrent >= total
      ? 'Revisión completada'
      : 'Revisión activa';

  return (
    <section
      className="cell-review-progress"
      aria-label={`${label}: ${safeCurrent} de ${total}`}
    >
      <div
        className="cell-review-progress-ring"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={safeCurrent}
      >
        <svg viewBox="0 0 100 100" aria-hidden="true">
          <circle className="cell-review-progress-track" cx="50" cy="50" r={radius} />
          <circle
            className="cell-review-progress-value"
            cx="50"
            cy="50"
            r={radius}
            pathLength="1"
            strokeDasharray="1"
            strokeDashoffset={1 - progress}
          />
        </svg>
        <span><strong>{safeCurrent}</strong><small>/ {total}</small></span>
      </div>
      <p>{label}</p>
    </section>
  );
}

type MobileTab = 'image' | 'cells' | 'detail' | 'result';

type CellReviewWorkspaceProps = {
  detectionRunId: string;
  canReview: boolean;
  onClose: () => void;
  closeLabel?: string;
  initialMicroscopyImageId?: string | null;
  onMicroscopyImageChange?: (microscopyImageId: string | null) => void;
  initialSelectedDetectionId?: string | null;
  onSelectedDetectionChange?: (detectionId: string | null) => void;
  classificationRunId?: string | null;
  initialClassificationSummary?: SmearAnalysisSummary | null;
  canExplain?: boolean;
  canClassificationReview?: boolean;
  initialSelectedPredictionId?: string | null;
  onSelectedPredictionChange?: (predictionId: string | null) => void;
  validationSessionId?: string | null;
  canAnnotateValidation?: boolean;
  canReadValidationAnnotations?: boolean;
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
  classificationRunId = null,
  initialClassificationSummary = null,
  canExplain = false,
  canClassificationReview = false,
  initialSelectedPredictionId = null,
  onSelectedPredictionChange,
  validationSessionId = null,
  canAnnotateValidation = false,
  canReadValidationAnnotations = false,
}: CellReviewWorkspaceProps) {
  const [run, setRun] = useState<CellDetectionRunDetail | null>(null);
  const [images, setImages] = useState<CellDetectionImage[]>([]);
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [filter, setFilter] = useState<CellReviewFilter>('all');
  const [classificationFilter, setClassificationFilter] =
    useState<ClassificationFilter>('all');
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
  const [classificationRun, setClassificationRun] =
    useState<CellClassificationRunDetail | null>(null);
  const [classificationSummary, setClassificationSummary] =
    useState<SmearAnalysisSummary | null>(initialClassificationSummary);
  const [predictions, setPredictions] = useState<CellPredictionSummary[]>([]);
  const [predictionDetail, setPredictionDetail] =
    useState<CellPredictionDetail | null>(null);
  const [classificationReviews, setClassificationReviews] =
    useState<CellClassificationReview[]>([]);
  const [humanClassification, setHumanClassification] =
    useState<HumanCellClassification | null>(null);
  const [humanByPredictionId, setHumanByPredictionId] =
    useState<Record<string, HumanCellClassification>>({});
  const [classificationEditing, setClassificationEditing] = useState(false);
  const [annotationCountByCell, setAnnotationCountByCell] =
    useState<Record<string, number>>({});
  const [classificationLoading, setClassificationLoading] = useState(false);
  const [classificationError, setClassificationError] = useState('');
  const [classificationComment, setClassificationComment] = useState('');
  const [reviewedLabel, setReviewedLabel] =
    useState<CanonicalCellLabel>('parasitized');
  const [classificationSaving, setClassificationSaving] = useState(false);
  const [classificationReviewError, setClassificationReviewError] = useState('');
  const [explanationSaving, setExplanationSaving] = useState(false);
  const [auditOpen, setAuditOpen] = useState(false);
  const [focusRequest, setFocusRequest] = useState(0);
  const [resultExpanded, setResultExpanded] = useState(false);
  const [detailCollapsed, setDetailCollapsed] = useState(() => (
    typeof window !== 'undefined' && window.matchMedia('(max-width: 1200px)').matches
  ));
  const [railCollapsed, setRailCollapsed] = useState(() => (
    typeof window !== 'undefined' && window.matchMedia('(max-width: 1200px)').matches
  ));
  const [cellSearch, setCellSearch] = useState('');
  const [mobileTab, setMobileTab] = useState<MobileTab>('image');
  const [visibleGalleryLimit, setVisibleGalleryLimit] = useState(RAIL_RENDER_BATCH);
  const [selectionResolved, setSelectionResolved] = useState(false);
  const [selectionRefreshToken, setSelectionRefreshToken] = useState(0);
  const cardRefs = useRef(new Map<string, HTMLButtonElement>());
  const mobileTabRefs = useRef(new Map<MobileTab, HTMLButtonElement>());
  const galleryRequest = useRef(0);
  const selectFirstUnreviewed = useRef(false);
  const selectedDetectionIdRef = useRef<string | null>(null);
  const pendingInitialSelection = useRef<string | null>(initialSelectedDetectionId);
  const pendingInitialPrediction = useRef<string | null>(initialSelectedPredictionId);
  const pendingInitialImage = useRef<string | null>(initialMicroscopyImageId);
  const initialSelectionAttempted = useRef(false);
  const selectionDetectionRunId = useRef(detectionRunId);
  const selectionNavigationRequest = useRef(0);
  const selectionInputs = useRef({
    detectionRunId,
    imageId: initialMicroscopyImageId,
    detectionId: initialSelectedDetectionId,
    predictionId: initialSelectedPredictionId,
  });
  const lastNotifiedImage = useRef<string | null | undefined>(undefined);
  const lastNotifiedSelection = useRef<string | null | undefined>(undefined);
  const lastNotifiedPrediction = useRef<string | null | undefined>(undefined);

  const commitSelectedDetectionId = useCallback((detectionId: string | null) => {
    selectedDetectionIdRef.current = detectionId;
    setSelectedDetectionId(detectionId);
  }, []);

  const collapseRail = useCallback(() => {
    setRailCollapsed(true);
    window.requestAnimationFrame(() => {
      document.querySelector<HTMLButtonElement>(
        '[aria-label="Mostrar carrusel de células"]',
      )?.focus();
    });
  }, []);

  const expandRail = useCallback(() => {
    setRailCollapsed(false);
    window.requestAnimationFrame(() => {
      document.querySelector<HTMLButtonElement>(
        '[aria-label="Ocultar carrusel de células"]',
      )?.focus();
    });
  }, []);

  const collapseDetail = useCallback(() => {
    setDetailCollapsed(true);
    window.requestAnimationFrame(() => {
      document.querySelector<HTMLButtonElement>(
        '[aria-label="Mostrar detalle de la célula seleccionada"]',
      )?.focus();
    });
  }, []);

  const expandDetail = useCallback(() => {
    setDetailCollapsed(false);
    window.requestAnimationFrame(() => {
      document.querySelector<HTMLButtonElement>(
        '[aria-label="Ocultar detalle de la célula seleccionada"]',
      )?.focus();
    });
  }, []);

  useEffect(() => {
    const previous = selectionInputs.current;
    const next = {
      detectionRunId,
      imageId: initialMicroscopyImageId,
      detectionId: initialSelectedDetectionId,
      predictionId: initialSelectedPredictionId,
    };
    selectionInputs.current = next;
    const runChanged = selectionDetectionRunId.current !== detectionRunId;
    if (!runChanged) {
      if (!initialSelectionAttempted.current && !selectionResolved) {
        pendingInitialImage.current = initialMicroscopyImageId;
        pendingInitialSelection.current = initialSelectedDetectionId;
        pendingInitialPrediction.current = initialSelectedPredictionId;
        return;
      }

      const externalImageChange = previous.imageId !== initialMicroscopyImageId
        && initialMicroscopyImageId !== lastNotifiedImage.current;
      const externalDetectionChange = previous.detectionId !== initialSelectedDetectionId
        && initialSelectedDetectionId !== lastNotifiedSelection.current;
      const externalPredictionChange = previous.predictionId !== initialSelectedPredictionId
        && initialSelectedPredictionId !== lastNotifiedPrediction.current;
      if (!externalImageChange && !externalDetectionChange && !externalPredictionChange) return;

      pendingInitialImage.current = initialMicroscopyImageId;
      pendingInitialSelection.current = initialSelectedDetectionId;
      pendingInitialPrediction.current = initialSelectedPredictionId;
      initialSelectionAttempted.current = false;
      setSelectionResolved(false);
      const navigationRequest = ++selectionNavigationRequest.current;

      if (externalPredictionChange && initialSelectedPredictionId) {
        void api.getCellPrediction(initialSelectedPredictionId)
          .then((prediction) => {
            if (selectionNavigationRequest.current !== navigationRequest) return;
            pendingInitialImage.current = prediction.microscopy_image_id;
            pendingInitialSelection.current = prediction.cell_detection_id;
            if (
              prediction.microscopy_image_id !== selectedImageId
              && images.some(
                (item) => item.microscopy_image_id === prediction.microscopy_image_id,
              )
            ) {
              setSelectedImageId(prediction.microscopy_image_id);
            } else {
              setSelectionRefreshToken((value) => value + 1);
            }
          })
          .catch(() => {
            if (selectionNavigationRequest.current === navigationRequest) {
              setSelectionRefreshToken((value) => value + 1);
            }
          });
        return;
      }

      if (
        initialMicroscopyImageId
        && initialMicroscopyImageId !== selectedImageId
        && images.some((item) => item.microscopy_image_id === initialMicroscopyImageId)
      ) {
        setSelectedImageId(initialMicroscopyImageId);
      } else {
        setSelectionRefreshToken((value) => value + 1);
      }
      return;
    }
    selectionDetectionRunId.current = detectionRunId;
    selectionNavigationRequest.current += 1;
    pendingInitialImage.current = initialMicroscopyImageId;
    pendingInitialSelection.current = initialSelectedDetectionId;
    pendingInitialPrediction.current = initialSelectedPredictionId;
    initialSelectionAttempted.current = false;
    lastNotifiedImage.current = undefined;
    lastNotifiedSelection.current = undefined;
    lastNotifiedPrediction.current = undefined;
    setSelectionResolved(false);
    commitSelectedDetectionId(null);
  }, [
    commitSelectedDetectionId,
    detectionRunId,
    initialMicroscopyImageId,
    initialSelectedDetectionId,
    initialSelectedPredictionId,
    images,
    selectedImageId,
  ]);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 1200px)');
    const synchronizeFloatingPanels = (event: MediaQueryListEvent | MediaQueryList) => {
      setDetailCollapsed(event.matches);
      setRailCollapsed(event.matches);
    };
    synchronizeFloatingPanels(media);
    media.addEventListener('change', synchronizeFloatingPanels);
    return () => media.removeEventListener('change', synchronizeFloatingPanels);
  }, []);

  useEffect(() => {
    const returnToCanvas = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || !window.matchMedia('(max-width: 1200px)').matches) return;
      const openDetail = !detailCollapsed;
      const openRail = !railCollapsed;
      if (mobileTab === 'image' && !openDetail && !openRail) return;
      setDetailCollapsed(true);
      setRailCollapsed(true);
      setMobileTab('image');
      window.requestAnimationFrame(() => {
        if (window.matchMedia('(max-width: 700px)').matches) {
          mobileTabRefs.current.get('image')?.focus();
          return;
        }
        const label = openDetail
          ? 'Mostrar detalle de la célula seleccionada'
          : 'Mostrar carrusel de células';
        document.querySelector<HTMLButtonElement>(`[aria-label="${label}"]`)?.focus();
      });
    };
    window.addEventListener('keydown', returnToCanvas);
    return () => window.removeEventListener('keydown', returnToCanvas);
  }, [detailCollapsed, mobileTab, railCollapsed]);

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
  const predictionByDetectionId = useMemo(
    () => new Map(predictions.map((item) => [item.cell_detection_id, item])),
    [predictions],
  );
  const unclassifiedDetectionCount = useMemo(
    () => classificationRunId
      ? overlayDetections.filter((item) => !predictionByDetectionId.has(item.id)).length
      : 0,
    [classificationRunId, overlayDetections, predictionByDetectionId],
  );
  const selectedPrediction = selectedDetectionId
    ? predictionByDetectionId.get(selectedDetectionId) ?? null
    : null;
  const galleryDetections = useMemo(() => {
    if (!classificationRunId) {
      return detections.filter((detection) => detectionMatchesSearch(detection, cellSearch));
    }
    return overlayDetections.filter((detection) => {
      if (!detectionMatchesSearch(detection, cellSearch)) return false;
      const prediction = predictionByDetectionId.get(detection.id);
      if (!prediction) {
        return classificationFilter === 'all' || classificationFilter === 'failed';
      }
      if (classificationFilter === 'all') return true;
      if (classificationFilter === 'parasitized' || classificationFilter === 'uninfected') {
        return prediction.predicted_label === classificationFilter;
      }
      if (classificationFilter === 'near_threshold') return prediction.near_threshold;
      if (classificationFilter === 'failed') return prediction.prediction_status === 'failed';
      return prediction.review_status === classificationFilter;
    });
  }, [
    cellSearch,
    classificationFilter,
    classificationRunId,
    detections,
    overlayDetections,
    predictionByDetectionId,
  ]);
  const displayedGalleryDetections = useMemo(
    () => galleryDetections.slice(0, visibleGalleryLimit),
    [galleryDetections, visibleGalleryLimit],
  );
  const counts = runCounts(run);

  useEffect(() => {
    if (!selectionResolved || !onSelectedPredictionChange) return;
    const predictionId = selectedPrediction?.id ?? null;
    if (lastNotifiedPrediction.current === predictionId) return;
    lastNotifiedPrediction.current = predictionId;
    onSelectedPredictionChange(predictionId);
  }, [onSelectedPredictionChange, selectedPrediction?.id, selectionResolved]);

  const loadWorkspace = useCallback(async () => {
    setWorkspaceLoading(true);
    setWorkspaceError('');
    try {
      const requestedPredictionId = pendingInitialPrediction.current;
      const [nextRun, imagePage, requestedPrediction] = await Promise.all([
        api.getCellDetectionRun(detectionRunId),
        api.getCellDetectionImages(detectionRunId),
        requestedPredictionId
          ? api.getCellPrediction(requestedPredictionId).catch(() => null)
          : Promise.resolve(null),
      ]);
      if (requestedPrediction) {
        pendingInitialImage.current = requestedPrediction.microscopy_image_id;
        pendingInitialSelection.current = requestedPrediction.cell_detection_id;
      }
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
    setClassificationSummary(initialClassificationSummary);
  }, [initialClassificationSummary]);

  useEffect(() => {
    if (!classificationRunId) {
      setClassificationRun(null);
      setPredictions([]);
      setPredictionDetail(null);
      setClassificationReviews([]);
      setHumanClassification(null);
      setClassificationError('');
      return;
    }
    let active = true;
    setClassificationLoading(true);
    setClassificationError('');
    Promise.all([
      api.getCellClassificationRun(classificationRunId),
      api.getCellClassificationSummary(classificationRunId),
    ])
      .then(([nextRun, nextSummary]) => {
        if (!active) return;
        setClassificationRun(nextRun);
        setClassificationSummary(nextSummary);
      })
      .catch(() => {
        if (active) {
          setClassificationError('No fue posible cargar la clasificación celular.');
        }
      })
      .finally(() => {
        if (active) setClassificationLoading(false);
      });
    return () => {
      active = false;
    };
  }, [classificationRunId]);

  useEffect(() => {
    if (!classificationRunId || !selectedImageId) {
      setPredictions([]);
      return;
    }
    let active = true;
    setClassificationLoading(true);
    setClassificationError('');
    api.getCellClassificationPredictions(classificationRunId, {
      microscopy_image_id: selectedImageId,
      limit: 500,
      offset: 0,
    })
      .then((page) => {
        if (!active) return;
        setPredictions(page.items);
        const requestedPrediction = page.items.find(
          (item) => item.id === pendingInitialPrediction.current,
        );
        if (requestedPrediction) {
          commitSelectedDetectionId(requestedPrediction.cell_detection_id);
          pendingInitialPrediction.current = null;
        }
      })
      .catch(() => {
        if (active) {
          setPredictions([]);
          setClassificationError('No fue posible cargar las predicciones de esta imagen.');
        }
      })
      .finally(() => {
        if (active) setClassificationLoading(false);
      });
    return () => {
      active = false;
    };
  }, [
    classificationRunId,
    commitSelectedDetectionId,
    selectionRefreshToken,
    selectedImageId,
  ]);

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
    const query = {
      review_status:
        classificationRunId || filter === 'all' ? undefined : filter,
    };
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
        const selectedCandidate = overlayPage.items.find(
          (item) => item.id === nextSelection,
        );
        setDetections(
          selectedCandidate && !page.items.some((item) => item.id === selectedCandidate.id)
            ? [...page.items, selectedCandidate].sort(
              (left, right) => left.cell_index - right.cell_index,
            )
            : page.items,
        );
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
    classificationRunId,
    detectionRunId,
    filter,
    selectionRefreshToken,
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
    if (!selectedPrediction) {
      setPredictionDetail(null);
      setClassificationReviews([]);
      return;
    }
    let active = true;
    setClassificationLoading(true);
    setClassificationError('');
    Promise.all([
      api.getCellPrediction(selectedPrediction.id),
      api.getHumanCellClassificationHistory(selectedPrediction.id),
      api.getHumanCellClassification(selectedPrediction.id),
    ])
      .then(async ([detail, reviews, human]) => {
        if (!active) return;
        let explanation = detail.explanation;
        if (
          detail.explanation_status
          && detail.explanation_status !== 'not_requested'
        ) {
          try {
            explanation = await api.getCellExplanation(detail.id);
          } catch {
            // The prediction remains readable even if its optional artefact is unavailable.
          }
        }
        if (!active) return;
        setPredictionDetail({ ...detail, explanation });
        setClassificationReviews(reviews.items);
        setHumanClassification(human);
        setHumanByPredictionId((current) => ({ ...current, [detail.id]: human }));
        setReviewedLabel(human.label ?? detail.predicted_label ?? 'parasitized');
        setClassificationComment(human.comment ?? '');
        setClassificationEditing(human.status === 'unreviewed');
      })
      .catch(() => {
        if (active) {
          setClassificationError('No fue posible cargar el detalle de clasificación.');
        }
      })
      .finally(() => {
        if (active) setClassificationLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedPrediction?.id]);

  useEffect(() => {
    setReviewComment('');
    setReviewError('');
    setClassificationComment('');
    setHumanClassification(null);
    setClassificationEditing(false);
    setClassificationReviewError('');
    setAuditOpen(false);
  }, [selectedDetectionId]);

  useEffect(() => {
    setVisibleGalleryLimit(RAIL_RENDER_BATCH);
  }, [cellSearch, classificationFilter, selectedImageId]);

  useEffect(() => {
    if (!selectedDetectionId) return;
    const selectedIndex = galleryDetections.findIndex(
      (detection) => detection.id === selectedDetectionId,
    );
    if (selectedIndex < visibleGalleryLimit) return;
    setVisibleGalleryLimit(
      Math.ceil((selectedIndex + 1) / RAIL_RENDER_BATCH) * RAIL_RENDER_BATCH,
    );
  }, [galleryDetections, selectedDetectionId, visibleGalleryLimit]);

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

  function submitCellSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = normalizedSearch(cellSearch);
    if (!query) {
      setLiveMessage('Escribe un cell_code, identificador de detección o coordenada real.');
      return;
    }
    const exact = overlayDetections.find((detection) => (
      detection.cell_code.toLocaleLowerCase() === query
      || detection.id.toLocaleLowerCase() === query
    ));
    const target = exact ?? overlayDetections.find(
      (detection) => detectionMatchesSearch(detection, query),
    );
    if (!target) {
      setLiveMessage(`No se encontró una célula real para “${cellSearch.trim()}”.`);
      return;
    }
    if (classificationRunId) setClassificationFilter('all');
    else setFilter('all');
    selectDetection(target, true);
    setDetailCollapsed(false);
    setRailCollapsed(false);
    setLiveMessage(`${target.cell_code} seleccionada y centrada en la imagen.`);
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
    const visibleDetections = classificationRunId ? galleryDetections : detections;
    if (!visibleDetections.length) return;
    const currentIndex = visibleDetections.findIndex(
      (item) => item.id === selectedDetectionId,
    );
    if (
      !classificationRunId
      && direction === 1
      && currentIndex === visibleDetections.length - 1
      && visibleDetections.length < detectionTotal
    ) {
      void loadMore(true);
      return;
    }
    const nextIndex = currentIndex < 0
      ? 0
      : (
          currentIndex
          + direction
          + visibleDetections.length
        ) % visibleDetections.length;
    selectDetection(visibleDetections[nextIndex], true);
  }

  function nextUnreviewed() {
    if (classificationRunId) {
      const currentIndex = galleryDetections.findIndex(
        (item) => item.id === selectedDetectionId,
      );
      const ordered = [
        ...galleryDetections.slice(Math.max(0, currentIndex + 1)),
        ...galleryDetections.slice(0, Math.max(0, currentIndex + 1)),
      ];
      const next = ordered.find((item) => (
        (() => {
          const prediction = predictionByDetectionId.get(item.id) ?? null;
          return prediction
            && !(humanByPredictionId[prediction.id]?.label ?? inferredHumanLabel(prediction));
        })()
        && item.id !== selectedDetectionId
      ));
      if (next) {
        selectDetection(next, true);
        return;
      }
      if (classificationFilter !== 'unreviewed') {
        setClassificationFilter('unreviewed');
        return;
      }
      setLiveMessage('No quedan clasificaciones sin revisar en esta imagen.');
      return;
    }
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
      if (classificationRunId) await refreshClassificationSummary();
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

  async function refreshClassificationSummary() {
    if (!classificationRunId) return;
    try {
      const [nextSummary, nextRun] = await Promise.all([
        api.getCellClassificationSummary(classificationRunId),
        api.getCellClassificationRun(classificationRunId),
      ]);
      setClassificationSummary(nextSummary);
      setClassificationRun(nextRun);
    } catch {
      setClassificationError('No fue posible actualizar el resumen revisado.');
    }
  }

  async function generateExplanation(regenerate = false) {
    const target = predictionDetail ?? selectedPrediction;
    if (!target || !canExplain) throw new Error('Explicación no autorizada.');
    setExplanationSaving(true);
    setClassificationError('');
    try {
      const explanation = await api.createCellExplanation(
        target.id,
        regenerate || target.explanation?.status === 'failed',
      );
      setPredictionDetail((current) => current ? {
        ...current,
        explanation,
        explanation_status: explanation.status,
      } : current);
      setPredictions((items) => items.map((item) => (
        item.id === target.id
          ? { ...item, explanation, explanation_status: explanation.status }
          : item
      )));
      setLiveMessage(`Explicación ${explanation.status} para ${target.cell_code}.`);
      return explanation;
    } catch (generationError) {
      const hasPersistedExplanation = Boolean(
        target.explanation
        || (target.explanation_status && target.explanation_status !== 'not_requested')
      );
      if (!hasPersistedExplanation) {
        setClassificationError('No fue posible generar la explicación Grad-CAM.');
        throw generationError;
      }
      try {
        const explanation = await api.getCellExplanation(target.id);
        setPredictionDetail((current) => current ? {
          ...current,
          explanation,
          explanation_status: explanation.status,
        } : current);
        setPredictions((items) => items.map((item) => (
          item.id === target.id
            ? { ...item, explanation, explanation_status: explanation.status }
            : item
        )));
        setLiveMessage(`Estado de explicación recuperado: ${explanation.status}.`);
        return explanation;
      } catch {
        setClassificationError('No fue posible generar la explicación Grad-CAM.');
        throw generationError;
      }
    } finally {
      setExplanationSaving(false);
    }
  }

  async function submitHumanClassification() {
    const target = predictionDetail ?? selectedPrediction;
    if (!target || !canClassificationReview) return;
    setClassificationSaving(true);
    setClassificationReviewError('');
    try {
      const human = await api.saveHumanCellClassification(
        target.id, reviewedLabel, classificationComment,
      );
      const history = await api.getHumanCellClassificationHistory(target.id);
      setHumanClassification(human);
      setHumanByPredictionId((current) => ({ ...current, [target.id]: human }));
      setClassificationReviews(history.items);
      setClassificationEditing(false);
      await refreshClassificationSummary();
      setLiveMessage(`Clasificación humana guardada para ${target.cell_code}.`);
    } catch (error) {
      setClassificationReviewError(
        error instanceof ApiError && error.status === 403
          ? 'Tu rol no tiene permiso para revisar clasificaciones.'
          : error instanceof ApiError && error.status === 409
            ? 'Conflicto: la clasificación cambió. Actualiza antes de volver a guardar.'
          : 'No fue posible guardar la revisión de clasificación.',
      );
    } finally {
      setClassificationSaving(false);
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
    <AuthenticatedImageCacheProvider>
      <section
        className="cell-workspace-shell cell-workspace-shell--immersive"
        aria-label="Estación visual de revisión celular"
      >
      <header className="cell-workspace-actions cell-workspace-actions--sr">
        <p>Estación visual científica</p>
        <strong>{run.detection_run_code}</strong>
        <span>{run.subject_code} · {run.sample_code} · {run.slide_code}</span>
        <button type="button" onClick={onClose}>{closeLabel}</button>
      </header>

      {classificationError ? <p className="cell-classification-error" role="alert">{classificationError}</p> : null}

      <div className="cell-review-mobile-tabs" role="tablist" aria-label="Paneles de revisión">
        {([
          ['image', 'Imagen', 'cell-image-panel'],
          ['cells', 'Células', 'cell-gallery-panel'],
          ['detail', 'Detalle', 'cell-detail-panel'],
          ['result', 'Resultado', 'cell-result-panel'],
        ] as const).map(([id, label, controls]) => (
          <button
            key={id}
            ref={(node) => {
              if (node) mobileTabRefs.current.set(id, node);
              else mobileTabRefs.current.delete(id);
            }}
            type="button"
            role="tab"
            aria-selected={mobileTab === id}
            aria-controls={controls}
            onClick={() => {
              setMobileTab(id);
              if (id === 'detail') setDetailCollapsed(false);
              if (id === 'cells') setRailCollapsed(false);
              if (id === 'result') setResultExpanded(true);
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div
        className="cell-review-workspace cell-review-workspace--immersive"
        data-mobile-tab={mobileTab}
        data-detail-collapsed={detailCollapsed || undefined}
        data-rail-collapsed={railCollapsed || undefined}
      >
        <div id="cell-image-panel" className="cell-review-right cell-immersive-canvas" role="tabpanel">
          {selectedImage ? (
            <CellImageViewer
              detectionRunId={detectionRunId}
              images={images}
              image={selectedImage}
              detections={overlayDetections}
              classificationAnnotations={predictionByDetectionId}
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

        <div className="cell-immersive-top-controls">
          <form className="cell-gallery-search" role="search" onSubmit={submitCellSearch}>
            <label htmlFor="cell-immersive-search">Buscar célula</label>
            <span aria-hidden="true">⌕</span>
            <input
              id="cell-immersive-search"
              type="search"
              value={cellSearch}
              placeholder="cell_code, ID o x,y"
              onChange={(event) => setCellSearch(event.target.value)}
            />
            <button type="submit">Ubicar</button>
          </form>

          {classificationRun ? (
            <nav className="cell-status-filters classification-filters" aria-label="Filtrar clasificación celular">
              {(Object.keys(classificationFilterLabel) as ClassificationFilter[]).map((status) => {
                const reviewCounts = classificationRun.review_counts ?? {};
                const count = status === 'all'
                  ? Math.max(classificationRun.input_count, overlayDetections.length)
                  : status === 'parasitized'
                    ? classificationRun.parasitized_count
                    : status === 'uninfected'
                      ? classificationRun.uninfected_count
                      : status === 'near_threshold'
                        ? classificationRun.near_threshold_count
                        : status === 'failed'
                          ? classificationRun.failed_count + unclassifiedDetectionCount
                          : reviewCounts[status] ?? 0;
                return (
                  <button
                    key={status}
                    type="button"
                    className={`classification-status-${status}`}
                    aria-pressed={classificationFilter === status}
                    title={`${classificationFilterLabel[status]}: ${count}`}
                    onClick={() => setClassificationFilter(status)}
                  >
                    <span aria-hidden="true">{classificationFilterSymbol[status]}</span>
                    <span>{classificationFilterLabel[status]}</span>
                    <strong>{count}</strong>
                  </button>
                );
              })}
            </nav>
          ) : (
            <nav className="cell-status-filters" aria-label="Filtrar por estado de revisión">
              {(['all', 'unreviewed', 'accepted', 'rejected', 'needs_attention'] as CellReviewFilter[]).map((status) => {
                const count = status === 'all' ? run.detection_count : counts[status];
                return (
                  <button
                    key={status}
                    type="button"
                    className={`status-${status}`}
                    aria-pressed={filter === status}
                    title={`${filterLabel[status]}: ${count}`}
                    onClick={() => setFilter(status)}
                  >
                    <span aria-hidden="true">{status === 'all' ? '∑' : reviewStatusSymbol[status]}</span>
                    <span>{filterLabel[status]}</span>
                    <strong>{count}</strong>
                  </button>
                );
              })}
            </nav>
          )}
        </div>

        {!railCollapsed ? (
          <section id="cell-gallery-panel" className="cell-gallery-panel" role="tabpanel" aria-labelledby="cell-gallery-heading">
            <header className="cell-panel-heading">
              <div>
                <h2 id="cell-gallery-heading">
                  {classificationRun
                    ? `${classificationFilterLabel[classificationFilter]} (${galleryDetections.length})`
                    : `Células (${detectionTotal})`}
                </h2>
                <p>{selectedImage?.safe_name ?? 'Sin imagen seleccionada'}</p>
              </div>
              <button type="button" onClick={collapseRail} aria-label="Ocultar carrusel de células">×</button>
            </header>
            <div className="cell-gallery-scroll">
              {galleryError ? <p className="cell-error" role="alert">{galleryError}</p> : null}
              <div className="cell-crop-gallery" aria-busy={galleryLoading}>
                {displayedGalleryDetections.map((detection) => (
                  <DetectionCard
                    key={detection.id}
                    detection={detection}
                    prediction={predictionByDetectionId.get(detection.id) ?? null}
                    classificationExpected={Boolean(classificationRun)}
                    humanLabel={humanByPredictionId[predictionByDetectionId.get(detection.id)?.id ?? '']?.label
                      ?? inferredHumanLabel(predictionByDetectionId.get(detection.id) ?? null)}
                    annotationCount={annotationCountByCell[detection.id] ?? 0}
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
              {!galleryLoading && !galleryError && selectedImage && !galleryDetections.length ? (
                <p className="cell-empty-state">
                  {selectedImage.detection_count === 0
                    ? 'Esta imagen no contiene detecciones candidatas.'
                    : 'No hay detecciones para el filtro seleccionado.'}
                </p>
              ) : null}
              {classificationRun && visibleGalleryLimit < galleryDetections.length ? (
                <button
                  className="cell-load-more"
                  type="button"
                  onClick={() => setVisibleGalleryLimit((value) => value + RAIL_RENDER_BATCH)}
                >
                  Mostrar más ({Math.min(visibleGalleryLimit, galleryDetections.length)} de {galleryDetections.length})
                </button>
              ) : null}
              {!classificationRun && galleryOffset < detectionTotal ? (
                <button className="cell-load-more" type="button" disabled={galleryLoading} onClick={() => void loadMore()}>
                  Cargar más ({Math.min(galleryOffset, detectionTotal)} de {detectionTotal})
                </button>
              ) : null}
            </div>
          </section>
        ) : (
          <button
            type="button"
            className="cell-panel-restore cell-panel-restore--rail"
            onClick={expandRail}
            aria-label="Mostrar carrusel de células"
          >
            Células <strong>{galleryDetections.length}</strong>
          </button>
        )}

        {!detailCollapsed ? (
          <CellDetailPanel
            selected={selectedDetection}
            detail={selectedDetail}
            history={reviewHistory}
            prediction={predictionDetail ?? selectedPrediction}
            classificationHistory={classificationReviews}
            humanClassification={humanClassification}
            classificationEditing={classificationEditing}
            classificationRun={classificationRun}
            classificationLoading={classificationLoading}
            classificationError={classificationError}
            canExplain={canExplain}
            canClassificationReview={canClassificationReview}
            validationSessionId={validationSessionId}
            canAnnotateValidation={canAnnotateValidation}
            canReadValidationAnnotations={canReadValidationAnnotations}
            classificationComment={classificationComment}
            reviewedLabel={reviewedLabel}
            classificationSaving={classificationSaving}
            explanationSaving={explanationSaving}
            classificationReviewError={classificationReviewError}
            loading={detailLoading}
            error={detailError}
            canReview={canReview}
            comment={reviewComment}
            saving={reviewSaving}
            reviewError={reviewError}
            run={run}
            image={selectedImage}
            onCollapse={collapseDetail}
            onCommentChange={(value) => {
              setReviewComment(value);
              setReviewError('');
            }}
            onReview={submitReview}
            onNextUnreviewed={nextUnreviewed}
            onClassificationCommentChange={(value) => {
              setClassificationComment(value);
              setClassificationReviewError('');
            }}
            onReviewedLabelChange={setReviewedLabel}
            onClassificationSave={submitHumanClassification}
            onClassificationEdit={() => setClassificationEditing(true)}
            onAnnotationCountChange={(count) => {
              if (!selectedDetectionId) return;
              setAnnotationCountByCell((current) => ({ ...current, [selectedDetectionId]: count }));
            }}
            onGenerateExplanation={generateExplanation}
            onAudit={() => setAuditOpen(true)}
          />
        ) : (
          <button
            type="button"
            className="cell-panel-restore cell-panel-restore--detail"
            onClick={expandDetail}
            aria-label="Mostrar detalle de la célula seleccionada"
          >
            Detalle {selectedDetection ? <strong>{selectedDetection.cell_code}</strong> : null}
          </button>
        )}

        <section
          id="cell-result-panel"
          className={`cell-experimental-summary cell-summary-panel${resultExpanded ? ' is-expanded' : ''}`}
          role="tabpanel"
          aria-labelledby="cell-experimental-summary-heading"
        >
          <button
            type="button"
            className="cell-result-toggle"
            aria-expanded={resultExpanded}
            aria-controls="cell-result-content"
            onClick={() => setResultExpanded((value) => !value)}
          >
            <span>Resultado experimental</span>
            <strong>
              {classificationSummary
                ? `${classificationSummary.classified_cell_count} / ${classificationSummary.eligible_cell_count}`
                : `${run.detection_count} detecciones`}
            </strong>
          </button>
          <div id="cell-result-content" className="cell-result-content">
            <div>
              <p className="cell-workspace-kicker">Resultado experimental del análisis</p>
              <h2 id="cell-experimental-summary-heading">
                {classificationSummary
                  ? classificationSummary.outcome === 'suspicious_cells_detected'
                    ? 'Células candidatas sospechosas detectadas'
                    : classificationSummary.outcome === 'no_suspicious_cells_detected'
                      ? 'Sin candidatos clasificados como parasitized'
                      : 'Resultado experimental inconcluso'
                  : 'Detección completada sin clasificación'}
              </h2>
              <p>
                {classificationSummary
                  ? classificationSummary.outcome === 'suspicious_cells_detected'
                    ? 'Se identificaron células candidatas clasificadas como parasitized. El resultado requiere revisión experta y no constituye un diagnóstico clínico.'
                    : classificationSummary.outcome === 'no_suspicious_cells_detected'
                      ? 'No se identificaron células candidatas clasificadas como parasitized dentro del conjunto procesado. Esto no descarta malaria ni reemplaza la revisión experta.'
                      : 'El procesamiento no permite establecer un resultado experimental completo. Revise los fallos, advertencias y células próximas al threshold.'
                  : 'Las bounding boxes y crops están disponibles; esta ejecución no contiene una clasificación IA persistida.'}
              </p>
            </div>
            <dl>
              <div><dt>Imágenes</dt><dd>{run.image_count}</dd></div>
              <div><dt>Detecciones</dt><dd>{run.detection_count}</dd></div>
              <div><dt>Revisadas</dt><dd>{run.reviewed_count}</dd></div>
              <div><dt>Pendientes</dt><dd>{counts.unreviewed}</dd></div>
              {classificationSummary ? (
                <>
                  <div><dt>Elegibles</dt><dd>{classificationSummary.eligible_cell_count}</dd></div>
                  <div><dt>Clasificadas</dt><dd>{classificationSummary.classified_cell_count}</dd></div>
                  <div><dt>Candidatos parasitized</dt><dd>{classificationSummary.parasitized_candidate_count}</dd></div>
                  <div><dt>Candidatos uninfected</dt><dd>{classificationSummary.uninfected_candidate_count}</dd></div>
                  <div><dt>Próximas al threshold</dt><dd>{classificationSummary.near_threshold_count}</dd></div>
                  <div><dt>Fallidas</dt><dd>{classificationSummary.failed_prediction_count}</dd></div>
                  <div><dt>Fracción experimental</dt><dd>{classificationSummary.parasitized_candidate_fraction == null ? '—' : `${(classificationSummary.parasitized_candidate_fraction * 100).toFixed(1)} %`}</dd></div>
                  <div><dt>Probabilidad máxima</dt><dd>{optionalMetric(classificationSummary.maximum_probability_parasitized)}</dd></div>
                </>
              ) : null}
              {classificationRun ? (
                <>
                  <div><dt>Modelo</dt><dd>{classificationRun.model_name} {classificationRun.model_version ?? ''}</dd></div>
                  <div><dt>Threshold publicado</dt><dd>{optionalMetric(classificationRun.model_snapshot.threshold)} · {classificationRun.model_snapshot.threshold_source}</dd></div>
                </>
              ) : null}
            </dl>
            {classificationSummary ? (
              <div className="cell-summary-comparison">
                <strong>Resumen automático ≠ Resumen revisado</strong>
                <span>
                  Automático: {classificationSummary.outcome.replaceAll('_', ' ')}
                  {' · '}
                  Revisado: {classificationSummary.reviewed_summary?.outcome?.replaceAll('_', ' ') ?? 'sin revisión suficiente'}
                </span>
              </div>
            ) : null}
          </div>
        </section>

        <ReviewProgressRing run={run} classificationRun={classificationRun} />
      </div>
      <p className="cell-review-live" aria-live="polite">{liveMessage}</p>
      {auditOpen && (predictionDetail ?? selectedPrediction) ? (
        <CellClassificationAuditModal
          prediction={predictionDetail ?? selectedPrediction!}
          run={classificationRun}
          onClose={() => setAuditOpen(false)}
          canGenerate={canExplain}
          onGenerate={generateExplanation}
        />
      ) : null}
      </section>
    </AuthenticatedImageCacheProvider>
  );
}

const DetectionCard = memo(function DetectionCard({
  detection,
  prediction,
  classificationExpected,
  humanLabel,
  annotationCount,
  selected,
  register,
  onSelect,
}: {
  detection: CellDetectionSummary;
  prediction: CellPredictionSummary | null;
  classificationExpected: boolean;
  humanLabel: CanonicalCellLabel | null;
  annotationCount: number;
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
        aria-label={`${detection.cell_code}, ${prediction?.predicted_label ?? reviewStatusLabel[detection.review_status]}, clasificación humana ${humanLabel ?? 'sin revisar'}${annotationCount ? `, ${annotationCount} anotaciones` : ''}`}
        onClick={onSelect}
      >
        <AuthenticatedCropImage
          crop={detection.crop}
          alt={`Crop técnico de la detección ${detection.cell_code}`}
          eager={selected}
        />
        <span className="cell-card-caption">
          <strong>{detection.cell_code}</strong>
          {prediction ? (
            <>
              <span className={`cell-prediction-label prediction-${prediction.predicted_label ?? 'failed'}`}>
                {prediction.prediction_status === 'failed'
                  ? '× Predicción fallida'
                  : `${prediction.predicted_label === 'parasitized' ? 'P' : 'U'} ${prediction.predicted_label}`}
              </span>
              <small>
                P(parasitized) {optionalMetric(prediction.probability_parasitized)}
                {prediction.near_threshold ? ' · ≈ Próxima al threshold' : ''}
              </small>
              <small>
                Explicación: {prediction.explanation?.status ?? prediction.explanation_status ?? 'not_requested'}
                {' · '}
                Revisión: {classificationFilterLabel[prediction.review_status]}
              </small>
              <small className="cell-card-human-indicators">
                {humanLabel ? `Revisada ${humanLabel}` : '○ Sin revisar'}
                {annotationCount ? ` · 📝 ${annotationCount}` : ''}
                {prediction.review_status === 'needs_attention' ? ' · ! Requiere atención' : ''}
              </small>
            </>
          ) : classificationExpected ? (
            <span className="cell-prediction-label prediction-failed">
              × Sin clasificación
            </span>
          ) : (
            <span className={`cell-review-status status-${detection.review_status}`}>
              <span aria-hidden="true">{reviewStatusSymbol[detection.review_status]}</span>
              {reviewStatusLabel[detection.review_status]}
            </span>
          )}
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
  prediction,
  classificationHistory,
  humanClassification,
  classificationEditing,
  classificationRun,
  classificationLoading,
  classificationError,
  canExplain,
  canClassificationReview,
  validationSessionId,
  canAnnotateValidation,
  canReadValidationAnnotations,
  classificationComment,
  reviewedLabel,
  classificationSaving,
  explanationSaving,
  classificationReviewError,
  loading,
  error,
  canReview,
  comment,
  saving,
  reviewError,
  run,
  image,
  onCollapse,
  onCommentChange,
  onReview,
  onNextUnreviewed,
  onClassificationCommentChange,
  onReviewedLabelChange,
  onClassificationSave,
  onClassificationEdit,
  onAnnotationCountChange,
  onGenerateExplanation,
  onAudit,
}: {
  selected: CellDetectionSummary | null;
  detail: CellDetectionDetail | null;
  history: ScientificCellReview[];
  prediction: CellPredictionSummary | CellPredictionDetail | null;
  classificationHistory: CellClassificationReview[];
  humanClassification: HumanCellClassification | null;
  classificationEditing: boolean;
  classificationRun: CellClassificationRunDetail | null;
  classificationLoading: boolean;
  classificationError: string;
  canExplain: boolean;
  canClassificationReview: boolean;
  validationSessionId: string | null;
  canAnnotateValidation: boolean;
  canReadValidationAnnotations: boolean;
  classificationComment: string;
  reviewedLabel: CanonicalCellLabel;
  classificationSaving: boolean;
  explanationSaving: boolean;
  classificationReviewError: string;
  loading: boolean;
  error: string;
  canReview: boolean;
  comment: string;
  saving: boolean;
  reviewError: string;
  run: CellDetectionRunDetail;
  image: CellDetectionImage | null;
  onCollapse: () => void;
  onCommentChange: (value: string) => void;
  onReview: (decision: CellReviewDecision) => void;
  onNextUnreviewed: () => void;
  onClassificationCommentChange: (value: string) => void;
  onReviewedLabelChange: (value: CanonicalCellLabel) => void;
  onClassificationSave: () => void;
  onClassificationEdit: () => void;
  onAnnotationCountChange: (count: number) => void;
  onGenerateExplanation: () => void;
  onAudit: () => void;
}) {
  const detection = detail ?? selected;
  return (
    <section id="cell-detail-panel" className="cell-detail-panel" role="tabpanel" aria-labelledby="cell-detail-heading">
      {detection ? (
        <div className="cell-detail-crop">
          <AuthenticatedCropImage
            crop={detection.crop}
            alt={`Crop ampliado de la detección ${detection.cell_code}`}
            eager
          />
        </div>
      ) : null}
      <header className="cell-panel-heading">
        <div>
          <h2 id="cell-detail-heading">Detalle de la detección candidata</h2>
          <p>{detection?.cell_code ?? 'Sin selección'}</p>
        </div>
        <div className="cell-panel-heading-actions">
          {detection ? (
            <span className={`cell-review-status status-${detection.review_status}`}>
              {reviewStatusSymbol[detection.review_status]} {reviewStatusLabel[detection.review_status]}
            </span>
          ) : null}
          <button type="button" onClick={onCollapse} aria-label="Ocultar detalle de la célula">×</button>
        </div>
      </header>
      {!detection ? <p className="cell-empty-state">Selecciona un crop o una bounding box para ver su detalle.</p> : null}
      {detection ? (
        <div className="cell-detail-content">
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

          {classificationRun ? (
            <section className="cell-classification-detail" aria-labelledby="cell-classification-detail-heading">
              <div className="cell-classification-heading">
                <div>
                  <h3 id="cell-classification-detail-heading">Predicción automática</h3>
                  <p>{classificationRun.classification_run_code}</p>
                </div>
                {prediction ? (
                  <span className={`cell-prediction-label prediction-${prediction.predicted_label ?? 'failed'}`}>
                    {prediction.prediction_status === 'failed'
                      ? '× Fallida'
                      : `${prediction.predicted_label === 'parasitized' ? 'P' : 'U'} ${prediction.predicted_label}`}
                  </span>
                ) : null}
              </div>
              {classificationLoading ? <p className="cell-panel-state">Cargando clasificación…</p> : null}
              {classificationError ? <p className="cell-error" role="alert">{classificationError}</p> : null}
              {prediction ? (
                <>
                  <dl className="cell-detail-facts classification-facts">
                    <div><dt>P(parasitized)</dt><dd>{optionalMetric(prediction.probability_parasitized)}</dd></div>
                    <div><dt>P(uninfected)</dt><dd>{optionalMetric(prediction.probability_uninfected)}</dd></div>
                    <div><dt>Threshold</dt><dd>{optionalMetric(prediction.threshold_used)}</dd></div>
                    <div><dt>Fuente threshold</dt><dd>{prediction.threshold_source}</dd></div>
                    <div><dt>Margen de decisión</dt><dd>{optionalMetric(prediction.decision_margin)}</dd></div>
                    <div><dt>Próxima al threshold</dt><dd>{prediction.near_threshold ? '≈ Sí · revisión prioritaria' : 'No'}</dd></div>
                    <div><dt>Modelo</dt><dd>{classificationRun.model_name}</dd></div>
                    <div><dt>Versión</dt><dd>{classificationRun.model_version ?? '—'}</dd></div>
                    <div><dt>Checkpoint</dt><dd>{`${classificationRun.model_snapshot.checkpoint_sha256.slice(0, 12)}…`}</dd></div>
                    <div><dt>Preprocessing</dt><dd>{
                      'preprocessing_snapshot' in prediction
                        ? JSON.stringify(prediction.preprocessing_snapshot)
                        : JSON.stringify(classificationRun.model_snapshot.preprocessing ?? {})
                    }</dd></div>
                    <div><dt>Estado explicación</dt><dd>{prediction.explanation?.status ?? prediction.explanation_status ?? 'not_requested'}</dd></div>
                    <div><dt>Revisión de clasificación</dt><dd>{classificationFilterLabel[prediction.review_status]}</dd></div>
                  </dl>

                  <CellGradCamPreview prediction={prediction} />

                  <section className="cell-explanation-actions" aria-labelledby="cell-explanation-heading">
                    <h4 id="cell-explanation-heading">Explicabilidad Grad-CAM</h4>
                    {prediction.explanation?.status === 'unsupported' ? (
                      <p>El modelo productivo no admite Grad-CAM con la configuración registrada.</p>
                    ) : null}
                    {prediction.explanation?.status === 'failed' ? (
                      <p>{prediction.explanation.error_message || 'La explicación terminó con error.'}</p>
                    ) : null}
                    {prediction.explanation?.status === 'pending' ? (
                      <p>La explicación permanece en procesamiento. Actualiza el estado para consultarla.</p>
                    ) : null}
                    <div>
                      <button type="button" onClick={onAudit}>Auditar clasificación</button>
                    </div>
                  </section>

                  <section className="cell-classification-review" aria-labelledby="cell-classification-review-heading">
                    <h4 id="cell-classification-review-heading">Revisión humana de clasificación</h4>
                    {humanClassification?.label ? (
                      <div className="human-classification-current">
                        <span>Clasificación humana</span>
                        <strong>{humanClassification.label === 'parasitized' ? 'Parasitized' : 'Uninfected'}</strong>
                        {humanClassification.comment ? <p>{humanClassification.comment}</p> : null}
                        <small>
                          {humanClassification.actor_username ?? humanClassification.actor_user_id}
                          {' · '}{safeDate(humanClassification.created_at)}
                        </small>
                        {humanClassification.label !== prediction.predicted_label ? (
                          <span className="human-ai-disagreement" role="status">
                            Diferencia IA / revisión
                          </span>
                        ) : null}
                        {canClassificationReview && !classificationEditing ? (
                          <button type="button" onClick={onClassificationEdit}>Editar</button>
                        ) : null}
                      </div>
                    ) : <p>Sin revisión de clasificación registrada.</p>}
                    {canClassificationReview && (classificationEditing || !humanClassification?.label) ? (
                      <div className="cell-review-form">
                        <fieldset className="human-label-buttons">
                          <legend>Clasificación humana</legend>
                          <button type="button" aria-pressed={reviewedLabel === 'parasitized'} onClick={() => onReviewedLabelChange('parasitized')}>Parasitized</button>
                          <button type="button" aria-pressed={reviewedLabel === 'uninfected'} onClick={() => onReviewedLabelChange('uninfected')}>Uninfected</button>
                        </fieldset>
                        <label>
                          Comentario <span>(opcional)</span>
                          <textarea
                            value={classificationComment}
                            maxLength={4000}
                            placeholder="Contexto de la clasificación humana"
                            onChange={(event) => onClassificationCommentChange(event.target.value)}
                          />
                        </label>
                        <div className="cell-review-actions">
                          <button type="button" disabled={classificationSaving} onClick={onClassificationSave}>
                            {humanClassification?.label ? 'Guardar cambios' : 'Guardar'}
                          </button>
                          <button type="button" disabled={classificationSaving} onClick={onNextUnreviewed}>Siguiente sin revisar</button>
                        </div>
                        {classificationReviewError ? <p className="cell-error" role="alert">{classificationReviewError}</p> : null}
                      </div>
                    ) : (
                      <p className="cell-readonly-note">
                        Vista de consulta: la predicción automática permanece separada de toda revisión humana.
                      </p>
                    )}
                  </section>

                </>
              ) : <p>No existe una predicción para esta detección.</p>}
            </section>
          ) : null}

          <ScientificAnnotations
            title="ANOTACIONES"
            sessionId={validationSessionId}
            targetType="cell"
            targetId={canReadValidationAnnotations ? detection?.id ?? null : null}
            targetContext={`CÉLULA · ${detection?.cell_code ?? '—'}`}
            canAnnotate={canAnnotateValidation}
            onCountChange={onAnnotationCountChange}
          />

          <section className="cell-human-review" aria-labelledby="cell-human-review-heading">
            <h3 id="cell-human-review-heading">Revisión humana de detección</h3>
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

          {classificationRun ? (
            <section className="cell-review-history classification-review-history" aria-labelledby="cell-classification-history-heading">
              <details>
                <summary><h3 id="cell-classification-history-heading">Historial de clasificación humana</h3></summary>
                {classificationHistory.length ? <ol>
                  {classificationHistory.map((review) => (
                    <li key={review.id}>
                      <div>
                        <strong>{review.decision.replaceAll('_', ' ')}</strong>
                        <span>{safeDate(review.created_at)} · {review.actor_username ?? review.actor_user_id}</span>
                      </div>
                      <p>
                        {review.reviewed_label ? `Label revisado: ${review.reviewed_label}. ` : ''}
                        {review.comment || 'Sin comentario.'}
                      </p>
                    </li>
                  ))}
                </ol> : <p>No existen revisiones de clasificación.</p>}
              </details>
            </section>
          ) : null}

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
