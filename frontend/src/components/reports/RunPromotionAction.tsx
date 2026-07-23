import type { TrainingPromotionStatus } from '../../types/api';

interface RunPromotionActionProps {
  error?: string | null;
  loading: boolean;
  preparing: boolean;
  runId: string;
  status?: TrainingPromotionStatus;
  onAction: () => void;
}

function shortId(value: string | null): string | null {
  return value ? `${value.slice(0, 8)}…` : null;
}

const BLOCKING_MESSAGES: Record<string, string> = {
  TRAINING_NOT_COMPLETED: 'El entrenamiento debe finalizar antes de preparar una versión.',
  EVALUATION_REQUIRED: 'Falta una evaluación formal del modelo.',
  CLINICAL_THRESHOLD_REQUIRED: 'El threshold clínico no ha sido validado en el conjunto requerido.',
  UNRESOLVED_LINEAGE: 'No es posible demostrar el entrenamiento de origen del checkpoint.',
  CHECKPOINT_HASH_MISMATCH: 'El artefacto no coincide con el registrado.',
  MODEL_VERSION_CONFLICT: 'Ya existe una versión incompatible para este entrenamiento.',
};

export function RunPromotionAction({
  error,
  loading,
  preparing,
  runId,
  status,
  onAction,
}: RunPromotionActionProps) {
  const unavailable = !status || status.next_action === 'unavailable';
  const disabled = loading || preparing || unavailable || !status?.button_enabled;
  const reasons = status?.blocking_reasons ?? [];
  const helpId = `promotion-help-${runId}`;
  const label = loading
    ? 'Consultando…'
    : preparing
      ? 'Preparando…'
      : status?.button_label ?? 'No disponible';
  const trainingDone = status?.training_status === 'completed';
  const evaluationDone = Boolean(status?.evaluation_run_id);
  const explanationDone = Boolean(status?.explainability_run_ids.length);
  const approved = ['approved', 'deployed'].includes(status?.model_version_status ?? '');
  const deployed = status?.deployment_status === 'active';

  return (
    <div className="run-promotion">
      <div aria-label="Progreso de liberación" className="run-promotion__progress" role="status">
        <span className="run-promotion__title">Liberación</span>
        <span data-complete={trainingDone}>{trainingDone ? '✓' : '○'} Entrenamiento</span>
        <span data-complete={evaluationDone}>{evaluationDone ? '✓' : '○'} Evaluación</span>
        <span data-complete={explanationDone}>
          {explanationDone ? '✓' : '○'} Explicabilidad {!explanationDone ? '(opcional)' : ''}
        </span>
        <span data-complete={approved}>{approved ? '✓' : '○'} Versión aprobada</span>
        <span data-complete={deployed}>{deployed ? '✓' : '○'} Desplegada</span>
      </div>

      <button
        aria-describedby={(reasons.length || error) ? helpId : undefined}
        aria-disabled={disabled}
        aria-label={`${label} para training ${runId}`}
        className="report-detail-button run-promotion__button"
        disabled={disabled}
        onClick={onAction}
        type="button"
      >
        {preparing ? <span aria-hidden="true" className="run-promotion__spinner" /> : null}
        {label}
      </button>

      {(reasons.length > 0 || error) ? (
        <details className="run-promotion__help" id={helpId}>
          <summary>{error ? 'No se pudo consultar la promoción' : '¿Por qué no está disponible?'}</summary>
          {error ? <p role="alert">{error}</p> : (
            <ul>
              {reasons.map((reason) => (
                <li key={reason.code}>{BLOCKING_MESSAGES[reason.code] ?? reason.message}</li>
              ))}
            </ul>
          )}
        </details>
      ) : null}
      {status?.model_version_id ? (
        <span className="report-muted">
          Versión: <strong>{shortId(status.model_version_id)}</strong>
          {status.model_version_status ? ` · ${status.model_version_status}` : ''}
        </span>
      ) : null}
      {status?.has_active_production_model ? (
        <span className="production-run-badge">
          {status.production_scope==='stage2_technical'
            ? '✓ Modelo productivo para Etapa 2'
            : 'Modelo activo en producción clínica'}
        </span>
      ) : null}
      {status?.deployment_id ? (
        <span className="report-muted">
          {status.alias || 'deployment'} · {status.environment || 'environment no registrado'}
        </span>
      ) : null}
    </div>
  );
}
