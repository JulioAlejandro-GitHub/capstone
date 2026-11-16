import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useAuth } from '../../../auth';
import { useSmearAnalysisWorkflow } from '../../../hooks/useSmearAnalysisWorkflow';
import { routes, withAllowedQuery } from '../../../router';
import {
  analysisFromLive,
  stageLabel,
  type MicroscopeAnalysis,
} from '../adapters/analysisModel';
import {
  canStartAnalysis,
  capabilitiesFromPermissions,
  liveActionFor,
  missingIntakePermissions,
  type LiveActionKind,
} from '../adapters/liveActions';
import { microscopeAnalysisPath } from '../routes';
import { IntakeStage } from './IntakeStage';
import { LiveActionPanel } from './LiveActionPanel';
import {
  MicroscopeWorkspace,
  type CellSelection,
  type WorkspaceNotice,
  type WorkspaceTone,
} from './MicroscopeWorkspace';
import { WorkspaceLinks } from './WorkspaceLinks';
import { WorkspaceMessage } from './WorkspaceMessage';

/** Identificadores que el workflow existente escribe en la URL para poder recuperarse. */
const WORKFLOW_PARAMS = [
  'batch',
  'analysis',
  'queue',
  'detection',
  'classification',
  'image',
  'selected_detection',
  'selected_prediction',
];

const toneFor = (analysis: MicroscopeAnalysis, busy: boolean): WorkspaceTone => {
  if (analysis.phase === 'halted') return 'blocked';
  if (analysis.phase === 'attention') return 'warning';
  if (analysis.phase === 'technical_review') return busy ? 'progress' : 'warning';
  return ['classification_completed', 'review_ready'].includes(analysis.stage) ? 'ok' : 'warning';
};

/**
 * Acceso A — nuevo análisis. Incorpora imágenes y acompaña la revisión técnica
 * real dentro del mismo workspace. La orquestación científica es la del
 * workflow existente (`useSmearAnalysisWorkflow`): v3 no define un pipeline propio.
 */
export function LiveAnalysisSession({
  routeAnalysisId,
  onClaim,
}: {
  /** `:analysisId` de la URL, o `null` en la entrada `/frotis/microscopio`. */
  routeAnalysisId: string | null;
  /** Informa qué análisis pertenece a esta sesión en curso (o `null` al reiniciarla). */
  onClaim: (analysisId: string | null) => void;
}) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const controller = useSmearAnalysisWorkflow();
  const { stage, identifiers, snapshot, failure, recovering, busy, previewUrl } = controller;
  const permissions = useMemo(() => new Set(user?.permissions ?? []), [user?.permissions]);
  const capabilities = useMemo(() => capabilitiesFromPermissions(permissions), [permissions]);
  const datasource = searchParams.get('datasource');
  const analysisRunId = identifiers.analysisRunId;
  const hasWorkflowParams = WORKFLOW_PARAMS.some((key) => searchParams.has(key));
  const isUploadFailure = stage === 'error' && failure?.step === 'upload' && !identifiers.ingestionBatchId;

  // La sesión reclama su análisis en cuanto el backend devuelve el identificador,
  // y lo libera cuando el workflow vuelve a su estado inicial.
  const claimed = useRef<string | null>(null);
  useEffect(() => {
    if (analysisRunId) {
      claimed.current = analysisRunId;
      onClaim(analysisRunId);
    } else if (claimed.current) {
      claimed.current = null;
      onClaim(null);
    }
  }, [analysisRunId, onClaim]);

  // Ruta canónica: al existir el análisis, la URL pasa a /frotis/microscopio/:analysisId
  // sin desmontar el workspace. Solo se canoniza una URL escrita por el propio workflow.
  useEffect(() => {
    if (!analysisRunId || routeAnalysisId === analysisRunId) return;
    if (searchParams.get('analysis') !== analysisRunId) return;
    onClaim(analysisRunId);
    navigate(`${microscopeAnalysisPath(analysisRunId)}?${searchParams.toString()}`, { replace: true });
  }, [analysisRunId, navigate, onClaim, routeAnalysisId, searchParams]);

  // Entrada limpia a /frotis/microscopio con un estado residual sin lote (por
  // ejemplo, una recuperación fallida): se vuelve a la carga de imágenes.
  const { newAnalysis } = controller;
  useEffect(() => {
    if (routeAnalysisId || hasWorkflowParams || busy || recovering) return;
    if (stage !== 'setup' && !identifiers.ingestionBatchId && !isUploadFailure) newAnalysis();
  }, [
    busy,
    hasWorkflowParams,
    identifiers.ingestionBatchId,
    isUploadFailure,
    newAnalysis,
    recovering,
    routeAnalysisId,
    stage,
  ]);

  const startNewAnalysis = useCallback(() => {
    // Navegar a la entrada sin identificadores hace que el workflow existente
    // se reinicie por sí mismo; no se borra ningún recurso persistido.
    navigate(withAllowedQuery(routes.smearMicroscope, { datasource }));
  }, [datasource, navigate]);

  const run = useCallback((kind: LiveActionKind) => {
    if (kind === 'requeue_quality') void controller.requeueQuality();
    else if (kind === 'execute_requeued_quality') void controller.executeRequeuedQuality();
    else if (kind === 'retry_failed_step') void controller.retryFailedStep();
    else if (kind === 'continue' || kind === 'verify_productive_model') void controller.continueWorkflow();
    else if (kind === 'new_analysis') startNewAnalysis();
  }, [controller, startNewAnalysis]);

  const { selectImage, selectDetection, selectPrediction } = controller;
  const chooseImage = useCallback((imageId: string) => {
    selectImage(imageId);
    selectDetection(null);
    selectPrediction(null);
  }, [selectDetection, selectImage, selectPrediction]);
  const chooseCell = useCallback((next: CellSelection) => {
    selectDetection(next.detectionId);
    selectPrediction(next.predictionId);
  }, [selectDetection, selectPrediction]);
  const selection = useMemo<CellSelection>(() => ({
    detectionId: identifiers.selectedDetectionId,
    predictionId: identifiers.selectedPredictionId,
  }), [identifiers.selectedDetectionId, identifiers.selectedPredictionId]);

  if (recovering) {
    return (
      <MicroscopeWorkspace
        analysis={null}
        status={{ label: 'Recuperando análisis', tone: 'progress' }}
        headerActions={<WorkspaceLinks showNewAnalysis />}
        takeover={(
          <WorkspaceMessage
            kind="loading"
            title="Recuperando análisis…"
            detail="Consultando el estado persistido sin repetir operaciones."
          />
        )}
      />
    );
  }

  if (stage === 'setup' || isUploadFailure) {
    return (
      <MicroscopeWorkspace
        analysis={null}
        status={{ label: 'Nuevo análisis', tone: 'idle' }}
        headerActions={<WorkspaceLinks showNewAnalysis={false} />}
        takeover={(
          <IntakeStage
            files={controller.selectedFiles}
            busy={busy}
            canStart={canStartAnalysis(permissions)}
            missingPermissions={missingIntakePermissions(permissions)}
            errorMessage={isUploadFailure ? failure?.message ?? null : null}
            onFilesChange={controller.setSelectedFiles}
            onStart={controller.start}
          />
        )}
      />
    );
  }

  const analysis = analysisFromLive(stage, snapshot, identifiers);
  const imageIds = analysis.images.map((image) => image.id);
  const activeImageId = identifiers.microscopyImageId && imageIds.includes(identifiers.microscopyImageId)
    ? identifiers.microscopyImageId
    : imageIds[0] ?? null;
  const queueStatus = snapshot.queueItem?.status ?? null;
  const action = busy ? null : liveActionFor({
    stage,
    failureStep: failure?.step ?? null,
    queueStatus,
    hasAnalysisRun: Boolean(snapshot.analysisRun),
    hasQueueItem: Boolean(snapshot.queueItem),
    readyForAnalysis: Boolean(snapshot.analysisRun?.ready_for_analysis),
    hasDetectionRun: Boolean(snapshot.detectionRun),
  }, capabilities);
  const notices: WorkspaceNotice[] = [];
  if (failure && !action) {
    notices.push({ id: 'failure', tone: 'warning', text: failure.message });
  }
  if (stage === 'quality_failed') {
    notices.push({
      id: 'quality',
      tone: 'blocked',
      text: 'El control técnico bloqueó el análisis: la imagen puede inspeccionarse, pero no se ejecutarán detección ni clasificación.',
    });
  }

  return (
    <MicroscopeWorkspace
      analysis={analysis}
      status={{ label: stageLabel(stage), tone: toneFor(analysis, busy) }}
      activeImageId={activeImageId}
      onImageSelect={chooseImage}
      selection={selection}
      onSelectCell={chooseCell}
      // La vista previa local corresponde al primer archivo incorporado.
      localPreview={previewUrl ? { imageId: imageIds[0] ?? null, url: previewUrl } : null}
      scanning={busy && analysis.phase === 'technical_review'}
      notices={notices}
      headerActions={<WorkspaceLinks showNewAnalysis />}
      actions={action ? (
        <LiveActionPanel
          action={action}
          busy={busy}
          failureMessage={failure?.message ?? null}
          warningCodes={snapshot.analysisRun?.images[0]?.warning_codes ?? []}
          onRun={run}
          onDecideWarning={(decision, comment) => void controller.decideWarning(decision, comment)}
        />
      ) : null}
    />
  );
}
