import { useEffect, useMemo, useState } from 'react';

import { Loading } from '../components/Loading';
import { ReportFilters } from '../components/reports/ReportFilters';
import {
  ReportSelectFilter,
  type ReportFilterOption,
} from '../components/reports/ReportSelectFilter';
import { RunSummaryRow } from '../components/reports/RunSummaryRow';
import { api } from '../services/api';
import type { RunDashboard } from '../types/api';
import '../styles/report-components.css';

interface RunsProps {
  datasource: string;
  onRunSelect: (runId: string) => void;
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

export function Runs({ datasource, onRunSelect }: RunsProps) {
  const [runs, setRuns] = useState<RunDashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [selectedModel, setSelectedModel] = useState('');

  useEffect(() => {
    let active = true;
    setError(null);
    setRuns(null);
    setSelectedRunId('');
    setSelectedModel('');
    api
      .getRuns(datasource)
      .then((response) => {
        if (active) setRuns(response.items);
      })
      .catch((err: Error) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [datasource]);

  const runOptions = useMemo<ReportFilterOption[]>(() => {
    if (!runs) return [];
    const options = new Map<string, ReportFilterOption>();
    runs.forEach((run) => {
      options.set(run.run_id, {
        value: run.run_id,
        label: `${normalizedLabel(run.run_name) || 'No registrado'} · ${visibleRunId(run.run_id)}`,
      });
    });
    return Array.from(options.values());
  }, [runs]);

  const modelOptions = useMemo<ReportFilterOption[]>(() => {
    if (!runs) return [];
    const options = new Map<string, ReportFilterOption>();
    runs.forEach((run) => {
      const modelName = normalizedLabel(run.model_name);
      const value = modelFilterValue(modelName);
      options.set(value, { value, label: modelName || 'No registrado' });
    });
    return Array.from(options.values()).sort((left, right) => (
      left.label.localeCompare(right.label, 'es', { sensitivity: 'base' })
    ));
  }, [runs]);

  const filteredRuns = useMemo(() => {
    if (!runs) return [];
    return runs.filter((run) => (
      (!selectedRunId || run.run_id === selectedRunId)
      && (!selectedModel || modelFilterValue(run.model_name) === selectedModel)
    ));
  }, [runs, selectedModel, selectedRunId]);

  const hasActiveFilters = Boolean(selectedRunId || selectedModel);

  if (error) return <section className="panel error">{error}</section>;
  if (!runs) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Ejecuciones</h1>
          <p>Listado read-only de runs registrados por el tracking.</p>
        </div>
      </div>
      <section className="panel report-panel">
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
        {runs.length === 0 ? (
          <div className="report-empty-state" role="status">Sin ejecuciones registradas</div>
        ) : filteredRuns.length === 0 ? (
          <div className="report-empty-state" role="status">
            No hay ejecuciones que coincidan con los filtros seleccionados.
          </div>
        ) : (
          <div
            aria-label="Resumen de ejecuciones"
            aria-rowcount={filteredRuns.length + 1}
            className="report-table"
            role="table"
          >
            <div className="report-table__header" role="row">
              <span className="report-section-title" role="columnheader">RUN</span>
              <span className="report-section-title" role="columnheader">Modelo</span>
              <span className="report-section-title" role="columnheader">Resultados</span>
              <span className="report-section-title" role="columnheader">Análisis automático</span>
            </div>
            {filteredRuns.map((run) => (
              <RunSummaryRow key={run.run_id} run={run} onRunSelect={onRunSelect} />
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
