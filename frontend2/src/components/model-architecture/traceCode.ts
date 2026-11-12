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
 * Layers that produce one step. A convolutional block step (VGG16 or custom_cnn) is the whole block: its convolutions
 * end in the layer the trace read (pooling, or the activation of a block without pooling); a head step is the single
 * layer whose output was recorded.
 */
/** A step that reads the end of a backbone block (VGG16/custom_cnn convolutions, DenseNet121 dense blocks and transitions). */
const BACKBONE_KINDS = ['convolution', 'dense', 'transition'];
function isBackboneBlock(data: ModelArchitecture | null | undefined, step: ActivationTraceStep): boolean {
  const block = data?.blocks.find(item => item.id === step.block);
  return block?.kind ? BACKBONE_KINDS.includes(block.kind) : /^block\d+$/.test(step.block);
}
const CODE_LINES = 24;

export function stepLayers(data: ModelArchitecture | null | undefined, step: ActivationTraceStep | null): ArchitectureLayer[] {
  if (!data || !step) return [];
  const own = data.layers.find(layer => layer.name === step.layer);
  if (isBackboneBlock(data, step)) return data.layers.filter(layer => layer.block === step.block);
  return own ? [own] : [];
}

/** ViT step (timm VisionTransformer inside OpenCLIP): what the block computes, with the registered base's sizes. */
function vitCode(data: ModelArchitecture, step: ActivationTraceStep): string {
  const s = data.structure, patch = s?.patch_size?.[0] ?? 16, width = s?.width ?? 768, tokens = s?.tokens ?? 197;
  if (step.block === 'embedding') return [`x = patch_embed(image)        # Conv2d(3, ${width}, kernel=${patch}, stride=${patch}) → ${s?.patches ?? tokens - 1} parches × ${width}`,
    `x = concat([cls_token, x]) + pos_embed  # ${tokens} tokens × ${width}`].join('\n');
  const block = /^vit(\d+)$/.exec(step.block);
  if (block) return [`# Bloque ${Number(block[1]) + 1} de ${s?.vit_blocks ?? 12} · la forma no cambia: ${tokens} × ${width}`,
    'x = x + attn(norm1(x))   # autoatención multicabeza entre todos los tokens', 'x = x + mlp(norm2(x))    # MLP por token'].join('\n');
  if (step.block === 'projection') return `z = normalize(proj(norm(x)[:, 0]))   # token de clase → ${data.output?.embedding_features ?? 512}, norma L2`;
  return data.zero_shot
    ? `p = softmax(logit_scale.exp() * z @ text_features.T)   # ${data.zero_shot.prompts.length} prompts: ${data.zero_shot.class_order.join(', ')}`
    : 'p = sigmoid(head(z))   # Linear(512 → 1)';
}

export function stepCode(data: ModelArchitecture | null | undefined, step: ActivationTraceStep | null, inputShape?: number[]): string {
  if (data?.family === 'biomedclip' && step) return vitCode(data, step);
  if (!step) {
    const shape = inputShape ?? (data?.input_shape ?? []).slice(1).filter((value): value is number => value != null);
    return `inputs = layers.Input(shape=(${shape.join(', ')}))`;
  }
  const layers = stepLayers(data, step);
  if (!layers.length) return `# ${step.layer}: capa sin configuración registrada`;
  const backbone = isBackboneBlock(data, step) && data?.family === 'vgg16' ? '# Dentro de VGG16(include_top=False, weights=\'imagenet\'):\n'
    : isBackboneBlock(data, step) && data?.family === 'densenet121' ? '# Dentro de DenseNet121(include_top=False, weights=\'imagenet\'):\n' : '';
  const lines = layers.map(layer => `x = ${layerCode(layer)}(x)`);
  // Un bloque denso tiene decenas de capas: se muestran el comienzo y el final, sin inventar las del medio.
  const shown = lines.length > CODE_LINES
    ? [...lines.slice(0, CODE_LINES / 2), `# … ${lines.length - CODE_LINES} capas más del bloque …`, ...lines.slice(-CODE_LINES / 2)] : lines;
  return backbone + shown.join('\n');
}

/** Readable title of a step: the architecture names blocks; head layers are named by what they do. */
export function stepTitle(data: ModelArchitecture | null | undefined, step: ActivationTraceStep | null): string {
  if (!step) return 'Entrada';
  const own = data?.blocks.find(item => item.id === step.layer);
  if (own) return own.label;
  const block = data?.blocks.find(item => item.id === step.block);
  if (block && isBackboneBlock(data, step)) return block.label;
  if (step.kind === 'output') return 'Salida';
  const type = data?.layers.find(layer => layer.name === step.layer)?.type;
  if (type === 'Activation' || type === 'ReLU') return 'Activación final';
  if (type === 'GlobalAveragePooling2D') return 'Promedio global';
  if (type === 'Flatten') return 'Aplanado';
  if (type === 'Dense') return `Densa ${step.shape.at(-1) ?? ''}`.trim();
  return block?.label ?? step.layer;
}
