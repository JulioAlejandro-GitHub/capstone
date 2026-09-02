import { useState } from 'react';

import type {
  Stage2Availability,
  TrainingLineageChildren,
  TrainingSummary,
} from '../../types/api';
import { RunLineageChildCard } from './RunLineageChildCard';
import { RunSummaryRow } from './RunSummaryRow';
import { Stage2PublicationPanel } from './Stage2PublicationPanel';

export type TrainingChildrenLoadState = {
  status: 'idle' | 'loading' | 'success' | 'error';
  data: TrainingLineageChildren | null;
  error: string | null;
  loaded: boolean;
};

interface TrainingRunGroupCardProps {
  training: TrainingSummary;
  childrenState: TrainingChildrenLoadState;
  onChildrenExpand: () => void;
  onChildrenRetry: () => void;
  onRunSelect: (runId: string) => void;
  stage2Status?: Stage2Availability;
  stage2Loading?: boolean;
  stage2Error?: string;
  onStage2Open: () => void;
  onStage2Publish: (replaceExisting: boolean) => Promise<'published' | 'replacement-required' | 'failed'>;
  onStage2Deactivate: () => Promise<void>;
}

export function TrainingRunGroupCard({
  training,
  childrenState,
  onChildrenExpand,
  onChildrenRetry,
  onRunSelect,
  stage2Status,
  stage2Loading,
  stage2Error,
  onStage2Open,
  onStage2Publish,
  onStage2Deactivate,
}: TrainingRunGroupCardProps) {
  const [childrenExpanded, setChildrenExpanded] = useState(false);
  const [stage2Expanded, setStage2Expanded] = useState(false);
  const childrenPanelId = `lineage-children-${training.run_id}`;
  const stage2PanelId = `stage2-publication-${training.run_id}`;
  const linkedCount = training.evaluation_count + training.explainability_count;

  const toggleChildren = () => {
    if (linkedCount === 0 && !childrenExpanded) return;
    const next = !childrenExpanded;
    setChildrenExpanded(next);
    if (next) onChildrenExpand();
  };

  const toggleStage2 = () => {
    const next = !stage2Expanded;
    setStage2Expanded(next);
    if (next) onStage2Open();
  };

  const loadedChildren = childrenState.data;
  const visibleChildren = (loadedChildren?.evaluations.length ?? 0)
    + (loadedChildren?.explainabilities.length ?? 0);

  return (
    <article
      aria-label={`Entrenamiento ${training.run_name?.trim() || training.run_id}`}
      className={`run-lineage-group training-card ${training.release_status === 'productive_stage2' ? 'training-card--stage2-production' : ''}`}
    >
      <RunSummaryRow
        onRunSelect={onRunSelect}
        processKind="training"
        run={training}
        stage2Expanded={stage2Expanded}
        stage2ControlsId={stage2PanelId}
        onStage2Toggle={toggleStage2}
      />

      <section className="run-lineage-group__children" aria-label="Procesos derivados del entrenamiento">
        <header className="run-lineage-group__children-heading">
          <div>
            <strong>Pipeline derivado</strong>
            <span>TRAIN → EVALUATE / EXPLAIN</span>
            <small>{training.evaluation_count} EVALUATE</small>
            <small>{training.explainability_count} EXPLAIN</small>
            <small>{linkedCount} total</small>
          </div>
          <button
            aria-controls={childrenPanelId}
            aria-expanded={childrenExpanded}
            className="lineage-children-toggle"
            disabled={linkedCount === 0 && !childrenExpanded}
            onClick={toggleChildren}
            type="button"
          >
            {childrenExpanded
              ? 'Ocultar ejecuciones'
              : linkedCount === 0 ? 'Sin ejecuciones asociadas' : 'Mostrar ejecuciones'}
          </button>
        </header>

        {childrenExpanded ? (
          <div className="run-lineage-group__children-panel" id={childrenPanelId}>
            {childrenState.status === 'loading' ? (
              <p className="lineage-children-status" role="status">Cargando ejecuciones asociadas…</p>
            ) : null}
            {childrenState.status === 'error' ? (
              <div className="lineage-children-error" role="alert">
                <p>{childrenState.error}</p>
                <button className="report-detail-button" onClick={onChildrenRetry} type="button">
                  Reintentar carga
                </button>
              </div>
            ) : null}
            {childrenState.status === 'success' && loadedChildren ? (
              <>
                {loadedChildren.truncated ? (
                  <p className="lineage-children-warning" role="status">
                    Se muestran los primeros {visibleChildren} de {loadedChildren.total_count} registros asociados
                  </p>
                ) : null}
                {visibleChildren === 0 ? (
                  <p className="lineage-children-status" role="status">Sin ejecuciones asociadas.</p>
                ) : (
                  <div className="run-lineage-group__children-grid">
                    <div className="lineage-child-stack">
                      {loadedChildren.evaluations.map((run) => (
                        <RunLineageChildCard
                          key={run.run_id}
                          kind="evaluation"
                          onRunSelect={onRunSelect}
                          run={run}
                        />
                      ))}
                    </div>
                    <div className="lineage-child-stack">
                      {loadedChildren.explainabilities.map((run) => (
                        <RunLineageChildCard
                          key={run.run_id}
                          kind="explainability"
                          onRunSelect={onRunSelect}
                          run={run}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : null}
          </div>
        ) : null}
      </section>

      {stage2Expanded ? (
        <Stage2PublicationPanel
          error={stage2Error}
          explainCount={training.explainability_count}
          id={stage2PanelId}
          loading={stage2Loading}
          onDeactivate={onStage2Deactivate}
          onPublish={onStage2Publish}
          status={stage2Status}
        />
      ) : null}
    </article>
  );
}
