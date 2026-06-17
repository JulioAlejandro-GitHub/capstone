import type {
  ArtifactRow,
  DashboardSummary,
  Datasource,
  ExplainabilityRow,
  JsonRecord,
  ModelSummary,
  RunDashboard,
  RunDetailResponse,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export const DEFAULT_DATASOURCE = import.meta.env.VITE_DEFAULT_DATASOURCE ?? 'malaria';

async function request<T>(path: string, params: Record<string, string | number | undefined> = {}) {
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
  artifactUrl(path: string) {
    const url = new URL('/artifacts/file', API_BASE_URL);
    url.searchParams.set('path', path);
    return url.toString();
  },

  getDatasources() {
    return request<{ items: Datasource[] }>('/datasources');
  },

  getDashboardSummary(datasource: string) {
    return request<DashboardSummary>('/dashboard/summary', withDatasource(datasource));
  },

  getRuns(datasource: string) {
    return request<{ items: RunDashboard[] }>('/runs', withDatasource(datasource));
  },

  getRun(datasource: string, runId: string) {
    return request<RunDetailResponse>(`/runs/${runId}`, withDatasource(datasource));
  },

  getModels(datasource: string) {
    return request<{ items: ModelSummary[] }>('/models', withDatasource(datasource));
  },

  getDatasets(datasource: string) {
    return request<{ items: JsonRecord[] }>('/datasets', withDatasource(datasource));
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

  getErrors(datasource: string) {
    return request<{ items: JsonRecord[] }>('/errors', withDatasource(datasource));
  },

  getLogs(datasource: string) {
    return request<{ items: JsonRecord[] }>('/logs', withDatasource(datasource));
  },
};

export type ApiArtifact = ArtifactRow;

