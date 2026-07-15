import type { ExplainabilityCase } from '../types/api';

export function caseTypeLabel(caseType: string | null | undefined) {
  const labels: Record<string, string> = {
    true_positive: 'Verdadero positivo',
    true_negative: 'Verdadero negativo',
    false_positive: 'Falso positivo',
    false_negative: 'Falso negativo',
    low_confidence: 'Baja confianza',
  };
  return caseType ? labels[caseType] ?? caseType : 'Sin clasificar';
}

export function sourceImagePath(item: ExplainabilityCase) {
  return (
    item.source_image_path
    ?? item.image_stored_path
    ?? item.original_image_path
    ?? item.image_original_path
    ?? item.image_path
    ?? null
  );
}

export function evaluatedImagePath(item: ExplainabilityCase) {
  return item.crop_path ?? item.image_path ?? sourceImagePath(item);
}

export function explanationImagePath(item: ExplainabilityCase) {
  return item.explanation_output_path ?? item.artifact_path ?? null;
}

export function scorePositive(item: ExplainabilityCase) {
  return item.score_positive_label ?? item.probability_parasitized ?? item.score ?? null;
}

export function thresholdUsed(item: ExplainabilityCase) {
  return item.threshold_used ?? item.threshold ?? null;
}

export function confidenceLabel(item: ExplainabilityCase) {
  if (item.confidence_status) return item.confidence_status;
  if (item.confidence_level) return item.confidence_level;
  if (item.case_type === 'low_confidence') return 'Revisión prioritaria';
  return 'No registrada';
}

export function generateCaseInterpretation(item: ExplainabilityCase) {
  if (item.interpretation?.trim()) return item.interpretation;

  const positiveLabel = item.positive_label ?? 'parasitized';
  const trueLabel = item.true_label;
  const predictedLabel = item.predicted_label;
  const derivedCaseType = item.case_type
    ?? (trueLabel && predictedLabel
      ? trueLabel === positiveLabel
        ? predictedLabel === positiveLabel ? 'true_positive' : 'false_negative'
        : predictedLabel === positiveLabel ? 'false_positive' : 'true_negative'
      : null);

  if (derivedCaseType === 'low_confidence') {
    return 'La predicción está cercana al umbral de decisión. Este caso debe priorizarse para revisión humana.';
  }
  if (derivedCaseType === 'false_positive') {
    return 'La imagen estaba etiquetada como no parasitada, pero el modelo la clasificó como parasitada. Este caso debe revisarse como posible confusión visual, artefacto o umbral demasiado sensible.';
  }
  if (derivedCaseType === 'false_negative') {
    return 'La imagen estaba etiquetada como parasitada, pero el modelo la clasificó como no parasitada. Este caso es crítico porque representa una célula parasitada no detectada por el modelo.';
  }
  if (derivedCaseType === 'true_positive') {
    return 'La imagen estaba etiquetada como parasitada y el modelo también la clasificó como parasitada. La explicación visual permite revisar si la decisión se apoya en una región microscópica plausible.';
  }
  if (derivedCaseType === 'true_negative') {
    return 'La imagen estaba etiquetada como no parasitada y el modelo también la clasificó como no parasitada.';
  }
  return 'No hay suficientes etiquetas para clasificar automáticamente este caso. Revise la fuente, la predicción y la explicación visual.';
}
