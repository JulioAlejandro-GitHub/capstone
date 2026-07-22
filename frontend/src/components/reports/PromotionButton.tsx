import { useState } from 'react';
import type { PromotionStatusResponse } from '../../types/api';
import { api } from '../../services/api';

interface PromotionButtonProps {
  datasource: string;
  trainingRunId: string;
  runStatus?: string | null;
  status: PromotionStatusResponse | null;
  onNavigate?: (targetUrl: string) => void;
  onStatusChange?: (newStatus: PromotionStatusResponse) => void;
}

export function translateBlocker(reason: string): string {
  if (reason.includes('EVALUATION_REQUIRED')) return 'Falta una evaluación formal del modelo.';
  if (reason.includes('CLINICAL_THRESHOLD_REQUIRED')) return 'El threshold clínico no ha sido validado en el conjunto requerido.';
  if (reason.includes('UNRESOLVED_LINEAGE')) return 'No es posible demostrar el entrenamiento de origen del checkpoint.';
  if (reason.includes('CHECKPOINT_HASH_MISMATCH')) return 'El artefacto no coincide con el registrado.';
  if (reason.includes('MODEL_VERSION_CONFLICT')) return 'Ya existe una versión incompatible para este entrenamiento.';
  if (reason.includes('TRAINING_NOT_COMPLETED')) return 'El entrenamiento debe finalizar antes de preparar una versión.';
  return reason;
}

export function PromotionButton({
  datasource,
  trainingRunId,
  runStatus,
  status,
  onNavigate,
  onStatusChange,
}: PromotionButtonProps) {
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showBlockers, setShowBlockers] = useState(false);

  const isTrainingCompleted = runStatus?.toLowerCase() === 'completed';

  // Determinar acción
  const nextAction = status?.next_action ?? (isTrainingCompleted ? 'prepare_release' : 'unavailable');
  const label = status?.button_label ?? (isTrainingCompleted ? 'Preparar despliegue' : 'No disponible');
  const enabled = (status?.button_enabled ?? isTrainingCompleted) && !loading;
  const blockers = status?.blocking_reasons ?? [];

  const handleAction = async () => {
    if (loading || !enabled) return;
    setErrorMessage(null);

    // Si requiere POST prepare-release
    if (nextAction === 'prepare_release') {
      setLoading(true);
      try {
        const response = await api.prepareRelease(datasource, trainingRunId, 'ui_user');
        if (onStatusChange) onStatusChange(response);
        if (response.target_url && onNavigate) {
          onNavigate(response.target_url);
        } else if (onNavigate) {
          onNavigate(`/modelo-ia/modelos-liberados/${response.model_version_id}`);
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Error al preparar release';
        setErrorMessage(msg);
      } finally {
        setLoading(false);
      }
      return;
    }

    // Si ya existe target_url o ruta
    if (status?.target_url && onNavigate) {
      onNavigate(status.target_url);
      return;
    }

    // Rutas de fallback por acción
    if (status?.model_version_id && onNavigate) {
      if (nextAction === 'review_model_version' || nextAction === 'approve_model_version') {
        onNavigate(`/modelo-ia/modelos-liberados/${status.model_version_id}`);
      } else if (nextAction === 'create_deployment') {
        onNavigate(`/modelo-ia/modelos-liberados/${status.model_version_id}?action=deploy`);
      }
    } else if (status?.deployment_id && onNavigate) {
      onNavigate(`/modelo-ia/despliegues/${status.deployment_id}`);
    }
  };

  const hasBlockers = blockers.length > 0;
  const tooltipText = hasBlockers
    ? blockers.map(translateBlocker).join(' | ')
    : !isTrainingCompleted
    ? 'El entrenamiento debe finalizar antes de preparar una versión.'
    : undefined;

  return (
    <div style={{ position: 'relative', display: 'inline-flex', flexDirection: 'column', gap: '4px' }}>
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
        <button
          aria-disabled={!enabled}
          aria-label={`${label} para el entrenamiento ${trainingRunId}`}
          className={`promotion-action-button ${enabled ? 'btn-promotion-active' : 'btn-promotion-disabled'}`}
          disabled={!enabled}
          onClick={handleAction}
          style={{
            padding: '6px 12px',
            fontSize: '12px',
            fontWeight: 600,
            borderRadius: '6px',
            cursor: enabled ? 'pointer' : 'not-allowed',
            border: enabled ? '1px solid #0284c7' : '1px solid #cbd5e1',
            backgroundColor: enabled ? '#0284c7' : '#f1f5f9',
            color: enabled ? '#ffffff' : '#94a3b8',
            transition: 'all 0.15s ease-in-out',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
          }}
          title={tooltipText}
          type="button"
        >
          {loading ? (
            <span className="spinner" style={{ display: 'inline-block', width: '12px', height: '12px', border: '2px solid #ffffff', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          ) : null}
          {label}
        </button>

        {hasBlockers ? (
          <button
            aria-expanded={showBlockers}
            aria-label="Ver motivos de bloqueo de promoción"
            onClick={() => setShowBlockers(!showBlockers)}
            style={{
              background: 'none',
              border: 'none',
              color: '#dc2626',
              cursor: 'pointer',
              fontSize: '13px',
              padding: '2px 4px',
            }}
            title="Ver causas de no disponibilidad"
            type="button"
          >
            ⚠️
          </button>
        ) : null}
      </div>

      {showBlockers && hasBlockers ? (
        <div
          role="status"
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            zIndex: 30,
            width: '240px',
            padding: '8px 12px',
            backgroundColor: '#fef2f2',
            border: '1px solid #fca5a5',
            borderRadius: '6px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            fontSize: '11px',
            color: '#991b1b',
            marginTop: '4px',
          }}
        >
          <strong>Motivos de no disponibilidad:</strong>
          <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px' }}>
            {blockers.map((reason, idx) => (
              <li key={idx}>{translateBlocker(reason)}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {errorMessage ? (
        <span style={{ fontSize: '11px', color: '#dc2626', fontWeight: 500 }}>
          {errorMessage}
        </span>
      ) : null}
    </div>
  );
}
