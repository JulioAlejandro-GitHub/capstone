import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError, api } from '../../../services/api';
import type { CellPredictionSummary } from '../../../types/cellClassification';
import type { CellDetectionSummary } from '../../../types/cellReview';
import { mergeCells, type MicroscopeCell } from '../adapters/cellLayer';

const PAGE_SIZE = 100;

export type CellLayerState =
  | { status: 'idle'; cells: MicroscopeCell[] }
  | { status: 'loading'; cells: MicroscopeCell[] }
  | { status: 'ready'; cells: MicroscopeCell[]; classificationRestricted: boolean }
  | { status: 'unavailable'; cells: MicroscopeCell[]; message: string };

async function allPages<T>(fetchPage: (offset: number) => Promise<{ items: T[]; total: number }>) {
  const items: T[] = [];
  for (;;) {
    const page = await fetchPage(items.length);
    items.push(...page.items);
    if (!page.items.length || items.length >= page.total) return items;
  }
}

/**
 * Detecciones y predicciones reales de una imagen, leídas con los endpoints
 * paginados existentes (solo GET). Sin RUN de detección no hay capa.
 */
export function useCellLayer(
  detectionRunId: string | null,
  classificationRunId: string | null,
  imageId: string | null,
) {
  const [state, setState] = useState<CellLayerState>({ status: 'idle', cells: [] });
  const [version, setVersion] = useState(0);
  const request = useRef(0);

  useEffect(() => {
    const current = ++request.current;
    if (!detectionRunId || !imageId) {
      setState({ status: 'idle', cells: [] });
      return;
    }
    setState({ status: 'loading', cells: [] });
    (async () => {
      const detections = await allPages<CellDetectionSummary>((offset) =>
        api.getCellDetections(detectionRunId, imageId, { limit: PAGE_SIZE, offset }));
      let predictions: CellPredictionSummary[] = [];
      let classificationRestricted = false;
      if (classificationRunId) {
        try {
          predictions = await allPages<CellPredictionSummary>((offset) =>
            api.getCellClassificationPredictions(classificationRunId, {
              microscopy_image_id: imageId,
              limit: PAGE_SIZE,
              offset,
            }));
        } catch (error) {
          if (!(error instanceof ApiError && error.status === 403)) throw error;
          classificationRestricted = true;
        }
      }
      if (current === request.current) {
        setState({ status: 'ready', cells: mergeCells(detections, predictions), classificationRestricted });
      }
    })().catch((error) => {
      if (current !== request.current) return;
      setState({
        status: 'unavailable',
        cells: [],
        message: error instanceof ApiError && error.status === 403
          ? 'Tu rol no autoriza la lectura de detecciones celulares (scientific.cell_detection.read).'
          : 'No fue posible recuperar las células de esta imagen.',
      });
    });
  }, [classificationRunId, detectionRunId, imageId, version]);

  const reload = useCallback(() => setVersion((value) => value + 1), []);
  return { state, reload };
}
