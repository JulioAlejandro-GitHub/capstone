import type { Stage2Availability, TrainingRunLineageGroup, TrainingPromotionStatus } from '../../types/api';
import { RunLineageChildCard } from './RunLineageChildCard';
import { RunSummaryRow } from './RunSummaryRow';

interface TrainingRunGroupCardProps {
  group: TrainingRunLineageGroup;
  onRunSelect: (runId: string) => void;
  promotionError?: string | null;
  promotionLoading?: boolean;
  promotionPreparing?: boolean;
  promotionStatus?: TrainingPromotionStatus;
  onPromotionAction: (runId: string) => void;
  stage2Status?:Stage2Availability;stage2Loading?:boolean;stage2Busy?:boolean;stage2Error?:string;
  onStage2Enable:(runId:string)=>void;onStage2View:(deploymentId:string)=>void;
}

export function TrainingRunGroupCard({
  group,
  onRunSelect,
  promotionError,
  promotionLoading,
  promotionPreparing,
  promotionStatus,
  onPromotionAction,
  stage2Status,stage2Loading,stage2Busy,stage2Error,onStage2Enable,onStage2View,
}: TrainingRunGroupCardProps) {
  const { training, evaluations, explainability } = group;
  const linkedCount = evaluations.length + explainability.length;

  return (
    <article
      aria-label={`Entrenamiento ${training.run_name?.trim() || training.run_id}`}
      className="run-lineage-group"
    >
      <RunSummaryRow
        onRunSelect={onRunSelect}
        onPromotionAction={() => onPromotionAction(training.run_id)}
        processKind="training"
        promotionError={promotionError}
        promotionLoading={promotionLoading}
        promotionPreparing={promotionPreparing}
        promotionStatus={promotionStatus}
        run={training}
        stage2Status={stage2Status}
        stage2Loading={stage2Loading}
        stage2Busy={stage2Busy}
        stage2Error={stage2Error}
        onStage2Enable={()=>onStage2Enable(training.run_id)}
        onStage2View={onStage2View}
      />

      <section className="run-lineage-group__children" aria-label="Procesos derivados del entrenamiento">
        <header className="run-lineage-group__children-heading">
          <div>
            <strong>Pipeline derivado</strong>
            <span>TRAIN → EVALUATE / EXPLAIN</span>
          </div>
          <small>
            {linkedCount === 1 ? '1 proceso vinculado' : `${linkedCount} procesos vinculados`}
          </small>
        </header>
        <div className="run-lineage-group__children-grid">
          <div className="lineage-child-stack">
            {evaluations.length > 0 ? evaluations.map((run) => (
              <RunLineageChildCard
                key={run.run_id}
                kind="evaluation"
                onRunSelect={onRunSelect}
                run={run}
              />
            )) : (
              <RunLineageChildCard kind="evaluation" onRunSelect={onRunSelect} run={null} />
            )}
          </div>
          <div className="lineage-child-stack">
            {explainability.length > 0 ? explainability.map((run) => (
              <RunLineageChildCard
                key={run.run_id}
                kind="explainability"
                onRunSelect={onRunSelect}
                run={run}
              />
            )) : (
              <RunLineageChildCard kind="explainability" onRunSelect={onRunSelect} run={null} />
            )}
          </div>
        </div>
      </section>
    </article>
  );
}
