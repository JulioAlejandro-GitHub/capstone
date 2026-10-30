import type { ComparisonEligibility } from '../../types/scientificRead';

/** Compact eligibility mark under the selection checkbox; stages and reasons are in its tooltip. */
export function ComparisonEligibilityStatus({ eligibility, onRetry }: { eligibility?: ComparisonEligibility | null; onRetry?: () => void }) {
  if (!eligibility) {
    const text = 'Elegibilidad no disponible. No seleccionable.';
    return <span className="scc-eligibility" data-state="unknown" role="status" title={text} aria-label={text}>?</span>;
  }
  const error = eligibility.reasons.some(reason => reason.code === 'ERROR_DE_CONSULTA');
  const text = [
    (['train', 'evaluate', 'explain'] as const).map(stage =>
      `${stage.toUpperCase()}${stage === 'explain' ? ' (opcional)' : ''} ${eligibility[stage] === true ? '✓' : eligibility[stage] === null ? 'Error' : '—'}`).join(' · '),
    eligibility.eligible ? 'Seleccionable' : 'No seleccionable',
    ...eligibility.reasons.map(reason => reason.message),
  ].join(' · ');
  if (error && onRetry) {
    return <span role="alert"><button type="button" className="scc-eligibility" data-state="error" title={`${text} · Reintentar elegibilidad`}
      aria-label={`${text}. Reintentar elegibilidad`} onClick={onRetry}>↻</button></span>;
  }
  return <span className="scc-eligibility" data-state={error ? 'error' : eligibility.eligible ? 'eligible' : 'blocked'}
    role={error ? 'alert' : 'status'} title={text} aria-label={text}>{eligibility.eligible ? '✓' : '⊘'}</span>;
}
