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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export const DEFAULT_DATASOURCE = import.meta.env.VITE_DEFAULT_DATASOURCE ?? 'malaria';

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
  const timeout = window.setTimeout(() => controller.abort(), options.timeoutMs ?? 15000);
  try {
    const response = await fetch(url, { ...options.init, signal: controller.signal });
    if (!response.ok) {
      const message = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${message}`);
    }
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('La solicitud superó el tiempo de espera.');
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
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
