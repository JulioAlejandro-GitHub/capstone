/**
 * Resolución de contexto de deep link para v3. Módulo puro.
 *
 * Prioridad de selección (especificación §3):
 *   1. Contexto explícito de la URL.
 *   2. Contexto persistido y válido.
 *   3. Selección inicial determinista.
 */
import type { DeepLinkParam } from '../routes';

export type DeepLinkIssue = {
  param: DeepLinkParam;
  reason: 'invalid_format' | 'not_in_analysis';
  value: string;
};

export type DeepLinkRequest = {
  imageId: string | null;
  detectionId: string | null;
  predictionId: string | null;
  issues: DeepLinkIssue[];
};

type ParamReader = { get(name: string): string | null };

/** Lee los parámetros opcionales y descarta los que no tienen formato de identificador público. */
export function readDeepLink(
  params: ParamReader,
  isValidId: (value: string) => boolean,
): DeepLinkRequest {
  const issues: DeepLinkIssue[] = [];
  const read = (param: DeepLinkParam) => {
    const value = params.get(param);
    if (!value) return null;
    if (!isValidId(value)) {
      issues.push({ param, reason: 'invalid_format', value });
      return null;
    }
    return value;
  };
  return {
    imageId: read('image'),
    detectionId: read('selected_detection'),
    predictionId: read('selected_prediction'),
    issues,
  };
}

export type ImageResolution = {
  imageId: string | null;
  source: 'url' | 'persisted' | 'initial' | 'none';
  issue: DeepLinkIssue | null;
};

/**
 * Elige la imagen activa validando pertenencia al análisis.
 * `imageIds` debe venir ya en orden determinista (secuencia de captura).
 */
export function resolveActiveImage(input: {
  urlImageId: string | null;
  persistedImageId: string | null;
  imageIds: readonly string[];
}): ImageResolution {
  const { urlImageId, persistedImageId, imageIds } = input;
  let issue: DeepLinkIssue | null = null;
  if (urlImageId) {
    if (imageIds.includes(urlImageId)) return { imageId: urlImageId, source: 'url', issue: null };
    issue = { param: 'image', reason: 'not_in_analysis', value: urlImageId };
  }
  if (persistedImageId && imageIds.includes(persistedImageId)) {
    return { imageId: persistedImageId, source: 'persisted', issue };
  }
  const first = imageIds[0] ?? null;
  return { imageId: first, source: first ? 'initial' : 'none', issue };
}

const PARAM_LABEL: Record<DeepLinkParam, string> = {
  image: 'La imagen',
  selected_detection: 'La detección',
  selected_prediction: 'La predicción',
};

export function describeDeepLinkIssue(issue: DeepLinkIssue): string {
  const subject = PARAM_LABEL[issue.param];
  return issue.reason === 'invalid_format'
    ? `${subject} indicada en el enlace no tiene un identificador válido y fue ignorada.`
    : `${subject} indicada en el enlace no pertenece a este análisis; se muestra la selección inicial.`;
}
