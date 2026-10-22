import { useExplainGeneration } from '../../hooks/useExplainGeneration';
import { XAI_LABELS, type XAIComparison } from './xai/comparison';
import { XAIComparisonViewer } from './XAIComparisonViewer';

export function GeneratedXAIComparison({comparison, datasource, active, onEvidenceChange, lazy, authorized, blocked}: {comparison: XAIComparison; datasource: string; active?: boolean; onEvidenceChange?: () => void; lazy?: boolean; authorized?: boolean; blocked?: string | null}) {
  const generation = useExplainGeneration(comparison, active, onEvidenceChange, {lazy, authorized, blocked});
  // Methods still to produce, including those already running, keep the button visible but locked.
  const pending = [...generation.missing, ...generation.inFlight];
  return <section className="ds-report">
    {generation.error && <p role="alert">{generation.error}</p>}
    <XAIComparisonViewer comparison={generation.comparison} datasource={datasource} generation={generation.generation}
      actions={pending.length > 0 && <button className="ds-button" data-variant="primary" type="button" disabled={!generation.canGenerate}
        title={generation.canGenerate ? undefined : generation.generation[pending[0]].reason} onClick={() => { void generation.generateAll(); }}>
        {generation.submitting ? 'Preparando EXPLAIN…' : generation.inFlight.length ? `Generando ${generation.inFlight.map(method => XAI_LABELS[method]).join(' y ')}…` : `Generar faltantes: ${generation.missing.map(method => XAI_LABELS[method]).join(' y ')}`}
      </button>} />
  </section>;
}
