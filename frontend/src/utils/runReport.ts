import type { RunDashboard } from '../types/api';

export type RunAnalysisLevel = 'success' | 'warning' | 'danger' | 'neutral';

export interface RunAutoAnalysis {
  level: RunAnalysisLevel;
  title: string;
  message: string;
}

export interface RunConfusionCounts {
  tn: number | null;
  fp: number | null;
  fn: number | null;
  tp: number | null;
}

export interface RunReportMetrics {
  recall: number | null;
  specificity: number | null;
  f2: number | null;
  auc: number | null;
}

function tokenizeCommand(command: string): string[] {
  const tokens: string[] = [];
  let current = '';
  let quote: '"' | "'" | null = null;
  let escaped = false;

  const flush = () => {
    if (current) tokens.push(current);
    current = '';
  };

  for (const character of command) {
    if (escaped) {
      current += character;
      escaped = false;
      continue;
    }
    if (character === '\\' && quote !== "'") {
      escaped = true;
      continue;
    }
    if (quote) {
      if (character === quote) quote = null;
      else current += character;
      continue;
    }
    if (character === '"' || character === "'") {
      quote = character;
      continue;
    }
    if (/\s/.test(character)) {
      flush();
      continue;
    }
    current += character;
  }

  if (escaped) current += '\\';
  if (!quote) flush();
  return tokens;
}

export function extractCommandParam(
  command: string | null | undefined,
  paramName: string,
): string | null {
  const normalizedCommand = command?.trim();
  const normalizedName = paramName.trim().replace(/^--/, '');
  if (!normalizedCommand || !normalizedName) return null;

  const option = `--${normalizedName}`;
  const tokens = tokenizeCommand(normalizedCommand);
  let resolvedValue: string | null = null;

  tokens.forEach((token, index) => {
    if (token === option) {
      const nextToken = tokens[index + 1]?.trim();
      if (nextToken && !nextToken.startsWith('--')) resolvedValue = nextToken;
      return;
    }
    if (token.startsWith(`${option}=`)) {
      const inlineValue = token.slice(option.length + 1).trim();
      if (inlineValue && !inlineValue.startsWith('--')) resolvedValue = inlineValue;
    }
  });

  return resolvedValue;
}

function finiteNonNegative(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const numericValue = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numericValue) && numericValue >= 0 ? numericValue : null;
}

function finiteMetric(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const numericValue = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

function firstMetric(...values: unknown[]): number | null {
  for (const value of values) {
    const metric = finiteMetric(value);
    if (metric !== null) return metric;
  }
  return null;
}

export function resolveRunConfusion(run: RunDashboard): RunConfusionCounts {
  const matrix = Array.isArray(run.confusion_matrix) ? run.confusion_matrix : [];
  const explicitCounts: RunConfusionCounts = {
    tn: finiteNonNegative(run.tn),
    fp: finiteNonNegative(run.fp),
    fn: finiteNonNegative(run.fn),
    tp: finiteNonNegative(run.tp),
  };
  const matrixCounts: RunConfusionCounts = {
    tn: finiteNonNegative(matrix[0]?.[0]),
    fp: finiteNonNegative(matrix[0]?.[1]),
    fn: finiteNonNegative(matrix[1]?.[0]),
    tp: finiteNonNegative(matrix[1]?.[1]),
  };
  const isComplete = (counts: RunConfusionCounts) => (
    Object.values(counts).every((value) => value !== null)
  );

  if (isComplete(explicitCounts)) return explicitCounts;
  if (isComplete(matrixCounts)) return matrixCounts;
  if (Object.values(explicitCounts).some((value) => value !== null)) return explicitCounts;
  return matrixCounts;
}

export function resolveRunReportMetrics(run: RunDashboard): RunReportMetrics {
  const counts = resolveRunConfusion(run);
  const derivedRecall = (
    counts.tp !== null
    && counts.fn !== null
    && counts.tp + counts.fn > 0
  )
    ? counts.tp / (counts.tp + counts.fn)
    : null;
  const derivedSpecificity = (
    counts.tn !== null
    && counts.fp !== null
    && counts.tn + counts.fp > 0
  )
    ? counts.tn / (counts.tn + counts.fp)
    : null;
  return {
    recall: firstMetric(
      run.recall_parasitized,
      run.sensitivity_parasitized,
      derivedRecall,
      run.recall,
    ),
    specificity: firstMetric(run.specificity, derivedSpecificity),
    f2: firstMetric(run.f2_parasitized, run.f2_score),
    auc: firstMetric(run.roc_auc_parasitized, run.roc_auc, run.auc),
  };
}

export function generateRunAutoAnalysis(run: RunDashboard): RunAutoAnalysis {
  const counts = resolveRunConfusion(run);
  const metrics = resolveRunReportMetrics(run);
  const countValues = [counts.tn, counts.fp, counts.fn, counts.tp];
  const hasCompleteMatrix = countValues.every((value) => value !== null);
  const hasMetrics = Object.values(metrics).some((value) => value !== null);
  const totalPredictions = hasCompleteMatrix
    ? countValues.reduce<number>((sum, value) => sum + (value ?? 0), 0)
    : null;

  if (totalPredictions === 0) {
    return {
      level: 'neutral',
      title: 'Sin datos suficientes',
      message: 'No hay métricas suficientes para un análisis automático.',
    };
  }

  if (!hasMetrics && !hasCompleteMatrix) {
    return {
      level: 'neutral',
      title: 'Sin datos suficientes',
      message: 'No hay métricas suficientes para un análisis automático.',
    };
  }

  if (run.prediction_collapse_detected === true) {
    return {
      level: 'danger',
      title: 'Colapso de predicciones',
      message: 'Se detectó colapso en la distribución de predicciones. La mayoría de las predicciones se concentran en una sola clase.',
    };
  }

  if (hasCompleteMatrix) {
    const predictedUninfected = (counts.tn ?? 0) + (counts.fn ?? 0);
    const predictedParasitized = (counts.fp ?? 0) + (counts.tp ?? 0);
    if (
      predictedUninfected / (totalPredictions as number) >= 0.95
      || predictedParasitized / (totalPredictions as number) >= 0.95
    ) {
      return {
        level: 'danger',
        title: 'Colapso de predicciones',
        message: 'Se detectó colapso en la distribución de predicciones. La mayoría de las predicciones se concentran en una sola clase.',
      };
    }
  }

  if (counts.fn !== null && counts.fn > 0 && metrics.recall !== null && metrics.recall < 0.98) {
    return {
      level: 'danger',
      title: 'Riesgo por falsos negativos',
      message: 'Se observan falsos negativos que requieren revisión prioritaria.',
    };
  }

  if (metrics.specificity !== null && metrics.specificity < 0.7) {
    return {
      level: 'warning',
      title: 'Riesgo por falsos positivos',
      message: 'Se observan falsos positivos elevados, lo que puede aumentar revisiones innecesarias.',
    };
  }

  if (
    metrics.recall !== null
    && metrics.recall >= 0.98
    && metrics.specificity !== null
    && metrics.specificity >= 0.7
  ) {
    return {
      level: 'success',
      title: 'Ejecución estable',
      message: 'La ejecución presenta un comportamiento estable. No se detectan señales fuertes de colapso en la distribución de predicciones.',
    };
  }

  return {
    level: 'neutral',
    title: 'Lectura no concluyente',
    message: 'Las métricas disponibles no activan una señal automática concluyente; se recomienda revisar el detalle.',
  };
}
