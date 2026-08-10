import { useEffect, useState } from 'react';
import type { SmearAnalysisSummary } from '../../types/cellClassification';
import type { ScientificValidationSession } from '../../types/scientificValidation';
import { api } from '../../services/api';
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
  /** History exposes annotation capabilities only; every pipeline mutation stays disabled. */
  permissions: Pick<SmearAnalysisPermissions, 'canReadValidation' | 'canAnnotateValidation'>;
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
  const annotationPermissions = props.permissions;
  const [validationSession, setValidationSession] = useState<ScientificValidationSession | null>(null);
  const validationMutable = validationSession != null
    && validationSession.status !== 'archived';

  useEffect(() => {
    if (!annotationPermissions.canReadValidation) {
      setValidationSession(null);
      return;
    }
    let active = true;
    api.resolveScientificValidationSession(workflow.detectionRunId, workflow.classificationRunId)
      .then((session) => { if (active) setValidationSession(session); })
      .catch(() => { if (active) setValidationSession(null); });
    return () => { active = false; };
  }, [annotationPermissions.canReadValidation, workflow.classificationRunId, workflow.detectionRunId]);

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
              Vista histórica · Pipeline en solo lectura
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

      <ScientificAnnotations
        title="ANOTACIONES DE LA MUESTRA"
        sessionId={validationSession?.id ?? null}
        targetType="sample"
        targetId={workflow.sampleId ?? null}
        targetContext={`MUESTRA · ${workflow.sampleCode}`}
        canAnnotate={annotationPermissions.canAnnotateValidation && validationMutable}
        readOnly={false}
      />

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
        canAnnotateValidation={annotationPermissions.canAnnotateValidation && validationMutable}
        validationSessionId={validationSession?.id ?? null}
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
