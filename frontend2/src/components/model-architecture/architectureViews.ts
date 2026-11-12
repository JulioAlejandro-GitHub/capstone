import type { ArchitectureBlock, ArchitectureFamily, ArchitectureLayer, ArchitectureOutput, ArchitectureShape, ModelArchitecture } from '../../types/modelArchitecture';

export const architectureViews = {
  mapas: 'Mapas apilados', 'bloques-3d': 'Bloques 3D', bloques: 'Bloques', grafo: 'Grafo denso', conexiones: 'Conexiones',
  flujo: 'Flujo', vit: 'Bloques ViT', tabla: 'Tabla',
} as const;
export type ArchitectureView = keyof typeof architectureViews;

// The first view of each family is its default; every view draws the same response.
const familyViews: Record<ArchitectureFamily, ArchitectureView[]> = {
  custom_cnn: ['mapas', 'bloques', 'tabla'],
  vgg16: ['bloques-3d', 'mapas', 'tabla'],
  densenet121: ['grafo', 'conexiones', 'tabla'],
  biomedclip: ['flujo', 'vit', 'tabla'],
  generic: ['tabla'],
};
export const viewsFor = (family: ArchitectureFamily) => familyViews[family];
/** Familias con «Recorrido de una célula»: CNN Keras cuyas capas el backend agrupa en los bloques de la arquitectura. */
// biomedclip: the backend answers per model (today zero-shot); for the others the panel shows why it is unavailable.
export const traceableFamilies: ArchitectureFamily[] = ['vgg16', 'custom_cnn', 'densenet121', 'biomedclip'];
export const isTraceable = (family: ArchitectureFamily) => traceableFamilies.includes(family);
export const resolveView = (family: ArchitectureFamily, requested: string | null): ArchitectureView => {
  const views = viewsFor(family);
  return views.find(view => view === requested) ?? views[0];
};

export const phaseLabels: Record<string, string> = { base: 'Fase base', fine_tuning: 'Ajuste fino' };
export const isTrained = (block: ArchitectureBlock, phase: string) => block.trainable_phases.includes(phase);
export const shapeText = (shape: ArchitectureShape) => shape?.slice(1).join(' × ') ?? 'Sin evidencia';
export const countText = (value: number | null | undefined) => value == null ? 'Sin evidencia' : value.toLocaleString('es-CL');
const activationLabels: Record<string, string> = { sigmoid: 'Sigmoide', softmax: 'Softmax' };
const lossLabels: Record<string, string> = {
  binary_crossentropy: 'Binary Cross-Entropy', bce_with_logits: 'Binary Cross-Entropy with Logits',
  categorical_crossentropy: 'Cross-Entropy', sparse_categorical_crossentropy: 'Cross-Entropy', cross_entropy: 'Cross-Entropy',
};
export const outputText = (output: ArchitectureOutput | null | undefined) => {
  if (output?.neurons == null) return 'Sin evidencia';
  const neurons = `${output.neurons} ${output.neurons === 1 ? 'neurona' : 'neuronas'}`;
  return output.activation ? `${neurons} · ${activationLabels[output.activation] ?? output.activation}` : neurons;
};
export const lossText = (output: ArchitectureOutput | null | undefined) => {
  if (!output?.loss) return 'Pérdida sin evidencia';
  const loss = `Pérdida: ${lossLabels[output.loss] ?? output.loss}`;
  return output.from_logits ? `${loss}; la capa entrega logits y la activación se aplica aparte` : loss;
};
export const isSpatial = (shape: ArchitectureShape) => (shape?.length ?? 0) === 4;

// 200 to 6 px cannot share a linear scale: size is logarithmic and the label always carries the real value.
export const spatialSize = (shape: ArchitectureShape) => 44 + 15 * Math.log2(Math.max(2, shape?.[1] ?? 2));
export const depthSize = (shape: ArchitectureShape) => 10 + 3.2 * Math.log2(Math.max(2, shape?.at(-1) ?? 2));

const headLabels: Record<string, (layer: ArchitectureLayer) => string> = {
  GlobalAveragePooling2D: () => 'Promedio global', GlobalMaxPooling2D: () => 'Máximo global', Flatten: () => 'Aplanado',
  Dense: layer => `Densa ${layer.settings.units ?? ''}`.trim(),
};

/**
 * The head drawn as the layers that transform the tensor (pooling or flatten, each Dense), one block each, so the drawing
 * has one element per step of a cell's trace. Dropout is the identity in inference and joins the layer before it.
 */
export function splitHead(data: ModelArchitecture): ModelArchitecture {
  const head = data.layers.filter(layer => layer.block === 'head');
  const parts = head.filter(layer => headLabels[layer.type]);
  if (parts.length < 2) return data;
  const owner = new Map<string, string>();
  let current = parts[0].name;
  head.forEach(layer => { if (headLabels[layer.type]) current = layer.name; owner.set(layer.name, current); });
  const blocks: ArchitectureBlock[] = parts.map(part => {
    const members = head.filter(layer => owner.get(layer.name) === part.name);
    const counted = members.filter(layer => layer.parameters != null);
    return { id: part.name, label: headLabels[part.type](part), kind: 'head', layers: members.length, units: null, output_shape: part.output_shape,
      parameters: counted.length ? counted.reduce((sum, layer) => sum + (layer.parameters ?? 0), 0) : null, trainable_phases: part.trainable_phases, origin: 'recorded' };
  });
  const index = data.blocks.findIndex(block => block.id === 'head');
  if (index < 0) return data;
  return { ...data, blocks: [...data.blocks.slice(0, index), ...blocks, ...data.blocks.slice(index + 1)],
    layers: data.layers.map(layer => owner.has(layer.name) ? { ...layer, block: owner.get(layer.name)! } : layer) };
}
