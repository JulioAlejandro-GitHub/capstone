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
  ModelVersionLineageRow,
  PagedResponse,
  PromotionStatusResponse,
  RunDashboard,
  RunArtifact,
  RunClinicalSummary,
  RunDetailResponse,
  RunImagePrediction,
  ThresholdCalibrationSummary,
  UploadedPrediction,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export const DEFAULT_DATASOURCE = import.meta.env.VITE_DEFAULT_DATASOURCE ?? 'malaria';

type QueryValue = string | number | boolean | undefined;
type ArtifactUrlOptions = {
  artifactId?: string | null;
  datasource?: string;
};

type MediaUrlOptions = ArtifactUrlOptions & {
  url?: string | null;
  path?: string | null;
};

async function request<T>(path: string, params: Record<string, QueryValue> = {}) {
  const url = new URL(path, API_BASE_URL);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      url.searchParams.set(key, String(value));
    }
  });

  const response = await fetch(url);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${message}`);
  }
  return response.json() as Promise<T>;
}

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

  getDeployments(datasource: string, active = false) {
    return request<{ items: DeploymentRow[] }>(active ? '/api/deployments/active' : '/api/deployments', withDatasource(datasource));
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

  getPromotionStatus(datasource: string, trainingRunId: string) {
    return request<PromotionStatusResponse>(
      `/api/training-runs/${trainingRunId}/promotion-status`,
      withDatasource(datasource),
    );
  },

  async prepareRelease(datasource: string, trainingRunId: string, requester = 'user') {
    const url = new URL(`/api/training-runs/${trainingRunId}/prepare-release`, API_BASE_URL);
    url.searchParams.set('datasource', datasource);
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ requester }),
    });
    if (!response.ok) {
      const message = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${message}`);
    }
    return response.json() as Promise<PromotionStatusResponse>;
  },
};

export type ApiArtifact = ArtifactRow;

