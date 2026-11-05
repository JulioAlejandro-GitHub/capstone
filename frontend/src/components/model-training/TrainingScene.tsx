import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react';

import { formatCount, type TrainingLayer } from './trainingModel';
import { CELL_CATEGORY_LABELS, classText, type TrainingCell } from './cellModel';

/**
 * Escena isométrica del flujo de tensores (proyección oblicua calculada aquí, no CSS 3D):
 * eje X = flujo (canales como grosor) · eje Y = alto · eje Z = ancho en fuga diagonal.
 * Portada desde ejemplos_visualizacion_modelos/vgg16_arquitectura.html.
 */

type Scale = 'lineal' | 'comp';
interface ViewBox { x: number; y: number; w: number; h: number }
interface Placed { layer: TrainingLayer; H: number; W: number; D: number; X0: number; X1: number; cx: number }

const OX = 0.6, OY = 0.4, LABEL_GAP = 34;
/* Límites de zoom: ancho del viewBox en unidades del diagrama (medidos sobre la maqueta). */
export const ZOOM_W_MAX = 3324.002989724566;
export const ZOOM_W_MIN = 58.81532261437357;
const clampW = (w: number) => Math.min(ZOOM_W_MAX, Math.max(ZOOM_W_MIN, w));

function size(layer: TrainingLayer, scale: Scale) {
  if (!layer.shapeKnown) return { H: 40, W: 40, D: 10 };
  const d = layer.d ?? 1;
  if (layer.vector) return { H: scale === 'lineal' ? Math.max(d * 0.2, 10) : 10 + 17 * Math.log2(Math.max(d, 1)), W: 12, D: 12 };
  const s = layer.h ?? 1;
  return {
    H: scale === 'lineal' ? Math.max(s * 1.12, 8) : 17 * Math.sqrt(s),
    W: scale === 'lineal' ? Math.max((layer.w ?? s) * 1.12, 8) : 17 * Math.sqrt(layer.w ?? s),
    D: scale === 'lineal' ? Math.max(d * 0.11, 3) : 4 + 9 * Math.log2(Math.max(d, 2)),
  };
}

const P = (x: number, y: number, z: number): [number, number] => [x + z * OX, -y - z * OY];
const pts = (list: [number, number][]) => list.map(point => point.join(',')).join(' ');

const THUMB = 40;
function layout(layers: TrainingLayer[], scale: Scale, withCell: boolean) {
  let cursor = 0;
  const placed: Placed[] = layers.map(layer => {
    const { H, W, D } = size(layer, scale);
    const bw = D + W * OX;
    const slot = Math.max(bw + 44, 116);
    const X0 = cursor + (slot - bw) / 2 + (W / 2) * OX;
    const item = { layer, H, W, D, X0, X1: X0 + D, cx: cursor + slot / 2 };
    cursor += slot;
    return item;
  });
  const bottom = Math.max(0, ...placed.map(p => p.H / 2 + (p.W / 2) * OY));
  const top = Math.min(0, ...placed.map(p => -p.H / 2 - (p.W / 2) * OY));
  const bounds = { x: -40, y: top - 40, w: cursor + 80, h: bottom + LABEL_GAP + 50 + (withCell ? THUMB + 34 : 0) - (top - 40) };
  return { placed, bottom, width: cursor, bounds };
}

const ICON_FULL = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
  <path d="M3 7V5a2 2 0 0 1 2-2h2" /><path d="M17 3h2a2 2 0 0 1 2 2v2" /><path d="M21 17v2a2 2 0 0 1-2 2h-2" /><path d="M7 21H5a2 2 0 0 1-2-2v-2" /><rect width="10" height="8" x="7" y="8" rx="1" /></svg>;
const ICON_MIN = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
  <path d="M8 3v3a2 2 0 0 1-2 2H3" /><path d="M21 8h-3a2 2 0 0 1-2-2V3" /><path d="M3 16h3a2 2 0 0 1 2 2v3" /><path d="M16 21v-3a2 2 0 0 1 2-2h3" /></svg>;

export function TrainingScene({ layers, selected, onSelect, phaseLabel, cell = null, onCellOpen, tabs }: {
  layers: TrainingLayer[]; selected: number; onSelect: (index: number) => void; phaseLabel: string;
  /** Célula seleccionada: su imagen se muestra en la entrada y, con el resultado, en la salida. */
  cell?: TrainingCell | null;
  /** Abre «Vista ampliada · Célula original»; sin él la imagen es sólo ilustrativa. */
  onCellOpen?: () => void;
  /** Pestañas de la vista: reemplazan el título «Flujo de tensores» en la cabecera de la tarjeta. */
  tabs?: ReactNode;
}) {
  const card = useRef<HTMLDivElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const [scale, setScale] = useState<Scale>('lineal');
  const [beams, setBeams] = useState(true);
  const [progressive, setProgressive] = useState(false);
  const [maximized, setMaximized] = useState(false);
  const [nativeFull, setNativeFull] = useState(false);
  const [vb, setVb] = useState<ViewBox | null>(null);
  const [fitW, setFitW] = useState<number | null>(null);
  const [tip, setTip] = useState<{ x: number; y: number; index: number } | null>(null);
  const drag = useRef<{ x: number; y: number; vb: ViewBox } | null>(null);
  const geometry = useMemo(() => layout(layers, scale, Boolean(cell)), [layers, scale, cell]);

  const fit = useCallback(() => {
    const element = svg.current;
    if (!element) return;
    const rect = element.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const ar = rect.width / rect.height;
    let { x, y, w, h } = geometry.bounds;
    if (w / h > ar) { const nh = w / ar; y -= (nh - h) / 2; h = nh; } else { const nw = h * ar; x -= (nw - w) / 2; w = nw; }
    const cw = clampW(w);
    if (cw !== w) { const ch = cw / ar; x += (w - cw) / 2; y += (h - ch) / 2; w = cw; h = ch; }
    setFitW(w);
    setVb({ x, y, w, h });
  }, [geometry]);

  useEffect(() => {
    fit();
    const element = svg.current;
    if (!element || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => fit());
    observer.observe(element);
    return () => observer.disconnect();
  }, [fit]);

  const zoom = useCallback((factor: number, clientX?: number, clientY?: number) => setVb(current => {
    const element = svg.current;
    if (!current || !element) return current;
    const nw = clampW(current.w * factor);
    if (Math.abs(nw - current.w) < 1e-9) return current;
    const f = nw / current.w;
    const rect = element.getBoundingClientRect();
    const px = clientX == null ? 0.5 : (clientX - rect.left) / rect.width;
    const py = clientY == null ? 0.5 : (clientY - rect.top) / rect.height;
    const nh = current.h * f;
    return { x: current.x + (current.w - nw) * px, y: current.y + (current.h - nh) * py, w: nw, h: nh };
  }), []);

  useEffect(() => {
    const element = svg.current;
    if (!element) return;
    const onWheel = (event: WheelEvent) => { event.preventDefault(); zoom(event.deltaY > 0 ? 1.1 : 0.9, event.clientX, event.clientY); };
    element.addEventListener('wheel', onWheel, { passive: false });
    return () => element.removeEventListener('wheel', onWheel);
  }, [zoom]);

  /* Recorrido del flujo: avanza la selección y deja encendidas las capas ya recorridas. */
  useEffect(() => {
    if (!progressive) return;
    const timer = window.setTimeout(() => {
      if (selected >= layers.length - 1) setProgressive(false); else onSelect(selected + 1);
    }, 1100);
    return () => window.clearTimeout(timer);
  }, [progressive, selected, layers.length, onSelect]);

  /* Pantalla completa del card: API nativa (con prefijo Safari) y respaldo CSS si se rechaza. */
  useEffect(() => {
    const sync = () => {
      const doc = document as Document & { webkitFullscreenElement?: Element | null };
      setNativeFull((document.fullscreenElement ?? doc.webkitFullscreenElement ?? null) === card.current);
    };
    document.addEventListener('fullscreenchange', sync);
    document.addEventListener('webkitfullscreenchange', sync);
    return () => { document.removeEventListener('fullscreenchange', sync); document.removeEventListener('webkitfullscreenchange', sync); };
  }, []);
  const full = nativeFull || maximized;
  useEffect(() => { requestAnimationFrame(fit); }, [full, fit]);
  const toggleFull = async () => {
    if (maximized) { setMaximized(false); return; }
    const doc = document as Document & { webkitExitFullscreen?: () => Promise<void> | void };
    if (nativeFull) { try { await (document.exitFullscreen ? document.exitFullscreen() : doc.webkitExitFullscreen?.()); } catch { /* sin acción */ } return; }
    const element = card.current as (HTMLDivElement & { webkitRequestFullscreen?: () => Promise<void> | void }) | null;
    try {
      if (element?.requestFullscreen) await element.requestFullscreen();
      else if (element?.webkitRequestFullscreen) await element.webkitRequestFullscreen();
      else throw new Error('sin API');
    } catch { setMaximized(true); }
  };

  const onKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'ArrowRight') { event.preventDefault(); onSelect(Math.min(layers.length - 1, selected + 1)); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); onSelect(Math.max(0, selected - 1)); }
    if (event.key === 'Escape' && maximized) setMaximized(false);
  };
  const pointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    // Bloques, etiquetas y la imagen de la célula son controles: no inician el arrastre (la captura les robaría el clic).
    if ((event.target as Element).closest('[data-layer], .mt-lbl') || !vb) return;
    drag.current = { x: event.clientX, y: event.clientY, vb };
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const pointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    const start = drag.current;
    if (!start || !svg.current) return;
    const k = start.vb.w / svg.current.getBoundingClientRect().width;
    setVb({ ...start.vb, x: start.vb.x - (event.clientX - start.x) * k, y: start.vb.y - (event.clientY - start.y) * k });
  };
  const on = (index: number) => progressive ? index <= selected : index === selected;
  const beamOn = (index: number) => progressive ? index < selected : index === selected || index === selected - 1;
  const eps = 1e-6;
  const tipLayer = tip ? layers[tip.index] : null;
  const labelY = geometry.bottom + LABEL_GAP;

  return <div ref={card} className={`mt-card mt-viz${maximized ? ' is-max' : ''}`} onKeyDown={onKey}>
    <div className="mt-card-h">{tabs ?? <h2>Flujo de tensores</h2>}<span className="mt-hint">Arrastra para mover · rueda para zoom · <kbd>←</kbd> <kbd>→</kbd> para recorrer · {phaseLabel}</span></div>
    <nav className="mt-stepper" aria-label="Bloques">{layers.map(layer => <button key={layer.id} type="button" className="mt-step" aria-pressed={layer.index === selected}
      onClick={() => onSelect(layer.index)}><span className="mt-n">{String(layer.index).padStart(2, '0')}</span><i style={{ background: `rgb(${layer.color})` }} />{layer.label}</button>)}</nav>
    <div className="mt-stage">
      <div className="mt-toolbar">
        <div className="mt-tb-group" role="group" aria-label="Escala">
          <button type="button" className="mt-tb" aria-pressed={scale === 'lineal'} title="Tamaños proporcionales a los valores reales" onClick={() => setScale('lineal')}>Proporcional</button>
          <button type="button" className="mt-tb" aria-pressed={scale === 'comp'} title="Comprime los extremos (√ en espacio, log en canales)" onClick={() => setScale('comp')}>Compensada</button>
        </div>
        <div className="mt-tb-group">
          <button type="button" className="mt-tb" aria-pressed={progressive} onClick={() => { if (progressive) setProgressive(false); else { onSelect(0); setProgressive(true); } }}>{progressive ? '❚❚ Pausa' : '▶ Recorrer flujo'}</button>
          <button type="button" className="mt-tb" aria-pressed={beams} onClick={() => setBeams(value => !value)}>Haces</button>
        </div>
        <div className="mt-tb-group">
          <button type="button" className="mt-tb" aria-label="Acercar" disabled={!vb || vb.w <= ZOOM_W_MIN * (1 + eps)} onClick={() => zoom(0.8)}>＋</button>
          <span className="mt-zoom" aria-live="polite">{vb && fitW ? `${Math.round(100 * fitW / vb.w)}%` : '—'}</span>
          <button type="button" className="mt-tb" aria-label="Alejar" disabled={!vb || vb.w >= ZOOM_W_MAX * (1 - eps)} onClick={() => zoom(1.25)}>－</button>
          <button type="button" className="mt-tb" onClick={fit}>Encajar</button>
        </div>
        <div className="mt-tb-group">
          <button type="button" className="mt-tb mt-icon" aria-pressed={full} aria-label={full ? 'Salir de pantalla completa' : 'Pantalla completa'}
            title={full ? 'Salir de pantalla completa' : 'Pantalla completa'} onClick={toggleFull}>{full ? ICON_MIN : ICON_FULL}</button>
        </div>
      </div>
      <svg ref={svg} className="mt-scene" role="img" aria-label="Diagrama isométrico de los bloques del modelo"
        viewBox={vb ? `${vb.x} ${vb.y} ${vb.w} ${vb.h}` : undefined}
        onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={() => { drag.current = null; }}>
        <defs><filter id="mt-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
        <g className="mt-root mt-dim">
          <line x1={-20} x2={geometry.width + 20} y1={geometry.bottom + 12} y2={geometry.bottom + 12} className="mt-baseline" />
          {beams && <g>{geometry.placed.slice(0, -1).map((item, k) => {
            const next = geometry.placed[k + 1];
            const { X1 } = item, h = item.H / 2, w = item.W / 2, nh = next.H / 2, nw = next.W / 2, nx = next.X0;
            const fill = `rgba(${item.layer.color},0.07)`, stroke = `rgba(${item.layer.color},0.35)`;
            const quads: [number, number][][] = [
              [P(X1, -h, -w), P(X1, -h, w), P(nx, -nh, nw), P(nx, -nh, -nw)],
              [P(X1, h, w), P(X1, -h, w), P(nx, -nh, nw), P(nx, nh, nw)],
              [P(X1, h, -w), P(X1, h, w), P(nx, nh, nw), P(nx, nh, -nw)],
              [P(X1, h, -w), P(X1, -h, -w), P(nx, -nh, -nw), P(nx, nh, -nw)],
            ];
            const edges: [[number, number], [number, number]][] = [[P(X1, h, -w), P(nx, nh, -nw)], [P(X1, -h, -w), P(nx, -nh, -nw)], [P(X1, h, w), P(nx, nh, nw)], [P(X1, -h, w), P(nx, -nh, nw)]];
            return <g key={item.layer.id} className={`mt-beam${beamOn(k) ? ' on' : ''}`}>
              {quads.map((quad, q) => <polygon key={q} points={pts(quad)} fill={fill} />)}
              {edges.map(([a, b], e) => <line key={e} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke={stroke} />)}
            </g>;
          })}</g>}
          {geometry.placed.map(item => {
            const { layer, X0, X1 } = item, h = item.H / 2, w = item.W / 2, col = layer.color;
            const front = P(X0, 0, -w), bottomMid = P((X0 + X1) / 2, -h, -w), topMid = P((X0 + X1) / 2, h, w);
            return <g key={layer.id} data-layer={layer.index} className={`mt-layer${on(layer.index) ? ' on' : ''}`} data-trained={layer.trainable} data-pending={!layer.shapeKnown}
              tabIndex={0} role="button" aria-label={`${layer.label}: ${layer.outputText}`}
              onClick={() => onSelect(layer.index)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(layer.index); } }}
              onMouseMove={event => setTip({ x: event.clientX, y: event.clientY, index: layer.index })} onMouseLeave={() => setTip(null)}>
              <polygon className="mt-halo" points={pts([P(X0, h, -w), P(X1, h, -w), P(X1, h, w), P(X1, -h, w), P(X1, -h, -w), P(X0, -h, -w)])}
                fill={layer.index === selected ? `rgba(${col},0.25)` : 'transparent'} filter="url(#mt-glow)" />
              <polygon className="mt-face" points={pts([P(X0, h, -w), P(X1, h, -w), P(X1, h, w), P(X0, h, w)])} fill={`rgba(${col},0.55)`} stroke={`rgb(${col})`} />
              <polygon className="mt-face" points={pts([P(X1, h, -w), P(X1, h, w), P(X1, -h, w), P(X1, -h, -w)])} fill={`rgba(${col},0.38)`} stroke={`rgb(${col})`} />
              <polygon className="mt-face mt-front" points={pts([P(X0, h, -w), P(X1, h, -w), P(X1, -h, -w), P(X0, -h, -w)])} fill={`rgba(${col},0.28)`} stroke={`rgb(${col})`} />
              {layer.shapeKnown && !layer.vector && item.H > 26 && <>
                <text className="mt-dim-hw" x={front[0] - 6} y={front[1] + 4} textAnchor="end">{layer.h}</text>
                <text className="mt-dim-hw" x={bottomMid[0]} y={bottomMid[1] + 14} textAnchor="middle">{layer.w}</text>
              </>}
              <text className={layer.shapeKnown ? 'mt-dim-d' : 'mt-dim-pending'} x={topMid[0]} y={topMid[1] - 7} textAnchor="middle">{layer.shapeKnown ? layer.d : 'Pendiente'}</text>
            </g>;
          })}
          {geometry.placed.map(item => <g key={item.layer.id} className={`mt-lbl${on(item.layer.index) ? ' on' : ''}`} onClick={() => onSelect(item.layer.index)}>
            <rect x={item.cx - 6} y={labelY - 22} width={12} height={3} rx={1.5} fill={`rgb(${item.layer.color})`} />
            <text className="mt-lbl-name" x={item.cx} y={labelY} textAnchor="middle">{item.layer.label}</text>
            <text className="mt-lbl-desc" x={item.cx} y={labelY + 16} textAnchor="middle">{item.layer.description}</text>
            <text className="mt-lbl-shape" x={item.cx} y={labelY + 32} textAnchor="middle">{item.layer.shapeKnown ? (item.layer.vector ? `${item.layer.d}` : `${item.layer.h}×${item.layer.w}×${item.layer.d}`) : 'forma pendiente'}</text>
            {cell && (item.layer.kind === 'input' || item.layer.kind === 'output') && <g className="mt-cell" data-category={item.layer.kind === 'output' ? cell.category ?? 'unknown' : undefined}
              data-open={Boolean(onCellOpen)} {...(onCellOpen ? { role: 'button', tabIndex: 0, 'aria-label': 'Ampliar Célula original',
                onClick: (event: { stopPropagation: () => void }) => { event.stopPropagation(); onCellOpen(); },
                onKeyDown: (event: { key: string; preventDefault: () => void; stopPropagation: () => void }) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); event.stopPropagation(); onCellOpen(); } } } : {})}>
              <rect className="mt-cell-frame" x={item.cx - THUMB / 2 - 2} y={labelY + 42} width={THUMB + 4} height={THUMB + 4} rx={5} />
              <image href={cell.image} x={item.cx - THUMB / 2} y={labelY + 44} width={THUMB} height={THUMB} preserveAspectRatio="xMidYMid slice">
                <title>{item.layer.kind === 'input' ? `Célula ${cell.sampleId}` : `${classText(cell.predicted)} · score ${cell.score.toFixed(4)}`}</title></image>
              <text className="mt-cell-text" x={item.cx} y={labelY + THUMB + 60} textAnchor="middle">{item.layer.kind === 'input'
                ? `célula ${cell.sampleId.slice(0, 8)}`
                : `${cell.category ? CELL_CATEGORY_LABELS[cell.category] : classText(cell.predicted)} · ${cell.score.toFixed(3)}`}</text>
            </g>}
          </g>)}
        </g>
      </svg>
      <div className="mt-legend-mini"><b>Escala:</b> {scale === 'lineal' ? 'proporcional a los valores' : 'compensada (√ espacio · log canales)'}<br />
        <span className="mt-sw-hw">■</span> alto/ancho &nbsp; <span className="mt-sw-d">■</span> canales &nbsp; <span className="mt-sw-frozen">▭</span> congelado en la fase</div>
      {tip && tipLayer && <div className="mt-tip" role="tooltip" style={{ left: Math.min(tip.x + 14, window.innerWidth - 260), top: Math.min(tip.y + 14, window.innerHeight - (cell ? 290 : 150)) }}>
        <div className="mt-tip-t">{tipLayer.label} <span>· {tipLayer.description}</span></div>
        <div className="mt-io"><span className="mt-in">ENTRADA</span><span>{tipLayer.inputText}</span></div>
        <div className="mt-io"><span className="mt-out">SALIDA</span><span>{tipLayer.outputText}</span></div>
        <div className="mt-io mt-muted"><span>parámetros</span><span>{formatCount(tipLayer.parameters)}</span></div>
        <div className="mt-io mt-muted"><span>{tipLayer.trainable ? 'se entrena' : 'congelado'}</span><span>{formatCount(tipLayer.volume)} act.</span></div>
        {cell && (tipLayer.kind === 'input' || tipLayer.kind === 'output') && <div className="mt-tip-cell" data-category={tipLayer.kind === 'output' ? cell.category ?? 'unknown' : undefined}>
          <img src={cell.image} alt={`Célula ${cell.sampleId}`} />
          <dl>{tipLayer.kind === 'input'
            ? <><dt>Célula</dt><dd>{cell.sampleId.slice(0, 8)}…</dd><dt>Clase real</dt><dd>{classText(cell.label)}</dd><dt>Partición</dt><dd>{cell.split.toUpperCase()}</dd></>
            : <><dt>Predicción</dt><dd>{classText(cell.predicted)}</dd><dt>Categoría</dt><dd>{cell.category ? CELL_CATEGORY_LABELS[cell.category] : 'Pendiente'}</dd>
              <dt>Score</dt><dd>{cell.score.toFixed(4)}{cell.threshold != null && <small> umbral {cell.threshold.toFixed(4)}</small>}</dd></>}</dl>
        </div>}
      </div>}
    </div>
  </div>;
}
