import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const root = fileURLToPath(new URL('../src/', import.meta.url));
function load(filename, cache = new Map()) {
  const path = resolve(root, filename);
  if (cache.has(path)) return cache.get(path);
  const module = { exports: {} };
  cache.set(path, module.exports);
  const code = ts.transpileModule(readFileSync(path, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
  runInNewContext(code, { exports: module.exports, module, Math, Array, JSON, Map, Set, Number, String, Object, window: {}, require: (name) => {
    if (!name.startsWith('.')) return require(name);
    const base = `${dirname(path).slice(root.length)}/${name}`;
    return load(existsSync(resolve(root, `${base}.ts`)) ? `${base}.ts` : `${base}.tsx`, cache);
  } });
  return module.exports;
}
const model = load('components/model-training/trainingModel.ts');
const { TrainingScene } = load('components/model-training/TrainingScene.tsx');

const layer = (name, type, block, shape, parameters, phases = []) => ({ name, type, block, output_shape: shape, inputs: [], parameters, trainable_phases: phases, settings: type === 'Dense' ? { units: shape?.[1] } : {} });
const block = (id, label, kind, shape, parameters, phases = []) => ({ id, label, kind, layers: 1, units: null, output_shape: shape, parameters, trainable_phases: phases, origin: 'recorded' });
const vgg = {
  training_run_id: '87b3eff7-e09a-41c8-945d-bf31b3541adb', state: 'available', issues: [], model_name: 'tl_vgg16_malaria', architecture: 'vgg16', family: 'vgg16',
  framework: 'keras', input_shape: [null, 200, 200, 3], output: { neurons: 1, activation: 'sigmoid', loss: 'binary_crossentropy', from_logits: false, meaning: null },
  total_parameters: 1792 + 36928 + 525312 + 1025, checkpoint: { artifact_id: null, selected_epoch: 12, phase: 'fine_tuning' },
  phases: [{ phase: 'base', trainable_parameters: 526337, trainable_tensors: null, encoder: null }, { phase: 'fine_tuning', trainable_parameters: 600000, trainable_tensors: null, encoder: null }],
  blocks: [
    block('input', 'Entrada', 'input', [null, 200, 200, 3], 0),
    block('block1', 'Bloque 1', 'convolution', [null, 90, 90, 64], 1792 + 36928, ['fine_tuning']),
    block('head', 'Cabeza de clasificación', 'head', [null, 1024], 525312, ['base', 'fine_tuning']),
    block('output', 'Capa de salida', 'output', null, 1025, ['base', 'fine_tuning']),
  ],
  layers: [
    layer('input_layer_1', 'InputLayer', 'input', [null, 200, 200, 3], 0),
    layer('block1_conv1', 'Conv2D', 'block1', [null, 200, 200, 64], 1792, ['fine_tuning']),
    layer('block1_conv2', 'Conv2D', 'block1', [null, 200, 200, 64], 36928, ['fine_tuning']),
    layer('block1_pool', 'MaxPooling2D', 'block1', [null, 90, 90, 64], 0),
    layer('global_avg_pool', 'GlobalAveragePooling2D', 'head', [null, 64], 0),
    layer('feature_dense_1024', 'Dense', 'head', [null, 1024], 525312, ['base', 'fine_tuning']),
    layer('dropout_50', 'Dropout', 'head', [null, 1024], 0),
    layer('binary_output', 'Dense', 'output', null, 1025, ['base', 'fine_tuning']),
  ],
};
const run = { id: vgg.training_run_id, parameters: { img_size: 200, cli_arguments: { batch_size: 64 } },
  execution_parameters: { model_configuration_e2: { configuration: { resolved: { model: { dropout: 0.5, head_units: 1024, fine_tune_layers: 4 }, optimizer: { name: 'adam' } } } } } };

test('los bloques salen del TRAIN, la cabeza de VGG16 se separa por capa y la entrada es la salida previa', () => {
  const layers = model.buildTrainingLayers(vgg, 'base');
  assert.deepEqual(Array.from(layers, item => item.id), ['input', 'block1', 'global_avg_pool', 'feature_dense_1024', 'output']);
  assert.equal(layers[1].description, 'Conv ×2 + Pool');
  assert.equal(layers[1].inputText, '200 × 200 × 3');
  assert.equal(layers[1].trainable, false);
  assert.equal(model.buildTrainingLayers(vgg, 'fine_tuning')[1].trainable, true);
});

test('lo no registrado queda pendiente, nunca inventado', () => {
  const layers = model.buildTrainingLayers(vgg, 'base');
  const output = layers.at(-1);
  assert.equal(output.shapeKnown, false);
  assert.equal(output.outputText, 'Pendiente');
  const params = model.resolveTrainingParameters(run);
  assert.equal(model.parameterValue(params, 'learning_rate'), null);
  const pending = model.pendingItems(vgg, layers, params, true);
  assert.ok(pending.some(item => item.includes('Forma de salida de: Capa de salida')));
  assert.ok(pending.some(item => item.includes('Learning rate')));
});

test('los parámetros se leen de la configuración resuelta, los argumentos y las claves planas', () => {
  const params = model.resolveTrainingParameters(run);
  assert.equal(model.parameterValue(params, 'dropout'), '0.5');
  assert.equal(model.parameterValue(params, 'head_units'), '1024');
  assert.equal(model.parameterValue(params, 'optimizer'), 'adam');
  assert.equal(model.parameterValue(params, 'batch_size'), '64');
  assert.equal(model.parameterValue(params, 'img_size'), '200');
  assert.ok(model.resolveTrainingParameters(null).every(item => item.value === null));
});

test('los chequeos detectan un pool incoherente y confirman lo que coincide', () => {
  const layers = model.buildTrainingLayers(vgg, 'base');
  const checks = model.trainingChecks(vgg, layers, model.resolveTrainingParameters(run), 'base');
  assert.ok(checks.some(check => check.level === 'warn' && check.text.includes('100×100')));
  assert.ok(checks.some(check => check.level === 'ok' && check.text.includes('img_size')));
  assert.ok(checks.some(check => check.level === 'ok' && check.text.includes('coincide con el total')));
  assert.ok(checks.some(check => check.text.includes('GlobalAveragePooling2D')));
});

test('la escena dibuja cada bloque, marca los congelados y los pendientes', () => {
  const layers = model.buildTrainingLayers(vgg, 'base');
  const html = renderToStaticMarkup(React.createElement(TrainingScene, { layers, selected: 1, onSelect: () => undefined, phaseLabel: 'Fase base' }));
  assert.equal((html.match(/data-layer="/g) || []).length, layers.length);
  assert.match(html, /data-trained="false"/);
  assert.match(html, /data-pending="true"/);
  assert.match(html, /aria-label="Pantalla completa"/);
  assert.match(html, /forma pendiente/);
});

test('la célula seleccionada aparece en la entrada y, con su resultado, en la salida', () => {
  const layers = model.buildTrainingLayers({ ...vgg, blocks: vgg.blocks.map(item => item.id === 'output' ? { ...item, output_shape: [null, 1] } : item) }, 'base');
  const cell = { sampleId: '004cc347-5232-5b5a-ac2b-ee6629dbad37', image: 'data:image/png;base64,AAAA', label: 0, predicted: 1, score: 0.3084, threshold: 0.2512, split: 'test', attemptId: '00b8d407', category: 'false_positive' };
  const html = renderToStaticMarkup(React.createElement(TrainingScene, { layers, selected: 0, onSelect: () => undefined, phaseLabel: 'Fase base', cell }));
  assert.equal((html.match(/<image /g) || []).length, 2);
  assert.match(html, /data-category="false_positive"/);
  assert.match(html, /Falso positivo · 0\.308/);
  assert.match(html, /célula 004cc347/);
  const without = renderToStaticMarkup(React.createElement(TrainingScene, { layers, selected: 0, onSelect: () => undefined, phaseLabel: 'Fase base' }));
  assert.doesNotMatch(without, /<image /);
});

test('la imagen de la célula abre la vista ampliada cuando hay contexto, y sólo entonces', () => {
  const layers = model.buildTrainingLayers({ ...vgg, blocks: vgg.blocks.map(item => item.id === 'output' ? { ...item, output_shape: [null, 1] } : item) }, 'base');
  const cell = { sampleId: '004cc347-5232-5b5a-ac2b-ee6629dbad37', image: 'data:image/png;base64,AAAA', label: 0, predicted: 1, score: 0.3084, threshold: 0.2512, split: 'test', attemptId: '00b8d407', category: 'false_positive' };
  const props = { layers, selected: 0, onSelect: () => undefined, phaseLabel: 'Fase base', cell };
  const open = renderToStaticMarkup(React.createElement(TrainingScene, { ...props, onCellOpen: () => undefined }));
  assert.equal((open.match(/aria-label="Ampliar Célula original"/g) || []).length, 2);
  const closed = renderToStaticMarkup(React.createElement(TrainingScene, props));
  assert.doesNotMatch(closed, /Ampliar Célula original/);
  assert.doesNotMatch(open, /Ampliar comparación/);
});
