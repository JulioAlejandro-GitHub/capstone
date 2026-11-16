import { cellKind, isPendingReview, type CellFilter, type MicroscopeCell } from '../../adapters/cellLayer';
import type { CellLayerState } from '../../hooks/useCellLayer';
import type { LayerSettings } from '../../state/presentationStorage';

const FILTERS: Array<{ id: CellFilter; label: string }> = [
  { id: 'all', label: 'Todas' },
  { id: 'parasitized', label: 'Candidatas parasitadas' },
  { id: 'near_threshold', label: 'Cercanas al umbral' },
  { id: 'pending_review', label: 'Pendientes de revisión' },
];

const countBy = (cells: readonly MicroscopeCell[], filter: CellFilter) => {
  if (filter === 'parasitized') return cells.filter((cell) => cellKind(cell) === 'parasitized').length;
  if (filter === 'near_threshold') return cells.filter((cell) => cell.prediction?.nearThreshold).length;
  if (filter === 'pending_review') return cells.filter(isPendingReview).length;
  return cells.length;
};

/** IA y Revisión: capas de detección y clasificación de la imagen activa. */
export function AiPanel({
  layer,
  hasDetection,
  layers,
  onLayersChange,
  onOpenReview,
}: {
  layer: CellLayerState;
  hasDetection: boolean;
  layers: LayerSettings;
  onLayersChange: (layers: LayerSettings) => void;
  onOpenReview: (() => void) | null;
}) {
  if (!hasDetection) {
    return (
      <div className="frotis-v3-instrument">
        <p className="frotis-v3-hint">Este análisis aún no tiene detección celular: no hay capas de IA que mostrar.</p>
      </div>
    );
  }
  const cells = layer.cells;
  return (
    <div className="frotis-v3-instrument">
      <label className="frotis-v3-check">
        <input
          type="checkbox"
          checked={layers.cells}
          onChange={(event) => onLayersChange({ ...layers, cells: event.target.checked })}
        />
        <span>Mostrar células detectadas</span>
      </label>

      {layer.status === 'loading' ? <p className="frotis-v3-hint" role="status">Cargando células de esta imagen…</p> : null}
      {layer.status === 'unavailable' ? <p className="frotis-v3-hint" role="alert">{layer.message}</p> : null}
      {layer.status === 'ready' && layer.classificationRestricted ? (
        <p className="frotis-v3-hint" role="status">
          Tu rol no autoriza la lectura de la clasificación: se muestran solo las detecciones.
        </p>
      ) : null}

      {layer.status === 'ready' ? (
        <fieldset className="frotis-v3-options" disabled={!layers.cells}>
          <legend>Mostrar en esta imagen</legend>
          {FILTERS.map(({ id, label }) => (
            <label key={id} className="frotis-v3-check">
              <input
                type="radio"
                name="frotis-v3-cell-filter"
                checked={layers.filter === id}
                onChange={() => onLayersChange({ ...layers, filter: id })}
              />
              <span>{label}</span>
              <output>{countBy(cells, id)}</output>
            </label>
          ))}
        </fieldset>
      ) : null}

      <fieldset className="frotis-v3-options" disabled={!layers.cells}>
        <legend>Contorno según la tinción</legend>
        {([['light', 'Claro (fondos oscuros)'], ['dark', 'Oscuro (fondos claros)']] as const).map(([id, label]) => (
          <label key={id} className="frotis-v3-check">
            <input
              type="radio"
              name="frotis-v3-contour"
              checked={layers.contour === id}
              onChange={() => onLayersChange({ ...layers, contour: id })}
            />
            <span>{label}</span>
          </label>
        ))}
      </fieldset>

      <ul className="frotis-v3-legend" aria-label="Leyenda de contornos">
        <li data-kind="parasitized"><span aria-hidden="true" />Candidata parasitada: trazo continuo grueso</li>
        <li data-kind="uninfected"><span aria-hidden="true" />No infectada: trazo fino</li>
        <li data-kind="unclassified"><span aria-hidden="true" />Sin clasificar: trazo punteado</li>
      </ul>

      {onOpenReview ? (
        <button type="button" className="frotis-v3-button" onClick={onOpenReview}>
          Revisar células
        </button>
      ) : null}
    </div>
  );
}
