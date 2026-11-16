/**
 * Análisis de frotis v3 — Microscopio Digital Inmersivo.
 * Módulo puro: sin imports de runtime, para poder probarlo de forma aislada.
 * Las rutas canónicas equivalentes viven en `src/router.ts` (smearMicroscope*).
 */
export const frotis3Base = '/frotis/microscopio';

/** Segmento opcional: `/frotis/microscopio` y `/frotis/microscopio/:analysisId` comparten un único workspace montado. */
export const frotis3RoutePattern = `${frotis3Base}/:analysisId?`;

export const microscopeAnalysisPath = (analysisId: string) =>
  `${frotis3Base}/${encodeURIComponent(analysisId)}`;

/** Parámetros opcionales admitidos como deep link. `analysisId` es el único obligatorio. */
export const DEEP_LINK_PARAMS = ['image', 'selected_detection', 'selected_prediction'] as const;
export type DeepLinkParam = (typeof DEEP_LINK_PARAMS)[number];

export type MicroscopeViewId = 'full-field' | 'review-cells' | 'report';

/**
 * Vistas fijas del header. Su disponibilidad en cada momento depende de los
 * datos reales del análisis (por ejemplo, REVIEW CELLS exige detección celular).
 */
export const MICROSCOPE_VIEWS: ReadonlyArray<{ id: MicroscopeViewId; label: string }> = [
  { id: 'full-field', label: 'FULL FIELD REVIEW' },
  { id: 'review-cells', label: 'REVIEW CELLS' },
  { id: 'report', label: 'REPORT' },
];

/** Namespace exclusivo de v3 para cualquier persistencia local de presentación. */
export const FROTIS_V3_STORAGE_NAMESPACE = 'capstone:frotis:v3:';
