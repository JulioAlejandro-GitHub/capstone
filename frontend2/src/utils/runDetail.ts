import type {
  ClinicalMetrics,
  ConfusionMatrix,
  JsonRecord,
  JsonValue,
  MetricRow,
} from '../types/api';

export interface CommandSummary {
  command: string | null;
  reconstructed: boolean;
}

export interface TrainingSignals {
  available: boolean;
  assessmentAvailable: boolean;
  trainAccuracy: number | null;
  validationAccuracy: number | null;
  accuracyGap: number | null;
  trainLoss: number | null;
  validationLoss: number | null;
  lossGap: number | null;
  bestEpoch: number | null;
  fineTuningEpoch: number | null;
  fineTuningMarker: number | null;
  possibleOverfitting: boolean;
  reasons: string[];
}

const CORE_CLI_PARAMETERS = [
  ['model_name', 'model'],
  ['model', 'model'],
  ['epochs', 'epochs'],
  ['fine_tune_epochs', 'fine-tune-epochs'],
  ['batch_size', 'batch-size'],
  ['img_size', 'img-size'],
  ['learning_rate', 'learning-rate'],
  ['fine_tune_learning_rate', 'fine-tune-learning-rate'],
  ['preprocessing', 'preprocessing'],
  ['checkpoint_policy', 'checkpoint-policy'],
  ['checkpoint_metric', 'checkpoint-metric'],
  ['min_recall', 'min-recall'],
  ['target_recall', 'target-recall'],
  ['positive_label', 'positive-label'],
  ['seed', 'seed'],
] as const;

const CLI_ARGUMENT_ALLOWLIST = new Set([
  'model',
  'epochs',
  'fine_tune_epochs',
  'img_size',
  'batch_size',
  'seed',
  'learning_rate',
  'fine_tune_learning_rate',
  'pretrained_weights',
  'optimizer',
  'no_augment',
  'checkpoint_monitor',
  'checkpoint_policy',
  'min_recall',
  'beta',
  'reject_prediction_collapse',
  'allow_collapsed_checkpoint',
  'min_class_fraction',
  'calibrate_threshold',
  'target_recall',
  'min_specificity',
  'threshold_output_json',
  'monitor_mode',
  'early_stopping_monitor',
  'early_stopping_mode',
  'early_stopping_patience',
  'output_dir',
  'preprocessing',
  'positive_label',
  'data_source',
  'dataset_dir',
  'track_db',
  'checkpoint',
  'threshold',
  'label_mapping',
  'method',
  'num_samples',
  'max_candidates',
  'calibration_kind',
  'dataset_split',
  'output_file',
  'output_json',
  'update_model_metadata',
  'temperature_min',
  'temperature_max',
  'grid_size',
  'refinement_rounds',
  'image_path',
  'true_label',
  'image_id',
  'explain',
  'tta',
  'n_aug',
  'ensemble',
  'models',
  'weights',
  'explain_model',
  'calibration_method',
  'calibration_temperature',
  'calibration_file',
]);

function parsedJson(value: unknown): unknown {
  if (typeof value !== 'string') return value;
  const normalized = value.trim();
  if (!normalized.startsWith('{') && !normalized.startsWith('[')) return value;
  try {
    return JSON.parse(normalized) as unknown;
  } catch {
    return value;
  }
}

export function recordValue(value: unknown): JsonRecord | null {
  const parsed = parsedJson(value);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
  return parsed as JsonRecord;
}

export function numberValue(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

export function textValue(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const normalized = value.trim();
  return normalized || null;
}

export function booleanValue(value: unknown): boolean | null {
  if (typeof value === 'boolean') return value;
  if (typeof value !== 'string') return null;
  if (['true', 't', '1', 'yes'].includes(value.toLowerCase())) return true;
  if (['false', 'f', '0', 'no'].includes(value.toLowerCase())) return false;
  return null;
}

export function normalizeExecutionParameters(run: JsonRecord): JsonRecord {
  const legacy = recordValue(run.parameters) ?? {};
  const nested = recordValue(legacy.execution_parameters) ?? {};
  const direct = recordValue(run.execution_parameters) ?? {};
  const normalized = { ...legacy, ...nested, ...direct };
  delete normalized.execution_parameters;
  return normalized;
}

function shellQuote(value: string) {
  if (/^[a-zA-Z0-9_./:@%+=,-]+$/.test(value)) return value;
  return `'${value.replace(/'/g, `'"'"'`)}'`;
}

function cliTokens(key: string, value: JsonValue): string[] {
  const flag = `--${key.replaceAll('_', '-')}`;
  if (value === null || value === '') return [];
  if (typeof value === 'boolean') {
    if (value) return [flag];
    if (key === 'reject_prediction_collapse') return ['--no-reject-prediction-collapse'];
    return [];
  }
  if (Array.isArray(value)) {
    const items = value.filter((item) => ['string', 'number'].includes(typeof item));
    return items.length > 0 ? [flag, ...items.map((item) => shellQuote(String(item)))] : [];
  }
  if (typeof value === 'object') return [];
  return [flag, shellQuote(String(value))];
}

function commandPrefix(run: JsonRecord) {
  const scriptName = textValue(run.script_name) ?? 'src.train';
  if (scriptName.endsWith('.py') || scriptName.includes('/')) {
    return ['python', shellQuote(scriptName)];
  }
  return ['python', '-m', shellQuote(scriptName)];
}

function commandFromCliArguments(run: JsonRecord, parameters: JsonRecord) {
  const cliArguments = recordValue(parameters.cli_arguments);
  if (!cliArguments || Object.keys(cliArguments).length === 0) return null;
  if (Object.keys(cliArguments).some((key) => !CLI_ARGUMENT_ALLOWLIST.has(key))) return null;
  const tokens = commandPrefix(run);
  Object.entries(cliArguments).forEach(([key, value]) => {
    tokens.push(...cliTokens(key, value));
  });
  return tokens.length > commandPrefix(run).length ? tokens.join(' ') : null;
}

function commandFromCoreParameters(run: JsonRecord, parameters: JsonRecord) {
  const tokens = commandPrefix(run);
  const emittedFlags = new Set<string>();
  CORE_CLI_PARAMETERS.forEach(([parameterName, flagName]) => {
    const value = parameters[parameterName];
    if (value !== undefined && !emittedFlags.has(flagName)) {
      tokens.push(...cliTokens(flagName, value));
      emittedFlags.add(flagName);
    }
  });
  if (booleanValue(parameters.track_db) === true) tokens.push('--track-db');
  if (booleanValue(parameters.calibrate_threshold) === true) tokens.push('--calibrate-threshold');
  if (booleanValue(parameters.augment) === false) tokens.push('--no-augment');
  return tokens.length > commandPrefix(run).length ? tokens.join(' ') : null;
}

export function resolveCommand(run: JsonRecord, parameters: JsonRecord): CommandSummary {
  const exactCommand = textValue(run.command);
  if (exactCommand) return { command: exactCommand, reconstructed: false };

  const scriptName = textValue(run.script_name)?.toLowerCase();
  const reconstructedFromCli = commandFromCliArguments(run, parameters);
  const reconstructed = reconstructedFromCli
    ?? (!scriptName || scriptName.includes('train') ? commandFromCoreParameters(run, parameters) : null);
  return { command: reconstructed, reconstructed: reconstructed !== null };
}

export function resolveDurationSeconds(run: JsonRecord) {
  const storedDuration = numberValue(run.duration_seconds);
  if (storedDuration !== null && storedDuration >= 0) return storedDuration;
  const startedAt = textValue(run.started_at);
  const finishedAt = textValue(run.finished_at);
  if (!startedAt || !finishedAt) return null;
  const start = new Date(startedAt).getTime();
  const finish = new Date(finishedAt).getTime();
  if (!Number.isFinite(start) || !Number.isFinite(finish) || finish < start) return null;
  return (finish - start) / 1000;
}

function metricFromRows(metrics: MetricRow[], aliases: string[]) {
  const normalizedAliases = aliases.map((alias) => alias.toLowerCase());
  const candidates = metrics
    .map((metric, index) => ({ metric, index }))
    .filter(({ metric }) => normalizedAliases.includes(String(metric.metric_name).toLowerCase()))
    .sort((left, right) => {
      const splitScore = (split: unknown) => {
        const normalized = String(split ?? '').toLowerCase();
        if (normalized === 'test' || normalized === 'external') return 3;
        if (normalized === 'validation' || normalized === 'val') return 2;
        if (normalized === 'train') return 1;
        return 0;
      };
      const leftAliasIndex = normalizedAliases.indexOf(String(left.metric.metric_name).toLowerCase());
      const rightAliasIndex = normalizedAliases.indexOf(String(right.metric.metric_name).toLowerCase());
      const classScore = (className: unknown) => {
        const normalized = String(className ?? '').toLowerCase();
        return normalized === 'parasitized' || normalized === '1' ? 1 : 0;
      };
      return splitScore(right.metric.split_name) - splitScore(left.metric.split_name)
        || leftAliasIndex - rightAliasIndex
        || classScore(right.metric.class_name) - classScore(left.metric.class_name)
        || right.index - left.index;
    });
  return numberValue(candidates[0]?.metric.metric_value);
}

function firstNumber(...values: unknown[]) {
  for (const value of values) {
    const numeric = numberValue(value);
    if (numeric !== null) return numeric;
  }
  return null;
}

export function resolveClinicalMetrics(
  clinicalMetrics: ClinicalMetrics | null | undefined,
  metrics: MetricRow[],
  run: JsonRecord,
): ClinicalMetrics {
  return {
    accuracy: firstNumber(
      clinicalMetrics?.accuracy,
      metricFromRows(metrics, ['accuracy', 'test_accuracy']),
      run.accuracy,
    ),
    precision_parasitized: firstNumber(
      clinicalMetrics?.precision_parasitized,
      metricFromRows(metrics, ['precision_parasitized', 'test_precision_parasitized']),
    ),
    recall_parasitized: firstNumber(
      clinicalMetrics?.recall_parasitized,
      clinicalMetrics?.sensitivity_parasitized,
      metricFromRows(metrics, ['recall_parasitized', 'sensitivity_parasitized', 'test_recall_parasitized']),
    ),
    sensitivity_parasitized: firstNumber(
      clinicalMetrics?.sensitivity_parasitized,
      clinicalMetrics?.recall_parasitized,
    ),
    specificity: firstNumber(
      clinicalMetrics?.specificity,
      metricFromRows(metrics, ['specificity', 'test_specificity']),
      run.specificity,
    ),
    f2_parasitized: firstNumber(
      clinicalMetrics?.f2_parasitized,
      metricFromRows(metrics, ['f2_parasitized', 'f2', 'test_f2']),
    ),
    pr_auc_parasitized: firstNumber(
      clinicalMetrics?.pr_auc_parasitized,
      metricFromRows(metrics, ['pr_auc_parasitized', 'pr_auc', 'test_pr_auc']),
      run.pr_auc,
    ),
    roc_auc_parasitized: firstNumber(
      clinicalMetrics?.roc_auc_parasitized,
      metricFromRows(metrics, ['roc_auc_parasitized', 'roc_auc', 'auc', 'test_auc']),
      run.auc,
    ),
    balanced_accuracy: firstNumber(
      clinicalMetrics?.balanced_accuracy,
      metricFromRows(metrics, ['balanced_accuracy', 'test_balanced_accuracy']),
      run.balanced_accuracy,
    ),
    prediction_collapse_detected: clinicalMetrics?.prediction_collapse_detected ?? null,
  };
}

function matrixValue(value: unknown): number[][] {
  const parsed = parsedJson(value);
  if (!Array.isArray(parsed)) return [];
  return parsed.map((row) => (
    Array.isArray(row)
      ? row.map((item) => numberValue(item) ?? Number.NaN)
      : []
  ));
}

function resolvedMatrixCounts(matrix: ConfusionMatrix | null | undefined) {
  const values = matrix?.matrix ?? [];
  return {
    tn: firstNumber(matrix?.tn, values[0]?.[0]),
    fp: firstNumber(matrix?.fp, values[0]?.[1]),
    fn: firstNumber(matrix?.fn, values[1]?.[0]),
    tp: firstNumber(matrix?.tp, values[1]?.[1]),
  };
}

export function resolveConfusionMatrix(
  clinicalMatrix: ConfusionMatrix | null | undefined,
  rows: JsonRecord[],
): ConfusionMatrix | null {
  const clinicalCounts = resolvedMatrixCounts(clinicalMatrix);
  if (Object.values(clinicalCounts).every((value) => value !== null)) {
    return clinicalMatrix ?? null;
  }
  const row = [...rows]
    .map((item, index) => ({ item, index }))
    .sort((left, right) => {
      const splitPriority = (item: JsonRecord) => {
        const split = textValue(item.split_name)?.toLowerCase();
        if (split === 'test' || split === 'external') return 2;
        if (split === 'validation' || split === 'val') return 1;
        return 0;
      };
      return splitPriority(right.item) - splitPriority(left.item) || left.index - right.index;
    })[0]?.item;
  if (!row && !Object.values(clinicalCounts).some((value) => value !== null)) return null;
  const rawMatrix = matrixValue(row?.matrix);
  const rawCounts = {
    tn: firstNumber(row?.tn, row?.true_negative, rawMatrix[0]?.[0]),
    fp: firstNumber(row?.fp, row?.false_positive, rawMatrix[0]?.[1]),
    fn: firstNumber(row?.fn, row?.false_negative, rawMatrix[1]?.[0]),
    tp: firstNumber(row?.tp, row?.true_positive, rawMatrix[1]?.[1]),
  };
  const clinicalAvailable = Object.values(clinicalCounts).filter((value) => value !== null).length;
  const rawAvailable = Object.values(rawCounts).filter((value) => value !== null).length;
  if (clinicalAvailable >= rawAvailable && clinicalMatrix) return clinicalMatrix;
  const labels = Array.isArray(row?.labels)
    ? row.labels.map(String)
    : ['uninfected', 'parasitized'];
  const { tn, fp, fn, tp } = rawCounts;
  return {
    labels,
    matrix: [[tn ?? Number.NaN, fp ?? Number.NaN], [fn ?? Number.NaN, tp ?? Number.NaN]],
    tn,
    fp,
    fn,
    tp,
  };
}

function epochNumber(row: JsonRecord) {
  return numberValue(row.epoch) ?? Number.MAX_SAFE_INTEGER;
}

function valueFromRow(row: JsonRecord | undefined, ...keys: string[]) {
  for (const key of keys) {
    const value = numberValue(row?.[key]);
    if (value !== null) return value;
  }
  return null;
}

export function resolveTrainingSignals(
  history: JsonRecord[],
  fineTuningMarker: unknown,
): TrainingSignals {
  const sortedHistory = [...history].sort((left, right) => epochNumber(left) - epochNumber(right));
  const finalRow = [...sortedHistory].reverse().find((row) => (
    valueFromRow(row, 'train_accuracy', 'accuracy', 'train_loss', 'loss', 'val_accuracy', 'val_loss') !== null
  ));
  const trainAccuracy = valueFromRow(finalRow, 'train_accuracy', 'accuracy');
  const validationAccuracy = valueFromRow(finalRow, 'val_accuracy');
  const trainLoss = valueFromRow(finalRow, 'train_loss', 'loss');
  const validationLoss = valueFromRow(finalRow, 'val_loss');
  const accuracyGap = trainAccuracy !== null && validationAccuracy !== null
    ? trainAccuracy - validationAccuracy
    : null;
  const lossGap = trainLoss !== null && validationLoss !== null
    ? validationLoss - trainLoss
    : null;
  const reasons: string[] = [];
  if (accuracyGap !== null && accuracyGap > 0.05) {
    reasons.push('la accuracy de entrenamiento supera a validación por más de 0,05');
  }
  if (lossGap !== null && lossGap > 0.10) {
    reasons.push('la loss de validación supera a entrenamiento por más de 0,10');
  }

  const rowsWithValidationAccuracy = sortedHistory.filter(
    (row) => valueFromRow(row, 'val_accuracy') !== null,
  );
  const bestRow = rowsWithValidationAccuracy.reduce<JsonRecord | undefined>((best, row) => {
    if (!best) return row;
    return (valueFromRow(row, 'val_accuracy') ?? Number.NEGATIVE_INFINITY)
      > (valueFromRow(best, 'val_accuracy') ?? Number.NEGATIVE_INFINITY)
      ? row
      : best;
  }, undefined);
  const bestEpochIndex = bestRow ? numberValue(bestRow.epoch) : null;
  const firstFineTuningRow = sortedHistory.find((row) => (
    textValue(row.phase)?.toLowerCase().includes('fine')
  ));
  const fineTuningEpochIndex = firstFineTuningRow
    ? numberValue(firstFineTuningRow.epoch)
    : null;
  const fallbackMarker = numberValue(fineTuningMarker);

  return {
    available: finalRow !== undefined,
    assessmentAvailable: accuracyGap !== null || lossGap !== null,
    trainAccuracy,
    validationAccuracy,
    accuracyGap,
    trainLoss,
    validationLoss,
    lossGap,
    bestEpoch: bestEpochIndex === null ? null : bestEpochIndex + 1,
    fineTuningEpoch: fineTuningEpochIndex !== null
      ? fineTuningEpochIndex + 1
      : fallbackMarker === null ? null : fallbackMarker + 2,
    fineTuningMarker: fallbackMarker,
    possibleOverfitting: reasons.length > 0,
    reasons,
  };
}
