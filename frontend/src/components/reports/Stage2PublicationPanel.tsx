import { useState } from 'react';
import type { Stage2Availability } from '../../types/api';

interface Props {
  id: string;
  status?: Stage2Availability;
  loading?: boolean;
  error?: string;
  explainCount: number;
  onPublish: (replaceExisting: boolean) => Promise<'published' | 'replacement-required' | 'failed'>;
  onRetry?: () => void;
}

const value = (raw?: string | null) => raw || 'Sin evidencia';
const date = (raw?: string | null) => raw ? new Intl.DateTimeFormat('es-CL', {
  dateStyle: 'medium', timeStyle: 'short',
}).format(new Date(raw)) : 'Sin evidencia';

function completionLabel(completed: boolean | undefined, state?: string | null): string {
  if (completed === true) return 'Completado';
  switch (state) {
    case 'running': case 'active': return 'En curso';
    case 'failed': return 'Fallido';
    case 'interrupted': return 'Interrumpido';
    case 'cancelled': case 'canceled': return 'Cancelado';
    case 'pending': case 'queued': return 'Pendiente';
    case 'completed': case 'verified': return 'Pendiente de validación';
    default: return 'Sin información';
  }
}

export function Stage2PublicationPanel({
  id, status, loading = false, error, explainCount, onPublish, onRetry,
}: Props) {
  const [confirm, setConfirm] = useState<'replace' | null>(null);
  const active = status?.is_stage2_available === true && status.available_for_inference === true;
  const publishable = status?.eligible === true;
  const execute = async (replaceExisting = false) => {
    if (loading || active || !publishable) return;
    const result = await onPublish(replaceExisting);
    if (result === 'replacement-required') { setConfirm('replace'); return; }
    if (result === 'failed') return;
    setConfirm(null);
  };

  if (loading && !status) return <section aria-label="Clasificación celular"
    className="stage2-publication-panel" id={id}>
    <p role="status">Consultando modelo…</p>
  </section>;
  if (!status) return <section aria-label="Clasificación celular"
    className="stage2-publication-panel" id={id}>
    <p role="alert">No se pudo consultar el modelo. Inténtalo de nuevo.</p>
    {onRetry ? <button type="button" onClick={onRetry}>Reintentar consulta</button> : null}
  </section>;

  const confirming = !active && publishable;
  const trainLabel = completionLabel(status.eligibility?.train_completed, status.train_status);
  const evaluateLabel = status.evaluation_status
    ? completionLabel(status.eligibility?.evaluate_completed, status.evaluation_status)
    : 'Sin evaluación asociada';
  return <section aria-label="Clasificación celular" className="stage2-publication-panel" id={id}>
    <header>
      <h3>Regla de liberación</h3>
      {active ? <strong role="status">Modelo en Estado Activo</strong> : null}
    </header>
    <div className="stage2-publication-grid">
      <span className="stage2-release-rule">Regla
        <strong>TRAIN completed + EVALUATE completed</strong>
        <span className="stage2-release-states">TRAIN: {trainLabel}. · EVALUATE: {evaluateLabel}.</span>
        {status.eligible
          ? <strong role="status">Cumple la regla de liberación para clasificación celular</strong>
          : <span className="stage2-missing-condition" role="status">
            {status.eligibility ? <>
              {!status.eligibility.train_completed ? 'Pendiente: TRAIN debe estar completado. ' : ''}
              {!status.eligibility.evaluate_completed
                ? 'Pendiente: EVALUATE debe estar completado y vinculado a este TRAIN.' : ''}
            </> : 'No se pudo confirmar el cumplimiento de la regla de liberación.'}
          </span>}
      </span>
      <span>TRAIN<strong>{value(status.training_run_id)} · {trainLabel}</strong></span>
      <span>TRAIN finalizado<strong>{date(status.train_finished_at)}</strong></span>
      <span>EVALUATE finalizado<strong>{date(status.evaluation_finished_at)} · {status.evaluation_split?.toUpperCase() ?? 'Sin evidencia'}</strong></span>
      <span>EXPLAIN<strong>{status.explanations?.length
        ? status.explanations.map((item) => `${item.status} · ${item.run_id}`).join(' / ')
        : explainCount ? `${explainCount} asociado(s) · informativo` : 'N/A · opcional, sin ejecución asociada'}</strong></span>
      <span>Arquitectura<strong>{value(status.architecture)}</strong></span>
      <span>Modelo / checkpoint<strong>{value(status.model_name)} · {value(status.checkpoint)}</strong></span>
      {status.deployment_id ? <>
        <span>Deployment<strong>{status.deployment_id.slice(0, 8)}</strong></span>
        <span>Slot productivo<strong>{status.environment} / {status.alias}</strong></span>
        <span>Threshold<strong>{status.threshold ?? 'Registrado'} · {status.threshold_source ?? 'fuente registrada'}</strong></span>
        <span>Desplegado<strong>{date(status.deployed_at)}</strong></span>
      </> : null}
      {status.publication ? <span>Publicado<strong>{date(status.publication.published_at)} · {value(status.publication.published_by)}</strong></span> : null}
    </div>
    <p className="stage2-experimental-warning">
      Uso experimental. No constituye aprobación clínica ni diagnóstico automatizado.
    </p>
    {error ? <p className="run-promotion-error" role="alert">
      {error}
    </p> : null}
    {confirm && confirming ? <div className="stage2-inline-confirmation" role="alert">
      <p>Ya hay otro modelo activo. Al continuar, este modelo lo reemplazará para las nuevas clasificaciones.</p>
      <div>
        <button className="primary-action" disabled={loading}
          onClick={() => void execute(true)} type="button">Continuar y reemplazar</button>
        <button disabled={loading} onClick={() => setConfirm(null)} type="button">Cancelar</button>
      </div>
    </div> : <button className={active ? '' : 'primary-action'} disabled={loading || active || !publishable}
      onClick={() => void execute()} type="button">
      Activar para clasificación celular
    </button>}
  </section>;
}
