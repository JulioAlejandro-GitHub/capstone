import type { Stage2PublicationStatus, TrainingRunLineageGroup } from '../../types/api';
import { RunLineageChildCard } from './RunLineageChildCard';
import { RunSummaryRow } from './RunSummaryRow';
import { Stage2PublicationPanel } from './Stage2PublicationPanel';
import { useEffect, useState } from 'react';

interface TrainingRunGroupCardProps {
  group: TrainingRunLineageGroup;
  onRunSelect: (runId: string) => void;
  stage2Status?:Stage2PublicationStatus;stage2Loading?:boolean;stage2Error?:string;
  defaultStage2Open?:boolean;
  onStage2Publish:()=>Promise<void>;onStage2Deactivate:()=>Promise<void>;
}

export function TrainingRunGroupCard({
  group,
  onRunSelect,
  stage2Status,stage2Loading,stage2Error,defaultStage2Open=false,
  onStage2Publish,onStage2Deactivate,
}: TrainingRunGroupCardProps) {
  const { training, evaluations, explainability } = group;
  const linkedCount = evaluations.length + explainability.length;
  const [expanded,setExpanded]=useState(defaultStage2Open);
  const panelId=`stage2-publication-${training.run_id}`;
  const published=Boolean(stage2Status?.publication?.is_active);

  useEffect(()=>{
    if(defaultStage2Open)setExpanded(true);
  },[defaultStage2Open]);

  return (
    <article
      aria-label={`Entrenamiento ${training.run_name?.trim() || training.run_id}`}
      className={`run-lineage-group training-card ${published ? 'training-card--stage2-production' : ''}`}
    >
      <RunSummaryRow
        onRunSelect={onRunSelect}
        processKind="training"
        run={training}
        stage2Status={stage2Status}
        stage2Loading={stage2Loading}
        stage2Error={stage2Error}
        stage2Expanded={expanded}
        stage2ControlsId={panelId}
        onStage2Toggle={()=>setExpanded(current=>!current)}
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
      {expanded?<Stage2PublicationPanel id={panelId} status={stage2Status}
        loading={stage2Loading} error={stage2Error} explainCount={explainability.length}
        onPublish={onStage2Publish} onDeactivate={onStage2Deactivate}/>:null}
    </article>
  );
}
