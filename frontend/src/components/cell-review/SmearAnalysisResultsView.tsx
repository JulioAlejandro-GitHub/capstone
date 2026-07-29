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

export type SmearAnalysisActions = {
  onBack: () => void;
  backLabel: string;
  onRefresh?: () => void;
  onImageChange?: (id: string | null) => void;
  onDetectionChange?: (id: string | null) => void;
  onPredictionChange?: (id: string | null) => void;
};

type SmearAnalysisResultsViewProps = {
  mode: SmearAnalysisViewMode;
  workflow: SmearAnalysisViewModel;
  permissions: SmearAnalysisPermissions;
  actions: SmearAnalysisActions;
};

const sections = [
  ['cell-image-panel', 'Imagen completa'],
  ['cell-summary-panel', 'Calidad y resumen'],
  ['cell-gallery-panel', 'Revisión celular'],
  ['cell-experimental-summary-heading', 'Resultado experimental'],
] as const;

const safeDate = (value?: string | null) => {
  if (!value) return 'Fecha no disponible';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Fecha no disponible' : date.toLocaleString();
};

export function SmearAnalysisResultsView({
  mode,
  workflow,
  permissions,
  actions,
}: SmearAnalysisResultsViewProps) {
  const focusSection = (id: string) => {
    const target = document.getElementById(id);
    target?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    const focusable = target?.querySelector<HTMLElement>('button, select, input, [tabindex="0"]');
    focusable?.focus({ preventScroll: true });
  };

  return (
    <section className="smear-results-view" data-view-mode={mode}>
      <header className="smear-results-header smear-glass-panel">
        <div className="smear-results-identity">
          <button
            type="button"
            className="smear-glass-button smear-results-back"
            onClick={actions.onBack}
            aria-label={actions.backLabel}
          >
            ←
          </button>
          <div>
            <p>Análisis de frotis</p>
            <h1>{workflow.subjectCode}</h1>
            <span>{workflow.sampleCode} · {workflow.analysisRunCode}</span>
          </div>
        </div>
        <nav className="smear-results-nav" aria-label="Secciones del análisis">
          {sections.map(([id, label], index) => (
            <button
              key={id}
              type="button"
              aria-current={index === 2 ? 'step' : undefined}
              onClick={() => focusSection(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="smear-results-actions">
          {mode === 'history' ? (
            <strong className="smear-status-badge">Vista histórica · Solo lectura</strong>
          ) : null}
          {actions.onRefresh ? (
            <button type="button" className="smear-glass-button" onClick={actions.onRefresh}>
              Actualizar
            </button>
          ) : null}
          <dl>
            <div><dt>Estado</dt><dd>{workflow.status}</dd></div>
            <div><dt>Modelo</dt><dd>{workflow.modelName ?? 'Sin clasificación'} {workflow.modelVersion ?? ''}</dd></div>
            <div><dt>Fecha</dt><dd>{safeDate(workflow.createdAt)}</dd></div>
          </dl>
        </div>
      </header>

      <CellReviewWorkspace
        detectionRunId={workflow.detectionRunId}
        classificationRunId={workflow.classificationRunId}
        initialClassificationSummary={workflow.classificationSummary}
        initialMicroscopyImageId={workflow.microscopyImageId}
        initialSelectedDetectionId={workflow.selectedDetectionId}
        initialSelectedPredictionId={workflow.selectedPredictionId}
        canReview={mode === 'live' && permissions.canReviewDetection}
        canExplain={mode === 'live' && permissions.canExplain}
        canClassificationReview={mode === 'live' && permissions.canReviewClassification}
        readOnly={mode === 'history'}
        onClose={actions.onBack}
        closeLabel={actions.backLabel}
        onMicroscopyImageChange={actions.onImageChange}
        onSelectedDetectionChange={actions.onDetectionChange}
        onSelectedPredictionChange={actions.onPredictionChange}
      />
    </section>
  );
}
