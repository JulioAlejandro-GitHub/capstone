/**
 * Capa celular de v3: une detecciones y predicciones reales por identificador.
 * Módulo puro (solo imports de tipos). No recalcula ni reinterpreta resultados:
 * la etiqueta, la probabilidad y el umbral son los que entregó el backend.
 */
import type { CellPredictionSummary } from '../../../types/cellClassification';
import type { CellDetectionSummary } from '../../../types/cellReview';

export type CellLabel = 'parasitized' | 'uninfected';

export type MicroscopeCell = {
  detectionId: string;
  cellCode: string;
  cellIndex: number;
  /** Bounding box en píxeles de la imagen original. */
  bbox: { x: number; y: number; width: number; height: number };
  detectorScore: number | null;
  detectionReview: string;
  cropId: string | null;
  cropUrl: string | null;
  prediction: {
    id: string;
    status: string;
    label: CellLabel | null;
    probabilityParasitized: number | null;
    threshold: number;
    nearThreshold: boolean;
    reviewStatus: string;
    reviewedLabel: CellLabel | null;
  } | null;
};

export type CellKind = 'parasitized' | 'uninfected' | 'failed' | 'unclassified';
export type CellFilter = 'all' | 'parasitized' | 'near_threshold' | 'pending_review';

export function mergeCells(
  detections: readonly CellDetectionSummary[],
  predictions: readonly CellPredictionSummary[],
): MicroscopeCell[] {
  const byDetection = new Map(predictions.map((prediction) => [prediction.cell_detection_id, prediction]));
  return detections.map((detection) => {
    const prediction = byDetection.get(detection.id) ?? null;
    return {
      detectionId: detection.id,
      cellCode: detection.cell_code,
      cellIndex: detection.cell_index,
      bbox: {
        x: detection.bbox_x,
        y: detection.bbox_y,
        width: detection.bbox_width,
        height: detection.bbox_height,
      },
      detectorScore: detection.detector_score,
      detectionReview: detection.review_status,
      cropId: detection.crop?.id ?? null,
      cropUrl: detection.crop?.content_url ?? null,
      prediction: prediction ? {
        id: prediction.id,
        status: prediction.prediction_status,
        label: prediction.predicted_label,
        probabilityParasitized: prediction.probability_parasitized,
        threshold: prediction.threshold_used,
        nearThreshold: prediction.near_threshold,
        reviewStatus: prediction.review_status,
        reviewedLabel: prediction.latest_review?.reviewed_label ?? null,
      } : null,
    };
  }).sort((first, second) => first.cellIndex - second.cellIndex);
}

export function cellKind(cell: MicroscopeCell): CellKind {
  if (!cell.prediction) return 'unclassified';
  if (cell.prediction.status === 'failed' || !cell.prediction.label) return 'failed';
  return cell.prediction.label;
}

export const isPendingReview = (cell: MicroscopeCell) => (
  cell.prediction ? cell.prediction.reviewStatus === 'unreviewed' : cell.detectionReview === 'unreviewed'
);

export function filterCells(cells: readonly MicroscopeCell[], filter: CellFilter): MicroscopeCell[] {
  if (filter === 'parasitized') return cells.filter((cell) => cellKind(cell) === 'parasitized');
  if (filter === 'near_threshold') return cells.filter((cell) => Boolean(cell.prediction?.nearThreshold));
  if (filter === 'pending_review') return cells.filter(isPendingReview);
  return [...cells];
}

/** Célula vecina en el orden dado; sin selección devuelve la primera (o la última). */
export function neighbourCell(
  cells: readonly MicroscopeCell[],
  currentDetectionId: string | null,
  step: 1 | -1,
): MicroscopeCell | null {
  if (!cells.length) return null;
  const index = cells.findIndex((cell) => cell.detectionId === currentDetectionId);
  if (index < 0) return step === 1 ? cells[0] : cells[cells.length - 1];
  return cells[(index + step + cells.length) % cells.length];
}

export const KIND_LABEL: Record<CellKind, string> = {
  parasitized: 'Candidata parasitada',
  uninfected: 'No infectada',
  failed: 'Predicción fallida',
  unclassified: 'Sin clasificar',
};

const REVIEW_LABEL: Record<string, string> = {
  unreviewed: 'Sin revisar',
  accepted: 'Aceptada',
  rejected: 'Rechazada',
  needs_attention: 'Requiere atención',
  confirmed: 'Confirmada',
  corrected: 'Corregida',
};
export const reviewLabel = (status: string) => REVIEW_LABEL[status] ?? status;

export const formatProbability = (value: number | null) =>
  (value == null ? '—' : `${(value * 100).toFixed(1)} %`);
