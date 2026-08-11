import type {
  CellClassificationRunDetail,
  CellPredictionDetail,
  CellPredictionSummary,
} from '../../types/cellClassification';
import { CaseExplainabilityView } from '../explainability/CaseExplainabilityView';
import { toSmearCellExplainabilityCase } from '../explainability/explainabilityCaseAdapters';

export function CellClassificationAuditModal({
  prediction,
  run,
  onClose,
  canGenerate,
  onGenerate,
}: {
  prediction: CellPredictionSummary | CellPredictionDetail;
  run: CellClassificationRunDetail | null;
  onClose: () => void;
  canGenerate: boolean;
  onGenerate: (regenerate: boolean) => Promise<import('../../types/cellClassification').CellExplanation>;
}) {
  return (
    <CaseExplainabilityView
      case={toSmearCellExplainabilityCase(prediction, run)}
      onClose={onClose}
      canGenerate={canGenerate}
      onGenerate={async (regenerate) => {
        const explanation = await onGenerate(regenerate);
        return toSmearCellExplainabilityCase({ ...prediction, explanation, explanation_status: explanation.status }, run);
      }}
    />
  );
}
