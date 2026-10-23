import { useExplainGeneration } from '../../hooks/useExplainGeneration';
import { XAI_LABELS, type XAIComparison } from './xai/comparison';
import { XAIComparisonViewer } from './XAIComparisonViewer';

const listText = (items: string[]) => items.length > 1 ? `${items.slice(0, -1).join(', ')} y ${items.at(-1)}` : items[0] ?? '';

export function GeneratedXAIComparison({comparison, datasource, active, onEvidenceChange, lazy, authorized, blocked}: {comparison: XAIComparison; datasource: string; active?: boolean; onEvidenceChange?: () => void; lazy?: boolean; authorized?: boolean; blocked?: string | null}) {
  const generation = useExplainGeneration(comparison, active, onEvidenceChange, {lazy, authorized, blocked});
  // Methods still to produce, including those already running, keep the button visible but locked.
  const pending = [...generation.missing, ...generation.inFlight];
  return <section className="ds-report">
    {generation.error && <p role="alert">{generation.error}</p>}
    <XAIComparisonViewer comparison={generation.comparison} datasource={datasource} generation={generation.generation}
      actions={pending.length > 0 && <button className="ds-button" data-variant="primary" type="button" disabled={!generation.canGenerate}
        title={generation.canGenerate ? undefined : generation.generation[pending[0]].reason} onClick={() => { void generation.generateAll(); }}>
        {generation.inFlight.length ? `Generando ${listText(generation.inFlight.map(method => XAI_LABELS[method]))}…` : `Generar faltantes: ${listText(generation.missing.map(method => XAI_LABELS[method]))}`}
      </button>} />
  </section>;
}
