import { useEffect, useState } from 'react';

import { ClinicalMetricsCards } from '../components/ClinicalMetricsCards';
import { ConfusionMatrix } from '../components/ConfusionMatrix';
import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type {
  ArtifactRow,
  ExplainabilityCase,
  JsonRecord,
  JsonValue,
  RunArtifact,
  RunClinicalSummary,
  RunDetailResponse,
  RunImagePrediction,
} from '../types/api';
import { explanationImagePath, scorePositive, sourceImagePath, thresholdUsed } from '../utils/explainability';
import { formatDate, formatDuration, formatMetric, stringifyJson } from '../utils/format';
import {
  booleanValue,
  normalizeExecutionParameters,
  numberValue,
  recordValue,
  resolveClinicalMetrics,
  resolveCommand,
  resolveConfusionMatrix,
  resolveDurationSeconds,
  resolveTrainingSignals,
  textValue,
} from '../utils/runDetail';

interface RunDetailProps {
  datasource: string;
  runId: string | null;
  onExplainabilitySelect?: (item: ExplainabilityCase) => void;
}

type PredictionFilters = {
  split: string;
  caseType: string;
  className: string;
  correct: string;
};

type ArtifactItem = ArtifactRow | RunArtifact;
type ArtifactGroupName =
  | 'Modelos'
  | 'Métricas'
  | 'Gráficos'
  | 'Predicciones'
  | 'Explicabilidad'
  | 'Logs'
  | 'Otros';

type ParameterItem = {
  key: string;
  label: string;
  value: unknown;
};

type ParameterGroup = {
  title: string;
  items: ParameterItem[];
};

type CriticalPoint = {
  level: 'critical' | 'warning';
  text: string;
};

const IMAGE_EXTENSIONS = /\.(png|jpe?g|webp)$/i;
const SERVED_IMAGE_MIME_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp']);
const TECHNICAL_METRIC_REFERENCE = 0.8;
const ARTIFACT_GROUP_ORDER: ArtifactGroupName[] = [
  'Modelos',
  'Métricas',
  'Gráficos',
  'Predicciones',
  'Explicabilidad',
  'Logs',
  'Otros',
];

function stringValue(value: unknown) {
  return typeof value === 'string' && value.trim() ? value : null;
}

function artifactPath(artifact: ArtifactItem) {
  return stringValue(('path' in artifact ? artifact.path : null) ?? artifact.artifact_path);
}

function artifactName(artifact: ArtifactItem) {
  const explicitName = stringValue(artifact.name);
  if (explicitName) return explicitName;
  return artifactPath(artifact)?.split(/[\\/]/).pop() ?? 'Artefacto sin nombre';
}

function artifactId(artifact: ArtifactItem) {
  return 'id' in artifact && typeof artifact.id === 'string' ? artifact.id : undefined;
}

function isImageArtifact(artifact: ArtifactItem) {
  const mimeType = artifact.mime_type?.toLowerCase() ?? '';
  const path = artifactPath(artifact)?.toLowerCase() ?? '';
  const name = artifactName(artifact).toLowerCase();
  return SERVED_IMAGE_MIME_TYPES.has(mimeType) || IMAGE_EXTENSIONS.test(path) || IMAGE_EXTENSIONS.test(name);
}

function isNamedCombinedTrainingCurvesArtifact(artifact: ArtifactItem) {
  return [artifactPath(artifact), artifactName(artifact)].some((value) => (
    value?.split(/[\\/]/).pop()?.toLowerCase() === 'combined_training_curves.png'
  ));
}

function isCombinedTrainingCurvesArtifact(artifact: ArtifactItem) {
  return artifactExists(artifact) && isNamedCombinedTrainingCurvesArtifact(artifact);
}

function mergeArtifacts(rawArtifacts: ArtifactRow[], summarizedArtifacts: RunArtifact[]) {
  const remainingSummaries = [...summarizedArtifacts];
  const mergedRaw = rawArtifacts.map((raw) => {
    const path = artifactPath(raw);
    const matchingIndex = remainingSummaries.findIndex((summary) => (
      artifactPath(summary) === path
      && (
        String(summary.created_at ?? '') === String(raw.created_at ?? '')
        || artifactName(summary) === artifactName(raw)
      )
    ));
    if (matchingIndex < 0) return raw;
    const [summary] = remainingSummaries.splice(matchingIndex, 1);
    return { ...raw, ...summary, id: artifactId(raw) };
  });
  return [...mergedRaw, ...remainingSummaries];
}

function artifactExists(artifact: ArtifactItem) {
  return !('exists' in artifact) || artifact.exists !== false;
}

function artifactGroup(artifact: ArtifactItem): ArtifactGroupName {
  const searchable = `${artifact.artifact_type ?? ''} ${artifactName(artifact)} ${artifactPath(artifact) ?? ''}`.toLowerCase();
  if (/explain|grad.?cam|lime|shap/.test(searchable)) return 'Explicabilidad';
  if (/predict|inference|case/.test(searchable)) return 'Predicciones';
  if (/\.log$|log_|logs?|stdout|stderr/.test(searchable)) return 'Logs';
  if (/\.keras$|\.h5$|model|checkpoint|weight/.test(searchable)) return 'Modelos';
  if (/\.png$|\.jpe?g$|\.webp$|plot|curve|confusion/.test(searchable)) return 'Gráficos';
  if (/metric|report|history|calibration|\.csv$|\.json$|\.md$/.test(searchable)) return 'Métricas';
  return 'Otros';
}

function booleanText(value: boolean | null | undefined) {
  if (value === true) return 'Sí';
  if (value === false) return 'No';
  return 'No disponible';
}

function caseTypeLabel(caseType: string | null | undefined) {
  const labels: Record<string, string> = {
    true_positive: 'Verdadero positivo',
    true_negative: 'Verdadero negativo',
    false_positive: 'Falso positivo',
    false_negative: 'Falso negativo',
    low_confidence: 'Baja confianza',
  };
  return caseType ? labels[caseType] ?? caseType : '-';
}

function TableImageLink({
  url,
  alt,
  label,
}: {
  url: string | null;
  alt: string;
  label: string;
}) {
  const [failed, setFailed] = useState(false);
  if (!url || failed) return <span className="muted-text">{failed ? 'Imagen no disponible' : 'Sin imagen'}</span>;
  return (
    <a className="table-image-cell" href={url} target="_blank" rel="noreferrer">
      <img src={url} alt={alt} loading="lazy" decoding="async" onError={() => setFailed(true)} />
      <span>{label}</span>
    </a>
  );
}

function nestedValue(record: JsonRecord, path: string) {
  return path.split('.').reduce<unknown>((current, key) => {
    const currentRecord = recordValue(current);
    return currentRecord?.[key];
  }, record);
}

function isAvailable(value: unknown) {
  return value !== null && value !== undefined && value !== '';
}

function firstAvailable(...values: unknown[]) {
  return values.find(isAvailable) ?? null;
}

function parameterValue(parameters: JsonRecord, cliArguments: JsonRecord, ...paths: string[]) {
  for (const path of paths) {
    const direct = nestedValue(parameters, path);
    if (isAvailable(direct)) return direct;
    const cli = nestedValue(cliArguments, path);
    if (isAvailable(cli)) return cli;
  }
  return null;
}

function displayParameterValue(value: unknown) {
  if (!isAvailable(value)) return 'No disponible';
  if (typeof value === 'boolean') return value ? 'Sí' : 'No';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function confusionCounts(confusionMatrix: ReturnType<typeof resolveConfusionMatrix>) {
  const matrix = confusionMatrix?.matrix ?? [];
  return {
    tn: numberValue(confusionMatrix?.tn) ?? numberValue(matrix[0]?.[0]),
    fp: numberValue(confusionMatrix?.fp) ?? numberValue(matrix[0]?.[1]),
    fn: numberValue(confusionMatrix?.fn) ?? numberValue(matrix[1]?.[0]),
    tp: numberValue(confusionMatrix?.tp) ?? numberValue(matrix[1]?.[1]),
  };
}

function criticalPoints({
  metrics,
  counts,
  recallReference,
  recallReferenceLabel,
  clinical,
  possibleOverfitting,
  errors,
  optionalFailures,
}: {
  metrics: ReturnType<typeof resolveClinicalMetrics>;
  counts: ReturnType<typeof confusionCounts>;
  recallReference: number | null;
  recallReferenceLabel: string | null;
  clinical: RunClinicalSummary | null;
  possibleOverfitting: boolean;
  errors: JsonRecord[];
  optionalFailures: string[];
}) {
  const points: CriticalPoint[] = [];
  const recall = numberValue(metrics.recall_parasitized);
  if (recall !== null && recallReference !== null && recall < recallReference) {
    points.push({
      level: 'critical',
      text: `Recall ${formatMetric(recall)} bajo la referencia ${recallReferenceLabel ?? 'configurada'} ${formatMetric(recallReference)}.`,
    });
  } else if (recall !== null && recallReference === null && recall < TECHNICAL_METRIC_REFERENCE) {
    points.push({
      level: 'warning',
      text: `Recall bajo la referencia técnica exploratoria ${formatMetric(TECHNICAL_METRIC_REFERENCE)}.`,
    });
  }
  ([
    ['Specificity', metrics.specificity],
    ['F2-score', metrics.f2_parasitized],
    ['PR-AUC', metrics.pr_auc_parasitized],
  ] as const).forEach(([label, value]) => {
    const numericValue = numberValue(value);
    if (numericValue !== null && numericValue < TECHNICAL_METRIC_REFERENCE) {
      points.push({
        level: 'warning',
        text: `${label} bajo la referencia técnica exploratoria ${formatMetric(TECHNICAL_METRIC_REFERENCE)}.`,
      });
    }
  });
  if (counts.fn !== null && counts.fn > 0) {
    points.push({ level: 'critical', text: `${counts.fn} falsos negativos requieren revisión prioritaria.` });
  }
  if (counts.fp !== null && counts.fp > 0) {
    points.push({ level: 'warning', text: `${counts.fp} falsos positivos pueden aumentar revisiones innecesarias.` });
  }
  if (clinical?.checkpoint_policy.policy_satisfied === false) {
    points.push({ level: 'critical', text: 'La política de checkpoint configurada no fue satisfecha.' });
  }
  if (clinical?.clinical_threshold.target_recall_satisfied === false) {
    points.push({ level: 'critical', text: 'El threshold calibrado no satisface el target recall en validación.' });
  }
  if (clinical?.clinical_threshold.enabled && clinical.clinical_threshold.threshold_used == null) {
    points.push({ level: 'warning', text: 'No se registró el threshold finalmente usado por esta ejecución.' });
  }
  if (clinical?.clinical_metrics.prediction_collapse_detected) {
    points.push({ level: 'critical', text: 'Se detectó colapso en la distribución de predicciones.' });
  }
  const checkpointWarning = firstAvailable(
    clinical?.checkpoint_policy.warning,
    clinical?.checkpoint_policy.checkpoint_warning,
  );
  if (checkpointWarning) {
    points.push({ level: 'warning', text: String(checkpointWarning) });
  }
  const thresholdWarning = firstAvailable(
    clinical?.clinical_threshold.warning,
    clinical?.clinical_threshold.threshold_warning,
  );
  if (thresholdWarning) {
    points.push({ level: 'warning', text: String(thresholdWarning) });
  }
  if (clinical?.clinical_threshold.enabled) {
    points.push({
      level: 'warning',
      text: 'El threshold se calibra en validation; el API actual no permite verificar aquí el split donde se evaluó.',
    });
  }
  if (possibleOverfitting) {
    points.push({ level: 'warning', text: 'El historial presenta una señal simple de posible sobreajuste.' });
  }
  if (errors.length > 0) {
    const firstError = errors[0];
    const message = firstAvailable(firstError.error_message, firstError.message, firstError.error_type);
    points.push({ level: 'critical', text: `La ejecución registró un error${message ? `: ${String(message)}` : '.'}` });
  }
  const hasMetricEvidence = [
    metrics.recall_parasitized,
    metrics.specificity,
    metrics.f2_parasitized,
    metrics.pr_auc_parasitized,
    metrics.roc_auc_parasitized,
    metrics.accuracy,
  ].some((value) => numberValue(value) !== null);
  const hasConfusionEvidence = Object.values(counts).some((value) => value !== null);
  if (!hasMetricEvidence && !hasConfusionEvidence) {
    points.push({
      level: 'warning',
      text: 'Datos clínicos insuficientes: no es posible concluir que este run esté libre de alertas.',
    });
  }
  if (optionalFailures.length > 0) {
    points.push({
      level: 'warning',
      text: `No respondieron fuentes auxiliares: ${optionalFailures.join(', ')}.`,
    });
  }
  return points;
}

function quickReading({
  metrics,
  counts,
  recallReference,
  recallReferenceLabel,
  possibleOverfitting,
  overfittingAssessmentAvailable,
  fineTuningEpoch,
}: {
  metrics: ReturnType<typeof resolveClinicalMetrics>;
  counts: ReturnType<typeof confusionCounts>;
  recallReference: number | null;
  recallReferenceLabel: string | null;
  possibleOverfitting: boolean;
  overfittingAssessmentAvailable: boolean;
  fineTuningEpoch: number | null;
}) {
  const sentences: string[] = [];
  const rocAuc = numberValue(metrics.roc_auc_parasitized);
  const prAuc = numberValue(metrics.pr_auc_parasitized);
  if ((rocAuc !== null && rocAuc >= 0.9) || (prAuc !== null && prAuc >= 0.9)) {
    sentences.push('Las AUC registradas muestran una discriminación global alta en esta evaluación experimental.');
  } else if (rocAuc !== null || prAuc !== null) {
    sentences.push('Las AUC registradas deben interpretarse junto con sensibilidad, especificidad y distribución de errores.');
  }
  const recall = numberValue(metrics.recall_parasitized);
  if (recall !== null && recallReference !== null) {
    sentences.push(
      recall >= recallReference
        ? `El recall parasitized alcanza la referencia ${recallReferenceLabel ?? 'configurada'} de ${formatMetric(recallReference)}.`
        : `El recall parasitized no alcanza la referencia ${recallReferenceLabel ?? 'configurada'} de ${formatMetric(recallReference)}.`,
    );
  }
  if (counts.tp !== null || counts.tn !== null) {
    sentences.push(`La matriz registra ${counts.tp ?? 'sin dato'} TP y ${counts.tn ?? 'sin dato'} TN como aciertos.`);
  }
  if (counts.fn !== null || counts.fp !== null) {
    sentences.push(`Los errores incluyen ${counts.fn ?? 'sin dato'} FN y ${counts.fp ?? 'sin dato'} FP.`);
  }
  if (overfittingAssessmentAvailable) {
    sentences.push(
      possibleOverfitting
        ? 'Las diferencias finales train-validation activan una heurística técnica de posible sobreajuste.'
        : 'No se activaron señales fuertes de sobreajuste con las diferencias finales disponibles.',
    );
  } else {
    sentences.push('El historial no contiene pares train-validation suficientes para evaluar sobreajuste.');
  }
  if (fineTuningEpoch !== null) {
    sentences.push(`El fine-tuning comenzó en la época ${fineTuningEpoch}.`);
  }
  return sentences;
}

async function copyToClipboard(value: string) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch {
    // El fallback siguiente también funciona en contextos HTTP locales.
  }
  const textarea = document.createElement('textarea');
  textarea.value = value;
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  try {
    const copied = document.execCommand('copy');
    textarea.remove();
    return copied;
  } catch {
    textarea.remove();
    return false;
  }
}

export function RunDetail({ datasource, runId, onExplainabilitySelect }: RunDetailProps) {
  const [detail, setDetail] = useState<RunDetailResponse | null>(null);
  const [clinical, setClinical] = useState<RunClinicalSummary | null>(null);
  const [confusion, setConfusion] = useState<JsonRecord[]>([]);
  const [report, setReport] = useState<JsonRecord[]>([]);
  const [artifacts, setArtifacts] = useState<RunArtifact[]>([]);
  const [imagePredictions, setImagePredictions] = useState<RunImagePrediction[]>([]);
  const [imagePredictionTotal, setImagePredictionTotal] = useState(0);
  const [explainability, setExplainability] = useState<ExplainabilityCase[]>([]);
  const [predictionFilters, setPredictionFilters] = useState<PredictionFilters>({
    split: '',
    caseType: '',
    className: '',
    correct: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [predictionsError, setPredictionsError] = useState<string | null>(null);
  const [optionalLoadErrors, setOptionalLoadErrors] = useState<string[]>([]);
  const [optionalDataLoading, setOptionalDataLoading] = useState(false);
  const [trainingCurvesLoadFailed, setTrainingCurvesLoadFailed] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    let active = true;
    setError(null);
    setDetail(null);
    setClinical(null);
    setConfusion([]);
    setReport([]);
    setArtifacts([]);
    setExplainability([]);
    setOptionalLoadErrors([]);
    setOptionalDataLoading(true);
    setTrainingCurvesLoadFailed(false);
    setCopyFeedback(null);

    api.getRun(datasource, runId)
      .then((response) => {
        if (active) setDetail(response);
      })
      .catch((requestError: Error) => {
        if (active) setError(requestError.message);
      });

    let pendingOptionalRequests = 5;
    const loadOptional = <T,>(label: string, request: Promise<T>, apply: (value: T) => void) => {
      request
        .then((value) => {
          if (active) apply(value);
        })
        .catch(() => {
          if (!active) return;
          setOptionalLoadErrors((current) => current.includes(label) ? current : [...current, label]);
        })
        .finally(() => {
          if (!active) return;
          pendingOptionalRequests -= 1;
          if (pendingOptionalRequests === 0) setOptionalDataLoading(false);
        });
    };

    loadOptional('matriz legacy', api.getConfusionMatrix(datasource, runId), (response) => setConfusion(response.items));
    loadOptional('reporte de clasificación', api.getClassificationReport(datasource, runId), (response) => setReport(response.items));
    loadOptional('resumen clínico', api.getRunClinicalSummary(datasource, runId), setClinical);
    loadOptional('artefactos', api.getRunArtifactsSummary(datasource, runId), (response) => setArtifacts(response.items));
    loadOptional('explicabilidad', api.getRunExplainability(datasource, runId, { limit: 50 }), (response) => setExplainability(response.items));

    return () => {
      active = false;
    };
  }, [datasource, runId]);

  useEffect(() => {
    if (!runId) return;
    let active = true;
    setPredictionsError(null);
    setImagePredictions([]);
    setImagePredictionTotal(0);
    api
      .getRunImagePredictions(datasource, runId, {
        split: predictionFilters.split || undefined,
        case_type: predictionFilters.caseType || undefined,
        class_name: predictionFilters.className || undefined,
        is_correct: predictionFilters.correct || undefined,
        limit: 100,
        offset: 0,
      })
      .then((response) => {
        if (!active) return;
        setImagePredictions(response.items);
        setImagePredictionTotal(response.total);
      })
      .catch((requestError: Error) => {
        if (active) setPredictionsError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, [datasource, runId, predictionFilters]);

  if (!runId) return <section className="panel">Selecciona una ejecución.</section>;
  if (error) return <section className="panel error">{error}</section>;
  if (!detail) return <Loading />;

  const run = detail.run;
  const executionParameters = normalizeExecutionParameters(run);
  const cliArguments = recordValue(executionParameters.cli_arguments) ?? {};
  const commandSummary = resolveCommand(run, executionParameters);
  const recordedArgvMayNeedInterpreter = Boolean(
    commandSummary.command
    && !commandSummary.reconstructed
    && !/^(python(?:3(?:\.\d+)?)?|uv\s+run|poetry\s+run|bash|sh)\b/i.test(commandSummary.command),
  );
  const modelName = String(firstAvailable(
    run.model_name,
    clinical?.model_name,
    parameterValue(executionParameters, cliArguments, 'model_name', 'model'),
    'No disponible',
  ));
  const executionType = String(firstAvailable(
    run.execution_type,
    parameterValue(executionParameters, cliArguments, 'execution_type'),
    run.run_type,
    clinical?.run_type,
    'No disponible',
  ));
  const datasetName = String(firstAvailable(
    run.dataset_name,
    parameterValue(executionParameters, cliArguments, 'dataset_name', 'dataset_dir'),
    'No disponible',
  ));
  const status = String(firstAvailable(run.status, clinical?.status, 'unknown'));
  const startedAt = firstAvailable(run.started_at, clinical?.started_at) as JsonValue;
  const finishedAt = firstAvailable(run.finished_at, clinical?.finished_at) as JsonValue;
  const durationSeconds = resolveDurationSeconds({ ...run, started_at: startedAt, finished_at: finishedAt });
  const clinicalMetrics = resolveClinicalMetrics(clinical?.clinical_metrics, detail.metrics, run);
  const normalizedConfusion = resolveConfusionMatrix(clinical?.confusion_matrix, confusion);
  const counts = confusionCounts(normalizedConfusion);
  const fineTuningMarker = firstAvailable(
    run.fine_tuning_start_epoch,
    parameterValue(executionParameters, cliArguments, 'fine_tuning_start_epoch'),
  );
  const trainingSignals = resolveTrainingSignals(detail.training_history, fineTuningMarker);
  const trackedSelectedEpoch = numberValue(clinical?.checkpoint_policy.selected_epoch)
    ?? numberValue(parameterValue(executionParameters, cliArguments, 'best_epoch'));
  const selectedEpoch = trackedSelectedEpoch ?? trainingSignals.bestEpoch;
  const selectedEpochLabel = trackedSelectedEpoch !== null ? 'Mejor época' : 'Mejor val accuracy';
  const checkpointPolicyName = String(firstAvailable(
    clinical?.checkpoint_policy.policy,
    parameterValue(executionParameters, cliArguments, 'checkpoint_policy'),
    '',
  )).toLowerCase();
  const checkpointRecallReference = checkpointPolicyName.includes('min_recall')
    ? numberValue(clinical?.checkpoint_policy.min_recall_required)
      ?? numberValue(parameterValue(executionParameters, cliArguments, 'min_recall'))
    : null;
  const thresholdParameter = parameterValue(executionParameters, cliArguments, 'threshold');
  const calibrationEnabled = clinical?.clinical_threshold.enabled === true
    || booleanValue(parameterValue(executionParameters, cliArguments, 'calibrate_threshold')) === true
    || textValue(thresholdParameter)?.toLowerCase() === 'clinical';
  const calibrationRecallReference = calibrationEnabled
    ? numberValue(clinical?.clinical_threshold.target_recall)
      ?? numberValue(parameterValue(executionParameters, cliArguments, 'target_recall'))
    : null;
  const recallReference = checkpointRecallReference ?? calibrationRecallReference;
  const recallReferenceLabel = checkpointRecallReference !== null
    ? 'de checkpoint en validation'
    : calibrationRecallReference !== null ? 'de calibración en validation' : null;
  const baseEpochs = numberValue(parameterValue(executionParameters, cliArguments, 'epochs'));
  const fineTuneEpochs = numberValue(parameterValue(executionParameters, cliArguments, 'fine_tune_epochs'));
  const historyCompletedEpochs = detail.training_history.reduce((maximum, row) => (
    Math.max(maximum, (numberValue(row.epoch) ?? -1) + 1)
  ), 0);
  const storedCompletedEpochs = numberValue(run.completed_epochs)
    ?? numberValue(parameterValue(executionParameters, cliArguments, 'completed_epochs'));
  const completedEpochs = storedCompletedEpochs === null || (storedCompletedEpochs === 0 && historyCompletedEpochs > 0)
    ? historyCompletedEpochs || null
    : storedCompletedEpochs;
  const totalEpochs = numberValue(run.total_epochs)
    ?? numberValue(parameterValue(executionParameters, cliArguments, 'total_epochs'))
    ?? (baseEpochs !== null ? baseEpochs + (fineTuneEpochs ?? 0) : null);
  const fineTuningDisplay = trainingSignals.fineTuningEpoch !== null
    ? `Época ${trainingSignals.fineTuningEpoch}${trainingSignals.fineTuningMarker !== null ? ` · marcador gráfico ${trainingSignals.fineTuningMarker}` : ''}`
    : fineTuneEpochs === 0 ? 'No aplica' : 'No disponible';
  const hasTrainingSummary = trainingSignals.available
    || selectedEpoch !== null
    || trainingSignals.fineTuningEpoch !== null;
  const points = criticalPoints({
    metrics: clinicalMetrics,
    counts,
    recallReference,
    recallReferenceLabel,
    clinical,
    possibleOverfitting: trainingSignals.possibleOverfitting,
    errors: detail.errors,
    optionalFailures: optionalLoadErrors,
  });
  const reading = quickReading({
    metrics: clinicalMetrics,
    counts,
    recallReference,
    recallReferenceLabel,
    possibleOverfitting: trainingSignals.possibleOverfitting,
    overfittingAssessmentAvailable: trainingSignals.assessmentAvailable,
    fineTuningEpoch: trainingSignals.fineTuningEpoch,
  });
  const mergedArtifacts = mergeArtifacts(detail.artifacts, artifacts);
  const groupedArtifacts = ARTIFACT_GROUP_ORDER.map((groupName) => ({
    groupName,
    items: mergedArtifacts.filter((artifact) => artifactGroup(artifact) === groupName),
  })).filter((group) => group.items.length > 0);
  const registeredTrainingCurvesArtifact = mergedArtifacts.find(isNamedCombinedTrainingCurvesArtifact);
  const trainingCurvesArtifact = mergedArtifacts.find(isCombinedTrainingCurvesArtifact);
  const trainingCurvesPath = trainingCurvesArtifact ? artifactPath(trainingCurvesArtifact) : null;
  const trainingCurvesUrl = trainingCurvesArtifact && trainingCurvesPath
    ? api.artifactUrl(trainingCurvesPath, {
        artifactId: artifactId(trainingCurvesArtifact),
        datasource,
      })
    : null;
  const effectiveThreshold = numberValue(clinical?.clinical_threshold.threshold_used)
    ?? numberValue(thresholdParameter);
  const parameterGroups: ParameterGroup[] = [
    {
      title: 'Modelo',
      items: [
        { key: 'model_name', label: 'Nombre', value: modelName },
        { key: 'model_type', label: 'Tipo', value: firstAvailable(run.model_type, parameterValue(executionParameters, cliArguments, 'model_type')) },
        { key: 'architecture', label: 'Arquitectura', value: firstAvailable(run.architecture, parameterValue(executionParameters, cliArguments, 'architecture')) },
        { key: 'checkpoint_policy', label: 'Política de checkpoint', value: firstAvailable(clinical?.checkpoint_policy.policy, parameterValue(executionParameters, cliArguments, 'checkpoint_policy')) },
        { key: 'checkpoint_metric', label: 'Métrica de checkpoint', value: firstAvailable(clinical?.checkpoint_policy.selected_metric, parameterValue(executionParameters, cliArguments, 'checkpoint_metric')) },
        { key: 'positive_label', label: 'Clase positiva', value: firstAvailable(parameterValue(executionParameters, cliArguments, 'positive_label', 'positive_class_name'), clinical?.label_mapping.positive_class) },
      ],
    },
    {
      title: 'Entrenamiento',
      items: [
        { key: 'epochs', label: 'Épocas base', value: parameterValue(executionParameters, cliArguments, 'epochs') },
        { key: 'fine_tune_epochs', label: 'Épocas fine-tuning', value: parameterValue(executionParameters, cliArguments, 'fine_tune_epochs') },
        { key: 'batch_size', label: 'Batch size', value: parameterValue(executionParameters, cliArguments, 'batch_size') },
        { key: 'img_size', label: 'Tamaño de imagen', value: parameterValue(executionParameters, cliArguments, 'img_size') },
        { key: 'learning_rate', label: 'Learning rate', value: parameterValue(executionParameters, cliArguments, 'learning_rate') },
        { key: 'fine_tune_learning_rate', label: 'Learning rate FT', value: parameterValue(executionParameters, cliArguments, 'fine_tune_learning_rate') },
        { key: 'seed', label: 'Seed', value: firstAvailable(run.random_seed, parameterValue(executionParameters, cliArguments, 'seed')) },
        { key: 'preprocessing', label: 'Preprocesamiento', value: parameterValue(executionParameters, cliArguments, 'preprocessing', 'preprocessing_mode') },
      ],
    },
    {
      title: 'Decisión clínica',
      items: [
        { key: 'threshold', label: 'Threshold usado', value: effectiveThreshold },
        { key: 'threshold_mode', label: 'Configuración de threshold', value: typeof thresholdParameter === 'string' ? thresholdParameter : null },
        { key: 'threshold_source', label: 'Fuente del threshold', value: firstAvailable(clinical?.clinical_threshold.threshold_source, parameterValue(executionParameters, cliArguments, 'threshold_source')) },
        { key: 'calibration_split', label: 'Split de calibración', value: firstAvailable(clinical?.clinical_threshold.calibration_split, parameterValue(executionParameters, cliArguments, 'calibration_split')) },
        { key: 'min_recall', label: 'Recall mínimo', value: firstAvailable(clinical?.checkpoint_policy.min_recall_required, parameterValue(executionParameters, cliArguments, 'min_recall')) },
        { key: 'target_recall', label: 'Target recall', value: firstAvailable(clinical?.clinical_threshold.target_recall, parameterValue(executionParameters, cliArguments, 'target_recall')) },
        { key: 'policy_satisfied', label: 'Política satisfecha', value: clinical?.checkpoint_policy.policy_satisfied ?? parameterValue(executionParameters, cliArguments, 'policy_satisfied') },
      ],
    },
    {
      title: 'Datos',
      items: [
        { key: 'dataset_name', label: 'Dataset', value: datasetName },
        { key: 'split', label: 'Split', value: parameterValue(executionParameters, cliArguments, 'split', 'split_name', 'dataset_split') },
        { key: 'train_count', label: 'Imágenes train', value: firstAvailable(parameterValue(executionParameters, cliArguments, 'counts.train.total', 'train_count')) },
        { key: 'validation_count', label: 'Imágenes validation', value: firstAvailable(parameterValue(executionParameters, cliArguments, 'counts.val.total', 'counts.validation.total', 'validation_count', 'val_count')) },
        { key: 'test_count', label: 'Imágenes test', value: firstAvailable(parameterValue(executionParameters, cliArguments, 'counts.test.total', 'test_count')) },
      ],
    },
  ];

  const handleCopy = async (value: string, key: string) => {
    const copied = await copyToClipboard(value);
    setCopyFeedback(copied ? key : 'copy-error');
    if (copied) window.setTimeout(() => setCopyFeedback((current) => current === key ? null : current), 1800);
  };

  return (
    <section className="page run-detail-page">
      <span className="run-detail-sr-only" aria-live="polite">
        {copyFeedback === 'copy-error' ? 'No fue posible acceder al portapapeles.' : copyFeedback ? 'Contenido copiado.' : ''}
      </span>
      <section className="panel run-detail-summary" aria-labelledby="run-detail-title">
        <div className="run-detail-summary__primary">
          <p className="run-detail-eyebrow">Ficha técnica reproducible</p>
          <div className="run-detail-summary__title-row">
            <h1 id="run-detail-title">{modelName}</h1>
            <span className="run-detail-type">{executionType}</span>
            <StatusBadge status={status} />
          </div>
          <p>{String(firstAvailable(run.run_name, run.experiment_name, 'Ejecución registrada'))}</p>
        </div>
        <dl className="run-detail-summary__facts">
          <div><dt>Dataset</dt><dd>{datasetName}</dd></div>
          <div><dt>Run ID</dt><dd><code>{String(firstAvailable(run.id, runId))}</code></dd></div>
          <div><dt>Inicio</dt><dd>{formatDate(String(startedAt ?? ''))}</dd></div>
          <div><dt>Fin</dt><dd>{finishedAt ? formatDate(String(finishedAt)) : status === 'started' ? 'En ejecución' : 'No finalizado'}</dd></div>
          <div><dt>Duración</dt><dd className="run-detail-tabular">{formatDuration(durationSeconds)}</dd></div>
          <div><dt>Épocas</dt><dd>{displayParameterValue(completedEpochs)} / {displayParameterValue(totalEpochs)}</dd></div>
        </dl>
      </section>

      {optionalLoadErrors.length > 0 ? (
        <p className="run-detail-data-notice" role="status">
          Datos parciales: no respondieron {optionalLoadErrors.join(', ')}. La ficha usa las fuentes disponibles del run.
        </p>
      ) : null}

      <section className="panel run-detail-command" aria-labelledby="run-command-title">
        <div className="section-heading run-detail-section-heading">
          <div>
            <h2 id="run-command-title">Comando ejecutado</h2>
            <span className={`run-detail-provenance ${!commandSummary.command ? 'unavailable' : commandSummary.reconstructed ? 'reconstructed' : 'exact'}`}>
              {!commandSummary.command ? 'No disponible' : commandSummary.reconstructed ? 'Reconstruido desde parámetros' : 'ARGV registrado por la ejecución'}
            </span>
          </div>
          <button
            className="run-detail-copy-button"
            type="button"
            disabled={!commandSummary.command}
            aria-live="polite"
            onClick={() => commandSummary.command && handleCopy(commandSummary.command, 'command')}
          >
            {copyFeedback === 'command' ? 'Comando copiado' : 'Copiar comando'}
          </button>
        </div>
        {commandSummary.command ? <code>{commandSummary.command}</code> : <p className="muted-text">Sin comando registrado ni parámetros suficientes para reconstruirlo.</p>}
        {recordedArgvMayNeedInterpreter ? (
          <p className="run-detail-command-note">El backend conserva el ARGV exacto. Si comienza en un archivo Python, puede requerir anteponer el mismo intérprete usado en el entorno original.</p>
        ) : null}
        {copyFeedback === 'copy-error' ? <p className="error-text">No fue posible acceder al portapapeles.</p> : null}
      </section>

      <section className="panel run-detail-metrics" aria-labelledby="main-metrics-title">
        <div className="section-heading run-detail-section-heading">
          <div>
            <h2 id="main-metrics-title">Métricas principales</h2>
            <span>Clase positiva: parasitized = 1</span>
          </div>
          {recallReference !== null ? <span className="run-detail-goal">Referencia recall ≥ {formatMetric(recallReference)}</span> : null}
        </div>
        <ClinicalMetricsCards metrics={clinicalMetrics} minRecall={recallReference} />
      </section>

      <div className="run-detail-analysis-grid">
        <section className="panel run-detail-confusion" aria-labelledby="confusion-title">
          <div className="section-heading run-detail-section-heading">
            <div>
              <h2 id="confusion-title">Matriz de confusión</h2>
              <span>Valores absolutos y porcentaje del total</span>
            </div>
          </div>
          <ConfusionMatrix confusionMatrix={normalizedConfusion} />
        </section>

        <section className="panel run-detail-critical" aria-labelledby="critical-title">
          <div className="section-heading run-detail-section-heading">
            <div>
              <h2 id="critical-title">Puntos críticos</h2>
              <span>Reglas técnicas simples y auditables</span>
            </div>
          </div>
          {points.length > 0 ? (
            <ul className="run-detail-critical-list">
              {points.map((point, index) => (
                <li className={`run-detail-critical-item ${point.level}`} key={`${point.text}-${index}`}>
                  <span aria-hidden="true">{point.level === 'critical' ? '!' : '△'}</span>
                  <p>{point.text}</p>
                </li>
              ))}
            </ul>
          ) : optionalDataLoading ? (
            <div className="run-detail-no-critical pending" role="status">
              <strong>Evaluación en curso</strong>
              <span>Cargando las fuentes clínicas auxiliares antes de cerrar esta lectura.</span>
            </div>
          ) : (
            <div className="run-detail-no-critical" role="status">
              <strong>Sin alertas automáticas</strong>
              <span>No se activaron las reglas disponibles para este run.</span>
            </div>
          )}
          <p className="run-detail-rule-note">Recall sin referencia configurada, Specificity, F2 y PR-AUC usan 0,80 como heurística exploratoria. La lectura de AUC usa 0,90. No son umbrales clínicos.</p>
        </section>
      </div>

      <div className="run-detail-training-grid">
        <section className="panel" aria-labelledby="training-signals-title">
          <div className="section-heading run-detail-section-heading">
            <div>
              <h2 id="training-signals-title">Señales de entrenamiento</h2>
              <span>Última época registrada</span>
            </div>
          </div>
          {hasTrainingSummary ? (
            <>
              <dl className="run-detail-signal-grid">
                <div><dt>Train accuracy</dt><dd>{formatMetric(trainingSignals.trainAccuracy)}</dd></div>
                <div><dt>Val accuracy</dt><dd>{formatMetric(trainingSignals.validationAccuracy)}</dd></div>
                <div><dt>Gap accuracy</dt><dd>{formatMetric(trainingSignals.accuracyGap)}</dd></div>
                <div><dt>Train loss</dt><dd>{formatMetric(trainingSignals.trainLoss)}</dd></div>
                <div><dt>Val loss</dt><dd>{formatMetric(trainingSignals.validationLoss)}</dd></div>
                <div><dt>Gap loss</dt><dd>{formatMetric(trainingSignals.lossGap)}</dd></div>
                <div><dt>{selectedEpochLabel}</dt><dd>{selectedEpoch ?? 'No disponible'}</dd></div>
                <div><dt>Inicio fine-tuning</dt><dd>{fineTuningDisplay}</dd></div>
              </dl>
              <div className={`run-detail-training-reading ${trainingSignals.possibleOverfitting ? 'warning' : trainingSignals.assessmentAvailable ? 'stable' : 'unknown'}`}>
                <strong>{trainingSignals.possibleOverfitting ? 'Posible sobreajuste' : trainingSignals.assessmentAvailable ? 'Sin señales fuertes de sobreajuste' : 'Historial insuficiente'}</strong>
                <p>
                  {trainingSignals.possibleOverfitting
                    ? trainingSignals.reasons.join('; ')
                    : trainingSignals.assessmentAvailable
                      ? 'Los gaps disponibles no superan 0,05 en accuracy ni 0,10 en loss.'
                      : 'Falta al menos un par train-validation para calcular los gaps.'}
                </p>
              </div>
            </>
          ) : (
            <p className="run-detail-empty-state">Historial insuficiente para evaluar señales de sobreajuste.</p>
          )}
        </section>

        <section className="panel run-detail-curves" aria-labelledby="training-curves-title">
          <div className="section-heading run-detail-section-heading">
            <div>
              <h2 id="training-curves-title">Curvas de entrenamiento</h2>
              <span>Accuracy y loss por época</span>
            </div>
            {trainingCurvesUrl && !trainingCurvesLoadFailed ? (
              <a className="run-detail-action-link" href={trainingCurvesUrl} target="_blank" rel="noreferrer">Abrir gráfico</a>
            ) : null}
          </div>
          {trainingCurvesUrl && !trainingCurvesLoadFailed ? (
            <figure className="training-curves-figure">
              <a href={trainingCurvesUrl} target="_blank" rel="noreferrer">
                <img
                  src={trainingCurvesUrl}
                  alt="Curvas combinadas de accuracy y loss del entrenamiento"
                  onError={() => setTrainingCurvesLoadFailed(true)}
                />
              </a>
              <figcaption>{trainingCurvesPath}</figcaption>
            </figure>
          ) : (
            <p className="run-detail-empty-state">
              {trainingCurvesLoadFailed
                ? 'La curva está registrada, pero no fue posible cargar su imagen.'
                : registeredTrainingCurvesArtifact && !artifactExists(registeredTrainingCurvesArtifact)
                  ? 'La curva está registrada, pero figura como no disponible en metadata.'
                  : 'No hay curvas de entrenamiento registradas para esta ejecución.'}
            </p>
          )}
        </section>
      </div>

      <section className="panel run-detail-parameters" aria-labelledby="parameters-title">
        <div className="section-heading run-detail-section-heading">
          <div>
            <h2 id="parameters-title">Parámetros de ejecución</h2>
            <span>Valores efectivos priorizados sobre el payload legacy</span>
          </div>
          <button
            className="run-detail-copy-button"
            type="button"
            aria-live="polite"
            onClick={() => handleCopy(JSON.stringify(executionParameters, null, 2), 'parameters')}
          >
            {copyFeedback === 'parameters' ? 'Parámetros copiados' : 'Copiar parámetros'}
          </button>
        </div>
        <div className="run-detail-parameter-groups">
          {parameterGroups.map((group) => (
            <section className="run-detail-parameter-group" key={group.title}>
              <h3>{group.title}</h3>
              <dl>
                {group.items.map((item) => (
                  <div key={item.key}>
                    <dt>{item.label}<code>{item.key}</code></dt>
                    <dd title={displayParameterValue(item.value)}>{displayParameterValue(item.value)}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
      </section>

      <section className="panel run-detail-reading" aria-labelledby="quick-reading-title">
        <div className="section-heading run-detail-section-heading">
          <div>
            <h2 id="quick-reading-title">Lectura rápida del resultado</h2>
            <span>Síntesis generada con reglas visibles en esta ficha</span>
          </div>
        </div>
        <div className="run-detail-reading__content">
          {reading.map((sentence) => <p key={sentence}>{sentence}</p>)}
        </div>
        <p className="run-detail-disclaimer"><strong>Resultado experimental.</strong> No corresponde a diagnóstico clínico definitivo.</p>
      </section>

      <details className="panel run-detail-disclosure">
        <summary>
          <span>Predicciones por imagen</span>
          <small>{imagePredictionTotal} registros · detalle opcional</small>
        </summary>
        <div className="run-detail-disclosure__content">
          <div className="filters-grid">
            <label>
              Split
              <select value={predictionFilters.split} onChange={(event) => setPredictionFilters((current) => ({ ...current, split: event.target.value }))}>
                <option value="">Todos</option><option value="train">train</option><option value="val">val</option><option value="test">test</option><option value="external">external</option>
              </select>
            </label>
            <label>
              Tipo de caso
              <select value={predictionFilters.caseType} onChange={(event) => setPredictionFilters((current) => ({ ...current, caseType: event.target.value }))}>
                <option value="">Todos</option><option value="true_positive">true_positive</option><option value="true_negative">true_negative</option><option value="false_positive">false_positive</option><option value="false_negative">false_negative</option><option value="low_confidence">low_confidence</option>
              </select>
            </label>
            <label>
              Clase
              <select value={predictionFilters.className} onChange={(event) => setPredictionFilters((current) => ({ ...current, className: event.target.value }))}>
                <option value="">Todas</option><option value="uninfected">uninfected</option><option value="parasitized">parasitized</option>
              </select>
            </label>
            <label>
              Correcta
              <select value={predictionFilters.correct} onChange={(event) => setPredictionFilters((current) => ({ ...current, correct: event.target.value }))}>
                <option value="">Todas</option><option value="true">Sí</option><option value="false">No</option>
              </select>
            </label>
          </div>
          {predictionsError ? <p className="error-text">{predictionsError}</p> : null}
          <DataTable<RunImagePrediction>
            rows={imagePredictions}
            columns={[
              { header: 'Archivo', render: (row) => row.filename ?? row.relative_path ?? '-' },
              { header: 'Split', render: (row) => row.split_name ?? '-' },
              { header: 'Clase real', render: (row) => row.true_label_name ?? row.true_label ?? '-' },
              { header: 'Predicción', render: (row) => row.predicted_label_name ?? row.predicted_label ?? '-' },
              { header: 'P(parasitized)', render: (row) => formatMetric(row.probability_parasitized) },
              { header: 'Threshold', render: (row) => formatMetric(row.threshold_used) },
              { header: 'Tipo de caso', render: (row) => <span className={`case-badge ${row.case_type ?? 'unknown'}`}>{caseTypeLabel(row.case_type)}</span> },
              { header: 'Correcta', render: (row) => booleanText(row.is_correct) },
              { header: 'Imagen', render: (row) => row.relative_path ? <a href={api.artifactUrl(row.relative_path, { datasource })} target="_blank" rel="noreferrer">Abrir imagen</a> : '-' },
            ]}
            getRowKey={(row, index) => row.run_image_prediction_id ?? `${row.filename}-${index}`}
          />
        </div>
      </details>

      <details className="panel run-detail-disclosure">
        <summary>
          <span>Explicabilidad por caso</span>
          <small>{explainability.length} casos cargados · detalle opcional</small>
        </summary>
        <div className="run-detail-disclosure__content">
          <p className="muted-text">Explicación visual experimental para apoyar revisión de casos, no una conclusión clínica definitiva.</p>
          <DataTable<ExplainabilityCase>
            rows={explainability}
            columns={[
              {
                header: 'Fuente',
                render: (row) => {
                  const path = sourceImagePath(row);
                  const url = api.mediaUrl({ url: row.source_image_url ?? row.image_url, path, datasource });
                  return <TableImageLink url={url} alt={`Fuente ${row.true_label ?? ''}`} label="Abrir fuente" />;
                },
              },
              {
                header: 'Explicación',
                render: (row) => {
                  const path = explanationImagePath(row);
                  const url = api.mediaUrl({ url: row.explanation_url, path, artifactId: row.artifact_id, datasource });
                  return <TableImageLink url={url} alt={`Explicación ${row.method ?? ''}`} label="Abrir explicación" />;
                },
              },
              { header: 'Método', render: (row) => row.method ?? '-' },
              { header: 'Tipo de caso', render: (row) => <span className={`case-badge ${row.case_type ?? 'unknown'}`}>{caseTypeLabel(row.case_type)}</span> },
              { header: 'Clase real', render: (row) => row.true_label ?? '-' },
              { header: 'Predicción', render: (row) => row.predicted_label ?? '-' },
              { header: 'P(parasitized)', render: (row) => formatMetric(scorePositive(row)) },
              { header: 'Threshold', render: (row) => formatMetric(thresholdUsed(row)) },
              { header: 'Correcta', render: (row) => booleanText(booleanValue(row.is_correct)) },
              { header: 'Error', render: (row) => row.error_message ?? '-' },
              { header: 'Auditar', render: (row) => onExplainabilitySelect ? <button className="audit-action-button" type="button" onClick={() => onExplainabilitySelect(row)}>Ver detalle</button> : '-' },
            ]}
            getRowKey={(row) => row.explainability_id}
          />
        </div>
      </details>

      <details className="panel run-detail-disclosure">
        <summary>
          <span>Métricas y reportes técnicos</span>
          <small>{detail.metrics.length} métrica{detail.metrics.length === 1 ? '' : 's'} · detalle legacy</small>
        </summary>
        <div className="run-detail-disclosure__content">
          <DataTable
            rows={detail.metrics}
            columns={[
              { header: 'Nombre', render: (row) => row.metric_name },
              { header: 'Valor', render: (row) => formatMetric(row.metric_value as number | null) },
              { header: 'Split', render: (row) => String(row.split_name ?? '-') },
              { header: 'Clase', render: (row) => String(row.class_name ?? '-') },
            ]}
          />
          <details className="run-detail-nested-details">
            <summary>Reporte de clasificación</summary>
            <pre>{stringifyJson(report)}</pre>
          </details>
        </div>
      </details>

      <details className="panel run-detail-disclosure run-detail-artifacts">
        <summary>
          <span>Artefactos generados ({mergedArtifacts.length})</span>
          <small>Modelos, métricas, gráficos y evidencia · colapsado por defecto</small>
        </summary>
        <div className="run-detail-disclosure__content">
          {groupedArtifacts.length > 0 ? groupedArtifacts.map((group) => (
            <section className="run-detail-artifact-group" key={group.groupName}>
              <h3>{group.groupName} <span>{group.items.length}</span></h3>
              <DataTable<ArtifactItem>
                rows={group.items}
                columns={[
                  { header: 'Nombre', render: (row) => artifactName(row) },
                  { header: 'Tipo', render: (row) => row.artifact_type ?? 'No disponible' },
                  { header: 'Ruta', render: (row) => artifactPath(row) ? <code>{artifactPath(row)}</code> : 'No disponible' },
                  {
                    header: 'Acciones',
                    render: (row) => {
                      const path = artifactPath(row);
                      const key = `artifact-${path ?? artifactName(row)}`;
                      return (
                        <div className="run-detail-artifact-actions">
                          {path && artifactExists(row) && isImageArtifact(row) ? <a href={api.artifactUrl(path, { artifactId: artifactId(row), datasource })} target="_blank" rel="noreferrer">Abrir</a> : <span>{artifactExists(row) ? 'Vista no disponible' : 'Marcado no disponible en metadata'}</span>}
                          <button type="button" aria-live="polite" disabled={!path} onClick={() => path && handleCopy(path, key)}>{copyFeedback === key ? 'Ruta copiada' : 'Copiar ruta'}</button>
                        </div>
                      );
                    },
                  },
                ]}
                getRowKey={(row, index) => `${artifactPath(row) ?? artifactName(row)}-${index}`}
              />
            </section>
          )) : <p className="run-detail-empty-state">No hay artefactos registrados para esta ejecución.</p>}
        </div>
      </details>
    </section>
  );
}
