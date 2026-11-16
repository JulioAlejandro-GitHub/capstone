import { ChevronLeft, ChevronRight, Crosshair, Link2 } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import {
  cellKind,
  formatProbability,
  KIND_LABEL,
  neighbourCell,
  reviewLabel,
  type CellFilter,
  type MicroscopeCell,
} from '../adapters/cellLayer';
import type { CellLayerState } from '../hooks/useCellLayer';
import { useCellCrop } from '../hooks/useCellCrop';

const FILTER_LABEL: Record<CellFilter, string> = {
  all: 'Todas',
  parasitized: 'Candidatas parasitadas',
  near_threshold: 'Cercanas al umbral',
  pending_review: 'Pendientes de revisión',
};

/**
 * Inspector de REVIEW CELLS: navegación y lectura de la célula seleccionada.
 * Panel fijo de la vista; los instrumentos flotantes se reubican a su alrededor.
 */
export function CellInspector({
  layer,
  cells,
  filter,
  onFilterChange,
  selected,
  onSelect,
  onFocus,
  shareUrl,
  reviewHref,
}: {
  layer: CellLayerState;
  /** Células de la imagen activa que cumplen el filtro, en orden de índice. */
  cells: readonly MicroscopeCell[];
  filter: CellFilter;
  onFilterChange: (filter: CellFilter) => void;
  selected: MicroscopeCell | null;
  onSelect: (cell: MicroscopeCell) => void;
  onFocus: (cell: MicroscopeCell) => void;
  /** Enlace reproducible al hallazgo seleccionado. */
  shareUrl: string | null;
  /** Revisión completa existente (decisiones humanas, explicabilidad). */
  reviewHref: string | null;
}) {
  const crop = useCellCrop(selected?.cropId ?? null, selected?.cropUrl ?? null);
  const [copied, setCopied] = useState('');
  const position = selected ? cells.findIndex((cell) => cell.detectionId === selected.detectionId) : -1;
  const go = (step: 1 | -1) => {
    const next = neighbourCell(cells, selected?.detectionId ?? null, step);
    if (next) onSelect(next);
  };
  const copy = async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied('Enlace copiado.');
    } catch {
      setCopied('No fue posible copiar el enlace.');
    }
  };
  const kind = selected ? cellKind(selected) : null;

  return (
    <aside className="frotis-v3-inspector" aria-label="Inspector de células">
      <header className="frotis-v3-inspector-head">
        <h2>Células de esta imagen</h2>
        <label className="frotis-v3-select">
          <span className="frotis-v3-visually-hidden">Filtrar células</span>
          <select value={filter} onChange={(event) => onFilterChange(event.target.value as CellFilter)}>
            {(Object.keys(FILTER_LABEL) as CellFilter[]).map((id) => (
              <option key={id} value={id}>{FILTER_LABEL[id]}</option>
            ))}
          </select>
        </label>
      </header>

      {layer.status === 'loading' ? <p className="frotis-v3-hint" role="status">Cargando células…</p> : null}
      {layer.status === 'unavailable' ? <p className="frotis-v3-hint" role="alert">{layer.message}</p> : null}

      {layer.status === 'ready' ? (
        <>
          <div className="frotis-v3-instrument-row" role="group" aria-label="Navegación celular">
            <button type="button" className="frotis-v3-icon-button" disabled={!cells.length} onClick={() => go(-1)} aria-label="Célula anterior">
              <ChevronLeft aria-hidden="true" />
            </button>
            <output className="frotis-v3-reading">
              {cells.length ? `${position >= 0 ? position + 1 : '—'} de ${cells.length}` : 'Sin células'}
            </output>
            <button type="button" className="frotis-v3-icon-button" disabled={!cells.length} onClick={() => go(1)} aria-label="Célula siguiente">
              <ChevronRight aria-hidden="true" />
            </button>
            <button
              type="button"
              className="frotis-v3-icon-button"
              disabled={!selected}
              onClick={() => selected && onFocus(selected)}
              aria-label="Centrar la célula seleccionada"
              title="Centrar en el visor"
            >
              <Crosshair aria-hidden="true" />
            </button>
          </div>

          {!cells.length ? (
            <p className="frotis-v3-hint">Ninguna célula de esta imagen cumple el filtro «{FILTER_LABEL[filter]}».</p>
          ) : null}

          {selected && kind ? (
            <div className="frotis-v3-cell">
              <div className="frotis-v3-cell-crop">
                {crop.url ? <img src={crop.url} alt={`Recorte de la célula ${selected.cellCode}`} /> : null}
                {!crop.url ? <span>{crop.failed || !selected.cropId ? 'Recorte no disponible' : 'Cargando recorte…'}</span> : null}
              </div>
              <dl className="frotis-v3-cell-facts">
                <div><dt>Célula</dt><dd>{selected.cellCode}</dd></div>
                <div><dt>Clasificación IA</dt><dd data-kind={kind}>{KIND_LABEL[kind]}</dd></div>
                {selected.prediction ? (
                  <>
                    <div><dt>P(parasitada)</dt><dd>{formatProbability(selected.prediction.probabilityParasitized)}</dd></div>
                    <div><dt>Umbral usado</dt><dd>{formatProbability(selected.prediction.threshold)}</dd></div>
                    {selected.prediction.nearThreshold ? <div><dt>Aviso</dt><dd>Cercana al umbral</dd></div> : null}
                    <div><dt>Revisión de la predicción</dt><dd>{reviewLabel(selected.prediction.reviewStatus)}</dd></div>
                    {selected.prediction.reviewedLabel ? (
                      <div><dt>Etiqueta humana</dt><dd>{KIND_LABEL[selected.prediction.reviewedLabel]}</dd></div>
                    ) : null}
                  </>
                ) : null}
                <div><dt>Revisión de la detección</dt><dd>{reviewLabel(selected.detectionReview)}</dd></div>
                <div>
                  <dt>Posición</dt>
                  <dd>x {selected.bbox.x}, y {selected.bbox.y} · {selected.bbox.width} × {selected.bbox.height} px</dd>
                </div>
              </dl>
              <div className="frotis-v3-panel-buttons">
                <button type="button" className="frotis-v3-button" onClick={() => void copy()} disabled={!shareUrl}>
                  <Link2 aria-hidden="true" /> Copiar enlace
                </button>
                {reviewHref ? (
                  <Link className="frotis-v3-button" to={reviewHref}>Registrar revisión</Link>
                ) : null}
              </div>
              <span className="frotis-v3-hint" role="status" aria-live="polite">{copied}</span>
              <p className="frotis-v3-hint">
                Confirmar o corregir esta célula se registra hoy en el detalle del Historial, que abre esta misma selección.
              </p>
            </div>
          ) : cells.length ? (
            <p className="frotis-v3-hint">Selecciona una célula en el frotis o usa las flechas para recorrerlas.</p>
          ) : null}
        </>
      ) : null}
    </aside>
  );
}
