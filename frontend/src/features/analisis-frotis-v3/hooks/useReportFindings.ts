import { useEffect, useState } from 'react';

import { ApiError, api } from '../../../services/api';
import type { CellPredictionSummary } from '../../../types/cellClassification';

const PAGE_SIZE = 100;

export type ReportFinding = {
  predictionId: string;
  detectionId: string;
  imageId: string;
  imageSequence: number;
  cellCode: string;
  probabilityParasitized: number | null;
  threshold: number;
  nearThreshold: boolean;
  label: 'parasitized' | 'uninfected' | null;
  reviewStatus: string;
};

export type ReportFindingsState =
  | { status: 'idle' | 'loading'; findings: ReportFinding[] }
  | { status: 'ready'; findings: ReportFinding[] }
  | { status: 'unavailable'; findings: ReportFinding[]; message: string };

const toFinding = (prediction: CellPredictionSummary): ReportFinding => ({
  predictionId: prediction.id,
  detectionId: prediction.cell_detection_id,
  imageId: prediction.microscopy_image_id,
  imageSequence: prediction.image_sequence_number,
  cellCode: prediction.cell_code,
  probabilityParasitized: prediction.probability_parasitized,
  threshold: prediction.threshold_used,
  nearThreshold: prediction.near_threshold,
  label: prediction.predicted_label,
  reviewStatus: prediction.review_status,
});

async function allPredictions(runId: string, filter: Record<string, string | boolean>) {
  const items: CellPredictionSummary[] = [];
  for (;;) {
    const page = await api.getCellClassificationPredictions(runId, { ...filter, limit: PAGE_SIZE, offset: items.length });
    items.push(...page.items);
    if (!page.items.length || items.length >= page.total) return items;
  }
}

/**
 * Hallazgos del reporte: candidatas parasitadas y células cercanas al umbral
 * de todo el análisis, leídas del RUN de clasificación persistido.
 */
export function useReportFindings(classificationRunId: string | null, enabled: boolean) {
  const [state, setState] = useState<ReportFindingsState>({ status: 'idle', findings: [] });

  useEffect(() => {
    if (!enabled || !classificationRunId) {
      setState({ status: 'idle', findings: [] });
      return undefined;
    }
    let active = true;
    setState({ status: 'loading', findings: [] });
    Promise.all([
      allPredictions(classificationRunId, { predicted_label: 'parasitized' }),
      allPredictions(classificationRunId, { near_threshold: true }),
    ]).then(([parasitized, nearThreshold]) => {
      if (!active) return;
      const byId = new Map([...parasitized, ...nearThreshold].map((item) => [item.id, toFinding(item)]));
      const findings = [...byId.values()].sort((first, second) => (
        first.imageSequence - second.imageSequence
        || (second.probabilityParasitized ?? 0) - (first.probabilityParasitized ?? 0)
      ));
      setState({ status: 'ready', findings });
    }).catch((error) => {
      if (!active) return;
      setState({
        status: 'unavailable',
        findings: [],
        message: error instanceof ApiError && error.status === 403
          ? 'Tu rol no autoriza la lectura de la clasificación celular (scientific.cell_classification.read).'
          : 'No fue posible recuperar las predicciones del análisis.',
      });
    });
    return () => {
      active = false;
    };
  }, [classificationRunId, enabled]);

  return state;
}
