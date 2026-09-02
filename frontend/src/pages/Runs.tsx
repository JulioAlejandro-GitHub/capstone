import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { Loading } from '../components/Loading';
import { ReportFilters } from '../components/reports/ReportFilters';
import {
  ReportSelectFilter,
  type ReportFilterOption,
} from '../components/reports/ReportSelectFilter';
import {
  TrainingRunGroupCard,
  type TrainingChildrenLoadState,
} from '../components/reports/TrainingRunGroupCard';
import { ApiError, api } from '../services/api';
import type {
  Stage2Availability,
  TrainingSummaryCollection,
} from '../types/api';
import '../styles/report-components.css';

interface RunsProps {
  datasource: string;
  onRunSelect: (runId: string) => void;
}

const MISSING_MODEL_FILTER = 'missing:';
const MODEL_FILTER_PREFIX = 'model:';
const EMPTY_CHILDREN_STATE: TrainingChildrenLoadState = {
  status: 'idle',
  data: null,
  error: null,
  loaded: false,
};

function normalizedLabel(value: string | null | undefined): string | null {
  return value?.trim() || null;
}

function modelFilterValue(modelName: string | null | undefined): string {
  const normalizedModel = normalizedLabel(modelName);
  return normalizedModel ? `${MODEL_FILTER_PREFIX}${normalizedModel}` : MISSING_MODEL_FILTER;
}

function visibleRunId(runId: string): string {
  return runId.length > 12 ? `${runId.slice(0, 8)}…` : runId;
}

function processLabel(runType: string): string {
  if (runType === 'training') return 'TRAIN';
  if (runType === 'evaluation') return 'EVALUATE';
  if (runType === 'explainability') return 'EXPLAIN';
  return runType.toUpperCase();
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

  const loadChildren = useCallback(async (trainingRunId: string, retry = false) => {
    const requestDatasource = datasource;
    const key = childrenCacheKey(requestDatasource, trainingRunId);
    const current = childrenByKeyRef.current[key] ?? EMPTY_CHILDREN_STATE;
    if (current.status === 'loading' || current.status === 'success') return;
    if (current.status === 'error' && !retry) return;

    const controller = new AbortController();
    childrenControllers.current.set(key, controller);
    commitChildrenState(key, { status: 'loading', data: null, error: null, loaded: false });

    try {
      const response = await api.getTrainingLineageChildren({
        trainingRunId,
        datasource: requestDatasource,
        limit: 100,
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
      const [release, preview] = await Promise.all([
        api.getStage2ReleaseStatus(requestDatasource, runId, controller.signal),
        api.getStage2Availability(requestDatasource, runId, controller.signal),
      ]);
      if (!mounted.current || activeDatasource.current !== requestDatasource) return null;
      const response: Stage2Availability = {
        ...release,
        technical_blockers: preview.technical_blockers,
      };
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
    const modelVersionId = stage2Status[runId]?.model_version_id;
    if (!modelVersionId) return 'failed';
    setStage2Loading((current) => ({ ...current, [runId]: true }));
    setStage2Errors((current) => {
      const next = { ...current };
      delete next[runId];
      return next;
    });
    try {
      if (!replaceExisting) {
        const current = await api.getProductiveModelAvailability(datasource);
        if (current.available && current.model?.model_version_id !== modelVersionId) {
          return 'replacement-required';
        }
      }
      const response = await api.publishStage2Model(datasource, modelVersionId, {
        reason: 'Disponibilización técnica desde el reporte de Ejecuciones',
        replace_existing: replaceExisting,
      });
      setStage2Status((current) => ({ ...current, [runId]: response }));
      await Promise.all(
        Object.keys(stage2Status)
          .filter((visibleId) => visibleId !== runId)
          .map((visibleId) => loadStage2(visibleId, true)),
      );
      return 'published';
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 409 && reason.message.includes('STAGE2_SELECTION_EXISTS')) {
        return 'replacement-required';
      }
      const message = reason instanceof ApiError && reason.message
        ? `No fue posible publicar el modelo: ${reason.message}`
        : promotionErrorMessage(reason);
      setStage2Errors((current) => ({ ...current, [runId]: message }));
      return 'failed';
    } finally {
      setStage2Loading((current) => ({ ...current, [runId]: false }));
    }
  };

  const deactivateStage2 = async (runId: string) => {
    const publicationId = stage2Status[runId]?.publication?.id;
    if (!publicationId) return;
    setStage2Loading((current) => ({ ...current, [runId]: true }));
    setStage2Errors((current) => {
      const next = { ...current };
      delete next[runId];
      return next;
    });
    try {
      const response = await api.deactivateStage2Publication(datasource, publicationId, {
        reason: 'Baja técnica desde el reporte de Ejecuciones',
      });
      setStage2Status((current) => ({ ...current, [runId]: response }));
    } catch (reason) {
      setStage2Errors((current) => ({ ...current, [runId]: promotionErrorMessage(reason) }));
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
      children.evaluations.forEach((run) => result.set(run.run_id, children.training_run_id));
      children.explainabilities.forEach((run) => result.set(run.run_id, children.training_run_id));
    });
    return result;
  }, [loadedChildren]);

  const runOptions = useMemo<ReportFilterOption[]>(() => {
    if (!summaries) return [];
    const options = new Map<string, ReportFilterOption>();
    const addOption = (runId: string, runName: string | null, runType: string) => {
      options.set(runId, {
        value: runId,
        label: `${processLabel(runType)} · ${normalizedLabel(runName) || 'No registrado'} · ${visibleRunId(runId)}`,
      });
    };
    summaries.items.forEach((training) => addOption(training.run_id, training.run_name, training.run_type));
    loadedChildren.forEach((children) => {
      children.evaluations.forEach((run) => addOption(run.run_id, run.run_name, run.run_type));
      children.explainabilities.forEach((run) => addOption(run.run_id, run.run_name, run.run_type));
    });
    return Array.from(options.values());
  }, [loadedChildren, summaries]);

  const modelOptions = useMemo<ReportFilterOption[]>(() => {
    if (!summaries) return [];
    const options = new Map<string, ReportFilterOption>();
    summaries.items.forEach((training) => {
      const modelName = normalizedLabel(training.model_name);
      options.set(modelFilterValue(modelName), {
        value: modelFilterValue(modelName),
        label: modelName || 'No registrado',
      });
    });
    return Array.from(options.values()).sort((left, right) => (
      left.label.localeCompare(right.label, 'es', { sensitivity: 'base' })
    ));
  }, [summaries]);

  const filteredTrainings = useMemo(() => summaries?.items.filter((training) => (
    (!selectedRunId
      || training.run_id === selectedRunId
      || childParentByRunId.get(selectedRunId) === training.run_id)
    && (!selectedModel || modelFilterValue(training.model_name) === selectedModel)
  )) ?? [], [childParentByRunId, selectedModel, selectedRunId, summaries]);

  const hasActiveFilters = Boolean(selectedRunId || selectedModel);
  const hasRuns = Boolean(summaries && summaries.items.length > 0);
  const visibleEvaluationCount = filteredTrainings.reduce(
    (total, training) => total + training.evaluation_count,
    0,
  );
  const visibleExplainabilityCount = filteredTrainings.reduce(
    (total, training) => total + training.explainability_count,
    0,
  );

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
      <section className="panel report-panel">
        <ReportFilters
          hasActiveFilters={hasActiveFilters}
          onClear={() => {
            setSelectedRunId('');
            setSelectedModel('');
            const next = new URLSearchParams(searchParams);
            next.delete('run');
            next.delete('modelo');
            setSearchParams(next);
          }}
        >
          <ReportSelectFilter
            allLabel="Todos los RUN"
            disabled={runOptions.length === 0}
            id="runs-filter-run"
            label="RUN"
            onChange={(value) => updateFilter('run', value)}
            options={runOptions}
            value={selectedRunId}
          />
          <ReportSelectFilter
            allLabel="Todos los modelos"
            disabled={modelOptions.length === 0}
            id="runs-filter-model"
            label="Modelo"
            onChange={(value) => updateFilter('modelo', value)}
            options={modelOptions}
            value={selectedModel}
          />
        </ReportFilters>
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
            <div aria-label="Entrenamientos agrupados por linaje" className="report-table">
              <div aria-hidden="true" className="report-table__header">
                <span className="report-section-title">RUN</span>
                <span className="report-section-title">Modelo</span>
                <span className="report-section-title">Resultados</span>
                <span className="report-section-title">Análisis automático</span>
              </div>
              {filteredTrainings.map((training) => {
                const key = childrenCacheKey(datasource, training.run_id);
                return <TrainingRunGroupCard
                  childrenState={childrenByKey[key] ?? EMPTY_CHILDREN_STATE}
                  key={key}
                  onChildrenExpand={() => { void loadChildren(training.run_id); }}
                  onChildrenRetry={() => { void loadChildren(training.run_id, true); }}
                  onRunSelect={onRunSelect}
                  onStage2Deactivate={() => deactivateStage2(training.run_id)}
                  onStage2Open={() => { void loadStage2(training.run_id); }}
                  onStage2Publish={(replaceExisting) => publishStage2(training.run_id, replaceExisting)}
                  stage2Error={stage2Errors[training.run_id]}
                  stage2Loading={stage2Loading[training.run_id] ?? false}
                  stage2Status={stage2Status[training.run_id]}
                  training={training}
                />;
              })}
            </div>
          </>
        )}
      </section>
    </section>
  );
}
