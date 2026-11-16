import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { isValidPublicId, routes, withAllowedQuery } from '../../../router';
import {
  analysisFromWorkflow,
  failureMessageFromWorkflow,
  isActivelyProcessing,
  stageLabel,
  type MicroscopeAnalysis,
} from '../adapters/analysisModel';
import { describeDeepLinkIssue, readDeepLink, resolveActiveImage } from '../adapters/deepLink';
import { isResumableStage } from '../adapters/liveActions';
import { useExistingAnalysis } from '../hooks/useExistingAnalysis';
import { readAnalysisContext, writeAnalysisContext } from '../state/presentationStorage';
import {
  MicroscopeWorkspace,
  type CellSelection,
  type WorkspaceNotice,
  type WorkspaceTone,
} from './MicroscopeWorkspace';
import { WorkspaceLinks } from './WorkspaceLinks';
import { WorkspaceMessage } from './WorkspaceMessage';

const toneFor = (analysis: MicroscopeAnalysis): WorkspaceTone => {
  if (analysis.phase === 'halted') return 'blocked';
  if (analysis.phase === 'attention') return 'warning';
  if (analysis.phase === 'technical_review') {
    return isActivelyProcessing(analysis.stage) ? 'progress' : 'warning';
  }
  return ['classification_completed', 'review_ready'].includes(analysis.stage) ? 'ok' : 'warning';
};

const phaseNotice = (analysis: MicroscopeAnalysis, failure: string | null): WorkspaceNotice | null => {
  const { stage, phase } = analysis;
  if (stage === 'quality_failed') {
    return {
      id: 'phase',
      tone: 'blocked',
      text: 'El control técnico bloqueó este análisis: la imagen puede inspeccionarse, pero no existen detección ni clasificación.',
    };
  }
  if (phase === 'halted') {
    return { id: 'phase', tone: 'blocked', text: failure ?? 'El análisis terminó con error.' };
  }
  if (phase === 'attention') {
    return {
      id: 'phase',
      tone: 'warning',
      text: 'El control técnico dejó una advertencia que requiere una decisión autorizada antes de detectar células.',
    };
  }
  if (stage === 'awaiting_productive_model') {
    return {
      id: 'phase',
      tone: 'warning',
      text: 'No hay un modelo productivo válido: las detecciones existen, pero no han sido clasificadas.',
    };
  }
  if (stage === 'classification_failed') {
    return { id: 'phase', tone: 'warning', text: failure ?? 'La clasificación terminó con error.' };
  }
  if (phase === 'technical_review' && !isActivelyProcessing(stage)) {
    return {
      id: 'phase',
      tone: 'warning',
      text: `Este análisis quedó en «${stageLabel(stage)}» y no está avanzando en este momento.`,
    };
  }
  return null;
};

/**
 * Acceso B — análisis existente. Recupera el análisis por `analysisId`, muestra
 * el frotis directamente y nunca solicita carga ni repite la validación técnica.
 */
export function ExistingAnalysisSession({
  analysisId,
  onResume,
}: {
  analysisId: string;
  onResume: (analysisId: string) => void;
}) {
  const { state, refresh } = useExistingAnalysis(analysisId);
  const [searchParams, setSearchParams] = useSearchParams();
  const datasource = searchParams.get('datasource');
  const request = useMemo(() => readDeepLink(searchParams, isValidPublicId), [searchParams]);
  const [persistedContext] = useState(() => readAnalysisContext(analysisId));

  // Copia síncrona de la query: cambios de imagen y de célula emitidos en el
  // mismo ciclo se combinan en lugar de pisarse.
  const queryRef = useRef(searchParams);
  useEffect(() => {
    queryRef.current = searchParams;
  }, [searchParams]);
  const patchQuery = useCallback((patch: Record<string, string | null>) => {
    const next = new URLSearchParams(queryRef.current);
    Object.entries(patch).forEach(([key, value]) => {
      if (value) next.set(key, value);
      else next.delete(key);
    });
    queryRef.current = next;
    setSearchParams(next, { replace: true });
  }, [setSearchParams]);

  const selectImage = useCallback((imageId: string) => {
    // La selección celular pertenece a una imagen: al cambiarla se limpia.
    patchQuery({ image: imageId, selected_detection: null, selected_prediction: null });
    writeAnalysisContext(analysisId, { imageId });
  }, [analysisId, patchQuery]);
  const selectCell = useCallback((selection: CellSelection) => {
    patchQuery({ selected_detection: selection.detectionId, selected_prediction: selection.predictionId });
  }, [patchQuery]);
  const selection = useMemo<CellSelection>(
    () => ({ detectionId: request.detectionId, predictionId: request.predictionId }),
    [request.detectionId, request.predictionId],
  );

  const links = <WorkspaceLinks showNewAnalysis />;

  if (state.status === 'loading') {
    return (
      <MicroscopeWorkspace
        analysis={null}
        status={{ label: 'Recuperando análisis', tone: 'progress' }}
        headerActions={links}
        takeover={<WorkspaceMessage kind="loading" title="Recuperando análisis…" detail="Consultando el estado persistido. No se inicia ningún procesamiento." />}
      />
    );
  }

  if (state.status === 'unavailable') {
    return (
      <MicroscopeWorkspace
        analysis={null}
        status={{ label: 'Análisis no disponible', tone: 'blocked' }}
        headerActions={links}
        takeover={(
          <WorkspaceMessage kind="problem" title="Análisis no disponible" detail={state.message}>
            {state.reason === 'error' ? (
              <button type="button" className="frotis-v3-button frotis-v3-button--primary" onClick={refresh}>
                Reintentar
              </button>
            ) : null}
            <Link className="frotis-v3-button" to={withAllowedQuery(routes.smearHistory, { datasource })}>
              Volver al historial
            </Link>
          </WorkspaceMessage>
        )}
      />
    );
  }

  const analysis = analysisFromWorkflow(state.response);
  const failure = failureMessageFromWorkflow(state.response);
  const resolution = resolveActiveImage({
    urlImageId: request.imageId,
    persistedImageId: persistedContext.imageId ?? null,
    imageIds: analysis.images.map((image) => image.id),
  });
  const issues = resolution.issue ? [...request.issues, resolution.issue] : request.issues;
  const notice = phaseNotice(analysis, failure);
  const notices: WorkspaceNotice[] = [
    ...(notice ? [notice] : []),
    ...issues.map((issue) => ({
      id: `link-${issue.param}`,
      tone: 'warning' as const,
      text: describeDeepLinkIssue(issue),
    })),
  ];
  const pending = analysis.phase !== 'microscope' || analysis.stage === 'awaiting_productive_model'
    || analysis.stage === 'classification_failed';
  const resumable = isResumableStage(analysis.stage) && Boolean(analysis.analysisRunId);

  return (
    <MicroscopeWorkspace
      analysis={analysis}
      status={{ label: stageLabel(analysis.stage), tone: toneFor(analysis) }}
      activeImageId={resolution.imageId}
      onImageSelect={selectImage}
      selection={selection}
      onSelectCell={selectCell}
      scanning={isActivelyProcessing(analysis.stage)}
      notices={notices}
      headerActions={links}
      actions={pending ? (
        <section className="frotis-v3-panel" aria-label="Estado del análisis">
          <h2>{stageLabel(analysis.stage)}</h2>
          <p>
            {resumable
              ? 'Reanudar recupera el estado persistido y ofrece la acción manual que corresponde. No ejecuta nada por sí solo.'
              : 'Se muestra el estado real informado por el backend.'}
          </p>
          <div className="frotis-v3-panel-buttons">
            {resumable ? (
              <button
                type="button"
                className="frotis-v3-button frotis-v3-button--primary"
                onClick={() => onResume(analysisId)}
              >
                Reanudar en el microscopio
              </button>
            ) : null}
            <button type="button" className="frotis-v3-button" disabled={state.refreshing} onClick={refresh}>
              {state.refreshing ? 'Actualizando…' : 'Actualizar estado'}
            </button>
          </div>
        </section>
      ) : null}
    />
  );
}
