import type {
  ArtifactRow,
  CheckpointPolicySummary,
  ClinicalDashboard,
  ClinicalRunSummary,
  DashboardSummary,
  DatasetBrowserSummary,
  DatasetImagePage,
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
export type EligibleBatch = { id:string; status:string; acquisition_origin:string; source_system:string|null;
  received_image_count:number; subject_code:string; sample_code:string; slide_code:string; previous_run_code:string|null };
export type QualityImage = { id:string; microscopy_image_id:string; sequence_number:number; input_sha256:string;
  input_width_px:number; input_height_px:number; original_filename:string; quality_verdict:string|null;
  integrity_verified:boolean|null; warning_codes:string[]|null; failure_codes:string[]|null;
  brightness_mean:number|null; contrast_p95_p05:number|null; entropy_bits:number|null;
  laplacian_variance:number|null; tenengrad_mean:number|null; dark_pixel_ratio:number|null;
  bright_pixel_ratio:number|null; usable_field_ratio:number|null };
export type AnalysisEvent = {
  id:string; analysis_run_id:string; microscopy_image_id:string|null; event_type:string;
  stage:string; status:string; message_code:string|null; message:string|null;
  progress_current:number|null; progress_total:number|null; created_at:string;
};
export type AnalysisRun = { id:string; run_code:string; ingestion_batch_id:string; subject_code:string;
  sample_code:string; slide_code:string; input_image_count:number; quality_profile_key:string;
  quality_profile_version:string; run_status:string; quality_gate_status:string; ready_for_analysis:boolean;
  active_stage:string; requested_by_username:string; created_at:string; images:QualityImage[];
  started_at?:string|null;completed_at?:string|null;updated_at?:string|null;
  events:AnalysisEvent[]; decisions:Array<Record<string,unknown>> };
export type QueuePriority = 1|50|100;
export type QualityQueueItem = { queue_item_id:string;analysis_run_id:string;run_code:string;
  subject_code:string;sample_code:string;priority:QueuePriority;status:'queued'|'running'|'completed'|'failed';
  attempt_count:number;requested_by:string;requested_by_username:string;requested_at:string;
  started_at:string|null;completed_at:string|null;failed_at:string|null;last_error_message:string|null };
export type QualityQueueMutation = {
  id:string;analysis_run_id:string;priority:QueuePriority;status:'queued'|'running'|'completed'|'failed';
  attempt_count:number;requested_by:string;requested_at:string;started_at:string|null;
  completed_at:string|null;failed_at:string|null;last_error_code:string|null;last_error_message:string|null;
};
export type QualityQueueRecord = QualityQueueItem | QualityQueueMutation;
export type SmearWorkflowImage = UploadedMicroscopyImage & {
  mime_type:string;
  file_size_bytes:number;
  image_sequence_number:number;
  detected_format:string|null;
};
export type SmearWorkflowResponse = {
  stage:string;
  batch:{
    id:string;status:string;acquisition_origin:string;source_system:string|null;
    received_image_count:number;expected_image_count:number|null;created_at:string;
    completed_at:string|null;
  };
  subject:{id:string;subject_code:string;status:string};
  case:{id:string;case_code:string;status:string};
  sample:{id:string;sample_code:string;status:string};
  slide:{id:string;slide_code:string;status:string};
  images:SmearWorkflowImage[];
  analysis_run:AnalysisRun|null;
  queue_item:QualityQueueItem|null;
  detection_run:CellDetectionRunDetail|null;
};
export type SmearAnalysisHistoryItem = {
  ingestion_batch_id:string;
  analysis_run_id:string;
  run_code:string;
  subject_code:string;
  sample_code:string;
  slide_code:string;
  image_count:number;
  analysis_status:string;
  quality_gate_status:string;
  ready_for_analysis:boolean;
  queue_status:string|null;
  detection_run_id:string|null;
  detection_status:string|null;
  detection_count:number;
  reviewed_count:number;
  requested_by_username:string;
  source_system:string|null;
  created_at:string;
  completed_at:string|null;
};
export type SmearAnalysisHistoryPage = {
  items:SmearAnalysisHistoryItem[];
  total:number;
  limit:number;
  offset:number;
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
}

export function onAuthenticationFailure(handler: (() => void) | null) {
  authenticationFailureHandler = handler;
}

export function cancelPendingRequests() {
  activeRequests.forEach((controller) => controller.abort());
  activeRequests.clear();
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number | null,
    public readonly kind: 'http' | 'network' | 'timeout',
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type QueryValue = string | number | boolean | undefined;
type RequestOptions = {
  init?: RequestInit;
  timeoutMs?: number;
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
  activeRequests.add(controller);
  const timeout = window.setTimeout(() => controller.abort(), options.timeoutMs ?? 15000);
  try {
    const headers = new Headers(options.init?.headers);
    if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
    const response = await fetch(url, { ...options.init, headers, signal: controller.signal });
    if (response.status === 401) {
      setAccessToken(null);
      authenticationFailureHandler?.();
    }
    if (!response.ok) {
      const message = await response.text();
      throw new ApiError(`${response.status} ${response.statusText}: ${message}`, response.status, 'http');
    }
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('La solicitud fue cancelada o superó el tiempo de espera.', null, 'timeout');
    }
    if (error instanceof ApiError) throw error;
    if (error instanceof TypeError) {
      throw new ApiError('No fue posible conectar con el servidor.', null, 'network');
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
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
      setAccessToken(null);
      authenticationFailureHandler?.();
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

export const authApi = {
  login(username: string, password: string) {
    return request<{ access_token: string }>('/api/v1/auth/login', {}, {
      init: { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }) },
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

  datasetImageUrl(imageId: string, datasource: string) {
    const url = new URL(`/api/dataset/images/${imageId}/file`, API_BASE_URL);
    url.searchParams.set('datasource', datasource);
    return url.toString();
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
    return request<{items: ScientificSample[]}>(`/api/v1/scientific/subjects/${subjectId}/samples`);
  },

  uploadMicroscopyImages(form: FormData) {
    return request<ImageUploadResponse>('/api/v1/scientific/images/upload', {}, {
      timeoutMs: 120000,
      init: { method: 'POST', body: form },
    });
  },

  getEligibleBatches(params:Record<string,QueryValue>={}) {
    return request<{items:EligibleBatch[];total:number}>('/api/v1/analysis/eligible-batches',params);
  },
  createAnalysisRun(ingestion_batch_id:string) {
    return request<AnalysisRun>('/api/v1/analysis/runs',{},{
      init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ingestion_batch_id})},
    });
  },
  executeQuality(runId:string) {
    return request<AnalysisRun>(`/api/v1/analysis/runs/${runId}/quality-assessment`,{},{
      timeoutMs:120000,init:{method:'POST'},
    });
  },
  getAnalysisRun(runId:string) { return request<AnalysisRun>(`/api/v1/analysis/runs/${runId}`); },
  getSmearWorkflow(ingestionBatchId:string) {
    return request<SmearWorkflowResponse>(
      `/api/v1/scientific/workflows/${encodeURIComponent(ingestionBatchId)}`,
    );
  },
  getSmearAnalysisHistory(params:Record<string,QueryValue>={}) {
    return request<SmearAnalysisHistoryPage>(
      '/api/v1/scientific/workflows',
      params,
    );
  },
  getSmearAnalysisHistoryDetail(analysisRunId:string) {
    return request<SmearWorkflowResponse>(
      `/api/v1/scientific/analysis-history/${encodeURIComponent(analysisRunId)}`,
    );
  },
  async getMicroscopyImageBlob(imageId:string) {
    const blob = await requestBlob(
      `/api/v1/scientific/images/${encodeURIComponent(imageId)}/content`,
    );
    return URL.createObjectURL(blob);
  },
  getEligibleCellAnalysisRuns(params:Record<string,QueryValue>={}) {
    return request<CellAnalysisPage<EligibleCellAnalysisRun>>(
      '/api/v1/cell-analysis/eligible-analysis-runs',
      params,
    );
  },
  createCellDetectionRun(analysisRunId:string) {
    return request<CellDetectionRunDetail>('/api/v1/cell-analysis/detection-runs',{},{
      timeoutMs:120000,
      init:{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({analysis_run_id:analysisRunId}),
      },
    });
  },
  getCellDetectionRuns(params:Record<string,QueryValue>={}) {
    return request<CellAnalysisPage<CellDetectionRunSummary>>(
      '/api/v1/cell-analysis/detection-runs',
      params,
    );
  },
  getCellDetectionRun(detectionRunId:string) {
    return request<CellDetectionRunDetail>(
      `/api/v1/cell-analysis/detection-runs/${encodeURIComponent(detectionRunId)}`,
    );
  },
  getCellDetectionImages(detectionRunId:string) {
    return request<CellAnalysisPage<CellDetectionImage>>(
      `/api/v1/cell-analysis/detection-runs/${encodeURIComponent(detectionRunId)}/images`,
    );
  },
  getCellDetections(
    detectionRunId:string,
    microscopyImageId:string,
    params:{review_status?:Exclude<CellReviewFilter,'all'>;limit?:number;offset?:number}={},
  ) {
    return request<CellAnalysisPage<CellDetectionSummary>>(
      `/api/v1/cell-analysis/detection-runs/${encodeURIComponent(detectionRunId)}/images/${encodeURIComponent(microscopyImageId)}/detections`,
      params,
    );
  },
  getCellDetection(cellDetectionId:string) {
    return request<CellDetectionDetail>(
      `/api/v1/cell-analysis/detections/${encodeURIComponent(cellDetectionId)}`,
    );
  },
  getCellReviews(cellDetectionId:string) {
    return request<CellAnalysisPage<ScientificCellReview>>(
      `/api/v1/cell-analysis/detections/${encodeURIComponent(cellDetectionId)}/reviews`,
    );
  },
  createCellReview(
    cellDetectionId:string,
    decision:CellReviewDecision,
    comment?:string,
  ) {
    return request<CellDetectionReviewResult>(
      `/api/v1/cell-analysis/detections/${encodeURIComponent(cellDetectionId)}/reviews`,
      {},
      {
        init:{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({decision,comment:comment?.trim()||undefined}),
        },
      },
    );
  },
  getCellCropBlob(cropId:string,contentUrl?:string|null,signal?:AbortSignal) {
    const fallback=`/api/v1/cell-analysis/crops/${encodeURIComponent(cropId)}/content`;
    return requestBlob(trustedCellContentPath(contentUrl,fallback),signal);
  },
  getCellOriginalImageBlob(
    detectionRunId:string,
    microscopyImageId:string,
    contentUrl?:string|null,
    signal?:AbortSignal,
  ) {
    const fallback=`/api/v1/cell-analysis/detection-runs/${encodeURIComponent(detectionRunId)}/images/${encodeURIComponent(microscopyImageId)}/content`;
    return requestBlob(trustedCellContentPath(contentUrl,fallback),signal);
  },
  reviewQuality(runId:string,decision:'approve_with_warnings'|'reject',comment:string) {
    return request<AnalysisRun>(`/api/v1/analysis/runs/${runId}/quality-decision`,{},{
      init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision,comment})},
    });
  },
  enqueueQuality(analysis_run_id:string,priority:QueuePriority=50) {
    return request<QualityQueueMutation>('/api/v1/analysis/queue',{},{
      init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({analysis_run_id,priority})},
    });
  },
  getQualityQueue(params:Record<string,QueryValue>={}) {
    return request<{items:QualityQueueItem[];total:number}>('/api/v1/analysis/queue',params);
  },
  executeQueueItem(queueItemId:string) {
    return request<QualityQueueMutation>(`/api/v1/analysis/queue/${queueItemId}/execute`,{},{
      timeoutMs:120000,init:{method:'POST'},
    });
  },
  retryQueueItem(queueItemId:string,priority:QueuePriority) {
    return request<QualityQueueMutation>(`/api/v1/analysis/queue/${queueItemId}/retry`,{},{
      init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({priority})},
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

  getStage2Availability(datasource:string,trainingRunId:string) {
    return request<Stage2Availability>(
      `/api/training-runs/${trainingRunId}/stage2-availability`,
      withDatasource(datasource),{timeoutMs:30000},
    );
  },
  getStage2ReleaseStatus(datasource:string,trainingRunId:string) {
    return request<Stage2Availability>(
      `/api/training-runs/${trainingRunId}/stage2-release-status`,
      withDatasource(datasource),
      {timeoutMs:30000},
    );
  },
  publishStage2Model(datasource:string,modelVersionId:string,payload:{
    actor?:string;reason?:string;
  }) {
    return request<Stage2Availability>(
      `/api/model-versions/${modelVersionId}/stage2-publications`,
      withDatasource(datasource),{
        init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},
      },
    );
  },
  deactivateStage2Publication(datasource:string,publicationId:string,payload:{
    actor?:string;reason?:string;
  }) {
    return request<Stage2Availability>(
      `/api/stage2-publications/${publicationId}/deactivate`,
      withDatasource(datasource),{
        init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},
      },
    );
  },

  enableStage2(datasource:string,trainingRunId:string,payload:{
    actor:string;reason:string;confirm_stage2_enablement:boolean;
    preprocessing_candidate_id?:string;threshold_candidate_id?:string;source_image_id?:string;
  }) {
    return request<Stage2EnablementResult>(
      `/api/training-runs/${trainingRunId}/enable-stage2`,
      withDatasource(datasource),{
        timeoutMs:120000,
        init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},
      },
    );
  },
  publishTrainingStage2(datasource:string,trainingRunId:string,payload:{
    actor:string;reason:string;confirm_publication:boolean;source_image_id?:string;
  }) {
    return request<Stage2EnablementResult>(
      `/api/training-runs/${trainingRunId}/publish-technical-production`,
      withDatasource(datasource),
      {init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},timeoutMs:120000},
    );
  },

  getStage2Models(datasource:string) {
    return request<{items:Stage2EnablementResult[]}>('/api/stage2/models',withDatasource(datasource));
  },

  getTechnicalProductionPreview(datasource:string,modelVersionId:string) {
    return request<Stage2Availability>(
      `/api/model-versions/${modelVersionId}/technical-production-preview`,
      withDatasource(datasource),{timeoutMs:30000},
    );
  },

  publishTechnicalProduction(datasource:string,modelVersionId:string,payload:{
    actor:string;reason:string;confirm_publication:boolean;
    preprocessing_profile?:string;threshold?:number;source_image_id?:string;
  }) {
    return request<Stage2EnablementResult>(
      `/api/model-versions/${modelVersionId}/publish-technical-production`,
      withDatasource(datasource),{
        timeoutMs:120000,
        init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},
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

  getModelVersionContractCandidates(datasource:string,modelVersionId:string) {
    return request<ModelContractCandidates>(`/api/model-versions/${modelVersionId}/contract-candidates`,withDatasource(datasource),{timeoutMs:30000});
  },

  completeModelVersionContract(datasource:string,modelVersionId:string,selections:Record<string,string>,actor:string,reason:string) {
    return request<{model_version:ModelVersionRow;threshold_profile_id:string}>(`/api/model-versions/${modelVersionId}/build-production-package`,withDatasource(datasource),{
      timeoutMs:30000,init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({selections,actor,reason})},
    });
  },

  publishModelVersionToProduction(datasource:string,modelVersionId:string,payload:{deployment_name:string;alias:'champion';actor:string;reason:string;confirm_production:boolean;source_image_id?:string}) {
    return request<ProductionPublicationResult>(`/api/model-versions/${modelVersionId}/publish-to-production`,withDatasource(datasource),{
      timeoutMs:120000,init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},
    });
  },

  getModelProductionReadiness(datasource:string,modelVersionId:string) {
    return request<ModelProductionReadiness>(`/api/model-versions/${modelVersionId}/production-readiness`,withDatasource(datasource),{timeoutMs:30000});
  },

  getDeployments(datasource: string, active = false) {
    return request<{ items: DeploymentRow[] }>(active ? '/api/deployments/active' : '/api/deployments', withDatasource(datasource));
  },

  getDeploymentReadiness(datasource:string,deploymentId:string) {
    return request<DeploymentReadiness>(`/api/deployments/${deploymentId}/readiness`,withDatasource(datasource),{timeoutMs:30000});
  },

  getAvailableModels(datasource: string, environment?: string) {
    return request<{ items: AvailableModel[] }>('/api/models/available', { datasource, environment });
  },

  validateModelVersion(datasource:string,modelVersionId:string,thresholdProfileId:string,actor:string,reason:string) {
    return request<ModelVersionRow>(`/api/model-versions/${modelVersionId}/validate`,withDatasource(datasource),{
      init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({threshold_profile_id:thresholdProfileId,actor,reason})},
    });
  },

  approveModelVersion(datasource:string,modelVersionId:string,actor:string,reason:string) {
    return request<ModelVersionRow>(`/api/model-versions/${modelVersionId}/approve`,withDatasource(datasource),{
      init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({actor,reason})},
    });
  },

  createDeployment(datasource:string,payload:{model_version_id:string;deployment_name:string;environment:string;alias:string;threshold_profile_id:string;deployed_by:string}) {
    return request<DeploymentRow>('/api/deployments',withDatasource(datasource),{
      init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload,activate:false})},
    });
  },

  smokeTestDeployment(datasource:string,deploymentId:string,sourceImageId:string,actor:string) {
    return request<{deployment:DeploymentRow;smoke_test:JsonRecord}>(`/api/deployments/${deploymentId}/smoke-test`,withDatasource(datasource),{
      timeoutMs:30000,init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source_image_id:sourceImageId,actor})},
    });
  },

  activateDeployment(datasource:string,deploymentId:string,actor:string,confirmProduction:boolean) {
    return request<DeploymentRow>(`/api/deployments/${deploymentId}/activate`,withDatasource(datasource),{
      timeoutMs:30000,init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({actor,confirm_production:confirmProduction})},
    });
  },

  transitionDeployment(datasource:string,deploymentId:string,action:'deactivate'|'retire',actor:string,reason:string) {
    return request<DeploymentRow>(`/api/deployments/${deploymentId}/${action}`,withDatasource(datasource),{
      init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({actor,reason})},
    });
  },

  rollbackDeployment(datasource:string,deploymentId:string,targetDeploymentId:string,actor:string,reason:string) {
    return request<DeploymentRow>(`/api/deployments/${deploymentId}/rollback`,withDatasource(datasource),{
      init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target_deployment_id:targetDeploymentId,actor,reason})},
    });
  },

  createImageAnalysisJob(datasource:string,deployedModelVersionId:string,sourceImageId:string) {
    return request<InferenceResult>('/api/image-analysis-jobs',withDatasource(datasource),{
      timeoutMs:30000,init:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({deployed_model_version_id:deployedModelVersionId,source_image_id:sourceImageId})},
    });
  },

  getClinicalModelComparison(datasource: string) {
    return request<{ items: ClinicalRunSummary[] }>('/models/comparison', withDatasource(datasource));
  },

  getDatasets(datasource: string) {
    return request<{ items: JsonRecord[] }>('/datasets', withDatasource(datasource));
  },

  getDatasetSummary(datasource: string) {
    return request<DatasetBrowserSummary>('/api/dataset/summary', withDatasource(datasource));
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

export type ApiArtifact = ArtifactRow;
