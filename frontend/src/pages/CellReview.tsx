import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { useAuth } from '../auth';
import { CellReviewWorkspace } from '../components/cell-review/CellReviewWorkspace';
import { isValidPublicId } from '../router';
import { ApiError, api } from '../services/api';
import type {
  CellDetectionRunSummary,
  EligibleCellAnalysisRun,
} from '../types/cellReview';

const statusLabel: Record<CellDetectionRunSummary['status'], string> = {
  created: 'Creada',
  processing: 'Procesando',
  completed: 'Completada',
  completed_with_warnings: 'Completada con advertencias',
  failed: 'Fallida',
};

const safeDate = (value: string | null) => {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleString();
};

export function CellReview() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [eligibleRuns, setEligibleRuns] = useState<EligibleCellAnalysisRun[]>([]);
  const [detectionRuns, setDetectionRuns] = useState<CellDetectionRunSummary[]>([]);
  const [selectedEligibleId, setSelectedEligibleId] = useState('');
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const selectedDetectionRunId = searchParams.get('detection_run_id');
  const canRead = Boolean(user?.permissions.includes('scientific.cell_detection.read'));
  const canExecute = Boolean(user?.permissions.includes('scientific.cell_detection.execute'));
  const canReview = Boolean(user?.permissions.includes('scientific.cell_detection.review'));

  const load = useCallback(async () => {
    if (!canRead) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const [eligible, runs] = await Promise.all([
        api.getEligibleCellAnalysisRuns({ limit: 100, offset: 0 }),
        api.getCellDetectionRuns({ limit: 100, offset: 0 }),
      ]);
      setEligibleRuns(eligible.items);
      setDetectionRuns(runs.items);
      setSelectedEligibleId((current) => (
        eligible.items.some((item) => item.id === current)
          ? current
          : eligible.items[0]?.id ?? ''
      ));
    } catch {
      setError('No fue posible cargar las ejecuciones de detección celular.');
    } finally {
      setLoading(false);
    }
  }, [canRead]);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedEligible = useMemo(
    () => eligibleRuns.find((item) => item.id === selectedEligibleId) ?? null,
    [eligibleRuns, selectedEligibleId],
  );

  function openWorkspace(runId: string) {
    const next = new URLSearchParams(searchParams);
    next.set('detection_run_id', runId);
    setSearchParams(next);
  }

  function closeWorkspace() {
    const next = new URLSearchParams(searchParams);
    next.delete('detection_run_id');
    setSearchParams(next);
    void load();
  }

  async function executeDetection() {
    if (!selectedEligible || !canExecute) return;
    setExecuting(true);
    setError('');
    setMessage('');
    try {
      const created = await api.createCellDetectionRun(selectedEligible.id);
      setMessage(`Detección manual ${created.detection_run_code} completada. No se ejecutó clasificación ni diagnóstico.`);
      await load();
      openWorkspace(created.id);
    } catch (executionError) {
      setError(
        executionError instanceof ApiError && executionError.status === 409
          ? 'Ya existe una detección equivalente o el analysis run dejó de ser elegible.'
          : 'La detección manual fue rechazada o terminó con error.',
      );
      await load();
    } finally {
      setExecuting(false);
    }
  }

  if (!canRead) {
    return (
      <section className="page cell-review-page">
        <header className="page-title"><div>
          <h1>Revisión celular</h1>
          <p>Estación científica de detecciones candidatas.</p>
        </div></header>
        <section className="panel cell-access-denied" role="alert">
          <h2>Acceso restringido</h2>
          <p>Tu rol no incluye scientific.cell_detection.read.</p>
        </section>
      </section>
    );
  }

  if (selectedDetectionRunId) {
    if (!isValidPublicId(selectedDetectionRunId)) {
      return (
        <section className="page cell-review-page">
          <section className="panel cell-access-denied" role="alert">
            <h1>Identificador de ejecución inválido</h1>
            <p>La estación de revisión requiere un UUID público válido.</p>
            <button type="button" onClick={closeWorkspace}>Volver a ejecuciones</button>
          </section>
        </section>
      );
    }
    return (
      <section className="page cell-review-page cell-review-page--workspace">
        <CellReviewWorkspace
          detectionRunId={selectedDetectionRunId}
          canReview={canReview}
          onClose={closeWorkspace}
        />
      </section>
    );
  }

  return (
    <section className="page cell-review-page">
      <header className="page-title cell-review-title">
        <div>
          <p className="cell-workspace-kicker">Análisis de frotis</p>
          <h1>Revisión celular</h1>
          <p>Detecta regiones candidatas y registra revisiones humanas sin modificar las imágenes originales.</p>
        </div>
        <button type="button" disabled={loading || executing} onClick={() => void load()}>Actualizar</button>
      </header>

      <section className="panel cell-baseline-notice">
        <strong>Línea base académica</strong>
        <p>
          connected_components_v1 genera bounding boxes y crops técnicos. No clasifica células,
          no estima malaria y no produce diagnóstico.
        </p>
      </section>

      <section className="panel cell-detection-launcher" aria-labelledby="cell-launch-heading">
        <div>
          <h2 id="cell-launch-heading">Iniciar detección manual</h2>
          <p>Solo se muestran analysis runs cuyo control técnico dejó ready_for_analysis=true.</p>
        </div>
        {eligibleRuns.length ? (
          <div className="cell-launch-controls">
            <label>
              Analysis run elegible
              <select value={selectedEligibleId} onChange={(event) => setSelectedEligibleId(event.target.value)}>
                {eligibleRuns.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.run_code} · {run.subject_code} · {run.sample_code} · {run.slide_code}
                  </option>
                ))}
              </select>
            </label>
            {selectedEligible ? (
              <p>
                {selectedEligible.input_image_count} imágenes · quality gate {selectedEligible.quality_gate_status}
              </p>
            ) : null}
            <button
              type="button"
              disabled={executing || !canExecute || !selectedEligible}
              title={canExecute ? undefined : 'Tu rol no permite ejecutar detección celular.'}
              onClick={() => void executeDetection()}
            >
              {executing ? 'Procesando detección…' : 'Iniciar detección'}
            </button>
          </div>
        ) : (
          <p className="cell-empty-state">
            No existen analysis runs elegibles. Completa primero el control técnico de calidad.
          </p>
        )}
      </section>

      <section className="panel cell-run-list" aria-labelledby="cell-run-list-heading">
        <div className="section-heading">
          <div>
            <h2 id="cell-run-list-heading">Ejecuciones de detección</h2>
            <p>Abre una ejecución para sincronizar crops, bounding boxes e historial humano.</p>
          </div>
          <span>{detectionRuns.length} mostradas</span>
        </div>
        {loading ? <p className="cell-panel-state" aria-live="polite">Cargando ejecuciones…</p> : null}
        {error ? <p className="cell-error" role="alert">{error}</p> : null}
        {message ? <p className="cell-success" aria-live="polite">{message}</p> : null}
        {!loading && !error ? (
          <div className="table-wrap">
            <table className="cell-runs-table">
              <thead>
                <tr>
                  <th>Ejecución</th>
                  <th>Analysis run</th>
                  <th>Paciente / muestra / frotis</th>
                  <th>Imágenes</th>
                  <th>Detector</th>
                  <th>Estado</th>
                  <th>Componentes</th>
                  <th>Detecciones / crops</th>
                  <th>Avance de revisión</th>
                  <th>Fecha</th>
                  <th>Acción</th>
                </tr>
              </thead>
              <tbody>
                {detectionRuns.map((run) => {
                  const reviewPct = run.detection_count
                    ? Math.min(100, run.reviewed_count / run.detection_count * 100)
                    : 0;
                  return (
                    <tr key={run.id} className={run.status === 'failed' ? 'is-failed' : undefined}>
                      <td data-label="Ejecución"><strong>{run.detection_run_code}</strong></td>
                      <td data-label="Analysis run">{run.analysis_run_code}</td>
                      <td data-label="Identidad pseudonimizada">
                        {run.subject_code}<br />{run.sample_code}<br />{run.slide_code}
                      </td>
                      <td data-label="Imágenes">{run.processed_image_count}/{run.image_count}</td>
                      <td data-label="Detector">
                        {run.detector_key}<br /><small>v{run.detector_version} · {run.algorithm_version}</small>
                      </td>
                      <td data-label="Estado">
                        <span className={`cell-run-status status-${run.status}`}>{statusLabel[run.status]}</span>
                        {run.warning_count ? <small>{run.warning_count} advertencias</small> : null}
                      </td>
                      <td data-label="Componentes">{run.component_count}</td>
                      <td data-label="Detecciones / crops">{run.detection_count} / {run.crop_count}</td>
                      <td data-label="Avance de revisión">
                        <span>{run.reviewed_count}/{run.detection_count}</span>
                        <progress max={100} value={reviewPct} aria-label={`Revisión ${reviewPct.toFixed(0)} por ciento`} />
                      </td>
                      <td data-label="Fecha">{safeDate(run.completed_at ?? run.created_at)}</td>
                      <td data-label="Acción">
                        <button type="button" onClick={() => openWorkspace(run.id)}>
                          {run.status === 'failed' ? 'Ver estado' : 'Abrir revisión'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {!detectionRuns.length ? (
                  <tr><td colSpan={11}>No existen ejecuciones de detección celular.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </section>
  );
}
