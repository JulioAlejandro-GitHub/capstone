import { StatusBadge } from '../StatusBadge';
import type { RunDashboard } from '../../types/api';
import { getRunDuration } from '../../utils/format';
import {
  generateRunAutoAnalysis,
  resolveRunConfusion,
  resolveRunReportMetrics,
} from '../../utils/runReport';
import { AutoAnalysisBadge } from './AutoAnalysisBadge';
import { CommandChips } from './CommandChips';
import { MetricChip } from './MetricChip';
import { MiniConfusionMatrix } from './MiniConfusionMatrix';
import { RunProcessBadge, type RunProcessKind } from './RunProcessBadge';
import { PromotionButton } from './PromotionButton';
import { PromotionTracker } from './PromotionTracker';

interface RunSummaryRowProps {
  run: RunDashboard;
  onRunSelect: (runId: string) => void;
  processKind?: RunProcessKind;
  datasource?: string;
  onNavigate?: (targetUrl: string) => void;
}

function truncatedRunId(runId: string): string {
  return runId.length > 12 ? `${runId.slice(0, 8)}…` : runId;
}

export function RunSummaryRow({ run, onRunSelect, processKind, datasource = 'malaria', onNavigate }: RunSummaryRowProps) {
  const counts = resolveRunConfusion(run);
  const metrics = resolveRunReportMetrics(run);
  const analysis = generateRunAutoAnalysis(run);
  const isTrainingCard = !processKind || processKind === 'training';

  return (
    <div className="report-row">
      <section aria-label="RUN" className="report-cell report-run-cell" data-label="RUN">
        {processKind ? <RunProcessBadge kind={processKind} /> : null}
        <strong className="report-run-name">
          {run.run_name?.trim() || 'No registrado'}
        </strong>
        <span className="report-muted" title={run.run_id}>
          Run ID: {truncatedRunId(run.run_id)}
        </span>
        <div className="report-inline-facts">
          <StatusBadge status={run.status} />
          <span className="report-duration">
            Duración: {getRunDuration(
              run.started_at,
              run.finished_at,
              run.duration_seconds,
              run.status,
            )}
          </span>
        </div>
      </section>

      <section aria-label="Modelo" className="report-cell report-model-cell" data-label="Modelo">
        <strong className="report-primary-value">{run.model_name?.trim() || 'No registrado'}</strong>
        <span className="report-muted">
          Optimizer: <strong>{run.optimizer?.trim() || 'No registrado'}</strong>
        </span>
        <CommandChips command={run.command} />
      </section>

      <section aria-label="Resultados" className="report-cell report-results-cell" data-label="Resultados">
        <MiniConfusionMatrix counts={counts} />
        <div className="metric-grid">
          <MetricChip label="Recall" value={metrics.recall} />
          <MetricChip label="Specificity" value={metrics.specificity} />
          <MetricChip label="F2" value={metrics.f2} />
          <MetricChip label="AUC" value={metrics.auc} />
        </div>
      </section>

      <section
        aria-label="Análisis automático"
        className="report-cell report-analysis-cell"
        data-label="Análisis automático"
      >
        <AutoAnalysisBadge analysis={analysis} />
        {isTrainingCard ? (
          <PromotionTracker runStatus={run.status} status={run.promotion_status || null} />
        ) : null}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center', marginTop: '6px' }}>
          <button
            aria-label={`Ver detalle de ${run.run_name?.trim() || run.run_id}`}
            className="report-detail-button"
            onClick={() => onRunSelect(run.run_id)}
            type="button"
          >
            Ver detalle
          </button>

          {isTrainingCard ? (
            <PromotionButton
              datasource={datasource}
              onNavigate={onNavigate}
              runStatus={run.status}
              status={run.promotion_status || null}
              trainingRunId={run.run_id}
            />
          ) : null}
        </div>
      </section>
    </div>
  );
}

