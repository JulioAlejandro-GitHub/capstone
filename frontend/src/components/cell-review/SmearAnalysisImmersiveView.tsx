import type { SmearAnalysisSummary } from '../../types/cellClassification';
import { CellReviewWorkspace } from './CellReviewWorkspace';
import { ScientificAnnotations } from './ScientificAnnotations';

export type SmearAnalysisViewMode = 'live' | 'history';

export type SmearAnalysisViewModel = {
  subjectCode: string;
  sampleCode: string;
  analysisRunCode: string;
  analysisRunId?: string | null;
  sampleId?: string | null;
  status: string;
  modelName?: string | null;
  modelVersion?: string | null;
  createdAt?: string | null;
  detectionRunId: string;
  classificationRunId?: string | null;
  classificationSummary?: SmearAnalysisSummary | null;
  microscopyImageId?: string | null;
  selectedDetectionId?: string | null;
  selectedPredictionId?: string | null;
};

export type SmearAnalysisPermissions = {
  canReviewDetection: boolean;
  canExplain: boolean;
  canReviewClassification: boolean;
  canReadValidation: boolean;
  canAnnotateValidation: boolean;
};

/** Navigation and selection callbacks are safe in both live and historical views. */
export type SmearAnalysisActions = {
  onBack: () => void;
  backLabel: string;
  onRefresh?: () => void;
  onImageChange?: (id: string | null) => void;
  onDetectionChange?: (id: string | null) => void;
  onPredictionChange?: (id: string | null) => void;
};

type SharedSmearAnalysisProps = {
  workflow: SmearAnalysisViewModel;
  actions: SmearAnalysisActions;
};

export type SmearAnalysisLiveViewProps = SharedSmearAnalysisProps & {
  mode: 'live';
  permissions: SmearAnalysisPermissions;
};

export type SmearAnalysisHistoryViewProps = SharedSmearAnalysisProps & {
  mode: 'history';
  permissions: SmearAnalysisPermissions;
};

export type SmearAnalysisImmersiveViewProps =
  | SmearAnalysisLiveViewProps
  | SmearAnalysisHistoryViewProps;

/** @deprecated Use SmearAnalysisImmersiveViewProps. */
export type SmearAnalysisResultsViewProps = SmearAnalysisImmersiveViewProps;

export function SmearAnalysisImmersiveView(props: SmearAnalysisImmersiveViewProps) {
  const { mode, workflow, actions } = props;
  const modeLabel = mode === 'history' ? 'Histórico' : 'En vivo';
  const { permissions } = props;

  return (
    <section
      className="smear-analysis-immersive smear-results-view"
      data-view-mode={mode}
      aria-label={`Análisis de frotis · ${modeLabel}`}
    >
      <ScientificAnnotations
        title="ANOTACIONES DE LA MUESTRA"
        sessionId={null}
        targetType="sample"
        targetId={permissions.canReadValidation ? workflow.sampleId ?? null : null}
        targetContext={`MUESTRA · ${workflow.sampleCode}`}
        canAnnotate={permissions.canAnnotateValidation}
      />

      <CellReviewWorkspace
        detectionRunId={workflow.detectionRunId}
        classificationRunId={workflow.classificationRunId}
        initialClassificationSummary={workflow.classificationSummary}
        initialMicroscopyImageId={workflow.microscopyImageId}
        initialSelectedDetectionId={workflow.selectedDetectionId}
        initialSelectedPredictionId={workflow.selectedPredictionId}
        canReview={permissions.canReviewDetection}
        canExplain={permissions.canExplain}
        canClassificationReview={permissions.canReviewClassification}
        canAnnotateValidation={permissions.canAnnotateValidation}
        canReadValidationAnnotations={permissions.canReadValidation}
        validationSessionId={null}
        onClose={actions.onBack}
        closeLabel={actions.backLabel}
        onMicroscopyImageChange={actions.onImageChange}
        onSelectedDetectionChange={actions.onDetectionChange}
        onSelectedPredictionChange={actions.onPredictionChange}
      />

      <p className="smear-analysis-disclaimer smear-results-disclaimer" role="note">
        El resultado es experimental, requiere revisión experta y no constituye un diagnóstico clínico.
      </p>
    </section>
  );
}
