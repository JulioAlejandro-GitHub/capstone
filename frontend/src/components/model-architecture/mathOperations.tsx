import { createElement, type ReactNode } from 'react';

import type { ArchitectureBlock, ArchitectureLayer, ArchitectureOutput, ModelArchitecture } from '../../types/modelArchitecture';
import { shapeText } from './architectureViews';

export type MathOperation = { id: string; title: string; detail: string; count: number; formula: ReactNode; origin: 'recorded' | 'reference' };

// MathML nodes: the browser typesets them, so no equation library is needed.
const node = (tag: string, ...children: ReactNode[]) => createElement(tag, null, ...children);
const v = (name: string) => node('mi', name);
const num = (value: number | string) => node('mn', String(value));
const op = (symbol: string) => node('mo', symbol);
const word = (text: string) => node('mtext', text);
const row = (...items: ReactNode[]) => node('mrow', ...items);
const sub = (base: ReactNode, index: ReactNode) => node('msub', base, index);
const sup = (base: ReactNode, index: ReactNode) => node('msup', base, index);
const under = (base: ReactNode, index: ReactNode) => node('munder', base, index);
const frac = (top: ReactNode, bottom: ReactNode) => node('mfrac', top, bottom);
const root = (value: ReactNode) => node('msqrt', value);
const paren = (...items: ReactNode[]) => row(op('('), ...items, op(')'));
const indices = (...items: ReactNode[]) => row(...items.flatMap((item, index) => index ? [op(','), item] : [item]));
const tensor = (name: string, ...items: ReactNode[]) => sub(v(name), indices(...items));
const shifted = (index: string, offset: string, stride: number) => stride === 1 ? row(v(index), op('+'), v(offset)) : row(num(stride), v(index), op('+'), v(offset));
const math = (...items: ReactNode[]) => createElement('math', { display: 'block' }, row(...items));

const pair = (value: unknown) => Array.isArray(value) ? value as number[] : typeof value === 'number' ? [value, value] : null;
const activationOf = (name: unknown, input: ReactNode): ReactNode => name === 'relu' ? row(word('max'), paren(num(0), op(','), input))
  : name === 'sigmoid' ? row(v('σ'), paren(input)) : input;

function convolution(layer: ArchitectureLayer) {
  const { activation, use_bias: bias, strides } = layer.settings;
  const stride = pair(strides)?.[0] ?? 1;
  const sum = row(under(op('∑'), indices(v('u'), v('v'), v('c'))), tensor('W', v('u'), v('v'), v('c'), v('k')),
    tensor('X', shifted('i', 'u', stride), shifted('j', 'v', stride), v('c')), ...(bias ? [op('+'), sub(v('b'), v('k'))] : []));
  return math(tensor('Y', v('i'), v('j'), v('k')), op('='), activationOf(activation, sum));
}

function normalization(layer: ArchitectureLayer) {
  const { center, scale } = layer.settings;
  const standard = frac(row(tensor('X', v('i'), v('j'), v('k')), op('−'), sub(v('μ'), v('k'))), root(row(sup(sub(v('σ'), v('k')), num(2)), op('+'), v('ε'))));
  return math(tensor('Y', v('i'), v('j'), v('k')), op('='), ...(scale === false ? [] : [sub(v('γ'), v('k'))]), standard, ...(center === false ? [] : [op('+'), sub(v('β'), v('k'))]));
}

const pooling = (layer: ArchitectureLayer, name: string) => {
  const stride = pair(layer.settings.strides)?.[0] ?? pair(layer.settings.pool_size)?.[0] ?? 1;
  return math(tensor('Y', v('i'), v('j'), v('k')), op('='), under(word(name), indices(v('u'), v('v'))), tensor('X', shifted('i', 'u', stride), shifted('j', 'v', stride), v('k')));
};

const sizeText = (layer: unknown) => { const size = pair(layer); return size ? `${size[0]} × ${size[1]}` : null; };
const list = (...items: (string | null | false | undefined)[]) => items.filter(Boolean).join(' · ');

function describe(layer: ArchitectureLayer, layers: ArchitectureLayer[]): Omit<MathOperation, 'id' | 'count' | 'origin'> | null {
  const { filters, kernel_size: kernel, strides, padding, use_bias: bias, activation, rate, units, pool_size: pool, epsilon } = layer.settings;
  switch (layer.type) {
    case 'Conv2D': return { title: 'Convolución', formula: convolution(layer), detail: list(sizeText(kernel), `${filters} filtros`, `paso ${pair(strides)?.[0] ?? 1}`, `padding ${padding}`, bias ? 'con sesgo' : 'sin sesgo', activation === 'relu' ? 'ReLU incluida' : null) };
    case 'BatchNormalization': return { title: 'Normalización por lote', formula: normalization(layer), detail: list('μ y σ² móviles en inferencia', epsilon != null && `ε = ${epsilon}`) };
    case 'Activation': return activation === 'relu' ? { title: 'Activación ReLU', formula: math(v('Y'), op('='), row(word('max'), paren(num(0), op(','), v('X')))), detail: 'Por elemento' } : null;
    case 'MaxPooling2D': return { title: 'Max pooling', formula: pooling(layer, 'max'), detail: list(`ventana ${sizeText(pool)}`, `paso ${pair(strides)?.[0] ?? 1}`) };
    case 'AveragePooling2D': return { title: 'Average pooling', formula: pooling(layer, 'mean'), detail: list(`ventana ${sizeText(pool)}`, `paso ${pair(strides)?.[0] ?? 1}`) };
    case 'GlobalAveragePooling2D': {
      const incoming = layers.find(item => item.name === layer.inputs[0])?.output_shape;
      return { title: 'Promedio global', formula: math(sub(v('z'), v('k')), op('='), frac(num(1), row(v('H'), v('W'))), under(op('∑'), indices(v('i'), v('j'))), tensor('X', v('i'), v('j'), v('k'))),
        detail: incoming ? `H = ${incoming[1]}, W = ${incoming[2]}` : 'Por canal' };
    }
    case 'Dropout': return { title: 'Dropout', formula: math(v('y'), op('='), frac(row(v('m'), op('⊙'), v('x')), row(num(1), op('−'), v('r'))), op(','), word('  '), v('m'), op('∼'), word('Bernoulli'), paren(num(1), op('−'), v('r'))),
      detail: `r = ${rate}; solo en entrenamiento; en inferencia y = x` };
    case 'Dense': {
      const linear = row(v('W'), v('x'), op('+'), v('b'));
      return { title: activation === 'sigmoid' ? 'Capa de salida' : 'Capa densa', formula: math(activation === 'sigmoid' ? v('p') : v('y'), op('='), activationOf(activation, linear)), detail: list(`${units} ${units === 1 ? 'neurona' : 'neuronas'}`, typeof activation === 'string' ? `activación ${activation}` : null) };
    }
    case 'Concatenate': return { title: 'Concatenación densa', formula: math(sub(v('X'), v('ℓ')), op('='), row(op('['), sub(v('X'), row(v('ℓ'), op('−'), num(1))), op(','), sub(v('H'), v('ℓ')), op(']'))), detail: 'Une canales; así cada capa conserva las salidas anteriores del bloque' };
    case 'Normalization': return { title: 'Normalización de entrada', formula: math(v('Y'), op('='), frac(row(v('X'), op('−'), v('μ')), v('σ'))), detail: 'Medias y varianzas de ImageNet registradas' };
    default: return null;
  }
}

const lossOperation = (output: ArchitectureOutput): MathOperation | null => {
  if (output.loss !== 'binary_crossentropy' && output.loss !== 'bce_with_logits') return null;
  return { id: 'loss', title: 'Pérdida de entrenamiento', count: 1, origin: 'recorded', detail: output.from_logits ? 'Binary Cross-Entropy with Logits: p = σ(logit)' : 'Binary Cross-Entropy sobre la probabilidad',
    formula: math(v('L'), op('='), op('−'), paren(v('y'), word(' log '), v('p'), op('+'), paren(num(1), op('−'), v('y')), word(' log'), paren(num(1), op('−'), v('p')))) };
};

const referenceOperations = (block: ArchitectureBlock, output: ArchitectureOutput | null): MathOperation[] => {
  const base = { count: 1, origin: 'reference' as const };
  if (block.kind === 'encoder') return [
    { ...base, id: 'qkv', title: 'Proyecciones de atención', detail: 'Estructura de referencia del encoder; sus pesos no están registrados capa a capa',
      formula: math(v('Q'), op('='), v('X'), sub(v('W'), v('Q')), op(','), word('  '), v('K'), op('='), v('X'), sub(v('W'), v('K')), op(','), word('  '), v('V'), op('='), v('X'), sub(v('W'), v('V'))) },
    { ...base, id: 'attention', title: 'Autoatención', detail: 'Matriz de atención entre tokens; no se almacena en esta etapa',
      formula: math(word('Attention'), paren(v('Q'), op(','), v('K'), op(','), v('V')), op('='), word('softmax'), paren(frac(row(v('Q'), sup(v('K'), v('T'))), root(sub(v('d'), v('k'))))), v('V')) },
  ];
  if (block.kind !== 'output') return [];
  const operations: MathOperation[] = [
    { id: 'embedding', title: 'Embedding L2', count: 1, origin: 'recorded', detail: output?.embedding_features ? `${output.embedding_features} dimensiones` : 'Dimensión sin evidencia',
      formula: math(v('z'), op('='), frac(row(v('f'), paren(v('x'))), row(op('‖'), v('f'), paren(v('x')), sub(op('‖'), num(2))))) },
    { id: 'logit', title: 'Capa de salida', count: 1, origin: 'recorded', detail: 'Clasificador lineal entrenado sobre el embedding; no usa similitud con texto',
      formula: math(v('p'), op('='), v('σ'), paren(sup(v('w'), v('T')), v('z'), op('+'), v('b'))) },
  ];
  const loss = output && lossOperation(output);
  return loss ? [...operations, loss] : operations;
};

/** The operations of one block, built only from what its layers recorded; repeated layers collapse into one line. */
export function blockOperations(data: ModelArchitecture, block: ArchitectureBlock): MathOperation[] {
  if (block.origin === 'reference' || !data.layers.length) return referenceOperations(block, data.output);
  const loss = block.kind === 'output' && data.output ? lossOperation(data.output) : null;
  const operations = layerOperations(data, data.layers.filter(layer => layer.block === block.id));
  return loss ? [...operations, loss] : operations;
}

/** Operations of an explicit set of layers (one step of a cell's trace); repeated layers collapse into one line. */
export function layerOperations(data: ModelArchitecture, layers: ArchitectureLayer[]): MathOperation[] {
  const groups = new Map<string, MathOperation>();
  layers.forEach(layer => {
    const operation = describe(layer, data.layers);
    if (!operation) return;
    const id = `${layer.type}:${JSON.stringify(layer.settings)}`;
    const current = groups.get(id);
    if (current) current.count += 1; else groups.set(id, { ...operation, id, count: 1, origin: 'recorded' });
  });
  return Array.from(groups.values());
}

/** Real tensor path. Per-sample values are absent on purpose: this view describes the model, not one prediction. */
export function tensorPath(data: ModelArchitecture) {
  if (data.family === 'biomedclip') {
    const embedding = data.output?.embedding_features;
    return [shapeText(data.input_shape), 'Parches y tokens', `Encoder ViT · ${data.blocks.filter(block => block.kind === 'encoder').length} bloques`,
      embedding ? `Embedding ${embedding}` : 'Embedding', `${data.output?.neurons ?? '—'} logit`, 'Sigmoide'];
  }
  return data.blocks.map(block => shapeText(block.output_shape)).concat(data.output?.activation === 'sigmoid' ? ['Sigmoide'] : []);
}
