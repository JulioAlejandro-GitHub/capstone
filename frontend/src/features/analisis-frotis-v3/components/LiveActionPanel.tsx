import { useState } from 'react';

import type { LiveAction, LiveActionKind } from '../adapters/liveActions';

/**
 * Acción humana pendiente del análisis en curso. Cada botón invoca una
 * operación del workflow existente; este panel no ejecuta lógica científica.
 */
export function LiveActionPanel({
  action,
  busy,
  failureMessage,
  warningCodes,
  onRun,
  onDecideWarning,
}: {
  action: LiveAction;
  busy: boolean;
  failureMessage: string | null;
  warningCodes: readonly string[];
  onRun: (kind: LiveActionKind) => void;
  onDecideWarning: (decision: 'approve_with_warnings' | 'reject', comment: string) => void;
}) {
  const [comment, setComment] = useState('');
  const [confirmingReject, setConfirmingReject] = useState(false);
  const hasComment = Boolean(comment.trim());

  return (
    <section className="frotis-v3-panel" aria-label={action.title}>
      <h2>{action.title}</h2>
      {failureMessage ? <p className="frotis-v3-panel-failure" role="alert">{failureMessage}</p> : null}
      <p>{action.detail}</p>

      {action.kind === 'decide_quality_warning' && warningCodes.length ? (
        <p>Indicadores: {warningCodes.join(', ')}</p>
      ) : null}

      {!action.allowed ? <p role="status">{action.denial}</p> : null}

      {action.allowed && action.kind === 'decide_quality_warning' ? (
        <div className="frotis-v3-panel-form">
          <label htmlFor="frotis-v3-quality-comment">Comentario técnico obligatorio</label>
          <textarea
            id="frotis-v3-quality-comment"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
          {confirmingReject ? (
            <div className="frotis-v3-panel-buttons">
              <button
                type="button"
                className="frotis-v3-button frotis-v3-button--danger"
                disabled={busy || !hasComment}
                onClick={() => { onDecideWarning('reject', comment); setConfirmingReject(false); }}
              >
                Confirmar bloqueo técnico
              </button>
              <button type="button" className="frotis-v3-button" onClick={() => setConfirmingReject(false)}>
                Cancelar
              </button>
            </div>
          ) : (
            <div className="frotis-v3-panel-buttons">
              <button
                type="button"
                className="frotis-v3-button frotis-v3-button--primary"
                disabled={busy || !hasComment}
                onClick={() => onDecideWarning('approve_with_warnings', comment)}
              >
                {action.buttonLabel}
              </button>
              <button
                type="button"
                className="frotis-v3-button"
                disabled={busy || !hasComment}
                onClick={() => setConfirmingReject(true)}
              >
                Bloquear análisis
              </button>
            </div>
          )}
        </div>
      ) : null}

      {action.allowed && action.kind !== 'decide_quality_warning' ? (
        <div className="frotis-v3-panel-buttons">
          <button
            type="button"
            className="frotis-v3-button frotis-v3-button--primary"
            disabled={busy}
            onClick={() => onRun(action.kind)}
          >
            {action.buttonLabel}
          </button>
        </div>
      ) : null}
    </section>
  );
}
