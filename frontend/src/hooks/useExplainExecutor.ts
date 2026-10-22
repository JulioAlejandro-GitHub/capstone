import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ExplainExecutor } from '../types/explainGeneration';
import { executorUnavailable } from './useExplainGeneration';

const POLL_MS = 15000;

// While visible, re-read the host GPU agent heartbeat so generation unlocks as soon as the agent starts.
export function useExplainExecutor(active: boolean) {
  const [executor, setExecutor] = useState<ExplainExecutor | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const read = async () => {
      try { setExecutor(await api.getExplainExecutor(controller.signal)); setFailed(false); }
      catch { if (!controller.signal.aborted) setFailed(true); }
      if (!controller.signal.aborted) timer = setTimeout(() => { void read(); }, POLL_MS);
    };
    void read();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [active]);
  const blocked = failed ? 'No se pudo consultar el ejecutor EXPLAIN.' : executor && !executor.available ? executorUnavailable : executor ? null : 'Consultando ejecutor EXPLAIN…';
  return { executor, blocked };
}

export function executorLabel(executor: ExplainExecutor | null) {
  if (!executor) return 'Consultando ejecutor…';
  if (executor.executor === 'docker_cpu') return 'Ejecutor: CPU del contenedor (configurado)';
  if (!executor.available) return `Ejecutor GPU del host no activo${executor.age_seconds != null ? ` · último latido hace ${Math.round(executor.age_seconds)} s` : ''}`;
  return `Ejecutor: GPU del host · ${executor.host ?? 'host'}${executor.tensorflow_metal ? ` · tensorflow-metal ${executor.tensorflow_metal}` : ''}`;
}
