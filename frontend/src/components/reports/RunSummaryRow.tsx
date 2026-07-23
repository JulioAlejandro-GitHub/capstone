import { StatusBadge } from '../StatusBadge';
import type { RunDashboard, Stage2Availability, TrainingPromotionStatus } from '../../types/api';
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
import { RunPromotionAction } from './RunPromotionAction';
import { Stage2AvailabilityAction } from './Stage2AvailabilityAction';

interface RunSummaryRowProps {
  run: RunDashboard;
  onRunSelect: (runId: string) => void;
  processKind?: RunProcessKind;
  promotionError?: string | null;
  promotionLoading?: boolean;
  promotionPreparing?: boolean;
  promotionStatus?: TrainingPromotionStatus;
  onPromotionAction?: () => void;
  stage2Status?:Stage2Availability;stage2Loading?:boolean;stage2Busy?:boolean;stage2Error?:string;
  onStage2Enable?:()=>void;onStage2View?:(deploymentId:string)=>void;
}

function truncatedRunId(runId: string): string {
  return runId.length > 12 ? `${runId.slice(0, 8)}…` : runId;
}

export function RunSummaryRow({
  run,
  onRunSelect,
  processKind,
  promotionError,
  promotionLoading = false,
  promotionPreparing = false,
  promotionStatus,
  onPromotionAction,
  stage2Status,stage2Loading=false,stage2Busy=false,stage2Error,onStage2Enable,onStage2View,
}: RunSummaryRowProps) {
  const counts = resolveRunConfusion(run);
  const metrics = resolveRunReportMetrics(run);
  const analysis = generateRunAutoAnalysis(run);

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
        <button
          aria-label={`Ver detalle de ${run.run_name?.trim() || run.run_id}`}
          className="report-detail-button"
          onClick={() => onRunSelect(run.run_id)}
          type="button"
        >
          Ver detalle
        </button>
        {processKind === 'training' && onPromotionAction ? (
          <RunPromotionAction
            error={promotionError}
            loading={promotionLoading}
            onAction={onPromotionAction}
            preparing={promotionPreparing}
            runId={run.run_id}
            status={promotionStatus}
          />
        ) : null}
        {processKind==='training'&&onStage2Enable&&onStage2View?(
          <Stage2AvailabilityAction status={stage2Status} loading={stage2Loading}
            busy={stage2Busy} error={stage2Error} onEnable={onStage2Enable} onView={onStage2View}/>
        ):null}
      </section>
    </div>
  );
}
