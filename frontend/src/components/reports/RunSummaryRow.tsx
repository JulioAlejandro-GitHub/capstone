import { StatusBadge } from '../StatusBadge';
import type { RunDashboard, TrainingSummary } from '../../types/api';
import { getRunDuration } from '../../utils/format';
import {
  generateRunAutoAnalysis,
  resolveRunConfusion,
  resolveRunReportMetrics,
} from '../../utils/runReport';
import { AutoAnalysisBadge } from './AutoAnalysisBadge';
import { CommandChips } from './CommandChips';
import { ScientificParameters } from './ScientificParameters';
import { MetricChip } from './MetricChip';
import { MiniConfusionMatrix } from './MiniConfusionMatrix';
import { RunProcessBadge, type RunProcessKind } from './RunProcessBadge';

interface RunSummaryRowProps {
  run: RunDashboard | TrainingSummary;
  onRunSelect: (runId: string) => void;
  processKind?: RunProcessKind;
  stage2Active?: boolean; stage2Expanded?: boolean; stage2ControlsId?: string; onStage2Toggle?: () => void;
}

function truncatedRunId(runId: string): string {
  return runId.length > 12 ? `${runId.slice(0, 8)}…` : runId;
}

export function RunSummaryRow({
  run,
  onRunSelect,
  processKind,
  stage2Active = false, stage2Expanded = false, stage2ControlsId, onStage2Toggle,
}: RunSummaryRowProps) {
  const counts = resolveRunConfusion(run);
  const metrics = resolveRunReportMetrics(run);
  const analysis = generateRunAutoAnalysis(run);

  return (
    <div className="report-row">
      <section aria-label="RUN" className="report-cell report-run-cell" data-label="RUN">
        {processKind ? <RunProcessBadge kind={processKind} /> : null}
        <strong className="report-run-name">
          {run.run_name?.trim() || 'No registrado 1'}
        </strong>
        <span className="report-muted" title={run.run_id}>
          Run ID: {truncatedRunId(run.run_id)}
        </span>
        {processKind === 'training' ? (
          <span className="report-muted" title={run.dataset_version_id ?? undefined}>
            dataset-version-id: {run.dataset_version_id || 'No registrado 2'}
          </span>
        ) : null}
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
        <strong className="report-primary-value">{run.model_name?.trim() || 'No registrado 3'}</strong>
        <span className="report-muted">
          Optimizer: <strong>{run.optimizer?.trim() || 'No registrado 4'}</strong>
        </span>
        <CommandChips command={run.command} />
        {processKind === 'training' ? (
          <ScientificParameters parameters={'scientific_parameters' in run ? run.scientific_parameters : undefined} />
        ) : null}
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
        {processKind !== 'training' ? <button
          aria-label={`Ver detalle de ${run.run_name?.trim() || run.run_id}`}
          className="report-detail-button"
          onClick={() => onRunSelect(run.run_id)}
          type="button"
        >
          Ver detalle
        </button> : null}
        {processKind === 'training' ? <div className="stage2-release-summary">
          <button aria-controls={stage2ControlsId} aria-expanded={stage2Expanded}
            className="report-detail-button stage2-detail-link"
            onClick={onStage2Toggle} type="button">
            {stage2Active ? 'Modelo en Estado Activo' : 'Activar para clasificación celular'}
          </button>
        </div> : null}
      </section>
    </div>
  );
}
