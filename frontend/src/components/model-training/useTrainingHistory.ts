import { useEffect, useRef, useState } from 'react';
import { api } from '../../services/api';
import type { CurveEvidence } from '../../types/scientificReport';
import type { TrainingTrajectories } from '../../types/trainingTrajectories';
import type { TrainingView } from './trainingHistoryModel';

type Load<T> = { state: 'idle' | 'loading' | 'ready' | 'error'; data: T | null; error: string | null };
const idle = { state: 'idle', data: null, error: null } as const;
const message = (cause: unknown, fallback: string) => cause instanceof Error && cause.message ? cause.message : fallback;

/**
 * Carga diferida de la historia del TRAIN: cada fuente se consulta la primera vez que se abre una pestaña
 * que la usa y se conserva al cambiar de pestaña. Curvas = módulo «curves» del reporte científico (mismo
 * contrato que Comparación científica); trayectorias = GET /runs/{id}/training-trajectories.
 */
export function useTrainingHistory(datasource: string, runId: string, view: TrainingView) {
  const [curve, setCurve] = useState<Load<CurveEvidence>>(idle);
  const [trajectories, setTrajectories] = useState<Load<TrainingTrajectories>>(idle);

  // Una consulta por fuente y RUN; el cambio de estado a «loading» no debe cancelarla.
  const started = useRef({ key: '', curve: false, trajectories: false });
  const key = `${datasource}|${runId}`;
  if (started.current.key !== key) started.current = { key, curve: false, trajectories: false };
  useEffect(() => { setCurve(idle); setTrajectories(idle); }, [key]);

  const needsCurve = view === 'curvas' || view === 'lr';
  useEffect(() => {
    if (!needsCurve || started.current.curve) return;
    started.current.curve = true;
    let alive = true, done = false;
    setCurve({ state: 'loading', data: null, error: null });
    api.getComparisonReport<CurveEvidence[]>(datasource, { module: 'curves', selections: [{ training_run_id: runId }] })
      .then(response => { done = true; if (alive) setCurve({ state: 'ready', data: response.data[0] ?? null, error: null }); })
      .catch(cause => { done = true; if (alive) setCurve({ state: 'error', data: null, error: message(cause, 'No fue posible leer las épocas del TRAIN.') }); });
    // Al salir de la pestaña antes de la respuesta, se descarta y se vuelve a pedir al regresar; una respuesta recibida se conserva.
    return () => { alive = false; if (!done) started.current.curve = false; };
  }, [needsCurve, datasource, runId]);

  const needsTrajectories = view === 'trayectorias';
  useEffect(() => {
    if (!needsTrajectories || started.current.trajectories) return;
    started.current.trajectories = true;
    const controller = new AbortController();
    let done = false;
    setTrajectories({ state: 'loading', data: null, error: null });
    api.getTrainingTrajectories(datasource, runId, controller.signal)
      .then(data => { done = true; setTrajectories({ state: 'ready', data, error: null }); })
      .catch(cause => { done = true; if (!controller.signal.aborted) setTrajectories({ state: 'error', data: null, error: message(cause, 'No fue posible leer las trayectorias del TRAIN.') }); });
    return () => { if (!done) { controller.abort(); started.current.trajectories = false; } };
  }, [needsTrajectories, datasource, runId]);

  return { curve, trajectories };
}
