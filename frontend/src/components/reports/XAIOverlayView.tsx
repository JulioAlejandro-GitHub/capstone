import { useEffect, useRef, useState } from 'react';
import { useScientificArtifact, type XAIImageResource } from '../../hooks/useScientificArtifact';
import { attributionPixels, parseNpy } from '../../utils/attributionMaps';
import { XAI_LABELS, XAI_METHODS, type XAIArtifact, type XAIComparison, type XAIMethod } from './xai/comparison';

type Layer = { canvas: HTMLCanvasElement | null; loading: boolean; error: string | null };
const signedMethods: Record<XAIMethod, boolean> = { gradcam: false, lime: true, shap: true };
const descriptions: Record<XAIMethod, string> = {
  gradcam: 'Mapa de activación de la última capa convolucional',
  lime: 'Superpíxeles: rojo a favor de la clase explicada, azul en contra',
  shap: 'Atribución por píxel: rojo a favor, azul en contra',
};
export const defaultOpacity: Record<XAIMethod, number> = { gradcam: 50, lime: 0, shap: 0 };

// Decodes one `map` artifact into an offscreen canvas at the model input resolution.
function useAttributionLayer(artifact: XAIArtifact | undefined, datasource: string, enabled: boolean, signed: boolean): Layer {
  const resource = useScientificArtifact(artifact, datasource, enabled, false);
  const [layer, setLayer] = useState<Layer>({ canvas: null, loading: false, error: null });
  useEffect(() => {
    if (!resource.url) return;
    let active = true;
    fetch(resource.url).then(response => response.arrayBuffer()).then(buffer => {
      const map = parseNpy(buffer);
      const canvas = document.createElement('canvas');
      canvas.width = map.width; canvas.height = map.height;
      canvas.getContext('2d')!.putImageData(new ImageData(attributionPixels(map, signed), map.width, map.height), 0, 0);
      if (active) setLayer({ canvas, loading: false, error: null });
    }).catch((error: unknown) => {
      if (active) setLayer({ canvas: null, loading: false, error: error instanceof Error ? error.message : 'Mapa no legible.' });
    });
    return () => { active = false; };
  }, [resource.url, signed]);
  if (resource.failure) return { canvas: null, loading: false, error: resource.failure.message };
  return { ...layer, loading: layer.loading || Boolean(resource.loading) };
}

function useLoadedImage(url: string | null | undefined) {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  useEffect(() => {
    setImage(null);
    if (!url) return;
    const element = new Image();
    element.onload = () => setImage(element);
    element.src = url;
  }, [url]);
  return image;
}

/** Original cell as base; each attribution map drawn on top with its own opacity (0–100 %). */
export function XAIOverlayView({ comparison, resources, datasource }: { comparison: XAIComparison; resources: Record<XAIMethod | 'original', XAIImageResource>; datasource: string }) {
  const [settings, setSettings] = useState(() => Object.fromEntries(XAI_METHODS.map(method => [method, { on: true, opacity: defaultOpacity[method] }])) as Record<XAIMethod, { on: boolean; opacity: number }>);
  const layers: Record<XAIMethod, Layer> = {
    gradcam: useAttributionLayer(comparison.methods.gradcam?.mapArtifact, datasource, Boolean(comparison.methods.gradcam?.mapArtifact), signedMethods.gradcam),
    lime: useAttributionLayer(comparison.methods.lime?.mapArtifact, datasource, Boolean(comparison.methods.lime?.mapArtifact), signedMethods.lime),
    shap: useAttributionLayer(comparison.methods.shap?.mapArtifact, datasource, Boolean(comparison.methods.shap?.mapArtifact), signedMethods.shap),
  };
  const original = useLoadedImage(resources.original.url);
  const stage = useRef<HTMLCanvasElement>(null);
  const size = layers.gradcam.canvas ?? layers.lime.canvas ?? layers.shap.canvas;
  const width = size?.width ?? 200, height = size?.height ?? 200;
  const visible = XAI_METHODS.filter(method => settings[method].on && settings[method].opacity > 0 && layers[method].canvas);
  useEffect(() => {
    const context = stage.current?.getContext('2d');
    if (!context) return;
    context.globalAlpha = 1;
    context.clearRect(0, 0, width, height);
    // The model sees the cell resized to its input size; the maps share that grid.
    if (original) context.drawImage(original, 0, 0, width, height);
    for (const method of visible) {
      context.globalAlpha = settings[method].opacity / 100;
      context.drawImage(layers[method].canvas!, 0, 0, width, height);
    }
    context.globalAlpha = 1;
  });
  const update = (method: XAIMethod, change: Partial<{ on: boolean; opacity: number }>) =>
    setSettings(old => ({ ...old, [method]: { ...old[method], ...change } }));
  return <div className="xai-overlay">
    <div className="xai-overlay-main">
    <figure className="xai-overlay-stage">
      <canvas ref={stage} width={width} height={height} role="img"
        aria-label={`Célula original${visible.map(method => ` con ${XAI_LABELS[method]} al ${settings[method].opacity} %`).join('')}`} />
      {!original && <p role="status">{resources.original.loading ? 'Cargando célula original…' : 'Sin imagen original trazable.'}</p>}
      <figcaption>Célula original{visible.map(method => ` + ${XAI_LABELS[method]} (${settings[method].opacity} %)`).join('')} · {width}×{height} px, resolución de entrada del modelo</figcaption>
    </figure>
    <div className="xai-overlay-legend" aria-label="Escalas de color">
      <span><i className="xai-ramp" /> Grad-CAM: activación baja → alta</span>
      <span><i className="xai-swatch" data-sign="positive" /> a favor · <i className="xai-swatch" data-sign="negative" /> en contra (LIME, SHAP)</span>
      <small>Cada mapa se normaliza por su propio máximo; las intensidades no son comparables entre métodos.</small>
    </div>
    </div>
    <ul className="xai-overlay-layers" aria-label="Capas de explicación">
      {XAI_METHODS.map((method, index) => {
        const evidence = comparison.methods[method];
        const layer = layers[method];
        const usable = Boolean(evidence?.mapArtifact && layer.canvas);
        return <li key={method} data-method={method} data-usable={usable}>
          <div className="xai-overlay-thumb">{resources[method].url ? <img src={resources[method].url!} alt="" /> : <span aria-hidden="true">—</span>}</div>
          <div className="xai-overlay-control">
            <div className="xai-overlay-head">
              <label><input type="checkbox" checked={settings[method].on} disabled={!usable} onChange={event => update(method, { on: event.target.checked })} />
                <strong>{String(index + 1).padStart(2, '0')} · {XAI_LABELS[method]}</strong></label>
              <output>{settings[method].opacity} %</output>
            </div>
            <div className="xai-slider"><span>0 %</span>
              <input type="range" min={0} max={100} step={1} value={settings[method].opacity} disabled={!usable || !settings[method].on}
                aria-label={`Opacidad de ${XAI_LABELS[method]}`} onChange={event => update(method, { opacity: Number(event.target.value) })} />
              <span>100 %</span></div>
            <small>{!evidence ? 'Sin explicación generada para esta célula.' : !evidence.mapArtifact ? 'Sin mapa de atribución registrado.'
              : layer.error ? `Mapa no disponible: ${layer.error}` : layer.loading || !layer.canvas ? 'Cargando mapa…' : descriptions[method]}</small>
          </div>
        </li>;
      })}
    </ul>
  </div>;
}
