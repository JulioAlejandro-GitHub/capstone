export const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const encoded = (id: string) => encodeURIComponent(id);

export const routes = {
  summary: '/modelo-ia/resumen',
  runs: '/modelo-ia/ejecuciones',
  runDetail: (id: string) => `/modelo-ia/ejecuciones/${encoded(id)}`,
  evaluations: '/modelo-ia/evaluaciones',
  comparison: '/modelo-ia/comparacion',
  modelVersions: '/modelo-ia/modelos-liberados',
  modelVersionDetail: (id: string) => `/modelo-ia/modelos-liberados/${encoded(id)}`,
  deployments: '/modelo-ia/despliegues',
  deploymentDetail: (id: string) => `/modelo-ia/despliegues/${encoded(id)}`,
  traceability: '/modelo-ia/trazabilidad',
  explainability: '/modelo-ia/explicabilidad',
  predictions: '/modelo-ia/predicciones',
  dataset: '/modelo-ia/dataset',
  datasetsModels: '/modelo-ia/datasets-modelos',
  errorsLogs: '/modelo-ia/errores-logs',
  smearWorkflow: '/frotis/analizar',
  smearHistory: '/frotis/historial',
  smearHistoryDetail: (id: string) => `/frotis/historial/${encoded(id)}`,
  smearUpload: '/frotis/cargar',
  smearAnalysis: '/frotis/analisis',
  smearReview: '/frotis/revision',
} as const;

export const isValidPublicId = (value: string | undefined): value is string =>
  Boolean(value && UUID_PATTERN.test(value));

export function withAllowedQuery(
  pathname: string,
  values: Record<string, string | number | null | undefined>,
) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim()) {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return `${pathname.replace(/\/{2,}/g, '/')}${query ? `?${query}` : ''}`;
}

export function buildShareableUrl(
  pathname: string,
  values: Record<string, string | number | null | undefined>,
  origin = window.location.origin,
) {
  return new URL(withAllowedQuery(pathname, values), origin).toString();
}
