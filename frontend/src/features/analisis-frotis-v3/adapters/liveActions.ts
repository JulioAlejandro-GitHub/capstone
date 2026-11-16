/**
 * Acciones humanas disponibles durante un análisis en curso. Módulo puro.
 *
 * v3 no define un pipeline propio: reutiliza el controlador existente
 * (`useSmearAnalysisWorkflow`) y este adaptador solo decide QUÉ acción de ese
 * controlador corresponde ofrecer y si el rol la autoriza, con las mismas
 * reglas de permisos que el workflow actual.
 */
export type LiveCapabilities = {
  canCreateAnalysis: boolean;
  canCreateQueue: boolean;
  canExecuteQueue: boolean;
  canRetryQueue: boolean;
  canReviewQuality: boolean;
  canExecuteDetection: boolean;
  canExecuteClassification: boolean;
};

/** Permisos que el workflow existente exige para ejecutar «Cargar y analizar». */
export const INTAKE_PERMISSIONS = [
  'scientific.images.register',
  'scientific.analysis.create',
  'scientific.analysis.queue.create',
  'scientific.analysis.queue.execute',
  'scientific.cell_detection.execute',
  'scientific.cell_classification.execute',
] as const;

type PermissionSet = { has(permission: string): boolean };

export const canStartAnalysis = (permissions: PermissionSet) =>
  INTAKE_PERMISSIONS.every((permission) => permissions.has(permission));

export const missingIntakePermissions = (permissions: PermissionSet) =>
  INTAKE_PERMISSIONS.filter((permission) => !permissions.has(permission));

export const capabilitiesFromPermissions = (permissions: PermissionSet): LiveCapabilities => ({
  canCreateAnalysis: permissions.has('scientific.analysis.create'),
  canCreateQueue: permissions.has('scientific.analysis.queue.create'),
  canExecuteQueue: permissions.has('scientific.analysis.queue.execute'),
  canRetryQueue: permissions.has('scientific.analysis.queue.retry'),
  canReviewQuality: permissions.has('scientific.analysis.quality.review'),
  canExecuteDetection: permissions.has('scientific.cell_detection.execute'),
  canExecuteClassification: permissions.has('scientific.cell_classification.execute'),
});

export type LiveActionKind =
  | 'decide_quality_warning'
  | 'requeue_quality'
  | 'execute_requeued_quality'
  | 'retry_failed_step'
  | 'continue'
  | 'verify_productive_model'
  | 'new_analysis';

export type LiveAction = {
  kind: LiveActionKind;
  title: string;
  detail: string;
  buttonLabel: string;
  allowed: boolean;
  /** Mensaje visible cuando el rol no autoriza la acción. */
  denial: string | null;
};

export type LiveActionState = {
  stage: string;
  failureStep: string | null;
  queueStatus: string | null;
  hasAnalysisRun: boolean;
  hasQueueItem: boolean;
  readyForAnalysis: boolean;
  hasDetectionRun: boolean;
};

const action = (
  kind: LiveActionKind,
  title: string,
  detail: string,
  buttonLabel: string,
  allowed: boolean,
  denial: string,
): LiveAction => ({ kind, title, detail, buttonLabel, allowed, denial: allowed ? null : denial });

export function liveActionFor(
  state: LiveActionState,
  capabilities: LiveCapabilities,
): LiveAction | null {
  const { stage, failureStep, queueStatus } = state;

  if (stage === 'awaiting_productive_model') {
    return action(
      'verify_productive_model',
      'Modelo productivo requerido',
      'No se seleccionó un modelo alternativo ni se aplicó un umbral por defecto.',
      'Verificar nuevamente',
      capabilities.canExecuteClassification,
      'Tu rol no permite ejecutar la clasificación celular.',
    );
  }
  if (stage === 'quality_warning') {
    return action(
      'decide_quality_warning',
      'Advertencia técnica',
      'El control técnico requiere una decisión autorizada antes de detectar células.',
      'Aprobar con advertencias',
      capabilities.canReviewQuality,
      'Tu rol puede visualizar el frotis, pero no resolver esta advertencia.',
    );
  }
  if (stage === 'quality_failed') {
    return action(
      'new_analysis',
      'Bloqueo técnico',
      'La detección celular no fue iniciada. La imagen sigue disponible para inspección visual.',
      'Incorporar otra imagen',
      true,
      '',
    );
  }
  if ((stage === 'error' || stage === 'classification_failed') && failureStep) {
    if (failureStep === 'quality' && queueStatus === 'failed') {
      return action(
        'requeue_quality',
        'Control técnico interrumpido',
        'La solicitud de calidad falló. Reingresarla no la ejecuta automáticamente.',
        'Reingresar a cola',
        capabilities.canRetryQueue,
        'Tu rol no permite reingresar solicitudes fallidas a la cola.',
      );
    }
    if (failureStep === 'upload') {
      return action(
        'new_analysis',
        'Carga interrumpida',
        'Los recursos creados correctamente se conservaron.',
        'Incorporar imágenes nuevamente',
        true,
        '',
      );
    }
    const allowed = failureStep === 'analysis'
      ? capabilities.canCreateAnalysis
      : failureStep === 'queue'
        ? capabilities.canCreateQueue
        : failureStep === 'detection'
          ? capabilities.canExecuteDetection
          : failureStep === 'classification'
            ? capabilities.canExecuteClassification
            : failureStep === 'recovery';
    return action(
      'retry_failed_step',
      'Etapa interrumpida',
      'Los recursos creados correctamente permanecen disponibles.',
      'Reintentar desde esta etapa',
      allowed,
      'Tu rol no permite reintentar esta etapa.',
    );
  }
  if (stage === 'quality_queued' && queueStatus === 'queued') {
    return action(
      'execute_requeued_quality',
      'Control técnico en cola',
      'La ejecución del control es una acción manual.',
      'Ejecutar control',
      capabilities.canExecuteQueue,
      'Tu rol no permite ejecutar solicitudes de calidad.',
    );
  }
  const resumable = (
    (stage === 'ingested' && !state.hasQueueItem)
    || (stage === 'creating_analysis' && state.hasAnalysisRun && !state.hasQueueItem)
    || (stage === 'ready_for_detection' && state.readyForAnalysis)
    || (stage === 'classification_pending' && state.hasDetectionRun)
  );
  if (resumable) {
    const allowed = stage === 'ready_for_detection'
      ? capabilities.canExecuteDetection
      : stage === 'classification_pending'
        ? capabilities.canExecuteClassification
        : state.hasAnalysisRun ? capabilities.canCreateQueue : capabilities.canCreateAnalysis;
    return action(
      'continue',
      'Análisis en pausa',
      'Continuar es una acción manual y reutiliza los identificadores persistidos.',
      stage === 'ready_for_detection'
        ? 'Iniciar detección'
        : stage === 'classification_pending' ? 'Iniciar clasificación' : 'Continuar análisis',
      allowed,
      'Tu rol no permite continuar esta etapa.',
    );
  }
  return null;
}

/** Etapas persistidas que admiten reanudar el procesamiento desde un análisis existente. */
export const isResumableStage = (stage: string) => [
  'ingested',
  'creating_analysis',
  'quality_queued',
  'quality_warning',
  'ready_for_detection',
  'classification_pending',
  'awaiting_productive_model',
  'classification_failed',
  'error',
].includes(stage);
