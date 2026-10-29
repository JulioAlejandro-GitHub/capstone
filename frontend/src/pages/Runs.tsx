import { routes, withAllowedQuery } from '../router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { Loading } from '../components/Loading';
import { RunAnalysisCell } from '../components/reports/RunSummaryRow';
import {
  TrainingRunDetailPanel,
  isStage2Active,
  type TrainingChildrenLoadState,
} from '../components/reports/TrainingRunGroupCard';
import { TrainingRunsTable } from '../components/reports/TrainingRunsTable';
import { ApiError, api } from '../services/api';
import type {
  Stage2Availability,
  TrainingSummary,
  TrainingSummaryCollection,
} from '../types/api';
import '../styles/report-components.css';

interface RunsProps {
  datasource: string;
  onRunSelect: (runId: string) => void;
}

const EMPTY_CHILDREN_STATE: TrainingChildrenLoadState = {
  status: 'idle',
  data: null,
  error: null,
  loaded: false,
};

function visibleRunId(runId: string): string {
  return runId.length > 12 ? `${runId.slice(0, 8)}…` : runId;
}

function childrenCacheKey(datasource: string, trainingRunId: string): string {
  return `${datasource}:${trainingRunId}`;
}

function promotionErrorMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  if (message.includes('tiempo de espera')) return 'La consulta tardó demasiado. Intenta nuevamente.';
  return 'No fue posible consultar el estado de liberación.';
}

function lineageChildrenErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.kind === 'timeout') {
    return 'La carga tardó demasiado. Intenta nuevamente.';
  }
  return 'No fue posible cargar las ejecuciones asociadas.';
}

export function Runs({ datasource, onRunSelect }: RunsProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [summaries, setSummaries] = useState<TrainingSummaryCollection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [selectedRunId, setSelectedRunId] = useState(() => searchParams.get('run') ?? '');
  const [selectedModel, setSelectedModel] = useState(() => searchParams.get('modelo') ?? '');
  const [childrenByKey, setChildrenByKey] = useState<Record<string, TrainingChildrenLoadState>>({});
  const [childrenOpen, setChildrenOpen] = useState<Record<string, boolean>>({});
  const [stage2Open, setStage2Open] = useState<Record<string, boolean>>({});
  const childrenByKeyRef = useRef<Record<string, TrainingChildrenLoadState>>({});
  const childrenControllers = useRef(new Map<string, AbortController>());
  const activeDatasource = useRef(datasource);
  const mounted = useRef(false);

  const [stage2Status, setStage2Status] = useState<Record<string, Stage2Availability>>({});
  const [stage2Loading, setStage2Loading] = useState<Record<string, boolean>>({});
  const [stage2Errors, setStage2Errors] = useState<Record<string, string>>({});
  const stage2LoadState = useRef<Record<string, 'idle' | 'loading' | 'success' | 'error'>>({});
  const stage2Controllers = useRef(new Map<string, AbortController>());

  activeDatasource.current = datasource;

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    setSelectedRunId(searchParams.get('run') ?? '');
    setSelectedModel(searchParams.get('modelo') ?? '');
  }, [searchParams]);

  const updateFilter = (key: 'run' | 'modelo', value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
    if (key === 'run') setSelectedRunId(value);
    else setSelectedModel(value);
  };

  const commitChildrenState = useCallback((key: string, state: TrainingChildrenLoadState) => {
    if (!mounted.current) return;
    const next = { ...childrenByKeyRef.current, [key]: state };
    childrenByKeyRef.current = next;
    setChildrenByKey(next);
  }, []);

  const loadChildren = useCallback(async (trainingRunId: string, retry = false, offset = 0) => {
    const requestDatasource = datasource;
    const key = childrenCacheKey(requestDatasource, trainingRunId);
    const current = childrenByKeyRef.current[key] ?? EMPTY_CHILDREN_STATE;
    if (current.status === 'loading' || (current.status === 'success' && !retry)) return;
    if (current.status === 'error' && !retry) return;

    const controller = new AbortController();
    childrenControllers.current.set(key, controller);
    commitChildrenState(key, { status: 'loading', data: null, error: null, loaded: false });

    try {
      const response = await api.getTrainingLineageChildren({
        trainingRunId,
        datasource: requestDatasource,
        limit: 100,
        offset,
        signal: controller.signal,
      });
      if (!mounted.current || activeDatasource.current !== requestDatasource) return;
      if (response.training_run_id !== trainingRunId) {
        console.error('Respuesta de linaje descartada: el TRAIN solicitado no coincide.');
        commitChildrenState(key, {
          status: 'error',
          data: null,
          error: 'La respuesta recibida no corresponde a este entrenamiento.',
          loaded: false,
        });
        return;
      }

      const reconciledTotal = response.evaluation_count + response.explainability_count;
      if (response.total_count !== reconciledTotal) {
        console.warn('Los contadores de linaje recibidos no son internamente coherentes.');
      }
      setSummaries((currentSummaries) => currentSummaries ? {
        ...currentSummaries,
        items: currentSummaries.items.map((training) => {
          if (training.run_id !== trainingRunId) return training;
          if (
            training.evaluation_count === response.evaluation_count
            && training.explainability_count === response.explainability_count
          ) return training;
          return {
            ...training,
            evaluation_count: response.evaluation_count,
            explainability_count: response.explainability_count,
          };
        }),
      } : currentSummaries);
      commitChildrenState(key, {
        status: 'success',
        data: response,
        error: null,
        loaded: true,
      });
    } catch (reason) {
      if (reason instanceof ApiError && reason.kind === 'abort') return;
      if (!mounted.current || activeDatasource.current !== requestDatasource) return;
      commitChildrenState(key, {
        status: 'error',
        data: null,
        error: lineageChildrenErrorMessage(reason),
        loaded: false,
      });
    } finally {
      if (childrenControllers.current.get(key) === controller) {
        childrenControllers.current.delete(key);
      }
    }
  }, [commitChildrenState, datasource]);

  const loadStage2 = useCallback(async (runId: string, force = false) => {
    const currentLoadState = stage2LoadState.current[runId] ?? 'idle';
    if (!force && (currentLoadState === 'loading' || currentLoadState === 'success')) {
      return stage2Status[runId] ?? null;
    }
    const requestDatasource = datasource;
    const controller = new AbortController();
    stage2Controllers.current.get(runId)?.abort();
    stage2Controllers.current.set(runId, controller);
    stage2LoadState.current[runId] = 'loading';
    setStage2Loading((current) => ({ ...current, [runId]: true }));
    setStage2Errors((current) => {
      const next = { ...current };
      delete next[runId];
      return next;
    });
    try {
      const response = await api.getStage2ReleaseStatus(requestDatasource, runId, controller.signal);
      if (!mounted.current || activeDatasource.current !== requestDatasource) return null;
      stage2LoadState.current[runId] = 'success';
      setStage2Status((current) => ({ ...current, [runId]: response }));
      return response;
    } catch (reason) {
      if (reason instanceof ApiError && reason.kind === 'abort') {
        stage2LoadState.current[runId] = 'idle';
        return null;
      }
      if (!mounted.current || activeDatasource.current !== requestDatasource) return null;
      stage2LoadState.current[runId] = 'error';
      setStage2Status((current) => {
        const next = { ...current };
        delete next[runId];
        return next;
      });
      setStage2Errors((current) => ({ ...current, [runId]: promotionErrorMessage(reason) }));
      return null;
    } finally {
      if (stage2Controllers.current.get(runId) === controller) {
        stage2Controllers.current.delete(runId);
        if (mounted.current && activeDatasource.current === requestDatasource) {
          setStage2Loading((current) => ({ ...current, [runId]: false }));
        }
      }
    }
  }, [datasource, stage2Status]);

  const publishStage2 = async (
    runId: string,
    replaceExisting = false,
  ): Promise<'published' | 'replacement-required' | 'failed'> => {
    const candidate = stage2Status[runId];
    const modelVersionId = candidate?.model_version_id;
    if (!candidate?.eligible) return 'failed';
    setStage2Loading((current) => ({ ...current, [runId]: true }));
    setStage2Errors((current) => {
      const next = { ...current };
      delete next[runId];
      return next;
    });
    try {
      const current = await api.getProductiveModelAvailability(datasource);
      if (current.available && current.model?.model_version_id === modelVersionId
        && !candidate.threshold_update_available) {
        await loadStage2(runId, true);
        return 'published';
      }
      if (current.available && !replaceExisting) return 'replacement-required';
      const activated = await api.activateCellModel(datasource, runId, {
        reason: 'Activación para clasificación celular',
        replace_existing: replaceExisting,
      });
      if (!activated.available_for_inference) throw new Error('No se pudo activar el modelo para clasificación celular.');
      await Promise.all(
        Object.keys(stage2Status).map((visibleId) => loadStage2(visibleId, true)),
      );
      return 'published';
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 409 && reason.message.includes('STAGE2_SELECTION_EXISTS')) {
        return 'replacement-required';
      }
      const message = reason instanceof ApiError && reason.message
        ? `No fue posible activar el modelo: ${reason.message}`
        : reason instanceof Error ? reason.message : 'No fue posible activar el modelo.';
      setStage2Errors((current) => ({ ...current, [runId]: message }));
      return 'failed';
    } finally {
      setStage2Loading((current) => ({ ...current, [runId]: false }));
    }
  };

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    childrenControllers.current.forEach((pending) => pending.abort());
    childrenControllers.current.clear();
    stage2Controllers.current.forEach((pending) => pending.abort());
    stage2Controllers.current.clear();
    childrenByKeyRef.current = {};
    stage2LoadState.current = {};
    setChildrenByKey({});
    setChildrenOpen({});
    setStage2Open({});
    setStage2Status({});
    setStage2Loading({});
    setStage2Errors({});
    setError(null);
    setSummaries(null);

    // Deferring one tick prevents React StrictMode's discarded effect from issuing a duplicate GET.
    const timer = window.setTimeout(() => {
      api.getTrainingSummaries({ datasource, limit: 100, signal: controller.signal })
        .then((response) => {
          if (active && activeDatasource.current === datasource) setSummaries(response);
        })
        .catch((reason: unknown) => {
          if (!active || (reason instanceof ApiError && reason.kind === 'abort')) return;
          setError(reason instanceof Error ? reason.message : 'No fue posible cargar las ejecuciones.');
        });
    }, 0);

    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
      childrenControllers.current.forEach((pending) => pending.abort());
      childrenControllers.current.clear();
      stage2Controllers.current.forEach((pending) => pending.abort());
      stage2Controllers.current.clear();
    };
  }, [datasource, reloadToken]);

  const loadedChildren = useMemo(() => Object.values(childrenByKey)
    .map((entry) => entry.data)
    .filter((entry) => entry !== null), [childrenByKey]);

  const childParentByRunId = useMemo(() => {
    const result = new Map<string, string>();
    loadedChildren.forEach((children) => {
      children.evaluations.forEach((run) => result.set(
        run.source_kind === 'assessment_e6' ? `assessment:${run.attempt_id}` : run.run_id,
        children.training_run_id,
      ));
      children.explainabilities.forEach((run) => result.set(run.source_kind === 'assessment_explain_e6' ? `assessment:${run.attempt_id}` : run.run_id, children.training_run_id));
    });
    return result;
  }, [loadedChildren]);

  const filteredTrainings = useMemo(() => summaries?.items.filter((training) => (
    (!selectedRunId
      || training.run_id === selectedRunId
      || childParentByRunId.get(selectedRunId) === training.run_id)
  )) ?? [], [childParentByRunId, selectedRunId, summaries]);

  const hasRuns = Boolean(summaries && summaries.items.length > 0);
  const visibleEvaluationCount = filteredTrainings.reduce(
    (total, training) => total + training.evaluation_count,
    0,
  );
  const visibleExplainabilityCount = filteredTrainings.reduce(
    (total, training) => total + training.explainability_count,
    0,
  );
  const runFilterTraining = selectedRunId
    ? summaries?.items.find((training) => training.run_id === (childParentByRunId.get(selectedRunId) ?? selectedRunId))
    : undefined;

  const trainingActive = useCallback((training: TrainingSummary) => (
    isStage2Active(training, stage2Status[training.run_id], stage2Errors[training.run_id])
  ), [stage2Errors, stage2Status]);

  const toggleChildren = useCallback((training: TrainingSummary) => {
    const next = !childrenOpen[training.run_id];
    if (next && training.evaluation_count + training.explainability_count === 0) return;
    setChildrenOpen((current) => ({ ...current, [training.run_id]: next }));
    if (next) void loadChildren(training.run_id);
  }, [childrenOpen, loadChildren]);

  const toggleStage2 = useCallback((runId: string) => {
    const next = !stage2Open[runId];
    setStage2Open((current) => ({ ...current, [runId]: next }));
    if (next) void loadStage2(runId);
  }, [loadStage2, stage2Open]);

  const renderAnalysis = useCallback((training: TrainingSummary) => (
    <RunAnalysisCell
      onRunSelect={onRunSelect}
      onStage2Toggle={() => toggleStage2(training.run_id)}
      processKind="training"
      run={training}
      stage2Active={trainingActive(training)}
      stage2ControlsId={`stage2-publication-${training.run_id}`}
      stage2Expanded={stage2Open[training.run_id] ?? false}
    />
  ), [onRunSelect, stage2Open, toggleStage2, trainingActive]);

  const renderDetailPanel = (training: TrainingSummary) => {
    const key = childrenCacheKey(datasource, training.run_id);
    return <TrainingRunDetailPanel datasource={datasource}
      childrenExpanded={childrenOpen[training.run_id] ?? false}
      childrenState={childrenByKey[key] ?? EMPTY_CHILDREN_STATE}
      onChildrenPage={(offset) => { void loadChildren(training.run_id, true, offset); }}
      onChildrenRetry={() => { void loadChildren(training.run_id, true); }}
      onChildrenToggle={() => toggleChildren(training)}
      onRunSelect={onRunSelect}
      onStage2Publish={(replaceExisting) => publishStage2(training.run_id, replaceExisting)}
      onStage2Retry={() => { void loadStage2(training.run_id, true); }}
      stage2Error={stage2Errors[training.run_id]}
      stage2Expanded={stage2Open[training.run_id] ?? false}
      stage2Loading={stage2Loading[training.run_id] ?? false}
      stage2Status={stage2Status[training.run_id]}
      training={training}
    />;
  };

  if (error) return <section className="panel error">
    <p>{error}</p>
    <button className="report-detail-button" onClick={() => setReloadToken((value) => value + 1)} type="button">
      Reintentar
    </button>
  </section>;
  if (!summaries) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Ejecuciones</h1>
          <p>Linaje read-only de cada entrenamiento y sus procesos derivados.</p>
        </div>
      </div>
      <Link className="report-detail-button" to={withAllowedQuery(routes.comparison, { datasource })}>Análisis de Modelos</Link>
      <section className="panel report-panel">
        {selectedRunId ? (
          <div className="trn-url-filter" role="status">
            <span>Filtrado por RUN <code title={selectedRunId}>{visibleRunId(selectedRunId.replace(/^assessment:/, ''))}</code>
              {runFilterTraining ? ` · TRAIN ${runFilterTraining.run_name?.trim() || visibleRunId(runFilterTraining.run_id)}` : ''}</span>
            <button className="report-detail-button" onClick={() => updateFilter('run', '')} type="button">Quitar filtro</button>
          </div>
        ) : null}
        {!hasRuns ? (
          <div className="report-empty-state" role="status">Sin ejecuciones registradas</div>
        ) : filteredTrainings.length === 0 ? (
          <div className="report-empty-state" role="status">
            No hay ejecuciones que coincidan con los filtros seleccionados.
          </div>
        ) : (
          <>
            <div className="run-lineage-overview" aria-live="polite">
              <span><strong>{filteredTrainings.length}</strong> trainings</span>
              <span><strong>{visibleEvaluationCount}</strong> evaluate vinculados</span>
              <span><strong>{visibleExplainabilityCount}</strong> explain vinculados</span>
            </div>
            <TrainingRunsTable
              isActive={trainingActive}
              modelFilter={selectedModel}
              onModelFilterChange={(value) => updateFilter('modelo', value)}
              onRunSelect={onRunSelect}
              renderAnalysis={renderAnalysis}
              renderDetailPanel={renderDetailPanel}
              trainings={filteredTrainings}
            />
          </>
        )}
      </section>
    </section>
  );
}
