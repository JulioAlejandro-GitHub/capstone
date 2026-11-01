import type { ReactNode, RefObject } from 'react';

import type { TrainingSummary, TrainingSummaryCollection } from '../../types/api';
import { isStage2Active } from './TrainingRunGroupCard';
import { TrainingRunsTable } from './TrainingRunsTable';

/** Native dialog that picks TRAIN from the Ejecuciones report rows; the caller owns what the selection means. */
export function RunSelectorDialog({ dialog, ids, summaries, error, retry, maximum, counter, hint, emptyHint = 'Marca la casilla de cada TRAIN que quieras analizar.', submitLabel, runLabel, onRemove, onClose, onSubmit, canSelect, onChange, renderStatus }: {
  dialog: RefObject<HTMLDialogElement | null>; ids: string[]; summaries: TrainingSummaryCollection | null; error: string | null; retry: () => void;
  maximum?: number; counter: string; hint?: string; emptyHint?: string; submitLabel: string; runLabel: (id: string) => string; onRemove: (id: string) => void;
  onClose: () => void; onSubmit?: () => void; canSelect: (training: TrainingSummary) => boolean; onChange: (id: string, selected: boolean) => void;
  renderStatus?: (training: TrainingSummary) => ReactNode;
}) {
  return <dialog ref={dialog} className="report-viewer scc-run-selector" aria-labelledby="scc-selector-title" onClose={onClose}>
    <div className="ds-page-header"><h2 id="scc-selector-title">Seleccionar ejecuciones TRAIN</h2>
    <form method="dialog" className="xai-modal-close"><button type="submit" className="ds-button" aria-label="Cerrar vista ampliada" title="Cerrar" autoFocus>
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
    </button></form></div>
    <div className="scc-selector-summary" aria-live="polite">
      <p><strong>{counter}</strong>{hint}</p>
      {ids.length > 0 ? <ul className="scc-selected-chips" aria-label="Ejecuciones seleccionadas">{ids.map((id, index) =>
        <li key={id} title={id}><span>RUN {String.fromCharCode(65 + index)} · {runLabel(id)}</span>
          <button type="button" aria-label={`Quitar ${runLabel(id)} de la selección`} onClick={() => onRemove(id)}>×</button></li>)}
      </ul> : <p className="scc-meta">{emptyHint}</p>}
      <form method="dialog"><button type="submit" className="ds-button" data-variant="primary" disabled={!ids.length} onClick={onSubmit}>{submitLabel}</button></form>
    </div>
    {error && <div role="alert"><p>{error}</p><button className="ds-button" onClick={retry}>Reintentar carga</button></div>}
    {!summaries && !error && <p role="status">Cargando resúmenes de Ejecuciones…</p>}
    {summaries && <TrainingRunsTable inDialog variant="compact" trainings={summaries.items} isActive={isStage2Active}
      onRunSelect={() => {}} selection={{ ids, maximum, canSelect, onChange, renderStatus }} />}
    {summaries && summaries.count >= summaries.limit && <p role="status">Se muestran hasta {summaries.limit} entrenamientos recientes.</p>}
  </dialog>;
}
