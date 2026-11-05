import { useAuth } from '../../auth';
import { useExplainExecutor } from '../../hooks/useExplainExecutor';
import { useExplainGeneration } from '../../hooks/useExplainGeneration';
import { XAI_LABELS, type XAIComparison } from './xai/comparison';
import { XAIComparisonViewer } from './XAIComparisonViewer';

const listText = (items: string[]) => items.length > 1 ? `${items.slice(0, -1).join(', ')} y ${items.at(-1)}` : items[0] ?? '';

export function GeneratedXAIComparison({comparison, datasource, active, onEvidenceChange, lazy, authorized, blocked, variant, image, expandSignal}: {comparison: XAIComparison; datasource: string; active?: boolean; onEvidenceChange?: () => void; lazy?: boolean; authorized?: boolean; blocked?: string | null; variant?: 'inline' | 'expanded' | 'toolbar' | 'modal'; image?: string; expandSignal?: number}) {
  // Regla de usabilidad: las acciones de la «Vista ampliada» están habilitadas salvo que el host diga lo contrario
  // (authorized/blocked explícitos) o los datos lo impidan. Sin indicación, valen el permiso del usuario y el ejecutor EXPLAIN.
  const { user } = useAuth();
  const derived = authorized === undefined;
  const permitted = Boolean(user?.permissions?.includes('scientific.cell_classification.explain'));
  const executor = useExplainExecutor(Boolean(lazy && derived && permitted));
  const generation = useExplainGeneration(comparison, active, onEvidenceChange, {lazy,
    authorized: derived ? permitted : authorized,
    blocked: blocked !== undefined ? blocked : derived && lazy && permitted ? executor.blocked : blocked});
  // Methods still to produce, including those already running, keep the button visible but locked.
  const pending = [...generation.missing, ...generation.inFlight];
  return <section className="ds-report">
    {generation.error && <p role="alert">{generation.error}</p>}
    <XAIComparisonViewer comparison={generation.comparison} datasource={datasource} generation={generation.generation} variant={variant} image={image} expandSignal={expandSignal}
      actions={pending.length > 0 && <button className="ds-button" data-variant="primary" type="button" disabled={!generation.canGenerate}
        title={generation.canGenerate ? undefined : generation.generation[pending[0]].reason} onClick={() => { void generation.generateAll(); }}>
        {generation.inFlight.length ? `Generando ${listText(generation.inFlight.map(method => XAI_LABELS[method]))}…` : `Generar faltantes: ${listText(generation.missing.map(method => XAI_LABELS[method]))}`}
      </button>} />
  </section>;
}
