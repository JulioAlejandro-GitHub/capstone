import { StatusBadge } from '../StatusBadge';
import type {
  EvaluationLineageRun,
  ExplainabilityLineageRun,
} from '../../types/api';
import { normalizeConfusionMatrix } from '../../utils/runReport';
import { LineageBadge } from './LineageBadge';
import { MetricChip } from './MetricChip';
import { MiniConfusionMatrix } from './MiniConfusionMatrix';
import { ReportBadge } from './ReportBadge';
import { RunProcessBadge } from './RunProcessBadge';

type RunLineageChildCardProps =
  | {
    kind: 'evaluation';
    run: EvaluationLineageRun | null;
    onRunSelect: (runId: string) => void;
  }
  | {
    kind: 'explainability';
    run: ExplainabilityLineageRun | null;
    onRunSelect: (runId: string) => void;
  };

const countFormatter = new Intl.NumberFormat('es-CL');

function visibleRunId(runId: string): string {
  return runId.length > 12 ? `${runId.slice(0, 8)}…` : runId;
}

function checkpointName(path: string | null | undefined): string {
  if (!path?.trim()) return 'No registrado';
  return path.trim().split(/[\\/]/).pop() || path.trim();
}

function countLabel(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '-';
  return countFormatter.format(Number(value));
}

export function RunLineageChildCard(props: RunLineageChildCardProps) {
  const { kind, run, onRunSelect } = props;
  const isEvaluation = kind === 'evaluation';
  const pendingTitle = isEvaluation ? 'Evaluación pendiente' : 'Explicabilidad pendiente';
  const pendingMessage = isEvaluation
    ? 'Este entrenamiento todavía no tiene una evaluación asociada por linaje.'
    : 'Este entrenamiento todavía no tiene una explicación visual asociada por linaje.';

  if (!run) {
    return (
      <article
        aria-label={pendingTitle}
        className="lineage-child-card lineage-child-card--pending"
      >
        <header className="lineage-child-card__header">
          <RunProcessBadge kind={kind} />
          <ReportBadge level="neutral">Pendiente</ReportBadge>
        </header>
        <div className="lineage-pending-copy">
          <strong>{pendingTitle}</strong>
          <p>{pendingMessage}</p>
        </div>
      </article>
    );
  }

  const methods = kind === 'explainability'
    ? (run.methods?.filter(Boolean).join(', ') || run.method?.trim() || 'No registrado')
    : null;
  const evaluationConfusion = normalizeConfusionMatrix(run);

  return (
    <article
      aria-label={`${isEvaluation ? 'Evaluación' : 'Explicabilidad'} ${run.run_name?.trim() || run.run_id}`}
      className={`lineage-child-card lineage-child-card--${kind}`}
    >
      <header className="lineage-child-card__header">
        <RunProcessBadge kind={kind} />
        <StatusBadge status={run.status} />
      </header>

      <div className="lineage-child-card__identity">
        <strong>{run.run_name?.trim() || 'No registrado'}</strong>
        <span className="report-muted" title={run.run_id}>
          Run ID: {visibleRunId(run.run_id)}
        </span>
      </div>

      <div className="lineage-child-card__lineage">
        <LineageBadge confidence={run.confidence} />
        <span className="report-muted" title={run.checkpoint_path || undefined}>
          Checkpoint: <strong>{checkpointName(run.checkpoint_path)}</strong>
        </span>
      </div>

      {kind === 'evaluation' ? (
        <div className="lineage-evaluation-results">
          <div className="lineage-evaluation-matrix">
            <MiniConfusionMatrix
              counts={evaluationConfusion}
              emptyLabel="Sin matriz de confusión registrada"
            />
          </div>
          <div className="metric-grid lineage-child-metrics">
            <MetricChip label="Recall" value={run.recall} />
            <MetricChip label="Specificity" value={run.specificity} />
            <MetricChip label="F2" value={run.f2_score} />
            <MetricChip label="AUC" value={run.auc} />
          </div>
        </div>
      ) : (
        <dl className="lineage-stats">
          <div className="lineage-stats__wide">
            <dt>Método</dt>
            <dd>{methods}</dd>
          </div>
          <div>
            <dt>Total</dt>
            <dd>{countLabel(run.total_explanations)}</dd>
          </div>
          <div>
            <dt>Exitosas</dt>
            <dd>{countLabel(run.success_count)}</dd>
          </div>
          <div>
            <dt>Fallidas</dt>
            <dd>{countLabel(run.failed_count)}</dd>
          </div>
        </dl>
      )}

      <button
        aria-label={`${isEvaluation ? 'Ver evaluación' : 'Ver explicabilidad'} ${run.run_name?.trim() || run.run_id}`}
        className="report-detail-button lineage-child-card__action"
        onClick={() => onRunSelect(run.run_id)}
        type="button"
      >
        {isEvaluation ? 'Ver evaluación' : 'Ver explicabilidad'}
      </button>
    </article>
  );
}
