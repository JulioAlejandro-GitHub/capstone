import type {
  CheckpointPolicySummary,
  ClinicalDashboard,
  ClinicalRunSummary,
  DashboardSummary,
  DatasetImagePage,
  DatasetVersionDetail,
  DatasetVersionSummary,
  Datasource,
  ExplainabilityCase,
  ExplainabilityCaseSummary,
  ExplainabilityRow,
  GroupedRunLineageResponse,
  JsonRecord,
  ModelSummary,
  ModelVersionRow,
  DeploymentRow,
  DeploymentReadiness,
  AvailableModel,
  InferenceResult,
  ModelVersionLineageRow,
  ModelContractCandidates,
  ModelProductionReadiness,
  ProductionPublicationResult,
  ProductiveModelAvailability,
  PagedResponse,
  RunDashboard,
  RunArtifact,
  RunClinicalSummary,
  RunDetailResponse,
  RunImagePrediction,
  ThresholdCalibrationSummary,
  TrainingPromotionStatus,
  Stage2Availability,
  Stage2EnablementResult,
  TrainingLineageChildren,
  TrainingSummaryCollection,
  UploadedPrediction,
} from '../types/api';
import type {
  CellAnalysisPage,
  CellDetectionDetail,
  CellDetectionImage,
  CellDetectionReviewResult,
  CellDetectionRunDetail,
  CellDetectionRunSummary,
  CellReviewDecision,
  CellReviewFilter,
  EligibleCellAnalysisRun,
  ScientificCellReview,
  CellDetectionSummary,
} from '../types/cellReview';
import type {
  CellClassificationPage,
  CellClassificationReview,
  CellClassificationReviewCreate,
  CellClassificationRunDetail,
  CellExplanation,
  CellPredictionDetail,
  CellPredictionSummary,
  EligibleCellClassificationRun,
  SmearAnalysisSummary,
  HumanCellClassification,
  HumanCellClassificationHistoryPage,
} from '../types/cellClassification';
import type {
  ScientificValidationAnnotation,
  ScientificValidationAnnotationEvent,
  ScientificValidationPage,
  ScientificValidationSession,
  ScientificValidationSessionSummary,
  ScientificValidationTarget,
} from '../types/scientificValidation';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export const DEFAULT_DATASOURCE = import.meta.env.VITE_DEFAULT_DATASOURCE ?? 'malaria';
const ACCESS_TOKEN_KEY = 'capstone.access_token';
const activeRequests = new Set<AbortController>();
let authenticationFailureHandler: (() => void) | null = null;

export type ScientificSubject = { id: string; subject_code: string; status: string };
export type ScientificSample = { id: string; sample_code: string; status: string };
export type UploadedMicroscopyImage = {
  id: string;
  original_filename: string;
  sha256: string;
  width_px: number;
  height_px: number;
  content_url: string;
};
export type ImageUploadResponse = {
  subject: ScientificSubject;
  sample: ScientificSample;
  case: { id: string; case_code: string };
  slide: { id: string; slide_code: string };
  ingestion_batch: {
    id: string;
    status: 'complete' | 'incomplete' | 'inconsistent';
    acquisition_origin: string;
    source_system: string | null;
    received_image_count: number;
    expected_image_count: number | null;
    created_at: string;
    completed_at: string | null;
  };
  images: UploadedMicroscopyImage[];
  status: 'complete' | 'incomplete' | 'inconsistent';
  counts: { received: number; expected: number | null; ignored: number };
};
export type QualityImage = {
  id: string; microscopy_image_id: string; sequence_number: number; input_sha256: string;
  input_width_px: number; input_height_px: number; original_filename: string; quality_verdict: string | null;
  integrity_verified: boolean | null; warning_codes: string[] | null; failure_codes: string[] | null;
  brightness_mean: number | null; contrast_p95_p05: number | null; entropy_bits: number | null;
  laplacian_variance: number | null; tenengrad_mean: number | null; dark_pixel_ratio: number | null;
  bright_pixel_ratio: number | null; usable_field_ratio: number | null
};
export type AnalysisEvent = {
  id: string; analysis_run_id: string; microscopy_image_id: string | null; event_type: string;
  stage: string; status: string; message_code: string | null; message: string | null;
  progress_current: number | null; progress_total: number | null; created_at: string;
};
export type AnalysisRun = {
  id: string; run_code: string; ingestion_batch_id: string; subject_code: string;
  sample_code: string; slide_code: string; input_image_count: number; quality_profile_key: string;
  quality_profile_version: string; run_status: string; quality_gate_status: string; ready_for_analysis: boolean;
  active_stage: string; requested_by_username: string; created_at: string; images: QualityImage[];
  started_at?: string | null; completed_at?: string | null; updated_at?: string | null;
  events: AnalysisEvent[]; decisions: Array<Record<string, unknown>>
};
export type QueuePriority = 1 | 50 | 100;
export type QualityQueueItem = {
  queue_item_id: string; analysis_run_id: string; run_code: string;
  subject_code: string; sample_code: string; priority: QueuePriority; status: 'queued' | 'running' | 'completed' | 'failed';
  attempt_count: number; requested_by: string; requested_by_username: string; requested_at: string;
  started_at: string | null; completed_at: string | null; failed_at: string | null; last_error_message: string | null
};
export type QualityQueueMutation = {
  id: string; analysis_run_id: string; priority: QueuePriority; status: 'queued' | 'running' | 'completed' | 'failed';
  attempt_count: number; requested_by: string; requested_at: string; started_at: string | null;
  completed_at: string | null; failed_at: string | null; last_error_code: string | null; last_error_message: string | null;
};
export type QualityQueueRecord = QualityQueueItem | QualityQueueMutation;
export type SmearWorkflowImage = UploadedMicroscopyImage & {
  mime_type: string;
  file_size_bytes: number;
  image_sequence_number: number;
  detected_format: string | null;
};
export type SmearWorkflowResponse = {
  stage: string;
  batch: {
    id: string; status: string; acquisition_origin: string; source_system: string | null;
    received_image_count: number; expected_image_count: number | null; created_at: string;
    completed_at: string | null;
  };
  subject: { id: string; subject_code: string; status: string };
  case: { id: string; case_code: string; status: string };
  sample: { id: string; sample_code: string; status: string };
  slide: { id: string; slide_code: string; status: string };
  images: SmearWorkflowImage[];
  analysis_run: AnalysisRun | null;
  queue_item: QualityQueueItem | null;
  detection_run: CellDetectionRunDetail | null;
  classification_run?: CellClassificationRunDetail | null;
  classification_summary?: SmearAnalysisSummary | null;
};
export type SmearAnalysisHistoryItem = {
  ingestion_batch_id: string;
  analysis_run_id: string;
  run_code: string;
  subject_code: string;
  sample_code: string;
  slide_code: string;
  image_count: number;
  analysis_status: string;
  quality_gate_status: string;
  ready_for_analysis: boolean;
  queue_status: string | null;
  detection_run_id: string | null;
  detection_status: string | null;
  detection_count: number;
  reviewed_count: number;
  requested_by_username: string;
  source_system: string | null;
  created_at: string;
  completed_at: string | null;
};
export type SmearAnalysisHistoryPage = {
  items: SmearAnalysisHistoryItem[];
  total: number;
  limit: number;
  offset: number;
};

function readStoredAccessToken() {
  try {
    return window.localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
}

// Module initialization happens before React effects, so early application requests
// also carry the persisted credential while AuthProvider validates it with /me.
let accessToken: string | null = readStoredAccessToken();

export function restoreAccessToken() {
  accessToken = readStoredAccessToken();
  return accessToken;
}

export function setAccessToken(token: string | null) {
  accessToken = token;
  try {
    if (token) window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
    else window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  } catch {
    // Storage can be unavailable; the in-memory session remains usable.
  }
  if (!token) {
    try {
      window.sessionStorage.clear();
    } catch {
      // Session invalidation remains effective even when storage is unavailable.
    }
  }
}

export function onAuthenticationFailure(handler: (() => void) | null) {
  authenticationFailureHandler = handler;
}

export function cancelPendingRequests() {
  activeRequests.forEach((controller) => controller.abort());
  activeRequests.clear();
}

function handleAuthenticationFailure() {
  setAccessToken(null);
  if (authenticationFailureHandler) {
    authenticationFailureHandler();
    return;
  }
  // Fallback for requests that fail before AuthProvider registers its handler.
  if (window.location.pathname !== '/login') window.location.replace('/login');
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number | null,
    public readonly kind: 'http' | 'network' | 'timeout' | 'abort' | 'parse',
    public readonly code: string | null = null,
    public readonly classificationRunId: string | null = null,
    public readonly stage: string | null = null,
    public readonly retryable: boolean | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type QueryValue = string | number | boolean | undefined;
type RequestOptions = {
  init?: RequestInit;
  timeoutMs?: number;
  signal?: AbortSignal;
};
type ArtifactUrlOptions = {
  artifactId?: string | null;
  datasource?: string;
};

type MediaUrlOptions = ArtifactUrlOptions & {
  url?: string | null;
  path?: string | null;
};

async function request<T>(
  path: string,
  params: Record<string, QueryValue> = {},
  options: RequestOptions = {},
) {
  const url = new URL(path, API_BASE_URL);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      url.searchParams.set(key, String(value));
    }
  });

  const controller = new AbortController();
  const abortFromCaller = () => controller.abort();
  if (options.signal?.aborted) controller.abort();
  options.signal?.addEventListener('abort', abortFromCaller, { once: true });
  let timedOut = false;
  activeRequests.add(controller);
  const timeout = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, options.timeoutMs ?? 15000);
  try {
    const headers = new Headers(options.init?.headers);
    if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
    const response = await fetch(url, { ...options.init, headers, signal: controller.signal });
    if (response.status === 401) {
      handleAuthenticationFailure();
    }
    if (!response.ok) {
      const raw = await response.text();
      let payload: JsonObject = {};
      try {
        payload = asObject(JSON.parse(raw));
      } catch {
        // Non-JSON HTTP errors remain HTTP errors, never parse/network errors.
      }
      const detail = asObject(payload.detail);
      const message = typeof detail.message === 'string'
        ? detail.message
        : (typeof payload.detail === 'string' ? payload.detail : raw || response.statusText);
      throw new ApiError(
        message,
        response.status,
        'http',
        typeof detail.code === 'string' ? detail.code : null,
        typeof detail.classification_run_id === 'string' ? detail.classification_run_id : null,
        typeof detail.stage === 'string' ? detail.stage : null,
        typeof detail.retryable === 'boolean' ? detail.retryable : null,
      );
    }
    try {
      return await response.json() as T;
    } catch {
      throw new ApiError(
        'El servidor devolvió una respuesta JSON inválida.',
        response.status,
        'parse',
      );
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(
        timedOut
          ? 'La solicitud superó el tiempo de espera.'
          : 'La solicitud fue cancelada.',
        null,
        timedOut ? 'timeout' : 'abort',
      );
    }
    if (error instanceof ApiError) throw error;
    if (error instanceof TypeError) {
      throw new ApiError('No fue posible conectar con el servidor.', null, 'network');
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
    options.signal?.removeEventListener('abort', abortFromCaller);
    activeRequests.delete(controller);
  }
}

async function requestBlob(path: string, externalSignal?: AbortSignal) {
  const controller = new AbortController();
  const abortFromCaller = () => controller.abort();
  if (externalSignal?.aborted) controller.abort();
  externalSignal?.addEventListener('abort', abortFromCaller, { once: true });
  activeRequests.add(controller);
  const timeout = window.setTimeout(() => controller.abort(), 30000);
  try {
    const headers = new Headers();
    if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
    const response = await fetch(new URL(path, API_BASE_URL), {
      headers,
      signal: controller.signal,
    });
    if (response.status === 401) {
      handleAuthenticationFailure();
    }
    if (!response.ok) {
      throw new ApiError('Contenido autenticado no disponible.', response.status, 'http');
    }
    return response.blob();
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('La descarga fue cancelada o superó el tiempo de espera.', null, 'timeout');
    }
    if (error instanceof ApiError) throw error;
    if (error instanceof TypeError) {
      throw new ApiError('No fue posible conectar con el servidor.', null, 'network');
    }
    throw error;
  } finally {
    externalSignal?.removeEventListener('abort', abortFromCaller);
    window.clearTimeout(timeout);
    activeRequests.delete(controller);
  }
}

function trustedCellContentPath(candidate: string | null | undefined, fallback: string) {
  if (!candidate) return fallback;
  try {
    const parsed = new URL(candidate, API_BASE_URL);
    const base = new URL(API_BASE_URL);
    if (
      parsed.origin === base.origin
      && parsed.pathname.startsWith('/api/v1/cell-analysis/')
    ) {
      return `${parsed.pathname}${parsed.search}`;
    }
  } catch {
    // A backend-provided malformed URL never replaces the governed fallback.
  }
  return fallback;
}

type JsonObject = Record<string, unknown>;

const asObject = (value: unknown): JsonObject => (
  value && typeof value === 'object' && !Array.isArray(value)
    ? value as JsonObject
    : {}
);

function normalizeClassificationRun(
  value: CellClassificationRunDetail,
): CellClassificationRunDetail {
  const raw = value as CellClassificationRunDetail & {
    reviewed_count?: number;
    unreviewed_count?: number;
    confirmed_count?: number;
    corrected_count?: number;
    needs_attention_review_count?: number;
  };
  if (raw.review_counts) return raw;
  return {
    ...raw,
    review_counts: {
      unreviewed: raw.unreviewed_count ?? Math.max(
        0,
        (raw.processed_count ?? 0) - (raw.reviewed_count ?? 0),
      ),
      confirmed: raw.confirmed_count ?? 0,
      corrected: raw.corrected_count ?? 0,
      needs_attention: raw.needs_attention_review_count ?? 0,
    },
  };
}

function normalizeExplanation(raw: JsonObject): CellExplanation | null {
  const nested = asObject(raw.explanation);
  if (Object.keys(nested).length) return nested as unknown as CellExplanation;
  const id = raw.explanation_id;
  if (typeof id !== 'string') return null;
  return {
    id,
    cell_prediction_id: String(raw.id ?? ''),
    method: String(raw.explanation_method ?? ''),
    method_version: String(raw.explanation_method_version ?? ''),
    status: String(raw.explanation_status ?? 'not_requested') as CellExplanation['status'],
    last_conv_layer:
      typeof raw.explanation_last_conv_layer === 'string'
        ? raw.explanation_last_conv_layer
        : null,
    parameters_json: asObject(raw.explanation_parameters_json),
    width_px: typeof raw.explanation_width_px === 'number' ? raw.explanation_width_px : null,
    height_px: typeof raw.explanation_height_px === 'number' ? raw.explanation_height_px : null,
    started_at:
      typeof raw.explanation_started_at === 'string' ? raw.explanation_started_at : null,
    completed_at:
      typeof raw.explanation_completed_at === 'string' ? raw.explanation_completed_at : null,
    error_code:
      typeof raw.explanation_error_code === 'string' ? raw.explanation_error_code : null,
    error_message:
      typeof raw.explanation_error_message === 'string' ? raw.explanation_error_message : null,
    created_at:
      typeof raw.explanation_created_at === 'string'
        ? raw.explanation_created_at
        : String(raw.created_at ?? ''),
  };
}

function normalizeClassificationReview(raw: JsonObject): CellClassificationReview | null {
  const nested = asObject(raw.latest_review);
  if (Object.keys(nested).length) {
    return nested as unknown as CellClassificationReview;
  }
  if (typeof raw.latest_review_id !== 'string') return null;
  return {
    id: raw.latest_review_id,
    cell_prediction_id: String(raw.id ?? ''),
    decision: String(raw.review_status ?? 'comment_only') as CellClassificationReview['decision'],
    reviewed_label:
      raw.latest_reviewed_label === 'parasitized'
        || raw.latest_reviewed_label === 'uninfected'
        ? raw.latest_reviewed_label
        : null,
    comment:
      typeof raw.latest_review_comment === 'string' ? raw.latest_review_comment : null,
    actor_user_id: String(raw.latest_review_actor_user_id ?? ''),
    actor_username:
      typeof raw.latest_review_actor_username === 'string'
        ? raw.latest_review_actor_username
        : null,
    created_at: String(raw.latest_review_created_at ?? ''),
  };
}

function normalizePrediction<T extends CellPredictionSummary>(value: T): T {
  const raw = value as T & JsonObject;
  const crop = Object.keys(asObject(raw.crop)).length
    ? raw.crop
    : typeof raw.crop_id === 'string'
      ? {
        id: raw.crop_id,
        sha256: String(raw.crop_persisted_sha256 ?? ''),
        width_px: Number(raw.crop_width_px ?? 0),
        height_px: Number(raw.crop_height_px ?? 0),
        format: 'png',
        padding_px: 0,
        content_url: `/api/v1/cell-analysis/crops/${encodeURIComponent(raw.crop_id)}/content`,
      }
      : null;
  const publicRaw = { ...raw };
  [
    'crop_storage_key',
    'relative_storage_key',
    'checkpoint_path',
    'model_path',
    'heatmap_storage_key',
    'overlay_storage_key',
  ].forEach((key) => delete publicRaw[key]);
  return {
    ...publicRaw,
    crop,
    explanation: normalizeExplanation(raw),
    latest_review: normalizeClassificationReview(raw),
  } as T;
}

function normalizeClassificationSummary(
  value: SmearAnalysisSummary | {
    automatic_summary: SmearAnalysisSummary;
    reviewed_summary?: SmearAnalysisSummary['reviewed_summary'];
  },
): SmearAnalysisSummary {
  if ('automatic_summary' in value) {
    return {
      ...value.automatic_summary,
      reviewed_summary: value.reviewed_summary ?? null,
    };
  }
  return value;
}

export const authApi = {
  login(username: string, password: string) {
    return request<{ access_token: string }>('/api/v1/auth/login', {}, {
      init: {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      },
    });
  },
  me() {
    return request<{ id: string; username: string; roles: string[]; permissions: string[] }>('/api/v1/auth/me');
  },
};

function withDatasource(datasource: string) {
  return { datasource };
}

export const api = {
  absoluteUrl(pathOrUrl: string | null | undefined) {
    if (!pathOrUrl) return null;
    try {
      const url = new URL(pathOrUrl, API_BASE_URL);
      return url.protocol === 'http:' || url.protocol === 'https:' ? url.toString() : null;
    } catch {
      return null;
    }
  },

  artifactUrl(path: string | null | undefined, options: ArtifactUrlOptions = {}) {
    const url = new URL('/artifacts/file', API_BASE_URL);
    if (options.datasource) {
      url.searchParams.set('datasource', options.datasource);
    }
    if (options.artifactId) {
      url.searchParams.set('artifact_id', options.artifactId);
    } else if (path) {
      url.searchParams.set('path', path);
    }
    return url.toString();
  },

  mediaUrl({ url, path, artifactId, datasource }: MediaUrlOptions) {
    const enrichedUrl = this.absoluteUrl(url);
    if (enrichedUrl) return enrichedUrl;
    if (!path && !artifactId) return null;
    return this.artifactUrl(path, { artifactId, datasource });
  },

  getDatasources() {
    return request<{ items: Datasource[] }>('/datasources');
  },

  lookupScientificSubject(subjectCode: string) {
    return request<ScientificSubject>('/api/v1/scientific/subjects/lookup', {
      subject_code: subjectCode,
    });
  },

  getScientificSamples(subjectId: string) {
    return request<{ items: ScientificSample[] }>(`/api/v1/scientific/subjects/${subjectId}/samples`);
  },

  uploadMicroscopyImages(form: FormData) {
    const token = localStorage.getItem('capstone.access_token');
    const headers = new Headers();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    return request<ImageUploadResponse>('/api/v1/scientific/images/upload', {}, {
      timeoutMs: 120000,
      init: { method: 'POST', body: form, headers },
    });
  },

  createAnalysisRun(ingestion_batch_id: string) {
    return request<AnalysisRun>('/api/v1/analysis/runs', {}, {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ingestion_batch_id }) },
    });
  },
  getAnalysisRun(runId: string) { return request<AnalysisRun>(`/api/v1/analysis/runs/${runId}`); },
  getSmearWorkflow(ingestionBatchId: string) {
    return request<SmearWorkflowResponse>(
      `/api/v1/scientific/workflows/${encodeURIComponent(ingestionBatchId)}`,
    );
  },
  getSmearAnalysisHistory(params: Record<string, QueryValue> = {}) {
    return request<SmearAnalysisHistoryPage>(
      '/api/v1/scientific/workflows',
      params,
    );
  },
  getSmearAnalysisHistoryDetail(analysisRunId: string) {
    return request<SmearWorkflowResponse>(
      `/api/v1/scientific/analysis-history/${encodeURIComponent(analysisRunId)}`,
    );
  },
  async getMicroscopyImageBlob(imageId: string) {
    const blob = await requestBlob(
      `/api/v1/scientific/images/${encodeURIComponent(imageId)}/content`,
    );
    return URL.createObjectURL(blob);
  },
  getEligibleCellAnalysisRuns(params: Record<string, QueryValue> = {}) {
    return request<CellAnalysisPage<EligibleCellAnalysisRun>>(
      '/api/v1/cell-analysis/eligible-analysis-runs',
      params,
    );
  },
  createCellDetectionRun(analysisRunId: string) {
    return request<CellDetectionRunDetail>('/api/v1/cell-analysis/detection-runs', {}, {
      timeoutMs: 120000,
      init: {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis_run_id: analysisRunId }),
      },
    });
  },
  getCellDetectionRuns(params: Record<string, QueryValue> = {}) {
    return request<CellAnalysisPage<CellDetectionRunSummary>>(
      '/api/v1/cell-analysis/detection-runs',
      params,
    );
  },
  getCellDetectionRun(detectionRunId: string) {
    return request<CellDetectionRunDetail>(
      `/api/v1/cell-analysis/detection-runs/${encodeURIComponent(detectionRunId)}`,
    );
  },
  getCellDetectionImages(detectionRunId: string) {
    return request<CellAnalysisPage<CellDetectionImage>>(
      `/api/v1/cell-analysis/detection-runs/${encodeURIComponent(detectionRunId)}/images`,
    );
  },
  getCellDetections(
    detectionRunId: string,
    microscopyImageId: string,
    params: { review_status?: Exclude<CellReviewFilter, 'all'>; limit?: number; offset?: number } = {},
  ) {
    return request<CellAnalysisPage<CellDetectionSummary>>(
      `/api/v1/cell-analysis/detection-runs/${encodeURIComponent(detectionRunId)}/images/${encodeURIComponent(microscopyImageId)}/detections`,
      params,
    );
  },
  getCellDetection(cellDetectionId: string) {
    return request<CellDetectionDetail>(
      `/api/v1/cell-analysis/detections/${encodeURIComponent(cellDetectionId)}`,
    );
  },
  getCellReviews(cellDetectionId: string) {
    return request<CellAnalysisPage<ScientificCellReview>>(
      `/api/v1/cell-analysis/detections/${encodeURIComponent(cellDetectionId)}/reviews`,
    );
  },
  createCellReview(
    cellDetectionId: string,
    decision: CellReviewDecision,
    comment?: string,
  ) {
    return request<CellDetectionReviewResult>(
      `/api/v1/cell-analysis/detections/${encodeURIComponent(cellDetectionId)}/reviews`,
      {},
      {
        init: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision, comment: comment?.trim() || undefined }),
        },
      },
    );
  },
  getCellCropBlob(cropId: string, contentUrl?: string | null, signal?: AbortSignal) {
    const fallback = `/api/v1/cell-analysis/crops/${encodeURIComponent(cropId)}/content`;
    return requestBlob(trustedCellContentPath(contentUrl, fallback), signal);
  },
  getCellOriginalImageBlob(
    detectionRunId: string,
    microscopyImageId: string,
    contentUrl?: string | null,
    signal?: AbortSignal,
  ) {
    const fallback = `/api/v1/cell-analysis/detection-runs/${encodeURIComponent(detectionRunId)}/images/${encodeURIComponent(microscopyImageId)}/content`;
    return requestBlob(trustedCellContentPath(contentUrl, fallback), signal);
  },
  getEligibleCellClassificationRuns(params: Record<string, QueryValue> = {}) {
    return request<CellClassificationPage<EligibleCellClassificationRun & { id?: string }>>(
      '/api/v1/cell-classification/eligible-detection-runs',
      params,
    ).then((page) => ({
      ...page,
      items: page.items.map((item) => ({
        ...item,
        detection_run_id: item.detection_run_id ?? item.id ?? '',
        eligible: item.eligible ?? true,
        productive_model: item.productive_model ?? null,
      })),
    }));
  },
  createCellClassificationRun(detectionRunId: string) {
    return request<CellClassificationRunDetail>(
      '/api/v1/cell-classification/classification-runs',
      {},
      {
        timeoutMs: 600000,
        init: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ detection_run_id: detectionRunId }),
        },
      },
    ).then(normalizeClassificationRun);
  },
  getCellClassificationRuns(params: Record<string, QueryValue> = {}) {
    return request<CellClassificationPage<CellClassificationRunDetail>>(
      '/api/v1/cell-classification/classification-runs',
      params,
    ).then((page) => ({
      ...page,
      items: page.items.map(normalizeClassificationRun),
    }));
  },
  getCellClassificationRun(classificationRunId: string) {
    return request<CellClassificationRunDetail>(
      `/api/v1/cell-classification/classification-runs/${encodeURIComponent(classificationRunId)}`,
    ).then(normalizeClassificationRun);
  },
  getCellClassificationPredictions(
    classificationRunId: string,
    params: Record<string, QueryValue> = {},
  ) {
    return request<CellClassificationPage<CellPredictionSummary>>(
      `/api/v1/cell-classification/classification-runs/${encodeURIComponent(classificationRunId)}/predictions`,
      params,
    ).then((page) => ({
      ...page,
      items: page.items.map(normalizePrediction),
    }));
  },
  getCellClassificationSummary(classificationRunId: string) {
    return request<
      SmearAnalysisSummary
      | {
        automatic_summary: SmearAnalysisSummary;
        reviewed_summary?: SmearAnalysisSummary['reviewed_summary'];
      }
    >(
      `/api/v1/cell-classification/classification-runs/${encodeURIComponent(classificationRunId)}/summary`,
    ).then(normalizeClassificationSummary);
  },
  getCellPrediction(predictionId: string) {
    return request<CellPredictionDetail>(
      `/api/v1/cell-classification/predictions/${encodeURIComponent(predictionId)}`,
    ).then(normalizePrediction);
  },
  createCellExplanation(predictionId: string, retry = false) {
    return request<CellExplanation>(
      `/api/v1/cell-classification/predictions/${encodeURIComponent(predictionId)}/explanation`,
      {},
      {
        timeoutMs: 180000,
        init: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ retry }),
        },
      },
    );
  },
  getCellExplanation(predictionId: string) {
    return request<CellExplanation>(
      `/api/v1/cell-classification/predictions/${encodeURIComponent(predictionId)}/explanation`,
    );
  },
  generateCaseGradCam(explainabilityId: string) {
    return request<ExplainabilityCase>(
      `/api/v1/explainability/cases/${encodeURIComponent(explainabilityId)}/gradcam`,
      {},
      { timeoutMs: 180000, init: { method: 'POST' } },
    );
  },
  getCellExplanationHeatmapBlob(explanationId: string, signal?: AbortSignal) {
    return requestBlob(
      `/api/v1/cell-classification/explanations/${encodeURIComponent(explanationId)}/heatmap`,
      signal,
    );
  },
  getCellExplanationOverlayBlob(explanationId: string, signal?: AbortSignal) {
    return requestBlob(
      `/api/v1/cell-classification/explanations/${encodeURIComponent(explanationId)}/overlay`,
      signal,
    );
  },
  createCellClassificationReview(
    predictionId: string,
    payload: CellClassificationReviewCreate,
  ) {
    return request<CellClassificationReview>(
      `/api/v1/cell-classification/predictions/${encodeURIComponent(predictionId)}/reviews`,
      {},
      {
        init: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            decision: payload.decision,
            reviewed_label: payload.reviewed_label,
            comment: payload.comment?.trim() || undefined,
          }),
        },
      },
    );
  },
  getCellClassificationReviews(predictionId: string) {
    return request<CellClassificationPage<CellClassificationReview>>(
      `/api/v1/cell-classification/predictions/${encodeURIComponent(predictionId)}/reviews`,
    );
  },
  getHumanCellClassification(predictionId: string) {
    return request<HumanCellClassification>(
      `/api/v1/cell-classification/predictions/${encodeURIComponent(predictionId)}/human-classification`,
    );
  },
  saveHumanCellClassification(
    predictionId: string,
    label: 'parasitized' | 'uninfected',
    comment?: string,
  ) {
    return request<HumanCellClassification>(
      `/api/v1/cell-classification/predictions/${encodeURIComponent(predictionId)}/human-classification`,
      {},
      {
        init: {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ label, comment: comment?.trim() || null }),
        },
      },
    );
  },
  getHumanCellClassificationHistory(predictionId: string) {
    return request<HumanCellClassificationHistoryPage>(
      `/api/v1/cell-classification/predictions/${encodeURIComponent(predictionId)}/human-classification/history`,
    );
  },
  listScientificValidationSessions() {
    return request<ScientificValidationPage<ScientificValidationSessionSummary>>(
      '/api/v1/scientific-validation/sessions', { limit: 200, offset: 0 },
    );
  },
  getScientificValidationSession(sessionId: string) {
    return request<ScientificValidationSession>(
      `/api/v1/scientific-validation/sessions/${encodeURIComponent(sessionId)}`,
    );
  },
  async resolveScientificValidationSession(
    detectionRunId: string,
    classificationRunId?: string | null,
  ) {
    const page = await this.listScientificValidationSessions();
    for (const item of page.items) {
      const session = await this.getScientificValidationSession(item.id);
      if (
        session.detection_run_ids.includes(detectionRunId)
        || Boolean(classificationRunId && session.classification_run_ids.includes(classificationRunId))
      ) return session;
    }
    return null;
  },
  listScientificValidationAnnotations(
    sessionId: string | null,
    filters: {
      target_type?: ScientificValidationTarget;
      cell_id?: string;
      analysis_run_id?: string;
      sample_id?: string;
      category?: string;
    },
  ) {
    return request<ScientificValidationPage<ScientificValidationAnnotation>>(
      sessionId
        ? `/api/v1/scientific-validation/sessions/${encodeURIComponent(sessionId)}/annotations`
        : '/api/v1/scientific-annotations',
      { ...filters, limit: 500, offset: 0 },
    );
  },
  createScientificValidationAnnotation(
    sessionId: string | null,
    payload: {
      target_type: ScientificValidationTarget;
      cell_id?: string;
      analysis_run_id?: string;
      sample_id?: string;
      category: string;
      content: string;
    },
  ) {
    return request<ScientificValidationAnnotation>(
      sessionId
        ? `/api/v1/scientific-validation/sessions/${encodeURIComponent(sessionId)}/annotations`
        : '/api/v1/scientific-annotations',
      {},
      { init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) } },
    );
  },
  updateScientificValidationAnnotation(
    sessionId: string | null,
    annotationId: string,
    payload: { category: string; content: string; version: number },
  ) {
    return request<ScientificValidationAnnotation>(
      sessionId
        ? `/api/v1/scientific-validation/sessions/${encodeURIComponent(sessionId)}/annotations/${encodeURIComponent(annotationId)}`
        : `/api/v1/scientific-annotations/${encodeURIComponent(annotationId)}`,
      {},
      { init: { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) } },
    );
  },
  getScientificValidationAnnotationHistory(sessionId: string | null, annotationId: string) {
    return request<ScientificValidationPage<ScientificValidationAnnotationEvent>>(
      sessionId
        ? `/api/v1/scientific-validation/sessions/${encodeURIComponent(sessionId)}/annotations/${encodeURIComponent(annotationId)}/history`
        : `/api/v1/scientific-annotations/${encodeURIComponent(annotationId)}/history`,
    );
  },
  reviewQuality(runId: string, decision: 'approve_with_warnings' | 'reject', comment: string) {
    return request<AnalysisRun>(`/api/v1/analysis/runs/${runId}/quality-decision`, {}, {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision, comment }) },
    });
  },
  enqueueQuality(analysis_run_id: string, priority: QueuePriority = 50) {
    return request<QualityQueueMutation>('/api/v1/analysis/queue', {}, {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ analysis_run_id, priority }) },
    });
  },
  executeQueueItem(queueItemId: string) {
    return request<QualityQueueMutation>(`/api/v1/analysis/queue/${queueItemId}/execute`, {}, {
      timeoutMs: 120000, init: { method: 'POST' },
    });
  },
  retryQueueItem(queueItemId: string, priority: QueuePriority) {
    return request<QualityQueueMutation>(`/api/v1/analysis/queue/${queueItemId}/retry`, {}, {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ priority }) },
    });
  },

  getDashboardSummary(datasource: string) {
    return request<DashboardSummary>('/dashboard/summary', withDatasource(datasource));
  },

  getClinicalDashboard(datasource: string) {
    return request<ClinicalDashboard>('/dashboard/clinical', withDatasource(datasource));
  },

  getRuns(datasource: string) {
    return request<{ items: RunDashboard[] }>('/runs', withDatasource(datasource));
  },

  getGroupedRunLineage(datasource: string) {
    return request<GroupedRunLineageResponse>(
      '/runs/grouped-lineage',
      withDatasource(datasource),
    );
  },

  getTrainingSummaries({
    datasource,
    limit = 100,
    signal,
  }: {
    datasource: string;
    limit?: number;
    signal?: AbortSignal;
  }) {
    return request<TrainingSummaryCollection>(
      '/runs/training-summaries',
      { datasource, limit },
      { signal },
    );
  },

  getTrainingLineageChildren({
    trainingRunId,
    datasource,
    limit = 100,
    signal,
  }: {
    trainingRunId: string;
    datasource: string;
    limit?: number;
    signal?: AbortSignal;
  }) {
    return request<TrainingLineageChildren>(
      `/runs/${encodeURIComponent(trainingRunId)}/lineage-children`,
      { datasource, limit },
      { signal },
    );
  },

  getTrainingPromotionStatus(datasource: string, trainingRunId: string) {
    return request<TrainingPromotionStatus>(
      `/api/training-runs/${trainingRunId}/promotion-status`,
      withDatasource(datasource),
    );
  },

  prepareTrainingRelease(
    datasource: string,
    trainingRunId: string,
    targetEnvironment?: string,
  ) {
    return request<TrainingPromotionStatus>(
      `/api/training-runs/${trainingRunId}/prepare-release`,
      withDatasource(datasource),
      {
        timeoutMs: 30000,
        init: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            target_environment: targetEnvironment || undefined,
          }),
        },
      },
    );
  },

  getStage2Availability(datasource: string, trainingRunId: string, signal?: AbortSignal) {
    return request<Stage2Availability>(
      `/api/training-runs/${trainingRunId}/stage2-availability`,
      withDatasource(datasource), { timeoutMs: 30000, signal },
    );
  },
  getStage2ReleaseStatus(datasource: string, trainingRunId: string, signal?: AbortSignal) {
    return request<Stage2Availability>(
      `/api/training-runs/${trainingRunId}/stage2-release-status`,
      withDatasource(datasource),
      { timeoutMs: 30000, signal },
    );
  },
  getProductiveModelAvailability(datasource: string) {
    return request<ProductiveModelAvailability>(
      '/api/stage2/productive-model-availability', withDatasource(datasource),
      { timeoutMs: 30000 },
    );
  },
  publishStage2Model(datasource: string, modelVersionId: string, payload: {
    actor?: string; reason?: string; replace_existing?: boolean;
  }) {
    return request<Stage2Availability>(
      `/api/model-versions/${modelVersionId}/stage2-publications`,
      withDatasource(datasource), {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
    },
    );
  },
  deactivateStage2Publication(datasource: string, publicationId: string, payload: {
    actor?: string; reason?: string;
  }) {
    return request<Stage2Availability>(
      `/api/stage2-publications/${publicationId}/deactivate`,
      withDatasource(datasource), {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
    },
    );
  },

  enableStage2(datasource: string, trainingRunId: string, payload: {
    actor: string; reason: string; confirm_stage2_enablement: boolean;
    preprocessing_candidate_id?: string; threshold_candidate_id?: string; source_image_id?: string;
  }) {
    return request<Stage2EnablementResult>(
      `/api/training-runs/${trainingRunId}/enable-stage2`,
      withDatasource(datasource), {
      timeoutMs: 120000,
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
    },
    );
  },
  publishTrainingStage2(datasource: string, trainingRunId: string, payload: {
    actor: string; reason: string; confirm_publication: boolean; source_image_id?: string;
  }) {
    return request<Stage2EnablementResult>(
      `/api/training-runs/${trainingRunId}/publish-technical-production`,
      withDatasource(datasource),
      { init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }, timeoutMs: 120000 },
    );
  },

  getStage2Models(datasource: string) {
    return request<{ items: Stage2EnablementResult[] }>('/api/stage2/models', withDatasource(datasource));
  },

  getTechnicalProductionPreview(datasource: string, modelVersionId: string) {
    return request<Stage2Availability>(
      `/api/model-versions/${modelVersionId}/technical-production-preview`,
      withDatasource(datasource), { timeoutMs: 30000 },
    );
  },

  publishTechnicalProduction(datasource: string, modelVersionId: string, payload: {
    actor: string; reason: string; confirm_publication: boolean;
    preprocessing_profile?: string; threshold?: number; source_image_id?: string;
  }) {
    return request<Stage2EnablementResult>(
      `/api/model-versions/${modelVersionId}/publish-technical-production`,
      withDatasource(datasource), {
      timeoutMs: 120000,
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
    },
    );
  },

  getRun(datasource: string, runId: string) {
    return request<RunDetailResponse>(`/runs/${runId}`, withDatasource(datasource));
  },

  getRunClinicalSummary(datasource: string, runId: string) {
    return request<RunClinicalSummary>(`/runs/${runId}/clinical-summary`, withDatasource(datasource));
  },

  getRunCheckpointPolicy(datasource: string, runId: string) {
    return request<{ items: CheckpointPolicySummary[] }>(
      `/runs/${runId}/checkpoint-policy`,
      withDatasource(datasource),
    );
  },

  getRunThresholdCalibration(datasource: string, runId: string) {
    return request<{ items: ThresholdCalibrationSummary[] }>(
      `/runs/${runId}/threshold-calibration`,
      withDatasource(datasource),
    );
  },

  getRunArtifactsSummary(datasource: string, runId: string) {
    return request<{ items: RunArtifact[] }>(`/runs/${runId}/artifacts`, withDatasource(datasource));
  },

  getRunImagePredictions(datasource: string, runId: string, params: Record<string, QueryValue> = {}) {
    return request<PagedResponse<RunImagePrediction>>(`/runs/${runId}/image-predictions`, {
      datasource,
      ...params,
    });
  },

  getRunExplainability(datasource: string, runId: string, params: Record<string, QueryValue> = {}) {
    return request<PagedResponse<ExplainabilityCase>>(`/runs/${runId}/explainability`, {
      datasource,
      ...params,
    }, {
      timeoutMs: 30000,
    });
  },

  getModels(datasource: string) {
    return request<{ items: ModelSummary[] }>('/models', withDatasource(datasource));
  },

  getModelVersions(datasource: string) {
    return request<{ items: ModelVersionRow[] }>('/api/model-versions', withDatasource(datasource));
  },

  getModelVersion(datasource: string, modelVersionId: string) {
    return request<ModelVersionRow>(`/api/model-versions/${modelVersionId}`, withDatasource(datasource));
  },

  getModelVersionLineage(datasource: string, modelVersionId: string) {
    return request<{ items: ModelVersionLineageRow[] }>(`/api/model-versions/${modelVersionId}/lineage`, withDatasource(datasource));
  },

  getModelVersionContractCandidates(datasource: string, modelVersionId: string) {
    return request<ModelContractCandidates>(`/api/model-versions/${modelVersionId}/contract-candidates`, withDatasource(datasource), { timeoutMs: 30000 });
  },

  completeModelVersionContract(datasource: string, modelVersionId: string, selections: Record<string, string>, actor: string, reason: string) {
    return request<{ model_version: ModelVersionRow; threshold_profile_id: string }>(`/api/model-versions/${modelVersionId}/build-production-package`, withDatasource(datasource), {
      timeoutMs: 30000, init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ selections, actor, reason }) },
    });
  },

  publishModelVersionToProduction(datasource: string, modelVersionId: string, payload: { deployment_name: string; alias: 'champion'; actor: string; reason: string; confirm_production: boolean; source_image_id?: string }) {
    return request<ProductionPublicationResult>(`/api/model-versions/${modelVersionId}/publish-to-production`, withDatasource(datasource), {
      timeoutMs: 120000, init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
    });
  },

  getModelProductionReadiness(datasource: string, modelVersionId: string) {
    return request<ModelProductionReadiness>(`/api/model-versions/${modelVersionId}/production-readiness`, withDatasource(datasource), { timeoutMs: 30000 });
  },

  getDeployments(datasource: string, active = false) {
    return request<{ items: DeploymentRow[] }>(active ? '/api/deployments/active' : '/api/deployments', withDatasource(datasource));
  },

  getDeploymentReadiness(datasource: string, deploymentId: string) {
    return request<DeploymentReadiness>(`/api/deployments/${deploymentId}/readiness`, withDatasource(datasource), { timeoutMs: 30000 });
  },

  getAvailableModels(datasource: string, environment?: string) {
    return request<{ items: AvailableModel[] }>('/api/models/available', { datasource, environment });
  },

  validateModelVersion(datasource: string, modelVersionId: string, thresholdProfileId: string, actor: string, reason: string) {
    return request<ModelVersionRow>(`/api/model-versions/${modelVersionId}/validate`, withDatasource(datasource), {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ threshold_profile_id: thresholdProfileId, actor, reason }) },
    });
  },

  approveModelVersion(datasource: string, modelVersionId: string, actor: string, reason: string) {
    return request<ModelVersionRow>(`/api/model-versions/${modelVersionId}/approve`, withDatasource(datasource), {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actor, reason }) },
    });
  },

  createDeployment(datasource: string, payload: { model_version_id: string; deployment_name: string; environment: string; alias: string; threshold_profile_id: string; deployed_by: string }) {
    return request<DeploymentRow>('/api/deployments', withDatasource(datasource), {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...payload, activate: false }) },
    });
  },

  smokeTestDeployment(datasource: string, deploymentId: string, sourceImageId: string, actor: string) {
    return request<{ deployment: DeploymentRow; smoke_test: JsonRecord }>(`/api/deployments/${deploymentId}/smoke-test`, withDatasource(datasource), {
      timeoutMs: 30000, init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source_image_id: sourceImageId, actor }) },
    });
  },

  activateDeployment(datasource: string, deploymentId: string, actor: string, confirmProduction: boolean) {
    return request<DeploymentRow>(`/api/deployments/${deploymentId}/activate`, withDatasource(datasource), {
      timeoutMs: 30000, init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actor, confirm_production: confirmProduction }) },
    });
  },

  transitionDeployment(datasource: string, deploymentId: string, action: 'deactivate' | 'retire', actor: string, reason: string) {
    return request<DeploymentRow>(`/api/deployments/${deploymentId}/${action}`, withDatasource(datasource), {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actor, reason }) },
    });
  },

  rollbackDeployment(datasource: string, deploymentId: string, targetDeploymentId: string, actor: string, reason: string) {
    return request<DeploymentRow>(`/api/deployments/${deploymentId}/rollback`, withDatasource(datasource), {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target_deployment_id: targetDeploymentId, actor, reason }) },
    });
  },

  createImageAnalysisJob(datasource: string, deployedModelVersionId: string, sourceImageId: string) {
    return request<InferenceResult>('/api/image-analysis-jobs', withDatasource(datasource), {
      timeoutMs: 30000, init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ deployed_model_version_id: deployedModelVersionId, source_image_id: sourceImageId }) },
    });
  },

  getClinicalModelComparison(datasource: string) {
    return request<{ items: ClinicalRunSummary[] }>('/models/comparison', withDatasource(datasource));
  },

  getDatasets(datasource: string) {
    return request<{ items: JsonRecord[] }>('/datasets', withDatasource(datasource));
  },

  getDatasetVersions(datasource: string) {
    return request<{ items: DatasetVersionSummary[] }>('/api/datasets', withDatasource(datasource));
  },

  getDatasetVersionDetail(datasource: string, datasetVersionId: string) {
    return request<DatasetVersionDetail>(`/api/datasets/${datasetVersionId}`, withDatasource(datasource));
  },

  getDatasetImages(datasource: string, params: Record<string, QueryValue> = {}) {
    return request<DatasetImagePage>('/api/dataset/images', {
      datasource,
      ...params,
    });
  },

  getMetrics(datasource: string, runId: string) {
    return request<{ items: JsonRecord[] }>(`/metrics/${runId}`, withDatasource(datasource));
  },

  getConfusionMatrix(datasource: string, runId: string) {
    return request<{ items: JsonRecord[] }>(`/confusion-matrix/${runId}`, withDatasource(datasource));
  },

  getClassificationReport(datasource: string, runId: string) {
    return request<{ items: JsonRecord[] }>(`/classification-report/${runId}`, withDatasource(datasource));
  },

  getExplainability(datasource: string) {
    return request<{ summary: JsonRecord[]; items: ExplainabilityRow[] }>(
      '/explainability',
      withDatasource(datasource),
    );
  },

  getExplainabilityCases(datasource: string, params: Record<string, QueryValue> = {}) {
    return request<PagedResponse<ExplainabilityCase>>('/explainability/cases', {
      datasource,
      ...params,
    });
  },

  getFalsePositiveCases(datasource: string, params: Record<string, QueryValue> = {}) {
    return request<PagedResponse<ExplainabilityCase>>('/explainability/cases/false-positives', {
      datasource,
      ...params,
    });
  },

  getFalseNegativeCases(datasource: string, params: Record<string, QueryValue> = {}) {
    return request<PagedResponse<ExplainabilityCase>>('/explainability/cases/false-negatives', {
      datasource,
      ...params,
    });
  },

  getLowConfidenceCases(datasource: string, params: Record<string, QueryValue> = {}) {
    return request<PagedResponse<ExplainabilityCase>>('/explainability/cases/low-confidence', {
      datasource,
      ...params,
    });
  },

  getExplainabilityCaseSummary(datasource: string, params: Record<string, QueryValue> = {}) {
    return request<PagedResponse<ExplainabilityCaseSummary>>('/explainability/cases/summary', {
      datasource,
      ...params,
    });
  },

  getExplainabilityGallery(datasource: string, params: Record<string, QueryValue> = {}) {
    return request<PagedResponse<ExplainabilityCase>>('/explainability/gallery', {
      datasource,
      ...params,
    });
  },

  getUploadedPredictions(datasource: string, params: Record<string, QueryValue> = {}) {
    return request<PagedResponse<UploadedPrediction>>('/predictions/uploads', {
      datasource,
      ...params,
    });
  },

  getErrors(datasource: string) {
    return request<{ items: JsonRecord[] }>('/errors', withDatasource(datasource));
  },

  getLogs(datasource: string) {
    return request<{ items: JsonRecord[] }>('/logs', withDatasource(datasource));
  },
};
