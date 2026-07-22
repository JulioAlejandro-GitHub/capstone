import type { PromotionStatusResponse } from '../../types/api';

interface PromotionTrackerProps {
  status: PromotionStatusResponse | null;
  runStatus?: string | null;
}

export function PromotionTracker({ status, runStatus }: PromotionTrackerProps) {
  const isTrainingDone = runStatus?.toLowerCase() === 'completed';
  const hasEval = Boolean(status?.evaluation_run_id);
  const hasExplain = Boolean(status?.explainability_run_ids && status.explainability_run_ids.length > 0);

  const mvStatus = status?.model_version_status;
  const isApproved = mvStatus === 'approved' || mvStatus === 'validated';

  const depStatus = status?.deployment_status;
  const isDeployed = depStatus === 'active';

  return (
    <div
      aria-label="Progreso de liberación del modelo"
      className="promotion-tracker"
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '6px 12px',
        fontSize: '11px',
        color: '#475569',
        margin: '6px 0',
      }}
    >
      <span style={{ color: isTrainingDone ? '#16a34a' : '#94a3b8', fontWeight: 600 }}>
        {isTrainingDone ? '✓' : '○'} Entrenamiento
      </span>
      <span style={{ color: hasEval ? '#16a34a' : '#94a3b8', fontWeight: 600 }}>
        {hasEval ? '✓' : '○'} Evaluación
      </span>
      <span style={{ color: hasExplain ? '#16a34a' : '#94a3b8' }}>
        {hasExplain ? '✓' : '○'} Explicabilidad <small style={{ opacity: 0.8 }}>(Opcional)</small>
      </span>
      <span style={{ color: isApproved ? '#16a34a' : '#94a3b8', fontWeight: 600 }}>
        {isApproved ? '✓' : '○'} Versión aprobada
      </span>
      <span style={{ color: isDeployed ? '#16a34a' : '#94a3b8', fontWeight: 600 }}>
        {isDeployed ? '✓' : '○'} Desplegada
      </span>
    </div>
  );
}
