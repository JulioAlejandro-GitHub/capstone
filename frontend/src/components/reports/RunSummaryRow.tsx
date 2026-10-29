import { useState } from 'react';

import { StatusBadge } from '../StatusBadge';
import { NavigationIcon } from '../navigation/NavigationIcon';
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
  variant?: 'full' | 'compact';
  run: RunDashboard | TrainingSummary;
  onRunSelect: (runId: string) => void;
  processKind?: RunProcessKind;
  stage2Active?: boolean; stage2Expanded?: boolean; stage2ControlsId?: string; onStage2Toggle?: () => void;
}

// Identifiers show their first characters; the full value goes to the clipboard so the RUN column stays narrow.
function CopyableId({ caption, value }: { caption: string; value: string | null | undefined }) {
  const [copied, setCopied] = useState<boolean | null>(null);
  if (!value) return <span className="report-muted">{caption}: No registrado</span>;
  return <span className="report-muted report-copy-id" title={value}>
    {caption}: <code>{value.slice(0, 8)}…</code>
    <button type="button" className="report-copy-id__button" aria-label={`Copiar ${caption} completo`}
      title={copied === null ? `Copiar ${value}` : copied ? 'Copiado' : 'No se pudo copiar'}
      onClick={() => { navigator.clipboard.writeText(value).then(() => setCopied(true), () => setCopied(false)); }}>
      {copied ? '✓' : <NavigationIcon name="copy" />}
    </button>
  </span>;
}

type RunCellProps = Pick<RunSummaryRowProps, 'run' | 'variant' | 'processKind'>;

export function RunIdentityCell({ run, processKind }: RunCellProps) {
  return <>
    {processKind ? <RunProcessBadge kind={processKind} /> : null}
    <strong className="report-run-name">
      {run.run_name?.trim() || 'No registrado 1'}
    </strong>
    <CopyableId caption="Run ID" value={run.run_id} />
    {processKind === 'training' ? <CopyableId caption="dataset-version-id" value={run.dataset_version_id} /> : null}
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
  </>;
}

export function RunModelCell({ run, variant = 'full', processKind }: RunCellProps) {
  return <>
    <strong className="report-primary-value">{run.model_name?.trim() || 'No registrado 3'}</strong>
    <span className="report-muted">
      Optimizer: <strong>{run.optimizer?.trim() || 'No registrado 4'}</strong>
    </span>
    <CommandChips command={run.command} params={variant === 'compact' ? ['model', 'max-epochs', 'optimizer', 'learning-rate', 'checkpoint-monitor'] : undefined} />
    {processKind === 'training' ? (
      <ScientificParameters parameters={'scientific_parameters' in run ? run.scientific_parameters : undefined} />
    ) : null}
  </>;
}

export function RunResultsCell({ run, variant = 'full' }: RunCellProps) {
  const counts = resolveRunConfusion(run);
  const metrics = resolveRunReportMetrics(run);
  return <>
    {variant === 'compact' && 'metrics_split' in run && run.metrics_split ? <span className="report-muted">Split de métricas: {run.metrics_split}</span> : null}
    <MiniConfusionMatrix counts={counts} />
    <div className="metric-grid">
      <MetricChip label="Recall" value={metrics.recall} />
      <MetricChip label="Specificity" value={metrics.specificity} />
      <MetricChip label="F2" value={metrics.f2} />
      <MetricChip label="AUC" value={metrics.auc} />
    </div>
  </>;
}

export function RunAnalysisCell({
  run, variant = 'full', onRunSelect, processKind,
  stage2Active = false, stage2Expanded = false, stage2ControlsId, onStage2Toggle,
}: RunSummaryRowProps) {
  const analysis = generateRunAutoAnalysis(run);
  return <>
    <AutoAnalysisBadge analysis={analysis} showExploratoryNote={variant !== 'compact'} />
    {processKind !== 'training' ? <button
      aria-label={`Ver detalle de ${run.run_name?.trim() || run.run_id}`}
      className="report-detail-button"
      onClick={() => onRunSelect(run.run_id)}
      type="button"
    >
      Ver detalle
    </button> : null}
    {processKind === 'training' && variant !== 'compact' ? <div className="stage2-release-summary">
      <button aria-controls={stage2ControlsId} aria-expanded={stage2Expanded}
        className="report-detail-button stage2-detail-link"
        onClick={onStage2Toggle} type="button">
        {stage2Active ? 'Modelo en Estado Activo' : 'Activar para clasificación celular'}
      </button>
    </div> : null}
  </>;
}

export function RunSummaryRow(props: RunSummaryRowProps) {
  const { variant = 'full' } = props;
  return (
    <div className={`report-row${variant === 'compact' ? ' report-row--compact' : ''}`}>
      <section aria-label="RUN" className="report-cell report-run-cell" data-label="RUN">
        <RunIdentityCell {...props} />
      </section>

      <section aria-label="Modelo" className="report-cell report-model-cell" data-label="Modelo">
        <RunModelCell {...props} />
      </section>

      <section aria-label="Resultados" className="report-cell report-results-cell" data-label="Resultados">
        <RunResultsCell {...props} />
      </section>

      <section
        aria-label="Análisis automático"
        className="report-cell report-analysis-cell"
        data-label="Análisis automático"
      >
        <RunAnalysisCell {...props} />
      </section>
    </div>
  );
}
