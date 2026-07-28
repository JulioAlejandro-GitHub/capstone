import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { isValidPublicId } from '../router';
import {
  ApiError,
  api,
  type AnalysisRun,
  type ImageUploadResponse,
  type QualityQueueRecord,
  type SmearWorkflowResponse,
} from '../services/api';
import type { CellDetectionRunDetail } from '../types/cellReview';

export type SmearWorkflowStage =
  | 'setup'
  | 'uploading'
  | 'ingested'
  | 'creating_analysis'
  | 'quality_queued'
  | 'quality_processing'
  | 'quality_warning'
  | 'quality_failed'
  | 'ready_for_detection'
  | 'detection_processing'
  | 'review_ready'
  | 'error';

export type SmearWorkflowFailureStep =
  | 'upload'
  | 'analysis'
  | 'queue'
  | 'quality'
  | 'detection'
  | 'recovery';

export type SmearWorkflowIdentifiers = {
  ingestionBatchId: string | null;
  microscopyImageId: string | null;
  analysisRunId: string | null;
  queueItemId: string | null;
  detectionRunId: string | null;
  selectedDetectionId: string | null;
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
};

const emptyIdentifiers: SmearWorkflowIdentifiers = {
  ingestionBatchId: null,
  microscopyImageId: null,
  analysisRunId: null,
  queueItemId: null,
  detectionRunId: null,
  selectedDetectionId: null,
};

const emptySnapshot: SmearWorkflowSnapshot = {
  upload: null,
  persisted: null,
  analysisRun: null,
  queueItem: null,
  detectionRun: null,
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
  'uploading',
  'ingested',
  'creating_analysis',
  'quality_queued',
  'quality_processing',
  'quality_warning',
  'quality_failed',
  'ready_for_detection',
  'detection_processing',
  'review_ready',
  'error',
]);

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
    recovery: 'No fue posible reconstruir el workflow persistido.',
  };
  return { step, message: fallback[step] };
};

const stageFromResponse = (response: SmearWorkflowResponse): SmearWorkflowStage =>
  workflowStages.has(response.stage as SmearWorkflowStage)
    ? response.stage as SmearWorkflowStage
    : 'error';

const persistedFailure = (response: SmearWorkflowResponse): SmearWorkflowError | null => {
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

  const queryIdentifiers = useMemo(() => ({
    batch: searchParams.get('batch'),
    analysis: searchParams.get('analysis'),
    queue: searchParams.get('queue'),
    detection: searchParams.get('detection') ?? searchParams.get('detection_run_id'),
    image: searchParams.get('image'),
    selected: searchParams.get('selected'),
  }), [searchParams]);

  const writeIdentifiers = useCallback((
    values: Partial<SmearWorkflowIdentifiers>,
  ) => {
    setIdentifiers((current) => ({ ...current, ...values }));
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      const queryMap: Array<[keyof SmearWorkflowIdentifiers, string]> = [
        ['ingestionBatchId', 'batch'],
        ['microscopyImageId', 'image'],
        ['analysisRunId', 'analysis'],
        ['queueItemId', 'queue'],
        ['detectionRunId', 'detection'],
        ['selectedDetectionId', 'selected'],
      ];
      queryMap.forEach(([stateKey, queryKey]) => {
        if (!(stateKey in values)) return;
        const value = values[stateKey];
        if (value) next.set(queryKey, value);
        else next.delete(queryKey);
      });
      next.delete('detection_run_id');
      return next;
    }, { replace: true });
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
    if (!candidate.batch && !candidate.analysis && !candidate.detection) {
      setRecovering(false);
      return;
    }
    setRecovering(true);
    setFailure(null);
    try {
      let batchId = candidate.batch;
      if (!batchId && candidate.detection) {
        const detection = await api.getCellDetectionRun(candidate.detection);
        const analysis = await api.getAnalysisRun(detection.analysis_run_id);
        batchId = analysis.ingestion_batch_id;
      } else if (!batchId && candidate.analysis) {
        const analysis = await api.getAnalysisRun(candidate.analysis);
        batchId = analysis.ingestion_batch_id;
      }
      if (!batchId) throw new Error('workflow without batch');
      const response = await api.getSmearWorkflow(batchId);
      setIdentifiers((current) => ({
        ...current,
        selectedDetectionId: candidate.selected ?? current.selectedDetectionId,
      }));
      const firstImage = response.images[0] ?? null;
      const requestedImage = response.images.find((image) => image.id === candidate.image) ?? null;
      const nextIdentifiers: SmearWorkflowIdentifiers = {
        ingestionBatchId: response.batch.id,
        microscopyImageId: requestedImage?.id ?? firstImage?.id ?? null,
        analysisRunId: response.analysis_run?.id ?? candidate.analysis,
        queueItemId: queueId(response.queue_item) ?? candidate.queue,
        detectionRunId: response.detection_run?.id ?? candidate.detection,
        selectedDetectionId: candidate.selected,
      };
      setSnapshot({
        upload: null,
        persisted: response,
        analysisRun: response.analysis_run,
        queueItem: response.queue_item,
        detectionRun: response.detection_run,
      });
      setIdentifiers(nextIdentifiers);
      writeIdentifiers(nextIdentifiers);
      setFailure(persistedFailure(response));
      setStage(stageFromResponse(response));
    } catch (error) {
      setFailure(sanitizeFailure(error, 'recovery'));
      setStage('error');
    } finally {
      setRecovering(false);
    }
  }, [writeIdentifiers]);

  useEffect(() => {
    const key = [
      queryIdentifiers.batch,
      queryIdentifiers.analysis,
      queryIdentifiers.detection,
    ].join('|');
    if (!key.replaceAll('|', '') || activeAction.current || hydratedKey.current === key) return;
    hydratedKey.current = key;
    void recover(queryIdentifiers);
  }, [
    queryIdentifiers.analysis,
    queryIdentifiers.batch,
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

  const executeDetection = useCallback(async (analysisRun: AnalysisRun) => {
    setStage('detection_processing');
    setFailure(null);
    try {
      const detectionRun = await api.createCellDetectionRun(analysisRun.id);
      setSnapshot((current) => ({ ...current, detectionRun }));
      writeIdentifiers({ detectionRunId: detectionRun.id });
      if (detectionRun.status === 'completed' || detectionRun.status === 'completed_with_warnings') {
        setStage('review_ready');
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
  }, [writeIdentifiers]);

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
            }));
            writeIdentifiers({
              analysisRunId: persisted.analysis_run.id,
              queueItemId: queueId(persisted.queue_item),
              detectionRunId: persisted.detection_run?.id ?? null,
            });
            if (persisted.detection_run) {
              setFailure(persistedFailure(persisted));
              setStage(stageFromResponse(persisted));
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
    executeDetection,
    executeQueuedQuality,
    writeIdentifiers,
  ]);

  const start = useCallback(async (form: FormData) => {
    if (activeAction.current) return;
    activeAction.current = true;
    setFailure(null);
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
    if (failure.step === 'recovery') {
      await recover(queryIdentifiers);
    }
  }, [
    createAnalysisAndContinue,
    createQueueAndAssess,
    executeDetection,
    failure,
    identifiers.ingestionBatchId,
    queryIdentifiers,
    recover,
    snapshot.analysisRun,
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
      }
    } finally {
      activeAction.current = false;
    }
  }, [
    createAnalysisAndContinue,
    createQueueAndAssess,
    executeDetection,
    executeQueuedQuality,
    identifiers.ingestionBatchId,
    snapshot.analysisRun,
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
      image: identifiers.microscopyImageId,
      selected: identifiers.selectedDetectionId,
    });
  }, [identifiers, recover]);

  const selectDetection = useCallback((id: string | null) => {
    writeIdentifiers({ selectedDetectionId: id });
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
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      ['batch', 'image', 'analysis', 'queue', 'detection', 'detection_run_id', 'selected']
        .forEach((key) => next.delete(key));
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  return {
    stage,
    identifiers,
    snapshot,
    selectedFiles,
    previewUrl,
    failure,
    recovering,
    busy: activeAction.current || recovering || [
      'uploading',
      'creating_analysis',
      'quality_processing',
      'detection_processing',
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
    newAnalysis,
  };
}

export type SmearWorkflowController = ReturnType<typeof useSmearAnalysisWorkflow>;
