import { useEffect, useMemo, useState } from 'react';

import { useAuth } from '../auth';
import { CellReviewWorkspace } from '../components/cell-review/CellReviewWorkspace';
import {
  useSmearAnalysisWorkflow,
  type SmearWorkflowController,
  type SmearWorkflowFailureStep,
  type SmearWorkflowStage,
} from '../hooks/useSmearAnalysisWorkflow';
import {
  ApiError,
  api,
  type AnalysisEvent,
  type QualityImage,
  type SmearWorkflowResponse,
} from '../services/api';
import { SmearUpload } from './SmearUpload';

type ContextStep = 'upload' | 'quality' | 'detection' | 'review';
type StepState = 'pending' | 'active' | 'complete' | 'warning' | 'failed' | 'locked';
type MobilePane = 'progress' | 'image' | 'cells' | 'detail';
type WorkflowCapabilities = {
  canCreateAnalysis: boolean;
  canCreateQueue: boolean;
  canExecuteQueue: boolean;
  canRetryQueue: boolean;
  canReviewQuality: boolean;
  canExecuteDetection: boolean;
};

const contextSteps: Array<{ id: ContextStep; label: string }> = [
  { id: 'upload', label: 'Carga' },
  { id: 'quality', label: 'Calidad de muestra' },
  { id: 'detection', label: 'Detección' },
  { id: 'review', label: 'Revisión celular' },
];

const stageLabel: Record<SmearWorkflowStage, string> = {
  setup: 'Configuración pendiente',
  uploading: 'Recibiendo imagen',
  ingested: 'Imagen recibida',
  creating_analysis: 'Creando ejecución',
  quality_queued: 'Control en cola',
  quality_processing: 'Control técnico en curso',
  quality_warning: 'Advertencia pendiente',
  quality_failed: 'Bloqueo técnico',
  ready_for_detection: 'Lista para detección',
  detection_processing: 'Detección en curso',
  review_ready: 'Revisión disponible',
  error: 'Interrupción técnica',
};

const activityLabel: Record<SmearWorkflowStage, string> = {
  setup: 'Carga aún no iniciada',
  uploading: 'Verificando integridad del archivo recibido',
  ingested: 'Imagen persistida y lista para crear la ejecución',
  creating_analysis: 'Preparando imagen para el control técnico',
  quality_queued: 'Solicitud de calidad registrada con prioridad normal',
  quality_processing: 'Evaluando nitidez y exposición',
  quality_warning: 'La advertencia requiere una decisión autorizada',
  quality_failed: 'El quality gate bloqueó el análisis',
  ready_for_detection: 'Preparando imagen para detección',
  detection_processing: 'Detectando regiones celulares y generando crops',
  review_ready: 'Detecciones disponibles para revisión',
  error: 'El workflow se detuvo en la etapa fallida',
};

const processingStages: SmearWorkflowStage[] = [
  'uploading',
  'creating_analysis',
  'quality_processing',
  'detection_processing',
];
const knownWorkflowStages = new Set<SmearWorkflowStage>(Object.keys(stageLabel) as SmearWorkflowStage[]);

const historyFailure = (
  workflow: SmearWorkflowResponse,
): { step: SmearWorkflowFailureStep; message: string } | null => {
  if (workflow.detection_run?.status === 'failed') {
    return {
      step: 'detection',
      message: workflow.detection_run.error_message || 'La detección terminó con error.',
    };
  }
  if (workflow.queue_item?.status === 'failed') {
    return {
      step: 'quality',
      message: workflow.queue_item.last_error_message || 'El control de calidad terminó con error.',
    };
  }
  return workflow.stage === 'error'
    ? { step: 'recovery', message: 'El análisis terminó con error.' }
    : null;
};

const safeDate = (value: string | null | undefined) => {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleString();
};

const safeTime = (value: string | null | undefined) => {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? null
    : parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const optionalMetric = (value: number | null | undefined, digits = 3) =>
  value == null ? '—' : value.toFixed(digits);

const ratio = (value: number | null | undefined) =>
  value == null ? '—' : `${(value * 100).toFixed(1)} %`;

function contextStepState(
  step: ContextStep,
  stage: SmearWorkflowStage,
  failureStep: SmearWorkflowFailureStep | undefined,
): StepState {
  if (stage === 'review_ready') {
    return step === 'review' ? 'active' : 'complete';
  }
  if (stage === 'detection_processing' || stage === 'ready_for_detection') {
    if (step === 'upload' || step === 'quality') return 'complete';
    return step === 'detection' ? 'active' : 'locked';
  }
  if (stage === 'quality_warning') {
    if (step === 'upload') return 'complete';
    return step === 'quality' ? 'warning' : 'locked';
  }
  if (stage === 'quality_failed') {
    if (step === 'upload') return 'complete';
    return step === 'quality' ? 'failed' : 'locked';
  }
  if (stage === 'error') {
    const failedContext: Record<SmearWorkflowFailureStep, ContextStep> = {
      upload: 'upload',
      analysis: 'quality',
      queue: 'quality',
      quality: 'quality',
      detection: 'detection',
      recovery: 'upload',
    };
    const failed = failedContext[failureStep ?? 'recovery'];
    if (step === failed) return 'failed';
    if (failed === 'quality' && step === 'upload') return 'complete';
    if (failed === 'detection' && (step === 'upload' || step === 'quality')) return 'complete';
    return 'locked';
  }
  if (['ingested', 'creating_analysis', 'quality_queued', 'quality_processing'].includes(stage)) {
    if (step === 'upload') return 'complete';
    return step === 'quality' ? 'active' : 'locked';
  }
  if (step === 'upload') return 'active';
  return 'locked';
}

function AuthenticatedWorkflowImage({
  localUrl,
  imageId,
  name,
}: {
  localUrl: string | null;
  imageId: string | null;
  name: string;
}) {
  const [persistedUrl, setPersistedUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (localUrl || !imageId) {
      setPersistedUrl(null);
      setFailed(false);
      return undefined;
    }
    let active = true;
    let objectUrl: string | null = null;
    setFailed(false);
    api.getMicroscopyImageBlob(imageId)
      .then((url) => {
        if (!active) {
          URL.revokeObjectURL(url);
          return;
        }
        objectUrl = url;
        setPersistedUrl(url);
      })
      .catch((error) => {
        if (active) setFailed(error instanceof ApiError || error instanceof Error);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [imageId, localUrl]);

  const source = localUrl ?? persistedUrl;
  if (source) return <img src={source} alt={`Imagen de frotis ${name}`} />;
  return (
    <div className="workflow-persisted-image-empty">
      <span aria-hidden="true">{failed ? '!' : '…'}</span>
      <strong>{failed ? 'Imagen no disponible' : 'Cargando imagen autenticada'}</strong>
    </div>
  );
}

function milestoneState(
  milestone: number,
  controller: SmearWorkflowController,
): StepState {
  const { stage, identifiers, snapshot, failure } = controller;
  const run = snapshot.analysisRun;
  const detection = snapshot.detectionRun;
  if (milestone === 0) {
    if (stage === 'error' && failure?.step === 'upload') return 'failed';
    return identifiers.ingestionBatchId ? 'complete' : stage === 'uploading' ? 'active' : 'pending';
  }
  if (milestone === 1) {
    if (run?.images.length && run.images.every((image) => image.integrity_verified === true)) return 'complete';
    if (stage === 'quality_processing') return 'active';
    if (stage === 'quality_failed') return 'failed';
    return identifiers.ingestionBatchId ? 'pending' : 'locked';
  }
  if (milestone === 2) {
    if (stage === 'quality_warning') return 'warning';
    if (stage === 'quality_failed' || (stage === 'error' && failure?.step === 'quality')) return 'failed';
    if (run?.ready_for_analysis) return 'complete';
    if (['creating_analysis', 'quality_queued', 'quality_processing'].includes(stage)) return 'active';
    return identifiers.analysisRunId ? 'pending' : 'locked';
  }
  if (milestone === 3) {
    if (run?.ready_for_analysis) return 'complete';
    if (stage === 'quality_warning') return 'warning';
    if (stage === 'quality_failed') return 'failed';
    return identifiers.analysisRunId ? 'pending' : 'locked';
  }
  if (milestone === 4) {
    if (detection?.status === 'completed' || detection?.status === 'completed_with_warnings') return 'complete';
    if (detection?.status === 'failed' || (stage === 'error' && failure?.step === 'detection')) return 'failed';
    if (stage === 'detection_processing' || stage === 'ready_for_detection') return 'active';
    return run?.ready_for_analysis ? 'pending' : 'locked';
  }
  if (stage === 'review_ready') return 'complete';
  if (detection?.status === 'failed') return 'failed';
  return detection ? 'pending' : 'locked';
}

function QualityMetrics({ image }: { image: QualityImage | null }) {
  if (!image) return <p className="workflow-panel-empty">Las métricas aún no están disponibles.</p>;
  return (
    <dl className="workflow-quality-metrics">
      <div><dt>Integridad</dt><dd>{image.integrity_verified ? 'Verificada' : 'No verificada'}</dd></div>
      <div><dt>Nitidez</dt><dd>{optionalMetric(image.laplacian_variance)}</dd></div>
      <div><dt>Brillo</dt><dd>{optionalMetric(image.brightness_mean)}</dd></div>
      <div><dt>Contraste</dt><dd>{optionalMetric(image.contrast_p95_p05)}</dd></div>
      <div><dt>Entropía</dt><dd>{optionalMetric(image.entropy_bits, 2)} bits</dd></div>
      <div><dt>Área útil</dt><dd>{ratio(image.usable_field_ratio)}</dd></div>
    </dl>
  );
}

function EventList({ events }: { events: AnalysisEvent[] }) {
  if (!events.length) {
    return <p className="workflow-panel-empty">Aún no hay eventos técnicos persistidos.</p>;
  }
  return (
    <ol className="workflow-event-list">
      {events.slice(-8).reverse().map((event) => (
        <li key={event.id}>
          <span className={`workflow-event-dot status-${event.status}`} aria-hidden="true" />
          <div>
            <strong>{event.stage.replaceAll('_', ' ')}</strong>
            <span>{event.message || event.status}</span>
          </div>
          <time dateTime={event.created_at}>{safeDate(event.created_at)}</time>
        </li>
      ))}
    </ol>
  );
}

function WorkflowProcessing({
  controller,
  capabilities,
  readOnly = false,
}: {
  controller: SmearWorkflowController;
  capabilities: WorkflowCapabilities;
  readOnly?: boolean;
}) {
  const [comment, setComment] = useState('');
  const [mobilePane, setMobilePane] = useState<MobilePane>('progress');
  const { stage, identifiers, snapshot, previewUrl, failure } = controller;
  const run = snapshot.analysisRun;
  const qualityImage = run?.images[0] ?? null;
  const uploadedImage = snapshot.upload?.images[0] ?? null;
  const persistedImage = snapshot.persisted?.images[0] ?? null;
  const imageId = identifiers.microscopyImageId;
  const imageName = (
    uploadedImage?.original_filename
    ?? persistedImage?.original_filename
    ?? qualityImage?.original_filename
    ?? 'Imagen persistida'
  );
  const imageWidth = uploadedImage?.width_px ?? persistedImage?.width_px ?? qualityImage?.input_width_px;
  const imageHeight = uploadedImage?.height_px ?? persistedImage?.height_px ?? qualityImage?.input_height_px;
  const imageFormat = (
    persistedImage?.detected_format
    ?? persistedImage?.mime_type
    ?? controller.selectedFiles[0]?.type
    ?? '—'
  );
  const batch = snapshot.upload?.ingestion_batch ?? snapshot.persisted?.batch;
  const queue = snapshot.queueItem;
  const queueStatus = queue?.status;
  const events = run?.events ?? [];
  const canRetryFailure = failure?.step === 'analysis'
    ? capabilities.canCreateAnalysis
    : failure?.step === 'queue'
      ? capabilities.canCreateQueue
      : failure?.step === 'detection'
        ? capabilities.canExecuteDetection
        : failure?.step === 'recovery';
  const canContinueRecovered = stage === 'ready_for_detection'
    ? capabilities.canExecuteDetection
    : run ? capabilities.canCreateQueue : capabilities.canCreateAnalysis;
  const eventAt = (eventType: string) =>
    events.find((event) => event.event_type === eventType)?.created_at;
  const milestoneTimes = [
    batch?.completed_at ?? batch?.created_at,
    eventAt('quality.image.completed'),
    eventAt('quality.run.completed') ?? queue?.completed_at,
    run?.completed_at ?? eventAt('quality.run.completed'),
    snapshot.detectionRun?.started_at,
    snapshot.detectionRun?.completed_at,
  ];
  const milestones = [
    ['Imagen recibida', 'Original persistido sin modificaciones'],
    ['Integridad verificada', 'Checksum y decodificación técnica'],
    ['Control de calidad', 'Nitidez, exposición y campo útil'],
    ['Lista para análisis', 'Quality gate autorizado'],
    ['Detección celular', 'Regiones candidatas y crops'],
    ['Revisión disponible', 'Workspace interactivo habilitado'],
  ] as const;

  async function decide(decision: 'approve_with_warnings' | 'reject') {
    if (!comment.trim()) return;
    if (decision === 'reject' && !window.confirm('¿Confirmas el bloqueo técnico de este análisis?')) return;
    await controller.decideWarning(decision, comment);
    setComment('');
  }

  return (
    <>
      <nav className="workflow-mobile-tabs" aria-label="Paneles del workflow">
        {([
          ['progress', 'Progreso'],
          ['image', 'Imagen'],
          ['cells', 'Células'],
          ['detail', 'Detalle'],
        ] as const).map(([id, label]) => (
          <button
            key={id}
            type="button"
            disabled={id === 'cells'}
            aria-pressed={mobilePane === id}
            onClick={() => setMobilePane(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      <div className="workflow-processing-grid" data-mobile-pane={mobilePane}>
        <aside className="workflow-console-panel workflow-progress-panel">
          <header className="workflow-panel-heading">
            <p className="workflow-panel-eyebrow">Progreso persistido</p>
            <h2>Etapas del análisis</h2>
          </header>
          <div className="workflow-panel-scroll">
            <ol className="workflow-milestones">
              {milestones.map(([title, detail], index) => {
                const state = milestoneState(index, controller);
                const milestoneTime = safeTime(milestoneTimes[index]);
                return (
                  <li key={title} data-state={state}>
                    <span className="workflow-milestone-mark" aria-hidden="true">
                      {state === 'complete' ? '✓' : state === 'warning' ? '!' : state === 'failed' ? '×' : index + 1}
                    </span>
                    <div><strong>{title}</strong><span>{detail}</span></div>
                    <small>
                      <span>{state === 'active' ? 'En curso' : state}</span>
                      {milestoneTime ? <time>{milestoneTime}</time> : null}
                    </small>
                  </li>
                );
              })}
            </ol>
          </div>
        </aside>

        <section className="workflow-console-panel workflow-image-panel">
          <header className="workflow-panel-heading workflow-image-heading">
            <div>
              <p className="workflow-panel-eyebrow">Imagen principal</p>
              <h2>{imageName}</h2>
            </div>
            <span className={`workflow-stage-badge status-${stage}`}>{stageLabel[stage]}</span>
          </header>
          <div className="workflow-processing-image">
            <AuthenticatedWorkflowImage localUrl={previewUrl} imageId={imageId} name={imageName} />
            {!readOnly && processingStages.includes(stage) ? (
              <div className="workflow-image-activity" role="status">
                <span className="workflow-indeterminate" aria-hidden="true" />
                <span>{activityLabel[stage]}</span>
              </div>
            ) : null}
          </div>
          <dl className="workflow-image-facts">
            <div><dt>Paciente</dt><dd>{run?.subject_code ?? snapshot.persisted?.subject.subject_code ?? snapshot.upload?.subject.subject_code ?? '—'}</dd></div>
            <div><dt>Muestra</dt><dd>{run?.sample_code ?? snapshot.persisted?.sample.sample_code ?? snapshot.upload?.sample.sample_code ?? '—'}</dd></div>
            <div><dt>Lote</dt><dd>{identifiers.ingestionBatchId ?? '—'}</dd></div>
            <div><dt>Dimensiones</dt><dd>{imageWidth && imageHeight ? `${imageWidth} × ${imageHeight} px` : '—'}</dd></div>
            <div><dt>Formato</dt><dd>{imageFormat}</dd></div>
            <div><dt>Estado</dt><dd>{stageLabel[stage]}</dd></div>
          </dl>
        </section>

        <aside className="workflow-console-panel workflow-activity-panel">
          <header className="workflow-panel-heading">
            <p className="workflow-panel-eyebrow">Actividad</p>
            <h2>{activityLabel[stage]}</h2>
          </header>
          <div className="workflow-panel-scroll workflow-activity-scroll">
            <dl className="workflow-run-facts">
              <div><dt>Run</dt><dd>{run?.run_code ?? 'Pendiente'}</dd></div>
              <div><dt>Prioridad</dt><dd>{queue?.priority ?? 50} · Normal</dd></div>
              <div><dt>Cola</dt><dd>{queueStatus ?? 'Pendiente'}</dd></div>
              <div><dt>Intentos</dt><dd>{queue?.attempt_count ?? 0}</dd></div>
            </dl>

            {run?.ready_for_analysis ? (
              <section className="workflow-decision-card status-pass">
                <span>Aprobación técnica</span>
                <h3>
                  {run.quality_gate_status === 'warning'
                    ? 'Quality gate aprobado con advertencias'
                    : 'Quality gate aprobado'}
                </h3>
                <QualityMetrics image={qualityImage} />
                <p>
                  {stage === 'detection_processing'
                    ? 'La detección se inició como continuación de la acción Cargar y analizar.'
                    : 'La ejecución está habilitada para iniciar la detección celular.'}
                </p>
              </section>
            ) : null}

            {stage === 'quality_warning' ? (
              <section className="workflow-decision-card status-warning">
                <span>Advertencia técnica</span>
                <h3>Se requiere una decisión autorizada</h3>
                <QualityMetrics image={qualityImage} />
                {qualityImage?.warning_codes?.length
                  ? <p>Indicadores: {qualityImage.warning_codes.join(', ')}</p>
                  : null}
                {!readOnly && capabilities.canReviewQuality ? (
                  <div className="workflow-warning-actions">
                    <label>
                      Comentario técnico obligatorio
                      <textarea value={comment} onChange={(event) => setComment(event.target.value)} />
                    </label>
                    <button type="button" disabled={controller.busy || !comment.trim()} onClick={() => void decide('approve_with_warnings')}>
                      Aprobar con advertencias
                    </button>
                    <button className="danger" type="button" disabled={controller.busy || !comment.trim()} onClick={() => void decide('reject')}>
                      Bloquear análisis
                    </button>
                  </div>
                ) : (
                  <p role="status">
                    Tu rol puede visualizar el resultado, pero no resolver esta advertencia.
                  </p>
                )}
              </section>
            ) : null}

            {stage === 'quality_failed' ? (
              <section className="workflow-decision-card status-failed">
                <span>Bloqueo técnico</span>
                <h3>La detección celular no fue iniciada</h3>
                <QualityMetrics image={qualityImage} />
                {qualityImage?.failure_codes?.length
                  ? <p>Causas: {qualityImage.failure_codes.join(', ')}</p>
                  : <p>Revisa la preparación o vuelve a cargar un original adecuado.</p>}
                {!readOnly ? (
                  <button type="button" onClick={controller.newAnalysis}>Cargar otra imagen</button>
                ) : null}
              </section>
            ) : null}

            {stage === 'error' && failure ? (
              <section className="workflow-decision-card status-failed" role="alert">
                <span>Etapa interrumpida: {failure.step}</span>
                <h3>{failure.message}</h3>
                <p>Los recursos creados correctamente permanecen disponibles:</p>
                <ul>
                  {identifiers.ingestionBatchId ? <li>Lote {identifiers.ingestionBatchId}</li> : null}
                  {identifiers.analysisRunId ? <li>Analysis run {identifiers.analysisRunId}</li> : null}
                  {identifiers.queueItemId ? <li>Queue item {identifiers.queueItemId}</li> : null}
                  {identifiers.detectionRunId ? <li>Detection run {identifiers.detectionRunId}</li> : null}
                </ul>
                {failure.step === 'quality' && queueStatus === 'failed' ? (
                  capabilities.canRetryQueue ? (
                    <button type="button" disabled={controller.busy} onClick={() => void controller.requeueQuality()}>
                      Reingresar a cola
                    </button>
                  ) : <p>Tu rol no permite reingresar solicitudes fallidas a la cola.</p>
                ) : failure.step !== 'upload' && canRetryFailure ? (
                  <button type="button" disabled={controller.busy} onClick={() => void controller.retryFailedStep()}>
                    Reintentar desde esta etapa
                  </button>
                ) : failure.step !== 'upload'
                  ? <p>Tu rol no permite reintentar esta etapa.</p>
                  : null}
              </section>
            ) : null}

            {stage === 'quality_queued' && queueStatus === 'queued' ? (
              <section className="workflow-decision-card">
                <span>Solicitud reingresada</span>
                <h3>El reintento aún no se ha ejecutado</h3>
                <p>La política requiere una segunda acción manual.</p>
                {capabilities.canExecuteQueue ? (
                  <button type="button" disabled={controller.busy} onClick={() => void controller.executeRequeuedQuality()}>
                    Ejecutar control
                  </button>
                ) : <p>Tu rol no permite ejecutar solicitudes de calidad.</p>}
              </section>
            ) : null}

            {!readOnly && (
              (stage === 'ingested' && !queue)
              || (stage === 'creating_analysis' && run && !queue)
              || (stage === 'ready_for_detection' && run?.ready_for_analysis)
            ) ? (
              <section className="workflow-decision-card">
                <span>Estado recuperado</span>
                <h3>
                  {stage === 'ready_for_detection'
                    ? 'La calidad está aprobada y la detección aún no existe'
                    : run
                      ? 'La ejecución existe y espera su solicitud de calidad'
                      : 'Imagen cargada, esperando control técnico'}
                </h3>
                <p>Continuar es una acción manual y reutilizará los identificadores persistidos.</p>
                {canContinueRecovered ? (
                  <button type="button" disabled={controller.busy} onClick={() => void controller.continueWorkflow()}>
                    {stage === 'ready_for_detection' ? 'Iniciar detección' : 'Continuar análisis'}
                  </button>
                ) : <p>Tu rol no permite continuar esta etapa.</p>}
              </section>
            ) : null}

            {!['quality_warning', 'quality_failed', 'error'].includes(stage) ? (
              <EventList events={events} />
            ) : null}
          </div>
        </aside>
      </div>
    </>
  );
}

const readOnlyCapabilities: WorkflowCapabilities = {
  canCreateAnalysis: false,
  canCreateQueue: false,
  canExecuteQueue: false,
  canRetryQueue: false,
  canReviewQuality: false,
  canExecuteDetection: false,
};

export function SmearAnalysisReadOnlyView({
  workflow,
  onBack,
}: {
  workflow: SmearWorkflowResponse;
  onBack: () => void;
}) {
  const stage = (
    knownWorkflowStages.has(workflow.stage as SmearWorkflowStage)
      ? workflow.stage
      : 'error'
  ) as SmearWorkflowStage;
  const firstImage = workflow.images[0] ?? null;
  const failure = historyFailure(workflow);
  const controller = {
    stage,
    identifiers: {
      ingestionBatchId: workflow.batch.id,
      microscopyImageId: firstImage?.id ?? null,
      analysisRunId: workflow.analysis_run?.id ?? null,
      queueItemId: workflow.queue_item?.queue_item_id ?? null,
      detectionRunId: workflow.detection_run?.id ?? null,
      selectedDetectionId: null,
    },
    snapshot: {
      upload: null,
      persisted: workflow,
      analysisRun: workflow.analysis_run,
      queueItem: workflow.queue_item,
      detectionRun: workflow.detection_run,
    },
    selectedFiles: [],
    previewUrl: null,
    failure,
    recovering: false,
    busy: false,
  } as unknown as SmearWorkflowController;
  const contextStates = new Map(contextSteps.map(({ id }) => [
    id,
    contextStepState(id, stage, failure?.step),
  ]));
  const run = workflow.analysis_run;

  return (
    <section className="page smear-workflow smear-workflow-history" data-mode="history">
      <header className="workflow-context-header">
        <div className="workflow-case-context">
          <p className="workflow-kicker">Análisis de frotis</p>
          <strong>{workflow.subject.subject_code}</strong>
          <span>{workflow.sample.sample_code} · {stageLabel[stage]}</span>
        </div>
        <nav className="workflow-stage-nav" aria-label="Etapas persistidas del análisis">
          {contextSteps.map((step) => {
            const state = contextStates.get(step.id) ?? 'locked';
            return (
              <span key={step.id} className="workflow-stage-item" data-state={state}>
                <span aria-hidden="true">
                  {state === 'complete' ? '✓' : state === 'warning' ? '!' : state === 'failed' ? '×' : '•'}
                </span>
                {step.label}
              </span>
            );
          })}
        </nav>
        <div className="workflow-header-actions">
          <button type="button" onClick={onBack}>Volver al historial</button>
        </div>
      </header>
      <section className="workflow-history-banner" aria-label="Modo de consulta">
        <strong>Vista histórica · Solo lectura</strong>
        <span>{run?.run_code ?? 'Análisis persistido'}</span>
        <span>{safeDate(run?.created_at)}</span>
        <span>{workflow.batch.source_system ?? workflow.batch.acquisition_origin}</span>
      </section>

      {stage === 'review_ready' && workflow.detection_run ? (
        <section className="workflow-review-frame">
          <CellReviewWorkspace
            detectionRunId={workflow.detection_run.id}
            canReview={false}
            onClose={onBack}
            closeLabel="Volver al historial"
            initialMicroscopyImageId={firstImage?.id}
          />
        </section>
      ) : (
        <WorkflowProcessing
          controller={controller}
          capabilities={readOnlyCapabilities}
          readOnly
        />
      )}
    </section>
  );
}

export function SmearWorkflow() {
  const { user } = useAuth();
  const controller = useSmearAnalysisWorkflow();
  const {
    stage,
    identifiers,
    snapshot,
    selectedFiles,
    previewUrl,
    failure,
    recovering,
  } = controller;
  const permissions = new Set(user?.permissions ?? []);
  const canAnalyze = [
    'scientific.images.register',
    'scientific.analysis.create',
    'scientific.analysis.queue.create',
    'scientific.analysis.queue.execute',
    'scientific.cell_detection.execute',
  ].every((permission) => permissions.has(permission));
  const canReviewQuality = permissions.has('scientific.analysis.quality.review');
  const capabilities: WorkflowCapabilities = {
    canCreateAnalysis: permissions.has('scientific.analysis.create'),
    canCreateQueue: permissions.has('scientific.analysis.queue.create'),
    canExecuteQueue: permissions.has('scientific.analysis.queue.execute'),
    canRetryQueue: permissions.has('scientific.analysis.queue.retry'),
    canReviewQuality,
    canExecuteDetection: permissions.has('scientific.cell_detection.execute'),
  };
  const canReadCells = permissions.has('scientific.cell_detection.read');
  const canReviewCells = permissions.has('scientific.cell_detection.review');
  const isUploadFailure = stage === 'error' && failure?.step === 'upload' && !identifiers.ingestionBatchId;
  const mode = stage === 'setup' || isUploadFailure
    ? 'setup'
    : stage === 'review_ready' ? 'review' : 'processing';
  const patientCode = (
    snapshot.analysisRun?.subject_code
    ?? snapshot.persisted?.subject.subject_code
    ?? snapshot.upload?.subject.subject_code
    ?? 'Paciente pendiente'
  );
  const sampleCode = (
    snapshot.analysisRun?.sample_code
    ?? snapshot.persisted?.sample.sample_code
    ?? snapshot.upload?.sample.sample_code
    ?? 'Muestra pendiente'
  );
  const headerState = stageLabel[stage];

  const contextStates = useMemo(
    () => new Map(contextSteps.map(({ id }) => [
      id,
      contextStepState(id, stage, failure?.step),
    ])),
    [failure?.step, stage],
  );

  return (
    <section className="page smear-workflow" data-mode={mode}>
      <header className="workflow-context-header">
        <div className="workflow-case-context">
          <p className="workflow-kicker">Análisis de frotis</p>
          <strong>{patientCode}</strong>
          <span>{sampleCode} · {headerState}</span>
        </div>
        <nav className="workflow-stage-nav" aria-label="Etapas del análisis">
          {contextSteps.map((step) => {
            const state = contextStates.get(step.id) ?? 'locked';
            return (
              <span
                key={step.id}
                className="workflow-stage-item"
                data-state={state}
                aria-current={state === 'active' ? 'step' : undefined}
              >
                <span aria-hidden="true">
                  {state === 'complete' ? '✓' : state === 'warning' ? '!' : state === 'failed' ? '×' : '•'}
                </span>
                {step.label}
              </span>
            );
          })}
        </nav>
        {mode !== 'setup' ? (
          <div className="workflow-header-actions">
            <button type="button" disabled={recovering} onClick={() => void controller.refresh()}>
              Actualizar estado
            </button>
            <button type="button" onClick={controller.newAnalysis}>Nuevo análisis</button>
          </div>
        ) : <span className="workflow-context-status">{headerState}</span>}
      </header>

      {recovering ? (
        <section className="workflow-recovering" aria-live="polite">
          <span className="workflow-indeterminate" aria-hidden="true" />
          <div><strong>Recuperando análisis</strong><p>Consultando el estado persistido sin repetir operaciones.</p></div>
        </section>
      ) : null}

      {mode === 'setup' && !recovering ? (
        <>
          {isUploadFailure ? <p className="workflow-setup-error" role="alert">{failure?.message}</p> : null}
          <SmearUpload
            files={selectedFiles}
            previewUrl={previewUrl}
            busy={controller.busy}
            canAnalyze={canAnalyze}
            onFilesChange={controller.setSelectedFiles}
            onAnalyze={controller.start}
          />
        </>
      ) : null}

      {mode === 'processing' && !recovering ? (
        <WorkflowProcessing controller={controller} capabilities={capabilities} />
      ) : null}

      {mode === 'review' && !recovering ? (
        <section className="workflow-review-frame">
          {identifiers.detectionRunId && canReadCells ? (
            <CellReviewWorkspace
              detectionRunId={identifiers.detectionRunId}
              canReview={canReviewCells}
              onClose={controller.newAnalysis}
              closeLabel="Nuevo análisis"
              initialMicroscopyImageId={identifiers.microscopyImageId}
              onMicroscopyImageChange={controller.selectImage}
              initialSelectedDetectionId={identifiers.selectedDetectionId}
              onSelectedDetectionChange={controller.selectDetection}
            />
          ) : (
            <section className="workflow-review-unavailable" role="alert">
              <h2>Revisión disponible con acceso restringido</h2>
              <p>
                La detección terminó, pero tu rol no incluye
                scientific.cell_detection.read.
              </p>
            </section>
          )}
        </section>
      ) : null}
    </section>
  );
}
