import { api } from '../../services/api';
import type { ExplainabilityCase } from '../../types/api';
import type { CellClassificationRunDetail, CellPredictionDetail, CellPredictionSummary } from '../../types/cellClassification';
import { evaluatedImagePath, explanationImagePath, scorePositive, thresholdUsed } from '../../utils/explainability';
import { formatDate, formatMetric } from '../../utils/format';
import type { ExplainabilityCaseViewModel } from './CaseExplainabilityView';

const six = (value: number | null | undefined) => value == null ? '—' : value.toFixed(6);
const jsonRecord = (value: unknown): Record<string, unknown> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};

type ArtifactAvailability = 'available' | 'missing' | 'not_registered' | null | undefined;

const canonicalMethod = (method: string | null | undefined) => (method ?? '').replace(/[-_\s]/g, '').toLowerCase();

export function resolveExplanationArtifact({
  method,
  status,
  success,
  availability,
  media,
}: {
  method: string | null | undefined;
  status?: string | null;
  success?: boolean | null;
  availability?: ArtifactAvailability;
  media: ExplainabilityCaseViewModel['explanation']['media'];
}): Pick<ExplainabilityCaseViewModel['explanation'], 'status' | 'media' | 'method' | 'otherMethods'> {
  const isGradCam = canonicalMethod(method) === 'gradcam';
  if (!isGradCam) {
    return { status: 'not_requested', media: [], method: 'Grad-CAM', otherMethods: method ? [method.toUpperCase()] : [] };
  }
  if (status === 'unsupported') return { status: 'unsupported', media: [], method: 'Grad-CAM' };
  if (status === 'pending' || status === 'generating') return { status: 'generating', media: [], method: 'Grad-CAM' };
  if (status === 'failed' || success === false) return { status: 'failed', media: [], method: 'Grad-CAM' };
  if (status === 'generated' || success === true) {
    if (availability === 'missing' || availability === 'not_registered' || media.length === 0) {
      return { status: 'artifact_missing', media: [], method: 'Grad-CAM' };
    }
    return { status: 'generated', media, method: 'Grad-CAM' };
  }
  return { status: 'not_requested', media: [], method: 'Grad-CAM' };
}

export function toModelExecutionExplainabilityCase(item: ExplainabilityCase, datasource: string): ExplainabilityCaseViewModel {
  const cropPath = evaluatedImagePath(item);
  const explanationPath = explanationImagePath(item);
  const explanationParameters = jsonRecord(item.explanation_parameters);
  const runParameters = jsonRecord(item.run_parameters);
  const sourceAvailability = item.crop_path
    ? item.crop_availability
    : item.image_path
      ? item.image_artifact_availability
      : item.source_image_availability;
  const sourceUrl = sourceAvailability === 'missing' || sourceAvailability === 'not_registered'
    ? null
    : api.mediaUrl({ url: item.crop_url ?? item.source_image_url ?? item.image_url, path: cropPath, datasource });
  const explanationMedia = explanationPath && item.explanation_artifact_availability === 'available'
    ? [{ kind: 'url' as const, url: api.mediaUrl({ url: item.explanation_url, path: explanationPath, artifactId: item.artifact_id, datasource }), path: explanationPath, alt: 'Explicación Grad-CAM del caso' }]
    : [];
  const resolvedExplanation = resolveExplanationArtifact({ method: item.method, success: item.success, availability: item.explanation_artifact_availability, media: explanationMedia });
  const positive = item.probability_parasitized ?? scorePositive(item);
  const negative = item.probability_uninfected ?? (positive == null ? null : 1 - positive);
  const threshold = thresholdUsed(item);
  return {
    sourceContext: 'model_execution',
    caseCode: item.source_image_id ?? item.image_id ?? item.prediction_id ?? item.explainability_id,
    input: {
      media: { kind: 'url', url: sourceUrl, path: cropPath, alt: 'Crop fuente del caso' },
      displayCode: item.original_filename ?? item.source_image_id ?? item.image_id ?? 'Caso de ejecución',
      id: item.source_image_id ?? item.image_id ?? null,
      checksum: typeof explanationParameters.input_sha256 === 'string' ? `${explanationParameters.input_sha256.slice(0, 12)}…` : null,
      facts: [{ label: 'Dataset', value: item.dataset_name ?? null }, { label: 'Split', value: item.dataset_split ?? null }],
    },
    prediction: {
      id: item.prediction_id ?? null,
      predictedLabel: item.predicted_label ?? null,
      probabilityParasitized: formatMetric(positive),
      probabilityUninfected: formatMetric(negative),
      threshold: formatMetric(threshold),
      thresholdSource: item.threshold_source ?? null,
      margin: positive == null || threshold == null ? '—' : formatMetric(Math.abs(positive - threshold)),
      nearThreshold: item.case_type === 'low_confidence' ? 'Sí' : 'No registrado',
      modelName: item.model_name ?? null,
      modelVersion: item.model_version_id ?? item.model_version ?? (typeof runParameters.model_version_id === 'string' ? runParameters.model_version_id : null),
      facts: [{ label: 'Clase real', value: item.true_label ?? null }, { label: 'Tipo de caso', value: item.case_type ?? null }],
    },
    explanation: {
      ...resolvedExplanation,
      methodVersion: typeof explanationParameters.method_version === 'string' ? explanationParameters.method_version : null,
      lastConvLayer: item.last_conv_layer ?? null,
      parameters: item.explanation_parameters ?? {},
      createdAt: formatDate(item.created_at ?? item.started_at ?? null),
      error: item.error_message ?? null,
    },
    associatedRunId: item.run_id ?? null,
  };
}

export function toSmearCellExplainabilityCase(prediction: CellPredictionSummary | CellPredictionDetail, run: CellClassificationRunDetail | null): ExplainabilityCaseViewModel {
  const explanation = prediction.explanation;
  const crop = prediction.detection?.crop ?? prediction.crop ?? null;
  const explanationMedia: ExplainabilityCaseViewModel['explanation']['media'] = explanation?.status === 'generated' ? [{ kind: 'cell_explanation', explanation, variant: 'heatmap', alt: 'Heatmap Grad-CAM de la célula' }, { kind: 'cell_explanation', explanation, variant: 'overlay', alt: 'Overlay Grad-CAM de la célula' }] : [];
  const resolvedExplanation = resolveExplanationArtifact({ method: explanation?.method, status: explanation?.status, availability: explanation?.status === 'generated' ? 'available' : undefined, media: explanationMedia });
  return {
    sourceContext: 'smear_analysis',
    caseCode: prediction.cell_code,
    input: { media: { kind: 'cell_crop', crop, alt: `Crop fuente ${prediction.cell_code}` }, displayCode: prediction.cell_code, id: prediction.cell_detection_id, checksum: crop ? `${crop.sha256.slice(0, 12)}…` : null },
    prediction: { id: prediction.id, predictedLabel: prediction.predicted_label, probabilityParasitized: six(prediction.probability_parasitized), probabilityUninfected: six(prediction.probability_uninfected), threshold: six(prediction.threshold_used), thresholdSource: prediction.threshold_source, margin: six(prediction.decision_margin), nearThreshold: prediction.near_threshold ? 'Sí' : 'No', modelName: run?.model_name ?? ('model_name' in prediction ? prediction.model_name ?? null : null), modelVersion: run?.model_version ?? ('model_version' in prediction ? prediction.model_version ?? null : null) },
    explanation: { ...resolvedExplanation, methodVersion: explanation?.method_version ?? null, lastConvLayer: explanation?.last_conv_layer ?? null, parameters: explanation?.parameters_json ?? {}, createdAt: explanation?.completed_at ?? explanation?.created_at ?? null, error: explanation?.error_message ?? null },
  };
}
