import type { ArchitectureBlock, ArchitectureLayer, ArchitecturePhase, ArchitectureShape, ModelArchitecture } from '../../types/modelArchitecture';
import type { RunRecord } from '../../types/api';
import { normalizeExecutionParameters } from '../../utils/runDetail';
import { splitHead } from '../model-architecture/architectureViews';

/**
 * Vista «Entrenamiento»: misma presentación que la maqueta ejemplos_visualizacion_modelos/vgg16_arquitectura.html,
 * alimentada por GET /runs/{id}/architecture y GET /runs/{id}. Nada se inventa: lo que el TRAIN no registró queda
 * como pendiente (null) y la interfaz lo muestra así hasta que exista.
 */

export type TrainingKind = ArchitectureBlock['kind'];

export interface TrainingLayer {
  index: number;
  id: string;
  label: string;
  kind: TrainingKind;
  description: string;
  /** Alto, ancho y canales de la salida; null cuando el TRAIN no registró la forma. */
  h: number | null;
  w: number | null;
  d: number | null;
  vector: boolean;
  /** Tensor de tokens (ViT): cantidad de tokens; h × w es la rejilla de parches y d el ancho de cada token. */
  tokens: number | null;
  shapeKnown: boolean;
  inputText: string;
  outputText: string;
  volume: number | null;
  parameters: number | null;
  trainable: boolean;
  trainablePhases: string[];
  innerLayers: number;
  convolutions: number;
  pooling: boolean;
  origin: ArchitectureBlock['origin'];
  color: string;
  spatialFactor: number | null;
  channelFactor: number | null;
}

/** Orden categórico fijo (mismo de la maqueta); el color sigue a la posición del bloque, nunca a su rango. */
export const LAYER_PALETTE = [
  '239, 68, 68', '245, 158, 11', '16, 185, 129', '6, 182, 212', '99, 102, 241',
  '139, 92, 246', '236, 72, 153', '20, 184, 166', '132, 204, 22', '234, 179, 8',
] as const;

const KIND_LABELS: Record<TrainingKind, string> = {
  input: 'Entrada', convolution: 'Bloque conv.', dense: 'Bloque denso', transition: 'Transición',
  encoder: 'Encoder', head: 'Cabeza', output: 'Salida',
};
export const kindLabel = (kind: TrainingKind) => KIND_LABELS[kind] ?? 'Capa';

const fmt = (value: number) => value.toLocaleString('es-CL');
export const formatCount = (value: number | null | undefined) => value == null ? 'Pendiente' : fmt(value);

function dimensions(shape: ArchitectureShape, tokenized = false) {
  if (!shape || shape.length < 2) return null;
  const values = shape.slice(1);
  if (values.some(value => value == null)) return null;
  const [a, b, c] = values as number[];
  if (values.length >= 3) return { h: a, w: b, d: c ?? 1, vector: false, tokens: null };
  // (batch, tokens, ancho) de un ViT: los parches forman una rejilla cuadrada, más el token de clase.
  const grid = Math.sqrt(a - 1);
  if (tokenized && values.length === 2 && b != null && Number.isInteger(grid)) return { h: grid, w: grid, d: b, vector: false, tokens: a };
  return { h: 1, w: 1, d: a, vector: true, tokens: null };
}
type Dimensions = ReturnType<typeof dimensions>;
const shapeLabel = (dims: Dimensions) => dims == null ? 'Pendiente'
  : dims.tokens != null ? `${fmt(dims.tokens)} tokens × ${fmt(dims.d)}`
  : dims.vector ? `${fmt(dims.d)}` : `${dims.h} × ${dims.w} × ${dims.d}`;
const volumeOf = (dims: Dimensions) => dims == null ? null : dims.tokens != null ? dims.tokens * dims.d : dims.h * dims.w * dims.d;

const ACTIVATIONS: Record<string, string> = { sigmoid: 'Sigmoide', softmax: 'Softmax', relu: 'ReLU', linear: 'Lineal' };

function describe(block: ArchitectureBlock, members: ArchitectureLayer[], data: ModelArchitecture) {
  const count = (type: string) => members.filter(layer => layer.type === type).length;
  if (block.kind === 'input') return data.framework ? `Imagen · ${data.framework}` : 'Imagen de entrada';
  if (data.family === 'biomedclip') {
    const patch = data.structure?.patch_size?.[0];
    if (block.kind === 'transition') return patch ? `Parches ${patch}×${patch} + CLS + posición` : 'Parches + CLS + posición';
    if (block.kind === 'encoder') return 'Atención + MLP';
    if (block.kind === 'head') return `Norma + proyección${data.output?.embedding_features ? ` → ${data.output.embedding_features}` : ''} · L2`;
    if (block.kind === 'output') return `Linear · ${ACTIVATIONS[data.output?.activation ?? ''] ?? data.output?.activation ?? 'salida'}`;
  }
  if (block.kind === 'convolution') {
    const conv = count('Conv2D');
    const pool = members.some(layer => /Pooling2D$/.test(layer.type) && !/^Global/.test(layer.type));
    return conv ? `Conv ×${conv}${pool ? ' + Pool' : ''}` : `${members.length || block.layers} capas`;
  }
  if (block.kind === 'output') {
    const activation = data.output?.activation;
    return activation ? `Dense · ${ACTIVATIONS[activation] ?? activation}` : 'Capa de salida';
  }
  if (block.kind === 'head') {
    const types = Array.from(new Set(members.map(layer => layer.type)));
    return types.length ? types.join(' + ') : block.label;
  }
  if (block.kind === 'dense' && block.units != null) return `${block.units} unidades densas`;
  return `${members.length || block.layers} capas`;
}

/** Bloques del TRAIN en el orden del flujo, con lo que la vista necesita ya calculado. */
export function buildTrainingLayers(source: ModelArchitecture, phase: string): TrainingLayer[] {
  const data = source.family === 'vgg16' ? splitHead(source) : source;
  const layers: TrainingLayer[] = [];
  data.blocks.forEach((block, index) => {
    const members = data.layers.filter(layer => layer.block === block.id);
    const shape = block.kind === 'input' && !block.output_shape ? data.input_shape : block.output_shape;
    const dims = dimensions(shape, data.family === 'biomedclip');
    const previous = layers[index - 1];
    const prevDims = previous && previous.shapeKnown ? { h: previous.h!, w: previous.w!, d: previous.d!, vector: previous.vector } : null;
    layers.push({
      index, id: block.id, label: block.label, kind: block.kind,
      description: describe(block, members, data),
      h: dims?.h ?? null, w: dims?.w ?? null, d: dims?.d ?? null,
      vector: dims?.vector ?? block.kind === 'output',
      tokens: dims?.tokens ?? null,
      shapeKnown: dims != null,
      inputText: previous ? previous.outputText : shapeLabel(dims),
      outputText: shapeLabel(dims),
      volume: volumeOf(dims),
      parameters: block.parameters,
      trainable: block.trainable_phases.includes(phase),
      trainablePhases: block.trainable_phases,
      innerLayers: members.length || block.layers,
      convolutions: members.filter(layer => layer.type === 'Conv2D').length,
      pooling: members.some(layer => /Pooling2D$/.test(layer.type) && !/^Global/.test(layer.type)),
      origin: block.origin,
      color: LAYER_PALETTE[index % LAYER_PALETTE.length],
      spatialFactor: dims && prevDims && dims.h ? prevDims.h / dims.h : null,
      channelFactor: dims && prevDims && prevDims.d ? dims.d / prevDims.d : null,
    });
  });
  return layers;
}

/* ----------------------------------------------------------------------------------------------
   Parámetros del TRAIN. Se buscan en el orden en que el pipeline los ha registrado históricamente:
   la configuración resuelta (model_configuration_e2), los argumentos CLI y las claves planas.
   ---------------------------------------------------------------------------------------------- */

export type ParameterGroup = 'entrada' | 'red' | 'optimizacion' | 'cabeza' | 'ajuste' | 'decision';
export interface TrainingParameter { key: string; label: string; group: ParameterGroup; value: string | null }

const PREFIXES = ['model_configuration_e2.configuration.resolved.', 'model_configuration.resolved.', 'model_configuration_e2.configuration.', 'cli_arguments.', ''];
const PARAMETERS: { key: string; label: string; group: ParameterGroup; paths: string[] }[] = [
  { key: 'img_size', label: 'Tamaño de imagen', group: 'entrada', paths: ['execution.img_size', 'img_size', 'model.input_shape'] },
  { key: 'preprocessing', label: 'Preprocesamiento', group: 'entrada', paths: ['model.preprocessing', 'preprocessing_mode', 'preprocessing'] },
  { key: 'weights', label: 'Pesos iniciales', group: 'entrada', paths: ['model.weights', 'pretrained_weights'] },
  { key: 'augment', label: 'Augmentación', group: 'entrada', paths: ['augment'] },
  { key: 'batch_normalization', label: 'Batch normalization', group: 'red', paths: ['model.batch_normalization', 'batch_normalization'] },
  { key: 'batch_size', label: 'Batch size', group: 'optimizacion', paths: ['execution.batch_size', 'batch_size'] },
  { key: 'optimizer', label: 'Optimizador', group: 'optimizacion', paths: ['optimizer.name', 'optimizer'] },
  { key: 'learning_rate', label: 'Learning rate', group: 'optimizacion', paths: ['optimizer.parameters.learning_rate', 'learning_rate'] },
  { key: 'max_epochs', label: 'Épocas base (máx.)', group: 'optimizacion', paths: ['execution.max_epochs', 'base_max_epochs', 'max_epochs'] },
  { key: 'early_stopping_patience', label: 'Paciencia early stopping', group: 'optimizacion', paths: ['execution.early_stopping_patience', 'early_stopping_patience'] },
  { key: 'head_units', label: 'Unidades de la cabeza', group: 'cabeza', paths: ['model.head_units', 'head_units'] },
  { key: 'dropout', label: 'Dropout', group: 'cabeza', paths: ['model.dropout', 'dropout'] },
  { key: 'l2', label: 'Regularización L2', group: 'cabeza', paths: ['model.l2', 'l2'] },
  { key: 'fine_tune_layers', label: 'Capas descongeladas', group: 'ajuste', paths: ['model.fine_tune_layers', 'fine_tune_layers'] },
  { key: 'fine_tune_epochs', label: 'Épocas de ajuste fino', group: 'ajuste', paths: ['execution.fine_tune_epochs', 'fine_tune_max_epochs', 'fine_tune_epochs'] },
  { key: 'fine_tune_learning_rate', label: 'LR de ajuste fino', group: 'ajuste', paths: ['optimizer.fine_tune_learning_rate', 'fine_tune_learning_rate'] },
  { key: 'checkpoint_policy', label: 'Política de checkpoint', group: 'decision', paths: ['execution.checkpoint_policy', 'checkpoint_policy'] },
  { key: 'target_recall', label: 'Recall objetivo', group: 'decision', paths: ['execution.target_recall', 'target_recall'] },
  { key: 'calibrate_threshold', label: 'Calibrar umbral', group: 'decision', paths: ['execution.calibrate_threshold', 'calibrate_threshold'] },
];
export const PARAMETER_GROUP_LABELS: Record<ParameterGroup, string> = {
  entrada: 'Entrada', red: 'Red', optimizacion: 'Optimización', cabeza: 'Cabeza', ajuste: 'Ajuste fino', decision: 'Decisión clínica',
};

function readPath(source: Record<string, unknown>, path: string): unknown {
  return path.split('.').reduce<unknown>((value, key) =>
    value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>)[key] : undefined, source);
}
function display(value: unknown): string | null {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'boolean') return value ? 'Sí' : 'No';
  if (typeof value === 'number') return Number.isFinite(value) ? (Math.abs(value) > 0 && Math.abs(value) < 1e-3 ? value.toExponential(0) : String(value)) : null;
  if (typeof value === 'string') return value.trim() || null;
  if (Array.isArray(value) && value.every(item => typeof item === 'number' || typeof item === 'string')) return value.join(' × ');
  return null;
}

/** Learning rate que TRAIN registró al compilar cada fase: respaldo cuando la configuración usa el valor por defecto. */
function recordedRate(phases: ArchitecturePhase[], phase: string, groups: string[]): string | null {
  const rate = phases.find(item => item.phase === phase)?.learning_rates?.find(item => groups.includes(item.group ?? ''))?.learning_rate;
  return rate != null && Number.isFinite(rate) ? `${display(Number(rate.toPrecision(6)))} (registrado por TRAIN)` : null;
}

export function resolveTrainingParameters(run: RunRecord | null, phases: ArchitecturePhase[] = []): TrainingParameter[] {
  const source = run ? normalizeExecutionParameters(run) as Record<string, unknown> : {};
  return PARAMETERS.map(({ key, label, group, paths }) => {
    let value: string | null = null;
    for (const prefix of PREFIXES) {
      for (const path of paths) {
        value = display(readPath(source, prefix + path));
        if (value != null) break;
      }
      if (value != null) break;
    }
    if (value == null && key === 'learning_rate') value = recordedRate(phases, 'base', ['model', 'head']);
    if (value == null && key === 'fine_tune_learning_rate') value = recordedRate(phases, 'fine_tuning', ['model', 'encoder']);
    return { key, label, group, value };
  });
}

/* ----------------------------------------------------------------------------------------------
   Régimen del TRAIN: si partió de pesos iniciales y si tuvo fase de ajuste fino. Decide qué textos y
   parámetros aplican a cada bloque; un modelo entrenado desde cero no tiene nada que congelar.
   ---------------------------------------------------------------------------------------------- */

export interface TrainingRegime { pretrained: boolean; fineTuning: boolean; /** false: TRAIN lógico (zero-shot), nada se entrenó. */ trained: boolean }

export function trainingRegime(data: ModelArchitecture | null, parameters: TrainingParameter[]): TrainingRegime {
  const weights = parameterValue(parameters, 'weights');
  const fineTuning = Boolean(data?.phases.some(item => item.phase === 'fine_tuning'));
  // Sin registro de pesos, una fase de ajuste fino implica pesos iniciales; si no, se asume desde cero sólo si lo dice el TRAIN.
  const pretrained = weights == null ? fineTuning || data?.family === 'vgg16' || data?.family === 'densenet121' || data?.family === 'biomedclip' : !/^(none|null|random|scratch)$/i.test(weights);
  return { pretrained, fineTuning, trained: !data?.zero_shot };
}
const FULL_REGIME: TrainingRegime = { pretrained: true, fineTuning: true, trained: true };
export const parameterValue = (parameters: TrainingParameter[], key: string) => parameters.find(item => item.key === key)?.value ?? null;

/** Qué parámetros del entrenamiento gobiernan cada tipo de bloque. */
export function parametersFor(layer: TrainingLayer, layers: TrainingLayer[], parameters: TrainingParameter[], regime: TrainingRegime = FULL_REGIME): TrainingParameter[] {
  if (!regime.pretrained && !regime.fineTuning && ['convolution', 'dense', 'transition', 'encoder'].includes(layer.kind)) {
    // Desde cero: los bloques aprenden con el optimizador del modelo y se regularizan con l2 y batch normalization.
    return ['l2', 'batch_normalization', 'optimizer', 'learning_rate'].map(key => parameters.find(item => item.key === key))
      .filter((item): item is TrainingParameter => Boolean(item));
  }
  const keys: Record<TrainingKind, string[]> = {
    input: ['img_size', 'preprocessing', 'weights', 'augment'],
    convolution: ['weights', 'fine_tune_layers', 'fine_tune_learning_rate', 'fine_tune_epochs'],
    dense: ['weights', 'fine_tune_layers', 'fine_tune_learning_rate'],
    transition: ['weights', 'fine_tune_layers'],
    encoder: ['weights', 'fine_tune_layers', 'fine_tune_learning_rate'],
    head: ['head_units', 'dropout', 'l2', 'learning_rate', 'optimizer', 'batch_size'],
    output: ['checkpoint_policy', 'target_recall', 'calibrate_threshold'],
  };
  const first = layers.findIndex(item => item.kind === 'convolution');
  const early = layer.kind === 'convolution' && layer.index <= first + 1;
  const list = early ? ['weights', 'fine_tune_layers'] : keys[layer.kind] ?? [];
  return list.map(key => parameters.find(item => item.key === key)).filter((item): item is TrainingParameter => Boolean(item));
}

/** Guía orientativa por tipo de bloque. `texto` entre acentos graves se muestra como código. */
export function tuningGuide(layer: TrainingLayer, layers: TrainingLayer[], regime: TrainingRegime = FULL_REGIME): string[] {
  const lastConv = [...layers].reverse().find(item => item.kind === 'convolution');
  const firstConv = layers.find(item => item.kind === 'convolution');
  const frozen = layer.trainable ? 'Se entrena en la fase mostrada.' : 'Congelado en la fase mostrada.';
  switch (layer.kind) {
    case 'input': return [
      'El tamaño de imagen fija todas las dimensiones posteriores: cambiar `img_size` reescala cada tensor de esta vista.',
      regime.pretrained
        ? 'El preprocesamiento debe coincidir con los pesos iniciales (p. ej. `vgg16_imagenet` con ImageNet, `openclip_original` con BiomedCLIP).'
        : 'Sin pesos iniciales (`weights` = none): el preprocesamiento sólo tiene que ser el mismo en TRAIN, EVALUATE y TEST.',
      'La augmentación actúa aquí: es la palanca principal contra sobreajuste sin tocar la arquitectura.'];
    case 'convolution': {
      const early = firstConv != null && layer.index <= firstConv.index + 1;
      const convolutions = layer.convolutions || layer.innerLayers;
      const notes = !regime.pretrained
        ? [early
          ? `Bloque temprano (${convolutions} ${convolutions === 1 ? 'convolución' : 'convoluciones'}): aprende desde cero filtros de bordes, color y textura, junto con el resto del modelo.`
          : 'Bloque profundo: combina los rasgos de los bloques previos; su capacidad depende de los filtros y se regulariza con `l2` y batch normalization.']
        : [early
          ? `Bloque temprano (${convolutions} capas): filtros genéricos de bordes y texturas; normalmente se mantiene congelado. ${frozen}`
          : `Bloque profundo: rasgos semánticos. Candidato a descongelar con \`fine_tune_layers\` y un \`fine_tune_learning_rate\` bajo. ${frozen}`];
      if (lastConv && layer.id === lastConv.id) notes.push(`Último bloque convolucional${layer.h ? ` (${layer.h}×${layer.w})` : ''}: capa habitual de Grad-CAM; su baja resolución explica mapas de calor «gruesos».`);
      else if (early && layer.h) notes.push(`Resolución ${layer.h}×${layer.w}: conserva detalle fino del parásito; útil para Grad-CAM de alta resolución.`);
      return notes;
    }
    case 'transition': return layer.tokens != null ? [
      `Corta la imagen en parches y suma posición: ${layer.tokens} tokens (rejilla ${layer.h}×${layer.w} más el token de clase) de ${layer.d} dimensiones.`,
      `Sólo se entrena con \`fine_tune_layers\` = 12 (ajuste total). ${frozen}`] : [frozen];
    case 'encoder': if (!regime.trained) return [
      'Bloque Transformer de la base registrada: autoatención entre todos los tokens y MLP. En el zero-shot se usa tal cual, sin entrenar.',
      'Para adaptarlo a malaria está `biomedclip_fine_tuning`, que descongela los últimos bloques con `fine_tune_layers`.',
      'Grad-CAM no aplica: la evidencia espacial de un ViT se lee en la atención del token de clase o con LIME y SHAP.'];
      return [
      'Bloque Transformer: autoatención entre todos los tokens y MLP. La forma no cambia entre bloques; cambia lo que representa cada token.',
      `\`fine_tune_layers\` descongela los últimos bloques primero; usan \`fine_tune_learning_rate\`, distinto del de la cabeza. ${frozen}`,
      'Grad-CAM no aplica: la evidencia espacial de un ViT se lee en la atención del token de clase o con LIME y SHAP.'];
    case 'head': if (layer.id === 'projection') return [
      'Norma final y proyección del token de clase al embedding; la salida se normaliza L2 antes de la cabeza.',
      regime.trained ? `Se entrena cuando \`fine_tune_layers\` > 0. ${frozen}` : 'En el zero-shot no se entrena: el embedding es el de la base registrada.'];
      return [
      'Cabeza entrenable: `head_units` controla el ancho de la capa densa.',
      regime.pretrained
        ? '`dropout` y `l2` regularizan aquí; con el backbone congelado, aquí se concentra el aprendizaje de la fase base.'
        : '`dropout` y `l2` regularizan aquí; sin backbone preentrenado, la cabeza aprende a la vez que los bloques convolucionales.'];
    case 'output': if (!regime.trained) return [
      'Compara el embedding de la imagen con los embeddings de los prompts de cada clase y aplica softmax: es un score relativo entre prompts.',
      'No está calibrado clínicamente: el umbral `clinical` se calibra en VAL con su EVALUATE.'];
      return [
      'Probabilidad única: el umbral de decisión (no la arquitectura) define el balance recall/especificidad.',
      'Ajustar `target_recall` o `calibrate_threshold` antes que la red cuando el objetivo es clínico.'];
    default: return [frozen];
  }
}

/* ----------------------------------------------------------------------------------------------
   Chequeos de coherencia y pendientes, calculados desde la respuesta real.
   ---------------------------------------------------------------------------------------------- */

export type CheckLevel = 'warn' | 'ok' | 'info' | 'pending';
export interface TrainingCheck { level: CheckLevel; layer: number | null; text: string }

export function trainingChecks(data: ModelArchitecture, layers: TrainingLayer[], parameters: TrainingParameter[], phase: string): TrainingCheck[] {
  const checks: TrainingCheck[] = [];
  layers.forEach((layer, i) => {
    const prev = layers[i - 1];
    if (layer.kind === 'convolution' && layer.pooling && prev?.h != null && layer.h != null) {
      const expected = Math.floor(prev.h / 2);
      if (layer.h !== expected) checks.push({ level: 'warn', layer: i, text: `${layer.label}: con un Pool 2×2 la salida esperada desde ${prev.h}×${prev.w} es ${expected}×${expected}, pero se registró ${layer.h}×${layer.w}.` });
    }
  });
  const input = layers.find(layer => layer.kind === 'input');
  const imgSize = Number(parameterValue(parameters, 'img_size')?.split(' × ')[0]);
  if (input?.h != null && Number.isFinite(imgSize)) {
    checks.push(input.h === imgSize
      ? { level: 'ok', layer: input.index, text: `La entrada registrada (${input.outputText}) coincide con \`img_size\` = ${imgSize}.` }
      : { level: 'warn', layer: input.index, text: `La entrada registrada (${input.outputText}) no coincide con \`img_size\` = ${imgSize}.` });
  }
  const head = data.layers.filter(layer => layer.block === 'head' || layers.some(item => item.kind === 'head' && item.id === layer.block));
  const pooling = head.find(layer => /^Global(Average|Max)Pooling2D$/.test(layer.type) || layer.type === 'Flatten');
  const poolingIndex = pooling ? layers.findIndex(item => item.id === pooling.name || item.id === pooling.block) : -1;
  if (pooling) checks.push({ level: 'info', layer: poolingIndex < 0 ? null : poolingIndex, text: pooling.type === 'Flatten'
    ? 'La cabeza aplana el mapa (Flatten): conserva la posición espacial y multiplica los parámetros de la primera capa densa.'
    : `La cabeza usa ${pooling.type}: resume cada canal en un valor, sin parámetros y con menos riesgo de sobreajuste.` });
  const known = layers.filter(layer => layer.parameters != null);
  if (data.total_parameters != null && known.length === layers.length) {
    const sum = known.reduce((total, layer) => total + (layer.parameters ?? 0), 0);
    checks.push(sum === data.total_parameters
      ? { level: 'ok', layer: null, text: `La suma de parámetros por bloque (${fmt(sum)}) coincide con el total del modelo.` }
      : { level: 'warn', layer: null, text: `La suma de parámetros por bloque (${fmt(sum)}) difiere del total registrado (${fmt(data.total_parameters)}).` });
  }
  const unfreeze = Number(parameterValue(parameters, 'fine_tune_layers'));
  const fine = data.phases.find(item => item.phase === 'fine_tuning');
  if (fine && Number.isFinite(unfreeze) && unfreeze > 0 && !data.layers.length) {
    // ViT: el TRAIN registra bloques, no capas; se cuentan los bloques del encoder entrenados en ajuste fino.
    const trained = data.blocks.filter(block => block.kind === 'encoder' && block.trainable_phases.includes('fine_tuning'));
    checks.push({ level: trained.length === unfreeze || (unfreeze >= 12 && trained.length === 12) ? 'ok' : 'warn', layer: null,
      text: `\`fine_tune_layers\` = ${unfreeze}; en ajuste fino se entrenan ${trained.length} bloques del encoder${trained.length ? ` (${trained.map(block => block.label).join(', ')})` : ''}.` });
  } else if (fine && Number.isFinite(unfreeze) && unfreeze > 0) {
    const weighted = data.layers.filter(layer => (layer.parameters ?? 0) > 0 && layer.trainable_phases.includes('fine_tuning')
      && layer.block !== 'head' && layer.block !== 'output'
      && !layers.some(item => item.id === layer.block && (item.kind === 'head' || item.kind === 'output')));
    checks.push({ level: weighted.length ? 'info' : 'warn', layer: null,
      text: `\`fine_tune_layers\` = ${unfreeze}; en ajuste fino se entrenan ${weighted.length} capas con pesos del backbone${weighted.length ? ` (${weighted.map(layer => layer.name).join(', ')})` : ''}.` });
  }
  if (data.structure) {
    const { patches, patch_size: patchSize, tokens } = data.structure;
    const side = patchSize?.[0] && Number.isFinite(imgSize) ? imgSize / patchSize[0] : null;
    if (patches != null && side != null) checks.push(side * side === patches
      ? { level: 'ok', layer: layers.find(layer => layer.kind === 'transition')?.index ?? null, text: `\`img_size\` = ${imgSize} con parches de ${patchSize![0]} px da ${side}×${side} = ${patches} parches; con el token de clase, ${tokens} tokens.` }
      : { level: 'warn', layer: null, text: `\`img_size\` = ${imgSize} con parches de ${patchSize![0]} px no da los ${patches} parches de la base.` });
    data.phases.forEach(item => {
      if (item.structure_check === 'match') checks.push({ level: 'ok', layer: null, text: `${item.phase === 'fine_tuning' ? 'Ajuste fino' : 'Fase base'}: el conjunto entrenable registrado (${fmt(item.trainable_parameters ?? 0)} parámetros, ${item.trainable_tensors} tensores) coincide con el que declara la base para \`${item.encoder}\`.` });
      if (item.structure_check === 'mismatch') checks.push({ level: 'warn', layer: null, text: `${item.phase === 'fine_tuning' ? 'Ajuste fino' : 'Fase base'}: el conjunto entrenable registrado no coincide con el que declara la base para \`${item.encoder}\`.` });
    });
  }
  const output = layers.find(layer => layer.kind === 'output');
  if (data.output?.neurons === 1) checks.push({ level: 'ok', layer: output?.index ?? null,
    text: `Salida de 1 neurona${data.output.activation ? ` (${ACTIVATIONS[data.output.activation] ?? data.output.activation})` : ''}: clasificación binaria${data.output.from_logits ? '; la pérdida recibe logits' : ''}.` });
  const current = data.phases.find(item => item.phase === phase);
  if (current?.trainable_parameters != null && data.total_parameters) checks.push({ level: 'info', layer: null,
    text: `En esta fase se entrenan ${fmt(current.trainable_parameters)} de ${fmt(data.total_parameters)} parámetros (${(100 * current.trainable_parameters / data.total_parameters).toFixed(1)} %).` });
  return checks;
}

/** Lo que falta para completar la vista; se muestra como «pendiente» hasta que el TRAIN lo registre. */
export function pendingItems(data: ModelArchitecture | null, layers: TrainingLayer[], parameters: TrainingParameter[], runLoaded: boolean): string[] {
  const items: string[] = [];
  if (!data || data.state === 'missing') items.push('Arquitectura registrada del TRAIN');
  const noShape = layers.filter(layer => !layer.shapeKnown).map(layer => layer.label);
  if (noShape.length) items.push(`Forma de salida de: ${noShape.join(', ')}`);
  const noParams = layers.filter(layer => layer.parameters == null && layer.kind !== 'input').map(layer => layer.label);
  if (noParams.length) items.push(`Parámetros de: ${noParams.join(', ')}`);
  if (data && data.total_parameters == null) items.push('Total de parámetros del modelo');
  if (data && data.checkpoint.selected_epoch == null) items.push('Época del checkpoint seleccionado');
  if (!runLoaded) items.push('Configuración del entrenamiento (GET /runs/{id})');
  else {
    const fineTuning = Boolean(data?.phases.some(item => item.phase === 'fine_tuning'));
    // Un TRAIN lógico (zero-shot) no tiene optimización, cabeza ni ajuste: sólo entrada y decisión pueden faltar.
    const applies = (item: TrainingParameter) => data?.zero_shot ? item.group === 'entrada' || item.group === 'decision' : fineTuning || item.group !== 'ajuste';
    const missing = parameters.filter(item => item.value == null && applies(item)).map(item => item.label);
    if (missing.length) items.push(`Parámetros de entrenamiento: ${missing.join(', ')}`);
  }
  if (layers.some(layer => layer.origin === 'reference')) items.push('Bloques registrados por el TRAIN (algunos son estructura de referencia)');
  return items;
}
