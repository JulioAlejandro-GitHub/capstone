import { useEffect, useMemo, useState } from 'react';

import { Loading } from '../components/Loading';
import { ReportFilters } from '../components/reports/ReportFilters';
import {
  ReportSelectFilter,
  type ReportFilterOption,
} from '../components/reports/ReportSelectFilter';
import { TrainingRunGroupCard } from '../components/reports/TrainingRunGroupCard';
import { UnlinkedRunsSection } from '../components/reports/UnlinkedRunsSection';
import { api } from '../services/api';
import type {
  GroupedRunLineageResponse,
  TrainingRunLineageGroup,
  TrainingPromotionStatus,
  UnresolvedLineageRun,
} from '../types/api';
import '../styles/report-components.css';

interface RunsProps {
  datasource: string;
  onRunSelect: (runId: string) => void;
  onModelVersionSelect: (modelVersionId: string) => void;
  onDeploymentSelect: (deploymentId: string) => void;
}

const MISSING_MODEL_FILTER = 'missing:';
const MODEL_FILTER_PREFIX = 'model:';

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

function groupContainsRun(group: TrainingRunLineageGroup, runId: string): boolean {
  return group.training.run_id === runId
    || group.evaluations.some((run) => run.run_id === runId)
    || group.explainability.some((run) => run.run_id === runId);
}

function promotionErrorMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  if (message.includes('tiempo de espera')) return 'La consulta tardó demasiado. Intenta nuevamente.';
  return 'No fue posible consultar el estado de liberación.';
}

export function Runs({
  datasource,
  onRunSelect,
  onModelVersionSelect,
  onDeploymentSelect,
}: RunsProps) {
  const [lineage, setLineage] = useState<GroupedRunLineageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [promotionStatus, setPromotionStatus] = useState<Record<string, TrainingPromotionStatus>>({});
  const [promotionErrors, setPromotionErrors] = useState<Record<string, string>>({});
  const [promotionLoading, setPromotionLoading] = useState<Record<string, boolean>>({});
  const [preparingRunId, setPreparingRunId] = useState<string | null>(null);
  const [promotionNotice, setPromotionNotice] = useState<string | null>(null);

  const loadPromotionStatus = async (runId: string) => {
    setPromotionLoading((current) => ({ ...current, [runId]: true }));
    setPromotionErrors((current) => {
      const next = { ...current };
      delete next[runId];
      return next;
    });
    try {
      const response = await api.getTrainingPromotionStatus(datasource, runId);
      setPromotionStatus((current) => ({ ...current, [runId]: response }));
      return response;
    } catch (reason) {
      setPromotionErrors((current) => ({
        ...current,
        [runId]: promotionErrorMessage(reason),
      }));
      return null;
    } finally {
      setPromotionLoading((current) => ({ ...current, [runId]: false }));
    }
  };

  useEffect(() => {
    let active = true;
    setError(null);
    setLineage(null);
    setSelectedRunId('');
    setSelectedModel('');
    setPromotionStatus({});
    setPromotionErrors({});
    setPromotionLoading({});
    setPreparingRunId(null);
    setPromotionNotice(null);
    api
      .getGroupedRunLineage(datasource)
      .then((response) => {
        if (active) {
          setLineage(response);
          response.items.forEach((group) => {
            void loadPromotionStatus(group.training.run_id);
          });
        }
      })
      .catch((err: Error) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [datasource]);

  const navigateForPromotion = (status: TrainingPromotionStatus) => {
    if (
      ['review_model_version', 'approve_model_version', 'create_deployment'].includes(status.next_action)
      && status.model_version_id
    ) {
      onModelVersionSelect(status.model_version_id);
      return;
    }
    if (
      ['review_pending_deployment', 'view_active_deployment'].includes(status.next_action)
      && status.deployment_id
    ) {
      onDeploymentSelect(status.deployment_id);
    }
  };

  const handlePromotionAction = async (runId: string) => {
    if (preparingRunId) return;
    const current = promotionStatus[runId];
    if (!current) {
      await loadPromotionStatus(runId);
      return;
    }
    if (current.next_action !== 'prepare_release') {
      navigateForPromotion(current);
      return;
    }
    setPreparingRunId(runId);
    setPromotionNotice(null);
    setPromotionErrors((errors) => {
      const next = { ...errors };
      delete next[runId];
      return next;
    });
    try {
      const prepared = await api.prepareTrainingRelease(datasource, runId);
      setPromotionStatus((statuses) => ({ ...statuses, [runId]: prepared }));
      setPromotionNotice('La versión fue preparada correctamente.');
      navigateForPromotion(prepared);
    } catch (reason) {
      const message = promotionErrorMessage(reason);
      await loadPromotionStatus(runId);
      setPromotionErrors((errors) => ({ ...errors, [runId]: message }));
    } finally {
      setPreparingRunId(null);
    }
  };

  const unresolvedRuns = useMemo<UnresolvedLineageRun[]>(() => (
    lineage
      ? [
          ...lineage.unlinked.evaluations,
          ...lineage.unlinked.explainability,
          ...lineage.conflicts.evaluations,
          ...lineage.conflicts.explainability,
        ]
      : []
  ), [lineage]);

  const runOptions = useMemo<ReportFilterOption[]>(() => {
    if (!lineage) return [];
    const options = new Map<string, ReportFilterOption>();

    const addOption = (runId: string, runName: string | null, runType: string) => {
      options.set(runId, {
        value: runId,
        label: `${processLabel(runType)} · ${normalizedLabel(runName) || 'No registrado'} · ${visibleRunId(runId)}`,
      });
    };

    lineage.items.forEach((group) => {
      addOption(group.training.run_id, group.training.run_name, 'training');
      group.evaluations.forEach((run) => addOption(run.run_id, run.run_name, run.run_type));
      group.explainability.forEach((run) => addOption(run.run_id, run.run_name, run.run_type));
    });
    unresolvedRuns.forEach((run) => addOption(run.run_id, run.run_name, run.run_type));
    return Array.from(options.values());
  }, [lineage, unresolvedRuns]);

  const modelOptions = useMemo<ReportFilterOption[]>(() => {
    if (!lineage) return [];
    const options = new Map<string, ReportFilterOption>();
    const addModel = (rawModelName: string | null | undefined) => {
      const modelName = normalizedLabel(rawModelName);
      const value = modelFilterValue(modelName);
      options.set(value, { value, label: modelName || 'No registrado' });
    };
    lineage.items.forEach((group) => addModel(group.training.model_name));
    unresolvedRuns.forEach((run) => addModel(run.model_name));
    return Array.from(options.values()).sort((left, right) => (
      left.label.localeCompare(right.label, 'es', { sensitivity: 'base' })
    ));
  }, [lineage, unresolvedRuns]);

  const filteredGroups = useMemo(() => {
    if (!lineage) return [];
    return lineage.items.filter((group) => (
      (!selectedRunId || groupContainsRun(group, selectedRunId))
      && (!selectedModel || modelFilterValue(group.training.model_name) === selectedModel)
    ));
  }, [lineage, selectedModel, selectedRunId]);

  const filteredUnresolvedRuns = useMemo(() => unresolvedRuns.filter((run) => (
    (!selectedRunId || run.run_id === selectedRunId)
    && (!selectedModel || modelFilterValue(run.model_name) === selectedModel)
  )), [selectedModel, selectedRunId, unresolvedRuns]);

  const hasActiveFilters = Boolean(selectedRunId || selectedModel);
  const hasRuns = Boolean(lineage && (lineage.items.length > 0 || unresolvedRuns.length > 0));
  const hasVisibleRuns = filteredGroups.length > 0 || filteredUnresolvedRuns.length > 0;
  const visibleEvaluationCount = filteredGroups.reduce(
    (total, group) => total + group.evaluations.length,
    0,
  );
  const visibleExplainabilityCount = filteredGroups.reduce(
    (total, group) => total + group.explainability.length,
    0,
  );

  if (error) return <section className="panel error">{error}</section>;
  if (!lineage) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Ejecuciones</h1>
          <p>Linaje read-only de cada entrenamiento y sus procesos derivados.</p>
        </div>
      </div>
      <section className="panel report-panel">
        {promotionNotice ? (
          <div className="run-promotion-notice" role="status">{promotionNotice}</div>
        ) : null}
        <ReportFilters
          hasActiveFilters={hasActiveFilters}
          onClear={() => {
            setSelectedRunId('');
            setSelectedModel('');
          }}
        >
          <ReportSelectFilter
            allLabel="Todos los RUN"
            disabled={runOptions.length === 0}
            id="runs-filter-run"
            label="RUN"
            onChange={setSelectedRunId}
            options={runOptions}
            value={selectedRunId}
          />
          <ReportSelectFilter
            allLabel="Todos los modelos"
            disabled={modelOptions.length === 0}
            id="runs-filter-model"
            label="Modelo"
            onChange={setSelectedModel}
            options={modelOptions}
            value={selectedModel}
          />
        </ReportFilters>
        {!hasRuns ? (
          <div className="report-empty-state" role="status">Sin ejecuciones registradas</div>
        ) : !hasVisibleRuns ? (
          <div className="report-empty-state" role="status">
            No hay ejecuciones que coincidan con los filtros seleccionados.
          </div>
        ) : (
          <>
            <div className="run-lineage-overview" aria-live="polite">
              <span><strong>{filteredGroups.length}</strong> trainings</span>
              <span><strong>{visibleEvaluationCount}</strong> evaluate vinculados</span>
              <span><strong>{visibleExplainabilityCount}</strong> explain vinculados</span>
              <span><strong>{filteredUnresolvedRuns.length}</strong> sin linaje resuelto</span>
            </div>
            {filteredGroups.length > 0 ? (
              <div aria-label="Entrenamientos agrupados por linaje" className="report-table">
                <div aria-hidden="true" className="report-table__header">
                  <span className="report-section-title">RUN</span>
                  <span className="report-section-title">Modelo</span>
                  <span className="report-section-title">Resultados</span>
                  <span className="report-section-title">Análisis automático</span>
                </div>
                {filteredGroups.map((group) => (
                  <TrainingRunGroupCard
                    group={group}
                    key={group.training.run_id}
                    onRunSelect={onRunSelect}
                    onPromotionAction={handlePromotionAction}
                    promotionError={promotionErrors[group.training.run_id]}
                    promotionLoading={promotionLoading[group.training.run_id] ?? false}
                    promotionPreparing={preparingRunId === group.training.run_id}
                    promotionStatus={promotionStatus[group.training.run_id]}
                  />
                ))}
              </div>
            ) : null}
            <UnlinkedRunsSection
              defaultOpen={Boolean(selectedRunId)}
              key={`unresolved-${selectedRunId || 'all'}`}
              runs={filteredUnresolvedRuns}
              onRunSelect={onRunSelect}
            />
          </>
        )}
      </section>
    </section>
  );
}
