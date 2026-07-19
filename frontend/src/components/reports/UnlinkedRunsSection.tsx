import { StatusBadge } from '../StatusBadge';
import type { UnresolvedLineageRun } from '../../types/api';
import { ReportBadge } from './ReportBadge';
import { RunProcessBadge, type RunProcessKind } from './RunProcessBadge';

interface UnlinkedRunsSectionProps {
  defaultOpen?: boolean;
  onRunSelect: (runId: string) => void;
  runs: UnresolvedLineageRun[];
}

function visibleRunId(runId: string): string {
  return runId.length > 12 ? `${runId.slice(0, 8)}…` : runId;
}

function processKind(runType: UnresolvedLineageRun['run_type']): Exclude<RunProcessKind, 'training'> {
  return runType === 'explainability' ? 'explainability' : 'evaluation';
}

export function UnlinkedRunsSection({
  defaultOpen = false,
  runs,
  onRunSelect,
}: UnlinkedRunsSectionProps) {
  if (runs.length === 0) return null;

  return (
    <details className="unlinked-runs" open={defaultOpen || undefined}>
      <summary>
        <span>
          <strong>Ejecuciones sin linaje</strong>
          <small>Estas ejecuciones no tienen entrenamiento origen resuelto.</small>
        </span>
        <ReportBadge level="warning">
          {runs.length} {runs.length === 1 ? 'ejecución' : 'ejecuciones'}
        </ReportBadge>
      </summary>
      <div className="unlinked-runs__list">
        {runs.map((run) => (
          <article
            aria-label={`Ejecución sin linaje ${run.run_name?.trim() || run.run_id}`}
            className="unlinked-run-card"
            key={run.run_id}
          >
            <div className="unlinked-run-card__badges">
              <RunProcessBadge kind={processKind(run.run_type)} />
              <StatusBadge status={run.status} />
              <ReportBadge level="danger">Linaje no resuelto</ReportBadge>
            </div>
            <strong>{run.run_name?.trim() || 'No registrado'}</strong>
            <span className="report-muted" title={run.run_id}>
              Run ID: {visibleRunId(run.run_id)}
            </span>
            <span className="report-muted">
              Modelo: <strong>{run.model_name?.trim() || 'No registrado'}</strong>
            </span>
            <p>{run.lineage_warning?.trim() || 'No se pudo asociar a un training específico.'}</p>
            <button
              aria-label={`Ver detalle de ${run.run_name?.trim() || run.run_id}`}
              className="report-detail-button"
              onClick={() => onRunSelect(run.run_id)}
              type="button"
            >
              Ver detalle
            </button>
          </article>
        ))}
      </div>
    </details>
  );
}
