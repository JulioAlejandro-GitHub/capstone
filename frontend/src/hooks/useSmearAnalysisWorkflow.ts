import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { isValidPublicId } from '../router';
import {
  ApiError,
  DEFAULT_DATASOURCE,
  api,
  type AnalysisRun,
  type ImageUploadResponse,
  type QualityQueueRecord,
  type SmearWorkflowResponse,
} from '../services/api';
import type { CellDetectionRunDetail } from '../types/cellReview';
import type {
  CellClassificationRunDetail,
  EligibleCellClassificationRun,
  SmearAnalysisSummary,
} from '../types/cellClassification';

export type SmearWorkflowStage =
  | 'setup'
  | 'validating'
  | 'uploading'
  | 'ingested'
  | 'creating_analysis'
  | 'quality_queued'
  | 'quality_processing'
  | 'quality_warning'
  | 'quality_failed'
  | 'ready_for_detection'
  | 'detection_processing'
  | 'awaiting_productive_model'
  | 'classification_pending'
  | 'classification_processing'
  | 'classification_completed'
  | 'classification_warning'
  | 'classification_failed'
  | 'review_ready'
  | 'error';

export type SmearFlowPhase =
  | 'idle'
  | 'validating'
  | 'uploading'
  | 'quality_check'
  | 'detecting'
  | 'classifying'
  | 'loading_result'
  | 'completed'
  | 'quality_rejected'
  | 'failed';

export type SmearWorkflowFailureStep =
  | 'upload'
  | 'analysis'
  | 'queue'
  | 'quality'
  | 'detection'
  | 'classification'
  | 'recovery';

export type SmearWorkflowIdentifiers = {
  ingestionBatchId: string | null;
  microscopyImageId: string | null;
  analysisRunId: string | null;
  queueItemId: string | null;
  detectionRunId: string | null;
  classificationRunId: string | null;
  selectedDetectionId: string | null;
  selectedPredictionId: string | null;
};

export type SmearWorkflowError = {
  step: SmearWorkflowFailureStep;
  message: string;
};

export type SmearWorkflowSnapshot = {
  upload: ImageUploadResponse | null;
  persisted: SmearWorkflowResponse | null;
  analysisRun: AnalysisRun | null;
  queueItem: QualityQueueRecord | null;
  detectionRun: CellDetectionRunDetail | null;
  classificationRun: CellClassificationRunDetail | null;
  classificationSummary: SmearAnalysisSummary | null;
  classificationEligibility: EligibleCellClassificationRun | null;
};

const emptyIdentifiers: SmearWorkflowIdentifiers = {
  ingestionBatchId: null,
  microscopyImageId: null,
  analysisRunId: null,
  queueItemId: null,
  detectionRunId: null,
  classificationRunId: null,
  selectedDetectionId: null,
  selectedPredictionId: null,
};

const emptySnapshot: SmearWorkflowSnapshot = {
  upload: null,
  persisted: null,
  analysisRun: null,
  queueItem: null,
  detectionRun: null,
  classificationRun: null,
  classificationSummary: null,
  classificationEligibility: null,
};

const createUploadRequestId = () => {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20),
  ].join('-');
};

const workflowStages = new Set<SmearWorkflowStage>([
  'setup',
  'validating',
  'uploading',
  'ingested',
  'creating_analysis',
  'quality_queued',
  'quality_processing',
  'quality_warning',
  'quality_failed',
  'ready_for_detection',
  'detection_processing',
  'awaiting_productive_model',
  'classification_pending',
  'classification_processing',
  'classification_completed',
  'classification_warning',
  'classification_failed',
  'review_ready',
  'error',
]);

const flowPhaseFromStage = (stage: SmearWorkflowStage): SmearFlowPhase => {
  if (stage === 'setup') return 'idle';
  if (stage === 'validating') return 'validating';
  if (stage === 'uploading') return 'uploading';
  if (['ingested', 'creating_analysis', 'quality_queued', 'quality_processing', 'quality_warning'].includes(stage)) return 'quality_check';
  if (stage === 'quality_failed') return 'quality_rejected';
  if (stage === 'ready_for_detection' || stage === 'detection_processing') return 'detecting';
  if (['awaiting_productive_model', 'classification_pending', 'classification_processing'].includes(stage)) return 'classifying';
  if (stage === 'classification_completed' || stage === 'classification_warning') return 'loading_result';
  if (stage === 'review_ready') return 'completed';
  return 'failed';
};

const queueId = (item: QualityQueueRecord | null) => {
  if (!item) return null;
  return 'queue_item_id' in item ? item.queue_item_id : item.id;
};

const sanitizeFailure = (
  error: unknown,
  step: SmearWorkflowFailureStep,
): SmearWorkflowError => {
  if (error instanceof ApiError && error.status === 403) {
    return {
      step,
      message: 'Tu rol no autoriza esta acción. Los recursos creados se conservaron.',
    };
  }
  const fallback: Record<SmearWorkflowFailureStep, string> = {
    upload: 'No fue posible persistir la imagen. Revisa el archivo y vuelve a intentarlo.',
    analysis: 'La imagen quedó guardada, pero no fue posible crear la ejecución de análisis.',
    queue: 'La ejecución existe, pero no fue posible crear la solicitud de calidad.',
    quality: 'El control técnico no pudo completarse. No se realizará un reintento automático.',
    detection: 'La calidad fue aprobada, pero la detección celular no pudo completarse.',
    classification: 'La detección se conservó, pero la clasificación celular no pudo completarse.',
    recovery: 'No fue posible reconstruir el workflow persistido.',
  };
  if (error instanceof ApiError) {
    const connectionContext = error.kind === 'timeout'
      ? 'La operación superó el tiempo de espera; verifica el estado persistido antes de reintentar.'
      : error.kind === 'network'
        ? 'Se perdió temporalmente la conexión con el backend.'
        : fallback[step];
    const diagnostics = [
      error.message,
      error.code ? `Código: ${error.code}.` : '',
      error.stage ? `Etapa backend: ${error.stage}.` : '',
    ].filter(Boolean).join(' ');
    return { step, message: `${connectionContext} ${diagnostics}`.trim() };
  }
  return { step, message: fallback[step] };
};

const stageFromResponse = (
  response: SmearWorkflowResponse,
  classificationRun: CellClassificationRunDetail | null = response.classification_run ?? null,
): SmearWorkflowStage => {
  const reportedStage = workflowStages.has(response.stage as SmearWorkflowStage)
    ? response.stage as SmearWorkflowStage
    : null;
  if (
    reportedStage === 'awaiting_productive_model'
    || reportedStage === 'classification_pending'
    || reportedStage === 'classification_processing'
    || reportedStage === 'classification_completed'
    || reportedStage === 'classification_warning'
    || reportedStage === 'classification_failed'
    || reportedStage === 'review_ready'
  ) {
    return reportedStage;
  }
  if (classificationRun?.status === 'completed_with_warnings') return 'classification_warning';
  if (classificationRun?.status === 'completed') return 'classification_completed';
  if (classificationRun?.status === 'failed') return 'classification_failed';
  if (classificationRun?.status === 'processing') return 'classification_processing';
  if (classificationRun?.status === 'created') return 'classification_pending';
  if (
    response.detection_run?.status === 'completed'
    || response.detection_run?.status === 'completed_with_warnings'
  ) {
    return 'classification_pending';
  }
  return reportedStage ?? 'error';
};

const persistedFailure = (
  response: SmearWorkflowResponse,
  classificationRun: CellClassificationRunDetail | null = response.classification_run ?? null,
): SmearWorkflowError | null => {
  if (response.stage === 'awaiting_productive_model') {
    return {
      step: 'classification',
      message:
        'No existe un modelo productivo válido para Etapa 2. Publique un modelo desde Modelo IA antes de continuar.',
    };
  }
  if (classificationRun?.status === 'failed') {
    return {
      step: 'classification',
      message: classificationRun.error_message
        || 'La clasificación celular persistida terminó con un error técnico.',
    };
  }
  if (response.detection_run?.status === 'failed') {
    return {
      step: 'detection',
      message: response.detection_run.error_message
        || 'La detección celular persistida terminó con un error técnico.',
    };
  }
  if (response.queue_item?.status === 'failed') {
    return {
      step: 'quality',
      message: response.queue_item.last_error_message
        || 'El control técnico persistido terminó con un error seguro.',
    };
  }
  return stageFromResponse(response) === 'error'
    ? { step: 'recovery', message: 'El backend informó un estado interrumpido.' }
    : null;
};

export function useSmearAnalysisWorkflow() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [stage, setStage] = useState<SmearWorkflowStage>('setup');
  const [identifiers, setIdentifiers] = useState<SmearWorkflowIdentifiers>(emptyIdentifiers);
  const [snapshot, setSnapshot] = useState<SmearWorkflowSnapshot>(emptySnapshot);
  const [selectedFiles, setSelectedFilesState] = useState<File[]>([]);
  const [uploadRequestId, setUploadRequestId] = useState(createUploadRequestId);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [failure, setFailure] = useState<SmearWorkflowError | null>(null);
  const [recovering, setRecovering] = useState(false);
  const activeAction = useRef(false);
  const hydratedKey = useRef('');
  const workflowQueryRef = useRef(searchParams);

  useEffect(() => {
    workflowQueryRef.current = searchParams;
  }, [searchParams]);

  const queryIdentifiers = useMemo(() => ({
    batch: searchParams.get('batch'),
    analysis: searchParams.get('analysis'),
    queue: searchParams.get('queue'),
    detection: searchParams.get('detection') ?? searchParams.get('detection_run_id'),
    classification: searchParams.get('classification'),
    image: searchParams.get('image'),
    selectedDetection:
      searchParams.get('selected_detection') ?? searchParams.get('selected'),
    selectedPrediction: searchParams.get('selected_prediction'),
  }), [searchParams]);

  const writeIdentifiers = useCallback((
    values: Partial<SmearWorkflowIdentifiers>,
  ) => {
    setIdentifiers((current) => ({ ...current, ...values }));
    const next = new URLSearchParams(workflowQueryRef.current);
    const queryMap: Array<[keyof SmearWorkflowIdentifiers, string]> = [
      ['ingestionBatchId', 'batch'],
      ['microscopyImageId', 'image'],
      ['analysisRunId', 'analysis'],
      ['queueItemId', 'queue'],
      ['detectionRunId', 'detection'],
      ['classificationRunId', 'classification'],
      ['selectedDetectionId', 'selected_detection'],
      ['selectedPredictionId', 'selected_prediction'],
    ];
    queryMap.forEach(([stateKey, queryKey]) => {
      if (!(stateKey in values)) return;
      const value = values[stateKey];
      if (value) next.set(queryKey, value);
      else next.delete(queryKey);
    });
    next.delete('detection_run_id');
    next.delete('selected');
    workflowQueryRef.current = next;
    setSearchParams(next, { replace: true });
  }, [setSearchParams]);

  const recover = useCallback(async (
    candidate: typeof queryIdentifiers,
  ) => {
    const supplied = Object.values(candidate).filter(Boolean) as string[];
    const invalid = supplied.find((value) => !isValidPublicId(value));
    if (invalid) {
      setFailure({
        step: 'recovery',
        message: 'La URL contiene un identificador de workflow inválido.',
      });
      setStage('error');
      return;
    }
    if (
      !candidate.batch
      && !candidate.analysis
      && !candidate.detection
      && !candidate.classification
      && !candidate.selectedPrediction
    ) {
      setRecovering(false);
      return;
    }
    setRecovering(true);
    setFailure(null);
    try {
      let batchId = candidate.batch;
      let analysisId = candidate.analysis;
      let detectionId = candidate.detection;
      let classificationId = candidate.classification;
      let imageId = candidate.image;
      let selectedDetectionId = candidate.selectedDetection;
      let requestedClassification: CellClassificationRunDetail | null = null;
      let requestedPrediction: Awaited<ReturnType<typeof api.getCellPrediction>> | null = null;

      if (candidate.selectedPrediction) {
        requestedPrediction = await api.getCellPrediction(candidate.selectedPrediction);
        classificationId = requestedPrediction.classification_run_id;
        analysisId = requestedPrediction.analysis_run_id ?? analysisId;
        detectionId = requestedPrediction.detection_run_id ?? detectionId;
        imageId = requestedPrediction.microscopy_image_id || imageId;
        selectedDetectionId = requestedPrediction.cell_detection_id || selectedDetectionId;
      }
      if (classificationId) {
        requestedClassification = await api.getCellClassificationRun(classificationId);
        analysisId = requestedClassification.analysis_run_id;
        detectionId = requestedClassification.detection_run_id;
      }
      if (!batchId && detectionId) {
        const detection = await api.getCellDetectionRun(detectionId);
        const analysis = await api.getAnalysisRun(detection.analysis_run_id);
        batchId = analysis.ingestion_batch_id;
      } else if (!batchId && analysisId) {
        const analysis = await api.getAnalysisRun(analysisId);
        batchId = analysis.ingestion_batch_id;
      }
      if (!batchId) throw new Error('workflow without batch');
      const response = await api.getSmearWorkflow(batchId);
      setIdentifiers((current) => ({
        ...current,
        selectedDetectionId: selectedDetectionId ?? current.selectedDetectionId,
        selectedPredictionId:
          requestedPrediction?.id ?? candidate.selectedPrediction ?? current.selectedPredictionId,
      }));
      const firstImage = response.images[0] ?? null;
      const requestedImage = response.images.find((image) => image.id === imageId) ?? null;
      const nextDetectionId = response.detection_run?.id ?? detectionId;
      requestedClassification ??= response.classification_run ?? null;
      if (!requestedClassification && nextDetectionId) {
        const classificationPage = await api.getCellClassificationRuns({
          detection_run_id: nextDetectionId,
          limit: 1,
          offset: 0,
        });
        requestedClassification = classificationPage.items[0] ?? null;
      }
      let classificationSummary = response.classification_summary ?? null;
      if (
        requestedClassification
        && requestedClassification.status !== 'failed'
        && !classificationSummary
      ) {
        try {
          classificationSummary = await api.getCellClassificationSummary(
            requestedClassification.id,
          );
        } catch {
          classificationSummary = null;
        }
      }
      const nextIdentifiers: SmearWorkflowIdentifiers = {
        ingestionBatchId: response.batch.id,
        microscopyImageId: requestedImage?.id ?? firstImage?.id ?? null,
        analysisRunId: response.analysis_run?.id ?? analysisId,
        queueItemId: queueId(response.queue_item) ?? candidate.queue,
        detectionRunId: nextDetectionId,
        classificationRunId: requestedClassification?.id ?? classificationId,
        selectedDetectionId,
        selectedPredictionId: requestedPrediction?.id ?? candidate.selectedPrediction,
      };
      setSnapshot({
        upload: null,
        persisted: response,
        analysisRun: response.analysis_run,
        queueItem: response.queue_item,
        detectionRun: response.detection_run,
        classificationRun: requestedClassification,
        classificationSummary,
        classificationEligibility: null,
      });
      setIdentifiers(nextIdentifiers);
      writeIdentifiers(nextIdentifiers);
      setFailure(persistedFailure(response, requestedClassification));
      setStage(stageFromResponse(response, requestedClassification));
    } catch (error) {
      setFailure(sanitizeFailure(error, 'recovery'));
      setStage('error');
    } finally {
      setRecovering(false);
    }
  }, [searchParams, writeIdentifiers]);

  useEffect(() => {
    const key = [
      queryIdentifiers.batch,
      queryIdentifiers.analysis,
      queryIdentifiers.detection,
      queryIdentifiers.classification,
    ].join('|');
    if (!key.replaceAll('|', '') || activeAction.current || hydratedKey.current === key) return;
    hydratedKey.current = key;
    void recover(queryIdentifiers);
  }, [
    queryIdentifiers.analysis,
    queryIdentifiers.batch,
    queryIdentifiers.classification,
    queryIdentifiers.detection,
    recover,
  ]);

  useEffect(() => {
    if (!selectedFiles[0]) {
      setPreviewUrl(null);
      return undefined;
    }
    const objectUrl = URL.createObjectURL(selectedFiles[0]);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFiles]);

  const setSelectedFiles = useCallback((files: File[]) => {
    setSelectedFilesState(files);
    setUploadRequestId(createUploadRequestId());
  }, []);

  const executeClassification = useCallback(async (
    detectionRun: CellDetectionRunDetail,
  ) => {
    setStage('classification_pending');
    setFailure(null);
    try {
      const datasource = searchParams.get('datasource') ?? DEFAULT_DATASOURCE;
      const availability = await api.getProductiveModelAvailability(datasource);
      if (!availability.available || !availability.model) {
        setFailure({ step: 'classification', message: availability.message });
        setStage('awaiting_productive_model');
        return null;
      }
      const eligibilityPage = await api.getEligibleCellClassificationRuns({
        detection_run_id: detectionRun.id,
        limit: 1,
        offset: 0,
      });
      const eligibility = eligibilityPage.items.find(
        (item) => item.detection_run_id === detectionRun.id,
      ) ?? eligibilityPage.items[0] ?? null;
      setSnapshot((current) => ({
        ...current,
        classificationEligibility: eligibility,
      }));
      if (!eligibility?.eligible || !eligibility.productive_model) {
        const reasonCode = eligibility?.reason_code ?? '';
        const productiveModelBlocked = (
          !eligibility
          || !eligibility.productive_model
          || reasonCode.startsWith('PRODUCTIVE_')
          || reasonCode.startsWith('MODEL_')
        );
        setFailure({
          step: 'classification',
          message: eligibility?.message
            || 'No existe un modelo productivo válido para Etapa 2. Publique un modelo desde Modelo IA antes de continuar.',
        });
        setStage(
          productiveModelBlocked
            ? 'awaiting_productive_model'
            : 'classification_failed',
        );
        return null;
      }

      setStage('classification_processing');
      const classificationRun = await api.createCellClassificationRun(detectionRun.id);
      setSnapshot((current) => ({
        ...current,
        classificationRun,
        classificationSummary: null,
      }));
      writeIdentifiers({ classificationRunId: classificationRun.id });

      if (
        classificationRun.status === 'completed'
        || classificationRun.status === 'completed_with_warnings'
      ) {
        const classificationSummary = await api.getCellClassificationSummary(
          classificationRun.id,
        );
        setSnapshot((current) => ({ ...current, classificationSummary }));
        setStage(
          classificationRun.status === 'completed_with_warnings'
            ? 'classification_warning'
            : 'classification_completed',
        );
      } else if (classificationRun.status === 'failed') {
        setFailure({
          step: 'classification',
          message: classificationRun.error_message
            || 'La clasificación celular terminó con error. La detección permanece disponible.',
        });
        setStage('classification_failed');
      } else {
        setStage(
          classificationRun.status === 'processing'
            ? 'classification_processing'
            : 'classification_pending',
        );
      }
      return classificationRun;
    } catch (error) {
      try {
        const persistedPage = await api.getCellClassificationRuns({
          detection_run_id: detectionRun.id,
          limit: 1,
          offset: 0,
        });
        const persisted = persistedPage.items[0] ?? null;
        if (persisted) {
          setSnapshot((current) => ({
            ...current,
            classificationRun: persisted,
          }));
          writeIdentifiers({ classificationRunId: persisted.id });
          if (
            persisted.status === 'completed'
            || persisted.status === 'completed_with_warnings'
          ) {
            const classificationSummary = await api.getCellClassificationSummary(
              persisted.id,
            );
            setSnapshot((current) => ({
              ...current,
              classificationSummary,
            }));
            setStage(
              persisted.status === 'completed_with_warnings'
                ? 'classification_warning'
                : 'classification_completed',
            );
            return persisted;
          }
          if (persisted.status === 'failed') {
            setFailure({
              step: 'classification',
              message: persisted.error_message
                || sanitizeFailure(error, 'classification').message,
            });
            setStage('classification_failed');
            return persisted;
          }
          setFailure(null);
          setStage(
            persisted.status === 'processing'
              ? 'classification_processing'
              : 'classification_pending',
          );
          return persisted;
        }
      } catch {
        // The original safe error remains authoritative if recovery is unavailable.
      }
      setFailure(sanitizeFailure(error, 'classification'));
      setStage('classification_failed');
      return null;
    }
  }, [writeIdentifiers]);

  const executeDetection = useCallback(async (analysisRun: AnalysisRun) => {
    setStage('detection_processing');
    setFailure(null);
    try {
      const detectionRun = await api.createCellDetectionRun(analysisRun.id);
      setSnapshot((current) => ({ ...current, detectionRun }));
      writeIdentifiers({ detectionRunId: detectionRun.id });
      if (detectionRun.status === 'completed' || detectionRun.status === 'completed_with_warnings') {
        await executeClassification(detectionRun);
      } else if (detectionRun.status === 'failed') {
        setFailure(sanitizeFailure(new Error('detection failed'), 'detection'));
        setStage('error');
      } else {
        setStage('detection_processing');
      }
      return detectionRun;
    } catch (error) {
      setFailure(sanitizeFailure(error, 'detection'));
      setStage('error');
      return null;
    }
  }, [executeClassification, writeIdentifiers]);

  const evaluateQuality = useCallback(async (analysisRun: AnalysisRun) => {
    setSnapshot((current) => ({ ...current, analysisRun }));
    if (analysisRun.quality_gate_status === 'warning' && !analysisRun.ready_for_analysis) {
      setStage('quality_warning');
      return;
    }
    if (
      analysisRun.quality_gate_status === 'fail'
      || analysisRun.run_status === 'blocked'
      || !analysisRun.ready_for_analysis
    ) {
      setStage('quality_failed');
      return;
    }
    setStage('ready_for_detection');
    await executeDetection(analysisRun);
  }, [executeDetection]);

  const executeQueuedQuality = useCallback(async (
    item: QualityQueueRecord,
    continueToDetection: boolean,
  ) => {
    const itemId = queueId(item);
    if (!itemId) return;
    setStage('quality_processing');
    setFailure(null);
    try {
      const completed = await api.executeQueueItem(itemId);
      setSnapshot((current) => ({ ...current, queueItem: completed }));
      const analysisRunId = completed.analysis_run_id || identifiers.analysisRunId;
      if (!analysisRunId) throw new Error('quality without analysis');
      const analysisRun = await api.getAnalysisRun(analysisRunId);
      if (continueToDetection) await evaluateQuality(analysisRun);
      else {
        setSnapshot((current) => ({ ...current, analysisRun }));
        setStage(
          analysisRun.quality_gate_status === 'warning'
            ? 'quality_warning'
            : analysisRun.ready_for_analysis ? 'ready_for_detection' : 'quality_failed',
        );
      }
    } catch (error) {
      if (identifiers.ingestionBatchId) {
        try {
          const persisted = await api.getSmearWorkflow(identifiers.ingestionBatchId);
          setSnapshot((current) => ({
            ...current,
            persisted,
            analysisRun: persisted.analysis_run,
            queueItem: persisted.queue_item,
            detectionRun: persisted.detection_run,
          }));
          writeIdentifiers({ queueItemId: queueId(persisted.queue_item) });
        } catch {
          // The original sanitized failure remains authoritative.
        }
      }
      setFailure(sanitizeFailure(error, 'quality'));
      setStage('error');
    }
  }, [
    evaluateQuality,
    identifiers.analysisRunId,
    identifiers.ingestionBatchId,
    writeIdentifiers,
  ]);

  const createQueueAndAssess = useCallback(async (analysisRun: AnalysisRun) => {
    setStage('quality_queued');
    try {
      const queueItem = await api.enqueueQuality(analysisRun.id, 50);
      setSnapshot((current) => ({ ...current, queueItem }));
      writeIdentifiers({ queueItemId: queueItem.id });
      await executeQueuedQuality(queueItem, true);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        try {
          const persisted = await api.getSmearWorkflow(analysisRun.ingestion_batch_id);
          if (persisted.queue_item) {
            setSnapshot((current) => ({
              ...current,
              persisted,
              analysisRun: persisted.analysis_run ?? analysisRun,
              queueItem: persisted.queue_item,
              detectionRun: persisted.detection_run,
            }));
            writeIdentifiers({ queueItemId: persisted.queue_item.queue_item_id });
            if (persisted.queue_item.status === 'queued') {
              await executeQueuedQuality(persisted.queue_item, true);
            } else if (persisted.queue_item.status === 'completed' && persisted.analysis_run) {
              await evaluateQuality(persisted.analysis_run);
            } else if (persisted.queue_item.status === 'running') {
              setStage('quality_processing');
            } else {
              setFailure(sanitizeFailure(error, 'quality'));
              setStage('error');
            }
            return;
          }
        } catch {
          // Fall through to the sanitized queue failure.
        }
      }
      setFailure(sanitizeFailure(error, 'queue'));
      setStage('error');
    }
  }, [evaluateQuality, executeQueuedQuality, writeIdentifiers]);

  const createAnalysisAndContinue = useCallback(async (batchId: string) => {
    setStage('creating_analysis');
    setFailure(null);
    try {
      const analysisRun = await api.createAnalysisRun(batchId);
      setSnapshot((current) => ({ ...current, analysisRun }));
      writeIdentifiers({ analysisRunId: analysisRun.id });
      await createQueueAndAssess(analysisRun);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        try {
          const persisted = await api.getSmearWorkflow(batchId);
          if (persisted.analysis_run) {
            setSnapshot((current) => ({
              ...current,
              persisted,
              analysisRun: persisted.analysis_run,
              queueItem: persisted.queue_item,
              detectionRun: persisted.detection_run,
              classificationRun: persisted.classification_run ?? null,
              classificationSummary: persisted.classification_summary ?? null,
            }));
            writeIdentifiers({
              analysisRunId: persisted.analysis_run.id,
              queueItemId: queueId(persisted.queue_item),
              detectionRunId: persisted.detection_run?.id ?? null,
              classificationRunId: persisted.classification_run?.id ?? null,
            });
            if (persisted.detection_run) {
              if (
                !persisted.classification_run
                && (
                  persisted.detection_run.status === 'completed'
                  || persisted.detection_run.status === 'completed_with_warnings'
                )
              ) {
                await executeClassification(persisted.detection_run);
              } else {
                setFailure(persistedFailure(persisted));
                setStage(stageFromResponse(persisted));
              }
            } else if (persisted.analysis_run.ready_for_analysis) {
              await executeDetection(persisted.analysis_run);
            } else if (
              persisted.analysis_run.quality_gate_status === 'warning'
              || persisted.analysis_run.quality_gate_status === 'fail'
              || persisted.analysis_run.run_status === 'blocked'
            ) {
              await evaluateQuality(persisted.analysis_run);
            } else if (persisted.queue_item?.status === 'queued') {
              await executeQueuedQuality(persisted.queue_item, true);
            } else if (persisted.queue_item?.status === 'running') {
              setStage('quality_processing');
            } else if (persisted.queue_item?.status === 'failed') {
              setFailure(sanitizeFailure(error, 'quality'));
              setStage('error');
            } else {
              await createQueueAndAssess(persisted.analysis_run);
            }
            return;
          }
        } catch {
          // Fall through to the sanitized analysis failure.
        }
      }
      setFailure(sanitizeFailure(error, 'analysis'));
      setStage('error');
    }
  }, [
    createQueueAndAssess,
    evaluateQuality,
    executeClassification,
    executeDetection,
    executeQueuedQuality,
    writeIdentifiers,
  ]);

  const start = useCallback(async (form: FormData) => {
    if (activeAction.current) return;
    activeAction.current = true;
    setFailure(null);
    setStage('validating');
    await Promise.resolve();
    setStage('uploading');
    try {
      form.set('metadata_json', JSON.stringify({
        client_request_id: uploadRequestId,
      }));
      const upload = await api.uploadMicroscopyImages(form);
      const firstImage = upload.images[0] ?? null;
      setSnapshot((current) => ({ ...current, upload }));
      writeIdentifiers({
        ingestionBatchId: upload.ingestion_batch.id,
        microscopyImageId: firstImage?.id ?? null,
      });
      setStage('ingested');
      await createAnalysisAndContinue(upload.ingestion_batch.id);
    } catch (error) {
      setFailure(sanitizeFailure(error, 'upload'));
      setStage('error');
    } finally {
      activeAction.current = false;
    }
  }, [createAnalysisAndContinue, uploadRequestId, writeIdentifiers]);

  const decideWarning = useCallback(async (
    decision: 'approve_with_warnings' | 'reject',
    comment: string,
  ) => {
    if (!snapshot.analysisRun || activeAction.current) return;
    activeAction.current = true;
    setFailure(null);
    try {
      const analysisRun = await api.reviewQuality(
        snapshot.analysisRun.id,
        decision,
        comment.trim(),
      );
      setSnapshot((current) => ({ ...current, analysisRun }));
      if (decision === 'approve_with_warnings') {
        setStage('ready_for_detection');
        await executeDetection(analysisRun);
      } else {
        setStage('quality_failed');
      }
    } catch (error) {
      setFailure(sanitizeFailure(error, 'quality'));
      setStage('error');
    } finally {
      activeAction.current = false;
    }
  }, [executeDetection, snapshot.analysisRun]);

  const requeueQuality = useCallback(async () => {
    const itemId = queueId(snapshot.queueItem);
    if (!itemId || activeAction.current) return;
    activeAction.current = true;
    setFailure(null);
    try {
      const queueItem = await api.retryQueueItem(itemId, 50);
      setSnapshot((current) => ({ ...current, queueItem }));
      setStage('quality_queued');
    } catch (error) {
      setFailure(sanitizeFailure(error, 'quality'));
      setStage('error');
    } finally {
      activeAction.current = false;
    }
  }, [snapshot.queueItem]);

  const executeRequeuedQuality = useCallback(async () => {
    if (!snapshot.queueItem || activeAction.current) return;
    activeAction.current = true;
    try {
      await executeQueuedQuality(snapshot.queueItem, true);
    } finally {
      activeAction.current = false;
    }
  }, [executeQueuedQuality, snapshot.queueItem]);

  const retryFailedStep = useCallback(async () => {
    if (!failure || activeAction.current) return;
    if (failure.step === 'analysis' && identifiers.ingestionBatchId) {
      activeAction.current = true;
      try {
        await createAnalysisAndContinue(identifiers.ingestionBatchId);
      } finally {
        activeAction.current = false;
      }
      return;
    }
    if (failure.step === 'queue' && snapshot.analysisRun) {
      activeAction.current = true;
      try {
        await createQueueAndAssess(snapshot.analysisRun);
      } finally {
        activeAction.current = false;
      }
      return;
    }
    if (failure.step === 'detection' && snapshot.analysisRun) {
      activeAction.current = true;
      try {
        await executeDetection(snapshot.analysisRun);
      } finally {
        activeAction.current = false;
      }
      return;
    }
    if (failure.step === 'classification' && snapshot.detectionRun) {
      activeAction.current = true;
      try {
        await executeClassification(snapshot.detectionRun);
      } finally {
        activeAction.current = false;
      }
      return;
    }
    if (failure.step === 'recovery') {
      await recover(queryIdentifiers);
    }
  }, [
    createAnalysisAndContinue,
    createQueueAndAssess,
    executeClassification,
    executeDetection,
    failure,
    identifiers.ingestionBatchId,
    queryIdentifiers,
    recover,
    snapshot.analysisRun,
    snapshot.detectionRun,
  ]);

  const continueWorkflow = useCallback(async () => {
    if (activeAction.current) return;
    activeAction.current = true;
    try {
      if (!snapshot.analysisRun && identifiers.ingestionBatchId) {
        await createAnalysisAndContinue(identifiers.ingestionBatchId);
      } else if (
        snapshot.analysisRun
        && !snapshot.queueItem
        && !snapshot.analysisRun.ready_for_analysis
        && snapshot.analysisRun.quality_gate_status === 'pending'
      ) {
        await createQueueAndAssess(snapshot.analysisRun);
      } else if (snapshot.queueItem?.status === 'queued') {
        await executeQueuedQuality(snapshot.queueItem, true);
      } else if (
        snapshot.analysisRun?.ready_for_analysis
        && !snapshot.detectionRun
      ) {
        await executeDetection(snapshot.analysisRun);
      } else if (
        snapshot.detectionRun
        && (
          snapshot.detectionRun.status === 'completed'
          || snapshot.detectionRun.status === 'completed_with_warnings'
        )
        && !snapshot.classificationRun
      ) {
        await executeClassification(snapshot.detectionRun);
      }
    } finally {
      activeAction.current = false;
    }
  }, [
    createAnalysisAndContinue,
    createQueueAndAssess,
    executeClassification,
    executeDetection,
    executeQueuedQuality,
    identifiers.ingestionBatchId,
    snapshot.analysisRun,
    snapshot.classificationRun,
    snapshot.detectionRun,
    snapshot.queueItem,
  ]);

  const refresh = useCallback(async () => {
    const batch = identifiers.ingestionBatchId;
    if (!batch || activeAction.current) return;
    hydratedKey.current = '';
    await recover({
      batch,
      analysis: identifiers.analysisRunId,
      queue: identifiers.queueItemId,
      detection: identifiers.detectionRunId,
      classification: identifiers.classificationRunId,
      image: identifiers.microscopyImageId,
      selectedDetection: identifiers.selectedDetectionId,
      selectedPrediction: identifiers.selectedPredictionId,
    });
  }, [identifiers, recover]);

  const selectDetection = useCallback((id: string | null) => {
    writeIdentifiers({ selectedDetectionId: id });
  }, [writeIdentifiers]);

  const selectPrediction = useCallback((id: string | null) => {
    writeIdentifiers({ selectedPredictionId: id });
  }, [writeIdentifiers]);

  const selectImage = useCallback((id: string | null) => {
    writeIdentifiers({ microscopyImageId: id });
  }, [writeIdentifiers]);

  const newAnalysis = useCallback(() => {
    activeAction.current = false;
    hydratedKey.current = '';
    setStage('setup');
    setIdentifiers(emptyIdentifiers);
    setSnapshot(emptySnapshot);
    setSelectedFilesState([]);
    setUploadRequestId(createUploadRequestId());
    setFailure(null);
    setRecovering(false);
    const next = new URLSearchParams(workflowQueryRef.current);
    [
      'batch',
      'image',
      'analysis',
      'queue',
      'detection',
      'detection_run_id',
      'classification',
      'selected',
      'selected_detection',
      'selected_prediction',
    ]
      .forEach((key) => next.delete(key));
    workflowQueryRef.current = next;
    setSearchParams(next, { replace: true });
  }, [setSearchParams]);

  return {
    stage,
    phase: flowPhaseFromStage(stage),
    identifiers,
    snapshot,
    selectedFiles,
    previewUrl,
    failure,
    recovering,
    busy: activeAction.current || recovering || [
      'validating',
      'uploading',
      'creating_analysis',
      'quality_processing',
      'detection_processing',
      'classification_pending',
      'classification_processing',
    ].includes(stage),
    setSelectedFiles,
    start,
    decideWarning,
    requeueQuality,
    executeRequeuedQuality,
    retryFailedStep,
    continueWorkflow,
    refresh,
    selectImage,
    selectDetection,
    selectPrediction,
    newAnalysis,
  };
}

export type SmearWorkflowController = ReturnType<typeof useSmearAnalysisWorkflow>;
