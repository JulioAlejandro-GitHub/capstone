import { Maximize, Minus, Plus, RotateCcw, RotateCw } from 'lucide-react';

import { DEFAULT_OPTICS, type OpticsSettings } from '../../state/presentationStorage';

const SLIDERS: Array<{ key: keyof OpticsSettings; label: string; min: number; max: number; step: number; unit: string }> = [
  { key: 'brightness', label: 'Brillo', min: 40, max: 200, step: 1, unit: '%' },
  { key: 'contrast', label: 'Contraste', min: 40, max: 200, step: 1, unit: '%' },
  { key: 'gamma', label: 'Gamma', min: 0.4, max: 2.5, step: 0.05, unit: '' },
  { key: 'saturation', label: 'Saturación', min: 0, max: 200, step: 1, unit: '%' },
];

/** Imagen y Óptica: zoom digital, rotación y ajustes visuales reversibles. */
export function OpticsPanel({
  available,
  zoomPercent,
  rotation,
  fitted,
  optics,
  minimap,
  onZoom,
  onFit,
  onActualSize,
  onRotate,
  onOpticsChange,
  onMinimapChange,
}: {
  /** Falso mientras no hay una imagen visible que ajustar. */
  available: boolean;
  zoomPercent: number | null;
  rotation: number;
  fitted: boolean;
  optics: OpticsSettings;
  minimap: boolean;
  onZoom: (factor: number) => void;
  onFit: () => void;
  onActualSize: () => void;
  onRotate: (delta: number) => void;
  onOpticsChange: (optics: OpticsSettings) => void;
  onMinimapChange: (visible: boolean) => void;
}) {
  const pristine = SLIDERS.every(({ key }) => optics[key] === DEFAULT_OPTICS[key]);
  return (
    <div className="frotis-v3-instrument">
      <div className="frotis-v3-instrument-row" role="group" aria-label="Zoom digital">
        <button type="button" className="frotis-v3-icon-button" disabled={!available} onClick={() => onZoom(0.8)} aria-label="Alejar">
          <Minus aria-hidden="true" />
        </button>
        <output className="frotis-v3-reading" aria-label="Zoom digital">
          {zoomPercent == null ? '—' : `${Math.round(zoomPercent)} %`}
        </output>
        <button type="button" className="frotis-v3-icon-button" disabled={!available} onClick={() => onZoom(1.25)} aria-label="Acercar">
          <Plus aria-hidden="true" />
        </button>
        <button type="button" className="frotis-v3-icon-button" disabled={!available} aria-pressed={fitted} onClick={onFit} aria-label="Ajustar a pantalla" title="Ajustar a pantalla">
          <Maximize aria-hidden="true" />
        </button>
        <button type="button" className="frotis-v3-chip" disabled={!available} onClick={onActualSize} title="Un píxel de imagen por píxel de pantalla">
          1:1
        </button>
      </div>
      <p className="frotis-v3-hint">Zoom digital sobre los píxeles de la imagen; no indica aumento óptico.</p>

      <div className="frotis-v3-instrument-row" role="group" aria-label="Rotación">
        <button type="button" className="frotis-v3-icon-button" disabled={!available} onClick={() => onRotate(-90)} aria-label="Rotar 90° a la izquierda">
          <RotateCcw aria-hidden="true" />
        </button>
        <output className="frotis-v3-reading" aria-label="Rotación">{rotation}°</output>
        <button type="button" className="frotis-v3-icon-button" disabled={!available} onClick={() => onRotate(90)} aria-label="Rotar 90° a la derecha">
          <RotateCw aria-hidden="true" />
        </button>
      </div>

      {SLIDERS.map(({ key, label, min, max, step, unit }) => (
        <label key={key} className="frotis-v3-slider">
          <span>{label}</span>
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={optics[key]}
            onChange={(event) => onOpticsChange({ ...optics, [key]: Number(event.target.value) })}
          />
          <output>{key === 'gamma' ? optics[key].toFixed(2) : `${optics[key]}${unit}`}</output>
        </label>
      ))}

      <button
        type="button"
        className="frotis-v3-button"
        disabled={pristine}
        onClick={() => onOpticsChange(DEFAULT_OPTICS)}
      >
        Restaurar imagen original
      </button>

      <label className="frotis-v3-check">
        <input type="checkbox" checked={minimap} onChange={(event) => onMinimapChange(event.target.checked)} />
        <span>Mostrar minimapa</span>
      </label>
      <p className="frotis-v3-hint">Los ajustes son solo visuales: la imagen original y el análisis no cambian.</p>
    </div>
  );
}
