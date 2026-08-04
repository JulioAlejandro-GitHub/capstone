import type { SmearAnalysisSummary } from '../../types/cellClassification';
import { CellReviewWorkspace } from './CellReviewWorkspace';

export type SmearAnalysisViewMode = 'live' | 'history';

export type SmearAnalysisViewModel = {
  subjectCode: string;
  sampleCode: string;
  analysisRunCode: string;
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
  /** Historical callers cannot opt back into mutation capabilities. */
  permissions?: never;
};

export type SmearAnalysisImmersiveViewProps =
  | SmearAnalysisLiveViewProps
  | SmearAnalysisHistoryViewProps;

/** @deprecated Use SmearAnalysisImmersiveViewProps. */
export type SmearAnalysisResultsViewProps = SmearAnalysisImmersiveViewProps;

const safeDate = (value?: string | null) => {
  if (!value) return 'Fecha no disponible';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Fecha no disponible' : date.toLocaleString();
};

export function SmearAnalysisImmersiveView(props: SmearAnalysisImmersiveViewProps) {
  const { mode, workflow, actions } = props;
  const isHistory = mode === 'history';
  const modeLabel = isHistory ? 'Histórico' : 'En vivo';
  const livePermissions = props.mode === 'live' ? props.permissions : null;

  return (
    <section
      className="smear-analysis-immersive smear-results-view"
      data-view-mode={mode}
      aria-label={`Análisis de frotis · ${modeLabel}`}
    >
      <header className="smear-results-header">
        <section
          className="smear-results-identity smear-results-case-panel smear-glass-panel"
          aria-label="Paciente, muestra y ejecución"
        >
          <div>
            <p>Análisis de frotis · {modeLabel}</p>
            <h1 className="smear-results-title">{workflow.analysisRunCode}</h1>
            <dl className="smear-results-case-data">
              <div><dt>Paciente</dt><dd>{workflow.subjectCode}</dd></div>
              <div><dt>Muestra</dt><dd>{workflow.sampleCode}</dd></div>
              <div><dt>Run</dt><dd>{workflow.analysisRunCode}</dd></div>
            </dl>
          </div>
        </section>

        <div className="smear-results-actions smear-glass-panel">
          {isHistory ? (
            <strong className="smear-status-badge" role="status">
              Vista histórica · Solo lectura
            </strong>
          ) : null}
          <dl className="smear-results-run-data">
            <div><dt>Estado</dt><dd>{workflow.status}</dd></div>
            <div>
              <dt>Modelo</dt>
              <dd>{workflow.modelName ?? 'Sin clasificación'} {workflow.modelVersion ?? ''}</dd>
            </div>
            <div><dt>Fecha</dt><dd>{safeDate(workflow.createdAt)}</dd></div>
          </dl>
          {actions.onRefresh ? (
            <button type="button" className="smear-glass-button" onClick={actions.onRefresh}>
              Actualizar
            </button>
          ) : null}
          <button
            type="button"
            className="smear-glass-button smear-results-context-action"
            onClick={actions.onBack}
          >
            {actions.backLabel}
          </button>
        </div>
      </header>

      <CellReviewWorkspace
        detectionRunId={workflow.detectionRunId}
        classificationRunId={workflow.classificationRunId}
        initialClassificationSummary={workflow.classificationSummary}
        initialMicroscopyImageId={workflow.microscopyImageId}
        initialSelectedDetectionId={workflow.selectedDetectionId}
        initialSelectedPredictionId={workflow.selectedPredictionId}
        canReview={livePermissions?.canReviewDetection ?? false}
        canExplain={livePermissions?.canExplain ?? false}
        canClassificationReview={livePermissions?.canReviewClassification ?? false}
        readOnly={isHistory}
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
