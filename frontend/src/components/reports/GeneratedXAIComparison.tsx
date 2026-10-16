import { useExplainGeneration } from '../../hooks/useExplainGeneration';
import type { XAIComparison } from './xai/comparison';
import { XAIComparisonViewer } from './XAIComparisonViewer';

export function GeneratedXAIComparison({comparison, datasource}: {comparison: XAIComparison; datasource: string}) {
  const generation = useExplainGeneration(comparison);
  return <section className="ds-report">
    <button className="ds-button" type="button" disabled={!generation.canGenerate} onClick={() => { void generation.generateAll(); }}>
      {generation.submitting ? 'Preparando EXPLAIN…' : 'Generar explicabilidad completa'}
    </button>
    {generation.error && <p role="alert">{generation.error}</p>}
    <XAIComparisonViewer comparison={generation.comparison} datasource={datasource} generation={generation.generation} />
  </section>;
}
