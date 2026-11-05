import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const root = fileURLToPath(new URL('../src/', import.meta.url));
function load(path, cache = new Map()) {
  if (cache.has(path)) return cache.get(path);
  const module = { exports: {} };
  cache.set(path, module.exports);
  const code = ts.transpileModule(readFileSync(path, 'utf8'), { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
  runInNewContext(code, { exports: module.exports, module, Math, Array, JSON, Map, Set, Number, String, Object, window: {}, require: (name) => {
    if (!name.startsWith('.')) return require(name);
    const base = resolve(dirname(path), name);
    return load(existsSync(`${base}.ts`) ? `${base}.ts` : `${base}.tsx`, cache);
  } });
  return module.exports;
}
const model = load(resolve(root, 'components/model-training/trainingModel.ts'));

// Bloques y parámetros del TRAIN custom_cnn 33348978 (normalize_keras sobre su checkpoint por época).
const block = (id, label, kind, shape, parameters, phases = ['base']) => ({ id, label, kind, layers: 4, units: null, output_shape: shape, parameters, trainable_phases: phases, origin: 'recorded' });
const layer = (name, type, blockId) => ({ name, type, block: blockId, output_shape: null, inputs: [], parameters: 0, trainable_phases: ['base'], settings: {} });
const cnn = {
  training_run_id: '33348978-9acf-4fb6-a1da-fefe0aa6f3be', state: 'available', issues: [], model_name: 'custom_cnn', architecture: 'custom_cnn', family: 'custom_cnn',
  framework: 'keras', input_shape: [null, 200, 200, 3], output: { neurons: 1, activation: 'sigmoid', loss: null, from_logits: null, meaning: null },
  total_parameters: 422881, checkpoint: { artifact_id: null, selected_epoch: 12, phase: 'base' },
  phases: [{ phase: 'base', trainable_parameters: 421921, learning_rates: [{ group: 'model', learning_rate: 0.0010000000474974513, parameters: null }] }],
  blocks: [block('input', 'Entrada', 'input', [null, 200, 200, 3], 0, []), block('block1', 'Bloque 1', 'convolution', [null, 100, 100, 32], 992),
    block('block2', 'Bloque 2', 'convolution', [null, 50, 50, 64], 18688), block('block3', 'Bloque 3', 'convolution', [null, 25, 25, 128], 74240),
    block('block4', 'Bloque 4', 'convolution', [null, 25, 25, 256], 295936), block('head', 'Cabeza de clasificación', 'head', [null, 128], 32896),
    block('output', 'Capa de salida', 'output', [null, 1], 129)],
  layers: ['block1', 'block2', 'block3', 'block4'].flatMap((id, i) => [layer(`conv2d_${i}`, 'Conv2D', id), layer(`bn_${i}`, 'BatchNormalization', id)]),
};
const run = { execution_parameters: { model_configuration_e2: { configuration: { resolved: {
  model: { input_shape: [200, 200, 3], preprocessing: 'rescale_0_1', weights: 'none', dropout: 0.4, l2: 0.0001, head_units: 128, batch_normalization: 'train', fine_tune_layers: 0 },
  optimizer: { name: 'adam', parameters: {}, fine_tune_learning_rate: 1e-5 }, execution: { max_epochs: 50, fine_tune_epochs: 0 } } } } } };

const setup = () => {
  const layers = model.buildTrainingLayers(cnn, 'base');
  const parameters = model.resolveTrainingParameters(run, cnn.phases);
  return { layers, parameters, regime: model.trainingRegime(cnn, parameters) };
};

test('un TRAIN desde cero no recibe textos de congelar, descongelar ni pesos iniciales', () => {
  const { layers, regime } = setup();
  assert.deepEqual({ ...regime }, { pretrained: false, fineTuning: false });
  const text = layers.flatMap(item => model.tuningGuide(item, layers, regime)).join(' ');
  for (const wrong of ['congelado', 'descongelar', 'backbone congelado', 'pesos iniciales (p. ej.']) assert.ok(!text.includes(wrong), wrong);
  assert.match(text, /aprende desde cero/);
  assert.match(text, /Sin pesos iniciales/);
  assert.match(text, /capa habitual de Grad-CAM/, 'Grad-CAM sí aplica a una CNN propia');
});

test('los bloques conv muestran sus parámetros reales y no los de ajuste fino', () => {
  const { layers, parameters, regime } = setup();
  const keys = Array.from(model.parametersFor(layers.find(item => item.id === 'block4'), layers, parameters, regime), item => item.key);
  assert.deepEqual(keys, ['l2', 'batch_normalization', 'optimizer', 'learning_rate']);
});

test('el learning rate por defecto se toma del registro de TRAIN, no queda pendiente', () => {
  const { parameters, layers } = setup();
  assert.equal(model.parameterValue(parameters, 'learning_rate'), '0.001 (registrado por TRAIN)');
  const pending = model.pendingItems(cnn, layers, parameters, true).join(' ');
  assert.ok(!pending.includes('Learning rate'));
  assert.ok(!pending.includes('LR de ajuste fino') && !pending.includes('Capas descongeladas'), 'el ajuste fino no aplica');
});

test('VGG16 conserva la guía de transferencia', () => {
  const vgg = { ...cnn, family: 'vgg16', phases: [...cnn.phases, { phase: 'fine_tuning', trainable_parameters: 1, learning_rates: [] }] };
  const parameters = model.resolveTrainingParameters({ execution_parameters: { model_configuration_e2: { configuration: { resolved: { model: { weights: 'imagenet' } } } } } }, vgg.phases);
  const regime = model.trainingRegime(vgg, parameters);
  assert.deepEqual({ ...regime }, { pretrained: true, fineTuning: true });
  const layers = model.buildTrainingLayers({ ...cnn, family: 'custom_cnn' }, 'base');
  assert.match(model.tuningGuide(layers.find(item => item.id === 'block4'), layers, regime).join(' '), /Candidato a descongelar/);
  assert.match(model.tuningGuide(layers.find(item => item.id === 'block4'), layers).join(' '), /Candidato a descongelar/, 'sin régimen se mantiene el comportamiento previo');
});
