import { StatusBadge } from '../StatusBadge';
import type { RunDashboard, Stage2PublicationStatus } from '../../types/api';
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

interface RunSummaryRowProps {
  run: RunDashboard;
  onRunSelect: (runId: string) => void;
  processKind?: RunProcessKind;
  stage2Status?:Stage2PublicationStatus;stage2Loading?:boolean;stage2Error?:string;
  stage2Expanded?:boolean;stage2ControlsId?:string;onStage2Toggle?:()=>void;
}

function truncatedRunId(runId: string): string {
  return runId.length > 12 ? `${runId.slice(0, 8)}…` : runId;
}

export function RunSummaryRow({
  run,
  onRunSelect,
  processKind,
  stage2Status,stage2Loading=false,stage2Error,
  stage2Expanded=false,stage2ControlsId,onStage2Toggle,
}: RunSummaryRowProps) {
  const counts = resolveRunConfusion(run);
  const metrics = resolveRunReportMetrics(run);
  const analysis = generateRunAutoAnalysis(run);
  const stage2Published = Boolean(stage2Status?.publication?.is_active);

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
        {processKind !== 'training' ? <button
          aria-label={`Ver detalle de ${run.run_name?.trim() || run.run_id}`}
          className="report-detail-button"
          onClick={() => onRunSelect(run.run_id)}
          type="button"
        >
          Ver detalle
        </button> : null}
        {processKind === 'training' ? <div className="stage2-release-summary" role="status">
          <span className="stage2-release-summary__title">Publicación Etapa 2</span>
          {stage2Loading ? <strong>Consultando estado…</strong>
            : stage2Published ? <>
              <strong className="stage2-production-badge"><span aria-hidden="true">✓</span> Publicado para Etapa 2</strong>
              <span>Disponible en el catálogo de candidatos para nuevos análisis.</span>
              <small>Referencia activa; la compatibilidad se valida al ejecutar inferencia</small>
            </>
            : stage2Status?.eligible ? <>
              <strong>Disponible para publicar</strong>
              <span>✓ TRAIN completado · ✓ EVALUATE completado</span>
            </>
            : <>
              <strong>No disponible</strong>
              <span>{stage2Status?.eligibility?.missing_conditions.join(' · ')
                || 'Se requiere un TRAIN completado y un EVALUATE completado asociado.'}</span>
            </>}
          {stage2Error ? <small className="stage2-publication-error">{stage2Error}</small> : null}
          <button aria-controls={stage2ControlsId} aria-expanded={stage2Expanded}
            className="report-detail-button stage2-detail-link" disabled={stage2Loading}
            onClick={onStage2Toggle} type="button">Ver detalle</button>
        </div> : null}
      </section>
    </div>
  );
}
