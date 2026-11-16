/**
 * Persistencia local de presentación exclusiva de v3.
 * Solo guarda estado de interfaz (nunca datos científicos) bajo el namespace
 * `capstone:frotis:v3:`, para no compartir claves con v1 ni v2.
 */
import { FROTIS_V3_STORAGE_NAMESPACE } from '../routes';

export type AnalysisPresentationContext = {
  imageId?: string | null;
};

const analysisKey = (analysisId: string) =>
  `${FROTIS_V3_STORAGE_NAMESPACE}analysis:${analysisId}`;

export function readAnalysisContext(analysisId: string): AnalysisPresentationContext {
  try {
    const raw = window.localStorage.getItem(analysisKey(analysisId));
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    const imageId = (parsed as { imageId?: unknown }).imageId;
    return { imageId: typeof imageId === 'string' ? imageId : null };
  } catch {
    return {};
  }
}

export function writeAnalysisContext(
  analysisId: string,
  context: AnalysisPresentationContext,
) {
  try {
    window.localStorage.setItem(
      analysisKey(analysisId),
      JSON.stringify({ ...readAnalysisContext(analysisId), ...context }),
    );
  } catch {
    // El almacenamiento es opcional: sin él la selección sigue viviendo en la URL.
  }
}

/** Preferencias de presentación del instrumento (no dependen del análisis). */
export type OpticsSettings = { brightness: number; contrast: number; saturation: number; gamma: number };
export type LayerSettings = {
  cells: boolean;
  filter: 'all' | 'parasitized' | 'near_threshold' | 'pending_review';
  contour: 'light' | 'dark';
  minimap: boolean;
};
export type WorkspacePreferences = {
  view: 'full-field' | 'review-cells' | 'report';
  panels: { optics: boolean; ai: boolean };
  optics: OpticsSettings;
  layers: LayerSettings;
};

export const DEFAULT_OPTICS: OpticsSettings = { brightness: 100, contrast: 100, saturation: 100, gamma: 1 };
export const DEFAULT_PREFERENCES: WorkspacePreferences = {
  view: 'full-field',
  panels: { optics: false, ai: false },
  optics: DEFAULT_OPTICS,
  // Las tinciones de campo claro (Giemsa) dejan fondos claros: contorno oscuro por defecto.
  layers: { cells: true, filter: 'all', contour: 'dark', minimap: true },
};

const PREFERENCES_KEY = `${FROTIS_V3_STORAGE_NAMESPACE}preferences`;
const finite = (value: unknown, fallback: number, min: number, max: number) =>
  (typeof value === 'number' && Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : fallback);

export function readPreferences(): WorkspacePreferences {
  try {
    const raw = window.localStorage.getItem(PREFERENCES_KEY);
    if (!raw) return DEFAULT_PREFERENCES;
    const parsed = JSON.parse(raw) as Partial<WorkspacePreferences> | null;
    if (!parsed || typeof parsed !== 'object') return DEFAULT_PREFERENCES;
    const base = DEFAULT_PREFERENCES;
    return {
      view: ['full-field', 'review-cells', 'report'].includes(parsed.view as string) ? parsed.view! : base.view,
      panels: { optics: Boolean(parsed.panels?.optics), ai: Boolean(parsed.panels?.ai) },
      optics: {
        brightness: finite(parsed.optics?.brightness, 100, 40, 200),
        contrast: finite(parsed.optics?.contrast, 100, 40, 200),
        saturation: finite(parsed.optics?.saturation, 100, 0, 200),
        gamma: finite(parsed.optics?.gamma, 1, 0.4, 2.5),
      },
      layers: {
        cells: parsed.layers?.cells !== false,
        filter: ['all', 'parasitized', 'near_threshold', 'pending_review'].includes(parsed.layers?.filter as string)
          ? parsed.layers!.filter
          : base.layers.filter,
        contour: parsed.layers?.contour === 'light' ? 'light' : 'dark',
        minimap: parsed.layers?.minimap !== false,
      },
    };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function writePreferences(preferences: WorkspacePreferences) {
  try {
    window.localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
  } catch {
    // Almacenamiento opcional.
  }
}
