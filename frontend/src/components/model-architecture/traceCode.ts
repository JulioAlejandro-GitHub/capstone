import type { ArchitectureLayer, ModelArchitecture } from '../../types/modelArchitecture';
import type { ActivationTraceStep } from '../../types/activationTrace';

const pair = (value: unknown) => Array.isArray(value) ? `(${value.join(', ')})` : typeof value === 'number' ? `(${value}, ${value})` : null;
const quoted = (value: unknown) => typeof value === 'string' ? `'${value}'` : null;
const args = (...items: unknown[]) => items.filter((item): item is string => typeof item === 'string' && item.length > 0).join(', ');

/** Keras call that rebuilds one recorded layer; only settings the TRAIN registered appear, nothing is assumed. */
export function layerCode(layer: ArchitectureLayer): string {
  const s = layer.settings, name = `name='${layer.name}'`;
  const strides = pair(s.strides), defaultStride = strides === '(1, 1)';
  switch (layer.type) {
    case 'InputLayer': return `layers.Input(shape=(${(layer.output_shape ?? []).slice(1).join(', ')}))`;
    case 'Conv2D': return `layers.Conv2D(${args(String(s.filters), pair(s.kernel_size), !defaultStride && strides && `strides=${strides}`,
      s.padding && `padding=${quoted(s.padding)}`, s.activation && s.activation !== 'linear' && `activation=${quoted(s.activation)}`, name)})`;
    case 'MaxPooling2D': case 'AveragePooling2D': return `layers.${layer.type}(${args(pair(s.pool_size), strides && strides !== pair(s.pool_size) && `strides=${strides}`, name)})`;
    case 'GlobalAveragePooling2D': case 'GlobalMaxPooling2D': case 'Flatten': return `layers.${layer.type}(${name})`;
    case 'Dense': return `layers.Dense(${args(String(s.units), s.activation && s.activation !== 'linear' && `activation=${quoted(s.activation)}`, name)})`;
    case 'Dropout': return `layers.Dropout(${args(String(s.rate), name)})`;
    case 'BatchNormalization': return `layers.BatchNormalization(${name})`;
    case 'Activation': return `layers.Activation(${args(quoted(s.activation), name)})`;
    default: return `# ${layer.type} · ${layer.name}`;
  }
}

/**
 * Layers that produce one step. A VGG16 block step is the whole block (its convolutions end in the pooling the trace
 * read); a head step is the single layer whose output was recorded.
 */
export function stepLayers(data: ModelArchitecture | null | undefined, step: ActivationTraceStep | null): ArchitectureLayer[] {
  if (!data || !step) return [];
  const own = data.layers.find(layer => layer.name === step.layer);
  if (/^block\d+$/.test(step.block)) return data.layers.filter(layer => layer.block === step.block);
  return own ? [own] : [];
}

export function stepCode(data: ModelArchitecture | null | undefined, step: ActivationTraceStep | null, inputShape?: number[]): string {
  if (!step) {
    const shape = inputShape ?? (data?.input_shape ?? []).slice(1).filter((value): value is number => value != null);
    return `inputs = layers.Input(shape=(${shape.join(', ')}))`;
  }
  const layers = stepLayers(data, step);
  if (!layers.length) return `# ${step.layer}: capa sin configuración registrada`;
  const backbone = /^block\d+$/.test(step.block)
    ? '# Dentro de VGG16(include_top=False, weights=\'imagenet\'):\n' : '';
  return backbone + layers.map(layer => `x = ${layerCode(layer)}(x)`).join('\n');
}

/** Readable title of a step: the architecture names blocks; head layers are named by what they do. */
export function stepTitle(data: ModelArchitecture | null | undefined, step: ActivationTraceStep | null): string {
  if (!step) return 'Entrada';
  const block = data?.blocks.find(item => item.id === step.block);
  if (/^block\d+$/.test(step.block) && block) return block.label;
  if (step.kind === 'output') return 'Salida';
  const type = data?.layers.find(layer => layer.name === step.layer)?.type;
  if (type === 'GlobalAveragePooling2D') return 'Promedio global';
  if (type === 'Flatten') return 'Aplanado';
  if (type === 'Dense') return `Densa ${step.shape.at(-1) ?? ''}`.trim();
  return block?.label ?? step.layer;
}
