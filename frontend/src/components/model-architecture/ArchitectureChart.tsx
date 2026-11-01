import { Fragment, useMemo, useState, type ReactNode } from 'react';

import type { ArchitectureBlock, ModelArchitecture } from '../../types/modelArchitecture';
import { countText, depthSize, isSpatial, isTrained, shapeText, spatialSize, type ArchitectureView } from './architectureViews';

type ChartProps = { data: ModelArchitecture; phase: string };
const HEIGHT = 300, MIDDLE = 140, GAP = 44;

const blockTitle = (block: ArchitectureBlock) => `${block.label} · ${shapeText(block.output_shape)} · ${countText(block.parameters)} parámetros · ${block.layers} capas`;

function Frame({ label, width, height = HEIGHT, children }: { label: string; width: number; height?: number; children: ReactNode }) {
  return <div className="mx-chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label} style={{ minWidth: Math.min(width, 900) }}>
    <defs><marker id="mx-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" className="mx-arrowhead" /></marker></defs>
    {children}
  </svg></div>;
}

const Arrow = ({ x1, x2, y = MIDDLE }: { x1: number; x2: number; y?: number }) => <line className="mx-link" x1={x1} x2={x2} y1={y} y2={y} markerEnd="url(#mx-arrow)" />;

function Labels({ x, block, top, bottom }: { x: number; block: ArchitectureBlock; top: number; bottom: number }) {
  return <>
    <text className="mx-dimension" x={x} y={top} textAnchor="middle">{shapeText(block.output_shape)}</text>
    <text className="mx-name" x={x} y={bottom} textAnchor="middle">{block.label}</text>
  </>;
}

/** Lays blocks left to right: each one reports its own width. */
function layout<T extends { width: number }>(items: T[], start = 16) {
  let cursor = start;
  const placed = items.map(item => { const x = cursor; cursor += item.width + GAP; return { ...item, x }; });
  return { placed, width: cursor - GAP + start };
}

function StackedMaps({ data, phase }: ChartProps) {
  const { placed, width } = layout(data.blocks.map(block => {
    const sheets = isSpatial(block.output_shape) ? Math.round(depthSize(block.output_shape) / 6) : 0;
    const side = isSpatial(block.output_shape) ? spatialSize(block.output_shape) : 26;
    return { block, sheets, side, width: Math.max(92, side + sheets * 7) };
  }));
  return <Frame label={`Mapas de características de ${data.architecture}`} width={width}>
    {placed.map((item, index) => {
      const { block, sheets, side, x } = item, center = x + item.width / 2, next = placed[index + 1];
      const height = isSpatial(block.output_shape) ? side : 36 + 7 * Math.log2(Math.max(2, block.output_shape?.at(-1) ?? 2));
      const span = side + sheets * 7, left = center - span / 2;
      return <g key={block.id} data-block={block.id} data-trained={isTrained(block, phase)} className="mx-block"><title>{blockTitle(block)}</title>
        {Array.from({ length: Math.max(1, sheets) }, (_, sheet) => <rect key={sheet} x={left + sheet * 7} y={MIDDLE - height / 2 - sheet * 5 + sheets * 2.5} width={side} height={height} rx="3" />)}
        <Labels x={center} block={block} top={MIDDLE - 90 - 18} bottom={HEIGHT - 24} />
        {next && <Arrow x1={x + item.width + 6} x2={next.x - 6} />}
      </g>;
    })}
  </Frame>;
}

function Blocks3D({ data, phase }: ChartProps) {
  const { placed, width } = layout(data.blocks.map(block => {
    const spatial = isSpatial(block.output_shape), side = spatial ? spatialSize(block.output_shape) : 48;
    return { block, side, depth: spatial ? side * 0.34 : 10, thick: depthSize(block.output_shape), width: Math.max(92, depthSize(block.output_shape) + (spatial ? side * 0.34 : 10)) };
  }));
  return <Frame label={`Bloques de ${data.architecture}`} width={width}>
    {placed.map((item, index) => {
      const { block, side, depth, thick, x } = item, left = x + (item.width - thick - depth) / 2, y0 = MIDDLE - side / 2 + depth / 3, next = placed[index + 1];
      return <g key={block.id} data-block={block.id} data-trained={isTrained(block, phase)} className="mx-block"><title>{blockTitle(block)}</title>
        <polygon points={`${left},${y0} ${left + depth},${y0 - depth * .66} ${left + depth + thick},${y0 - depth * .66} ${left + thick},${y0}`} data-face="top" />
        <polygon points={`${left + thick},${y0} ${left + thick + depth},${y0 - depth * .66} ${left + thick + depth},${y0 + side - depth * .66} ${left + thick},${y0 + side}`} data-face="side" />
        <rect x={left} y={y0} width={thick} height={side} />
        <Labels x={x + item.width / 2} block={block} top={MIDDLE - 90 - 18} bottom={HEIGHT - 24} />
        {next && <Arrow x1={x + item.width + 6} x2={next.x - 6} />}
      </g>;
    })}
  </Frame>;
}

function BlockBars({ data, phase }: ChartProps) {
  const largest = Math.log10(Math.max(10, ...data.blocks.map(block => block.parameters ?? 0)));
  const row = 42;
  return <Frame label={`Parámetros por bloque de ${data.architecture}`} width={900} height={data.blocks.length * row + 16}>
    {data.blocks.map((block, index) => {
      const y = 8 + index * row, parameters = block.parameters ?? 0;
      return <g key={block.id} data-block={block.id} data-trained={isTrained(block, phase)} className="mx-block"><title>{blockTitle(block)}</title>
        <text className="mx-name" x="8" y={y + 22}>{block.label}</text>
        <text className="mx-dimension" x="230" y={y + 22}>{shapeText(block.output_shape)}</text>
        <rect x="370" y={y + 6} width={parameters ? Math.max(4, 390 * Math.log10(parameters + 1) / largest) : 2} height="24" rx="3" />
        <text className="mx-dimension" x="892" y={y + 22} textAnchor="end">{countText(block.parameters)}</text>
      </g>;
    })}
  </Frame>;
}

function DenseGraph({ data, phase }: ChartProps) {
  const { placed, width } = layout(data.blocks.map(block => {
    const units = block.units ?? 0, columns = Math.ceil(units / 4);
    return { block, units, width: block.kind === 'dense' ? Math.max(92, columns * 18 + 26) : 92 };
  }));
  return <Frame label="Bloques densos de DenseNet121" width={width}>
    {placed.map((item, index) => {
      const { block, units, x } = item, next = placed[index + 1], dense = block.kind === 'dense';
      return <g key={block.id} data-block={block.id} data-trained={isTrained(block, phase)} className="mx-block"><title>{blockTitle(block)}</title>
        <rect x={x} y={MIDDLE - (dense ? 56 : 34)} width={item.width} height={dense ? 112 : 68} rx="8" />
        {Array.from({ length: units }, (_, unit) => <circle key={unit} className="mx-unit" r="6" cx={x + 22 + Math.floor(unit / 4) * 18} cy={MIDDLE - 27 + (unit % 4) * 18} />)}
        {dense ? null : <text className="mx-dimension" x={x + item.width / 2} y={MIDDLE + 4} textAnchor="middle">{block.layers} {block.layers === 1 ? 'capa' : 'capas'}</text>}
        <Labels x={x + item.width / 2} block={block} top={MIDDLE - 90} bottom={HEIGHT - 72} />
        {dense && <text className="mx-dimension" x={x + item.width / 2} y={HEIGHT - 52} textAnchor="middle">{units} capas densas</text>}
        {next && <Arrow x1={x + item.width + 6} x2={next.x - 6} />}
      </g>;
    })}
  </Frame>;
}

export function denseUnits(data: ModelArchitecture, blockId: string) {
  const stage = blockId.replace('dense', '');
  return data.layers.filter(layer => layer.type === 'Concatenate' && layer.block === blockId && layer.name.startsWith(`conv${stage}_block`));
}

function DenseConnections({ data, phase }: ChartProps) {
  const blocks = data.blocks.filter(block => block.kind === 'dense');
  const [blockId, setBlockId] = useState(blocks.at(-1)?.id ?? '');
  const units = useMemo(() => denseUnits(data, blockId), [data, blockId]);
  const [picked, setPicked] = useState<number | null>(null);
  const selected = picked !== null && picked < units.length ? picked : units.length - 1;
  const block = blocks.find(item => item.id === blockId);
  const step = 1040 / Math.max(1, units.length), y = 200;
  const unitX = (index: number) => 96 + step * index + step / 2;
  if (!block) return <p>Sin bloques densos registrados.</p>;
  return <>
    <div className="scc-segmented" role="group" aria-label="Bloque denso">{blocks.map(item => <button key={item.id} type="button" className="ds-button" data-size="compact"
      aria-pressed={item.id === blockId} onClick={() => { setBlockId(item.id); setPicked(null); }}>{item.label}</button>)}</div>
    <Frame label={`Conexiones de ${block.label}`} width={1180} height={280}>
      <rect className="mx-entry" x="8" y={y - 22} width="64" height="44" rx="6" />
      <text className="mx-dimension" x="40" y={y + 4} textAnchor="middle">Entrada</text>
      {units.slice(0, selected + 1).map((_, index) => {
        const from = index === 0 ? 72 : unitX(index - 1), to = unitX(selected);
        return index === selected && selected === 0 ? null : <path key={index} className="mx-arc" d={`M${from} ${y - 12}Q${(from + to) / 2} ${y - 40 - (to - from) * .26} ${to} ${y - 14}`} markerEnd="url(#mx-arrow)" />;
      })}
      {units.map((unit, index) => <g key={unit.name} className="mx-block mx-node" data-trained={unit.trainable_phases.includes(phase)} data-selected={index === selected}
        role="button" tabIndex={0} aria-label={`Capa ${index + 1}`} onClick={() => setPicked(index)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') setPicked(index); }}>
        <title>{`${unit.name} · ${shapeText(unit.output_shape)}`}</title>
        <circle cx={unitX(index)} cy={y} r={Math.min(13, step / 2.6)} />
      </g>)}
      <text className="mx-name" x="590" y="258" textAnchor="middle">Capa {selected + 1} de {units.length} · salida {shapeText(units[selected]?.output_shape ?? null)}</text>
    </Frame>
    <p className="scc-meta">Dibujo derivado: el modelo registra una cadena de concatenaciones; por eso cada capa recibe las salidas de todas las anteriores de su bloque.</p>
  </>;
}

function VitFlow({ data, phase }: ChartProps) {
  const input = data.blocks.find(block => block.kind === 'input'), head = data.blocks.find(block => block.kind === 'head');
  const encoder = data.blocks.filter(block => block.kind === 'encoder');
  const trained = encoder.filter(block => isTrained(block, phase)).length;
  const embedding = data.output?.embedding_features as number | undefined;
  const boxes = [
    { id: 'input', name: 'Entrada', lines: [shapeText(input?.output_shape ?? null)], active: false },
    { id: 'encoder', name: `Encoder ViT · ${encoder.length} bloques`, lines: [trained ? `${trained} entrenados, ${encoder.length - trained} congelados` : 'Todos congelados', 'Estructura de referencia'], active: trained > 0 },
    { id: 'embedding', name: 'Embedding L2', lines: [embedding ? `${embedding} dimensiones` : 'Sin evidencia'], active: false },
    { id: 'head', name: 'Cabeza lineal', lines: [`${countText(head?.parameters)} parámetros`, 'Salida sigmoide'], active: Boolean(head && isTrained(head, phase)) },
  ];
  const boxWidth = 216, step = boxWidth + 40;
  return <Frame label={`Flujo de ${data.architecture}`} width={step * boxes.length - 24} height={200}>
    {boxes.map((box, index) => <g key={box.id} className="mx-block" data-trained={box.active}>
      <rect x={12 + index * step} y="44" width={boxWidth} height="104" rx="8" />
      <text className="mx-name" x={12 + index * step + boxWidth / 2} y="82" textAnchor="middle">{box.name}</text>
      {box.lines.map((line, row) => <text key={line} className="mx-dimension" x={12 + index * step + boxWidth / 2} y={106 + row * 20} textAnchor="middle">{line}</text>)}
      {index < boxes.length - 1 && <Arrow x1={12 + index * step + boxWidth + 6} x2={12 + (index + 1) * step - 6} y={96} />}
    </g>)}
  </Frame>;
}

function VitBlocks({ data, phase }: ChartProps) {
  const encoder = data.blocks.filter(block => block.kind === 'encoder');
  const columns = 6, size = 138;
  return <Frame label={`Bloques ViT de ${data.architecture}`} width={columns * size + 16} height={Math.ceil(encoder.length / columns) * 92 + 16}>
    {encoder.map((block, index) => {
      const x = 8 + (index % columns) * size, y = 8 + Math.floor(index / columns) * 92;
      return <g key={block.id} data-block={block.id} data-trained={isTrained(block, phase)} className="mx-block"><title>{block.label}</title>
        <rect x={x} y={y} width={size - 12} height="76" rx="8" />
        <text className="mx-name" x={x + (size - 12) / 2} y={y + 34} textAnchor="middle">{block.label}</text>
        <text className="mx-dimension" x={x + (size - 12) / 2} y={y + 56} textAnchor="middle">{isTrained(block, phase) ? 'Entrenado' : 'Congelado'}</text>
      </g>;
    })}
  </Frame>;
}

function LayerTable({ data, phase }: ChartProps) {
  const [blockId, setBlockId] = useState('');
  const layers = data.layers.filter(layer => !blockId || layer.block === blockId);
  if (!data.layers.length) return <div className="report-table-scroll"><table className="report-data-table"><caption>Bloques del modelo</caption>
    <thead><tr><th>Bloque</th><th>Dimensión de salida</th><th>Parámetros</th><th>Estado en la fase</th><th>Origen</th></tr></thead>
    <tbody>{data.blocks.map(block => <tr key={block.id}><th scope="row">{block.label}</th><td>{shapeText(block.output_shape)}</td><td>{countText(block.parameters)}</td>
      <td>{block.kind === 'input' ? 'No aplica' : isTrained(block, phase) ? 'Entrenado' : 'Congelado'}</td><td>{block.origin === 'recorded' ? 'Registrado' : 'Referencia del encoder'}</td></tr>)}</tbody></table></div>;
  return <>
    <label className="mx-filter">Bloque<select className="ds-control" value={blockId} onChange={event => setBlockId(event.target.value)}>
      <option value="">Todos ({data.layers.length} capas)</option>
      {data.blocks.map(block => <option key={block.id} value={block.id}>{block.label} ({block.layers})</option>)}
    </select></label>
    <div className="report-table-scroll" tabIndex={0} role="region" aria-label="Capas del modelo"><table className="report-data-table"><caption>Capas registradas y parámetros calculados</caption>
      <thead><tr><th>Capa</th><th>Tipo</th><th>Salida</th><th>Parámetros</th><th>Entrada</th><th>Estado en la fase</th></tr></thead>
      <tbody>{layers.map(layer => <Fragment key={layer.name}><tr><th scope="row"><code>{layer.name}</code></th><td>{layer.type}</td><td>{shapeText(layer.output_shape)}</td><td>{countText(layer.parameters)}</td>
        <td>{layer.inputs.join(', ') || '—'}</td><td>{layer.parameters ? layer.trainable_phases.includes(phase) ? 'Entrenada' : 'Congelada' : 'Sin pesos'}</td></tr></Fragment>)}</tbody></table></div>
  </>;
}

export function ArchitectureChart({ view, ...props }: ChartProps & { view: ArchitectureView }) {
  switch (view) {
    case 'mapas': return <StackedMaps {...props} />;
    case 'bloques-3d': return <Blocks3D {...props} />;
    case 'bloques': return <BlockBars {...props} />;
    case 'grafo': return <DenseGraph {...props} />;
    case 'conexiones': return <DenseConnections {...props} />;
    case 'flujo': return <VitFlow {...props} />;
    case 'vit': return <VitBlocks {...props} />;
    default: return <LayerTable {...props} />;
  }
}
