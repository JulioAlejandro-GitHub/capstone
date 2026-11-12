import type { ComparisonEligibility } from '../../types/scientificRead';

/* Traducción de .scc-eligibility (scc-comparison.css): círculo 22px, color por data-state */
const STATE_CLASS: Record<string, string> = {
  eligible: 'text-[#1f7a45]',
  blocked: 'text-[#8a94a8]',
  unknown: 'text-[#8a94a8]',
  error: 'text-[#b42318]',
};
const MARK = 'inline-flex w-fit items-center justify-center h-5.5 w-5.5 border border-current rounded-pill bg-surface text-[13px] font-bold leading-[1] cursor-help';

/** Compact eligibility mark under the selection checkbox; stages and reasons are in its tooltip. */
export function ComparisonEligibilityStatus({ eligibility, onRetry }: { eligibility?: ComparisonEligibility | null; onRetry?: () => void }) {
  if (!eligibility) {
    const text = 'Elegibilidad no disponible. No seleccionable.';
    return <span className={`${MARK} ${STATE_CLASS.unknown}`} data-state="unknown" role="status" title={text} aria-label={text}>?</span>;
  }
  const error = eligibility.reasons.some(reason => reason.code === 'ERROR_DE_CONSULTA');
  const text = [
    (['train', 'evaluate', 'explain'] as const).map(stage =>
      `${stage.toUpperCase()}${stage === 'explain' ? ' (opcional)' : ''} ${eligibility[stage] === true ? '✓' : eligibility[stage] === null ? 'Error' : '—'}`).join(' · '),
    eligibility.eligible ? 'Seleccionable' : 'No seleccionable',
    ...eligibility.reasons.map(reason => reason.message),
  ].join(' · ');
  if (error && onRetry) {
    return <span role="alert"><button type="button" className={`${MARK} ${STATE_CLASS.error} cursor-pointer p-0` } data-state="error" title={`${text} · Reintentar elegibilidad`}
      aria-label={`${text}. Reintentar elegibilidad`} onClick={onRetry}>↻</button></span>;
  }
  const state = error ? 'error' : eligibility.eligible ? 'eligible' : 'blocked';
  return <span className={`${MARK} ${STATE_CLASS[state]}`} data-state={state}
    role={error ? 'alert' : 'status'} title={text} aria-label={text}>{eligibility.eligible ? '✓' : '⊘'}</span>;
}
