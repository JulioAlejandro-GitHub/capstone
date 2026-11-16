/**
 * Adaptador v3: convierte los contratos científicos existentes en el modelo de
 * presentación del Microscopio Digital. Módulo puro (solo imports de tipos).
 *
 * No calcula ni inventa resultados: cada número expuesto proviene tal cual de
 * la respuesta del backend; cuando un dato no existe se entrega `null`.
 */
import type {
  SmearWorkflowIdentifiers,
  SmearWorkflowSnapshot,
} from '../../../hooks/useSmearAnalysisWorkflow';
import type { SmearWorkflowResponse } from '../../../services/api';

/** Estados progresivos del instrumento una vez que existe un frotis. */
export type MicroscopePhase = 'technical_review' | 'attention' | 'microscope' | 'halted';

const PHASE_BY_STAGE: Record<string, MicroscopePhase> = {
  validating: 'technical_review',
  uploading: 'technical_review',
  ingested: 'technical_review',
  creating_analysis: 'technical_review',
  quality_queued: 'technical_review',
  quality_processing: 'technical_review',
  ready_for_detection: 'technical_review',
  detection_processing: 'technical_review',
  classification_pending: 'technical_review',
  classification_processing: 'technical_review',
  quality_warning: 'attention',
  quality_failed: 'halted',
  error: 'halted',
  // La detección existe: el frotis puede examinarse aunque la clasificación falte o haya fallado.
  awaiting_productive_model: 'microscope',
  classification_failed: 'microscope',
  classification_completed: 'microscope',
  classification_warning: 'microscope',
  review_ready: 'microscope',
};

/** Un estado desconocido nunca se presenta como resultado disponible. */
export const phaseForStage = (stage: string): MicroscopePhase =>
  PHASE_BY_STAGE[stage] ?? 'halted';

/** Etapas en las que el backend informa un proceso realmente en ejecución. */
const ACTIVE_STAGES = new Set([
  'validating',
  'uploading',
  'creating_analysis',
  'quality_processing',
  'detection_processing',
  'classification_processing',
]);
export const isActivelyProcessing = (stage: string) => ACTIVE_STAGES.has(stage);

const STAGE_LABEL: Record<string, string> = {
  setup: 'Sin imágenes',
  validating: 'Validando archivos',
  uploading: 'Recibiendo imágenes',
  ingested: 'Imágenes recibidas',
  creating_analysis: 'Creando análisis',
  quality_queued: 'Control técnico en cola',
  quality_processing: 'Control técnico en curso',
  quality_warning: 'Advertencia técnica pendiente',
  quality_failed: 'Bloqueado por control técnico',
  ready_for_detection: 'Listo para detección',
  detection_processing: 'Detección celular en curso',
  awaiting_productive_model: 'Sin modelo productivo para clasificar',
  classification_pending: 'Clasificación pendiente',
  classification_processing: 'Clasificación en curso',
  classification_completed: 'Clasificación completada',
  classification_warning: 'Clasificación con advertencias',
  classification_failed: 'Clasificación fallida',
  review_ready: 'Detecciones disponibles',
  error: 'Procesamiento interrumpido',
};
export const stageLabel = (stage: string) =>
  STAGE_LABEL[stage] ?? `Estado no reconocido (${stage})`;

export type MicroscopeImage = {
  id: string;
  name: string;
  /** Número de secuencia persistido; `null` mientras solo existe el orden de recepción. */
  sequence: number | null;
  widthPx: number | null;
  heightPx: number | null;
  mimeType: string | null;
  detectionCount: number | null;
};

export type MicroscopeDetection = {
  runId: string;
  status: string;
  detectionCount: number;
  reviewedCount: number;
  pendingReviewCount: number;
};

export type MicroscopeClassification = {
  runId: string;
  status: string;
  modelName: string | null;
  modelVersion: string | null;
  /** Conteos del resumen persistido; `null` cuando el backend aún no lo entrega. */
  classifiedCount: number | null;
  parasitizedCandidateCount: number | null;
  uninfectedCandidateCount: number | null;
  nearThresholdCount: number | null;
  failedPredictionCount: number | null;
  eligibleCount: number | null;
  /** Fracción de candidatas parasitadas informada por el resumen persistido. */
  parasitizedFraction: number | null;
  outcome: 'suspicious_cells_detected' | 'no_suspicious_cells_detected' | 'inconclusive' | null;
};

export type MicroscopeAnalysis = {
  analysisRunId: string | null;
  runCode: string | null;
  ingestionBatchId: string | null;
  subjectCode: string | null;
  sampleCode: string | null;
  /** Frotis físico (`smear_slides`): el contrato actual asocia un único frotis por análisis. */
  slideCode: string | null;
  stage: string;
  phase: MicroscopePhase;
  qualityGateStatus: string | null;
  images: MicroscopeImage[];
  detection: MicroscopeDetection | null;
  classification: MicroscopeClassification | null;
  createdAt: string | null;
  completedAt: string | null;
};

type DetectionRun = SmearWorkflowResponse['detection_run'];
type ClassificationRun = SmearWorkflowResponse['classification_run'];
type ClassificationSummary = SmearWorkflowResponse['classification_summary'];

const detectionOf = (run: DetectionRun): MicroscopeDetection | null => (run ? {
  runId: run.id,
  status: run.status,
  detectionCount: run.detection_count,
  reviewedCount: run.reviewed_count,
  pendingReviewCount: run.pending_review_count,
} : null);

const classificationOf = (
  run: ClassificationRun,
  summary: ClassificationSummary,
): MicroscopeClassification | null => (run ? {
  runId: run.id,
  status: run.status,
  modelName: run.model_name ?? null,
  modelVersion: run.model_version ?? null,
  classifiedCount: summary?.classified_cell_count ?? null,
  parasitizedCandidateCount: summary?.parasitized_candidate_count ?? null,
  uninfectedCandidateCount: summary?.uninfected_candidate_count ?? null,
  nearThresholdCount: summary?.near_threshold_count ?? null,
  failedPredictionCount: summary?.failed_prediction_count ?? null,
  eligibleCount: summary?.eligible_cell_count ?? null,
  parasitizedFraction: summary?.parasitized_candidate_fraction ?? null,
  outcome: summary?.outcome ?? null,
} : null);

const detectionCountsByImage = (run: DetectionRun) =>
  new Map((run?.images ?? []).map((image) => [image.microscopy_image_id, image.detection_count]));

/** Orden determinista: secuencia de captura persistida y, a igualdad, identificador. */
const bySequence = (first: MicroscopeImage, second: MicroscopeImage) =>
  (first.sequence ?? Number.MAX_SAFE_INTEGER) - (second.sequence ?? Number.MAX_SAFE_INTEGER)
  || first.id.localeCompare(second.id);

/** Análisis existente (Historial → Microscopio): respuesta de `analysis-history/:id`. */
export function analysisFromWorkflow(
  response: SmearWorkflowResponse,
  overrides: {
    stage?: string;
    detectionRun?: DetectionRun;
    classificationRun?: ClassificationRun;
    classificationSummary?: ClassificationSummary;
  } = {},
): MicroscopeAnalysis {
  const stage = overrides.stage ?? response.stage;
  const detectionRun = overrides.detectionRun ?? response.detection_run;
  const classificationRun = overrides.classificationRun ?? response.classification_run ?? null;
  const classificationSummary = (
    overrides.classificationSummary ?? response.classification_summary ?? null
  );
  const counts = detectionCountsByImage(detectionRun);
  const run = response.analysis_run;
  return {
    analysisRunId: run?.id ?? null,
    runCode: run?.run_code ?? null,
    ingestionBatchId: response.batch.id,
    subjectCode: response.subject.subject_code,
    sampleCode: response.sample.sample_code,
    slideCode: response.slide.slide_code,
    stage,
    phase: phaseForStage(stage),
    qualityGateStatus: run?.quality_gate_status ?? null,
    images: response.images.map((image) => ({
      id: image.id,
      name: image.original_filename,
      sequence: image.image_sequence_number,
      widthPx: image.width_px,
      heightPx: image.height_px,
      mimeType: image.mime_type,
      detectionCount: counts.get(image.id) ?? null,
    })).sort(bySequence),
    detection: detectionOf(detectionRun),
    classification: classificationOf(classificationRun, classificationSummary),
    createdAt: run?.created_at ?? response.batch.created_at,
    completedAt: run?.completed_at ?? null,
  };
}

/** Análisis nuevo (Menú → Carga → Revisión técnica): estado del workflow existente en curso. */
export function analysisFromLive(
  stage: string,
  snapshot: SmearWorkflowSnapshot,
  identifiers: SmearWorkflowIdentifiers,
): MicroscopeAnalysis {
  if (snapshot.persisted) {
    return analysisFromWorkflow(snapshot.persisted, {
      stage,
      detectionRun: snapshot.detectionRun ?? undefined,
      classificationRun: snapshot.classificationRun ?? undefined,
      classificationSummary: snapshot.classificationSummary ?? undefined,
    });
  }
  const upload = snapshot.upload;
  const run = snapshot.analysisRun;
  const counts = detectionCountsByImage(snapshot.detectionRun);
  return {
    analysisRunId: run?.id ?? identifiers.analysisRunId,
    runCode: run?.run_code ?? null,
    ingestionBatchId: upload?.ingestion_batch.id ?? identifiers.ingestionBatchId,
    subjectCode: run?.subject_code ?? upload?.subject.subject_code ?? null,
    sampleCode: run?.sample_code ?? upload?.sample.sample_code ?? null,
    slideCode: run?.slide_code ?? upload?.slide.slide_code ?? null,
    stage,
    phase: phaseForStage(stage),
    qualityGateStatus: run?.quality_gate_status ?? null,
    // La respuesta de carga aún no trae secuencia persistida: se conserva el orden de recepción.
    images: (upload?.images ?? []).map((image) => ({
      id: image.id,
      name: image.original_filename,
      sequence: null,
      widthPx: image.width_px,
      heightPx: image.height_px,
      mimeType: null,
      detectionCount: counts.get(image.id) ?? null,
    })),
    detection: detectionOf(snapshot.detectionRun),
    classification: classificationOf(snapshot.classificationRun, snapshot.classificationSummary),
    createdAt: run?.created_at ?? upload?.ingestion_batch.created_at ?? null,
    completedAt: run?.completed_at ?? null,
  };
}

/**
 * Motivo persistido de una interrupción, tal como lo registró el backend.
 * Devuelve `null` cuando el análisis no está interrumpido.
 */
export function failureMessageFromWorkflow(response: SmearWorkflowResponse): string | null {
  if (response.classification_run?.status === 'failed') {
    return response.classification_run.error_message || 'La clasificación terminó con error.';
  }
  if (response.detection_run?.status === 'failed') {
    return response.detection_run.error_message || 'La detección terminó con error.';
  }
  if (response.queue_item?.status === 'failed') {
    return response.queue_item.last_error_message || 'El control técnico terminó con error.';
  }
  return phaseForStage(response.stage) === 'halted' && response.stage !== 'quality_failed'
    ? 'El análisis terminó con error.'
    : null;
}
