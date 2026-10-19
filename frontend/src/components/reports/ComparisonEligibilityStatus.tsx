import type { ComparisonEligibility } from '../../types/scientificRead';

export function ComparisonEligibilityStatus({ eligibility }: { eligibility?: ComparisonEligibility | null }) {
  if (!eligibility) return <p role="status">Elegibilidad no disponible. No seleccionable.</p>;
  const error = eligibility.reasons.some(reason => reason.code === 'ERROR_DE_CONSULTA');
  return <div role={error ? 'alert' : 'status'}>
    <p>{(['train', 'evaluate', 'explain'] as const).map(stage =>
      `${stage.toUpperCase()} ${eligibility[stage] === true ? '✓' : eligibility[stage] === null ? 'Error' : '—'}`).join(' · ')}
      {' · '}{eligibility.eligible ? 'Seleccionable' : 'No seleccionable'}</p>
    {eligibility.reasons.length > 0 && <p>{eligibility.reasons.map(reason => reason.message).join(' ')}</p>}
  </div>;
}
