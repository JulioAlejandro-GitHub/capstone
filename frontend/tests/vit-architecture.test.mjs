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
const { ArchitectureChart } = load(resolve(root, 'components/model-architecture/ArchitectureChart.tsx'));

const block = (id, label, kind, shape, parameters, phases = [], origin = 'derived') => ({ id, label, kind, layers: 1, units: null, output_shape: shape, parameters, trainable_phases: phases, origin });
const VIT = 7087872;
const vit = {
  training_run_id: '5d1e66f1-dc53-4c37-bf9b-8e45f6095eb3', state: 'available', issues: [], model_name: 'biomedclip_fine_tuning', architecture: 'biomedclip_fine_tuning',
  family: 'biomedclip', framework: 'pytorch', input_shape: [null, 224, 224, 3],
  output: { neurons: 1, activation: 'sigmoid', loss: 'bce_with_logits', from_logits: true, meaning: 'probability_parasitized', embedding_features: 512 },
  total_parameters: 742656 + 12 * VIT + 394752 + 513, checkpoint: { artifact_id: null, selected_epoch: 9, phase: 'fine_tuning' },
  structure: { origin: 'derived', base_sha256: 'a'.repeat(64), vit_blocks: 12, patch_size: [16, 16], width: 768, patches: 196, tokens: 197 },
  phases: [
    { phase: 'base', encoder: 'frozen', trainable_parameters: 513, trainable_tensors: 2, structure_check: 'match', learning_rates: [{ group: 'head', learning_rate: 1e-3 }] },
    { phase: 'fine_tuning', encoder: 'last_4_blocks', trainable_parameters: 4 * VIT + 394752 + 513, trainable_tensors: 53, structure_check: 'match',
      learning_rates: [{ group: 'head', learning_rate: 1e-3 }, { group: 'encoder', learning_rate: 1e-5 }] },
  ],
  blocks: [
    block('input', 'Entrada', 'input', [null, 224, 224, 3], 0, [], 'recorded'),
    block('embedding', 'Parches y posición', 'transition', [null, 197, 768], 742656),
    ...Array.from({ length: 12 }, (_, i) => block(`vit${i}`, `Bloque ViT ${i + 1}`, 'encoder', [null, 197, 768], VIT, i >= 8 ? ['fine_tuning'] : [])),
    block('projection', 'Norma y proyección', 'head', [null, 512], 394752, ['fine_tuning']),
    block('output', 'Capa de salida', 'output', [null, 1], 513, ['base', 'fine_tuning'], 'recorded'),
  ],
  layers: [],
};
const run = { execution_parameters: { model_configuration_e2: { configuration: { resolved: { model: { input_shape: [224, 224, 3], fine_tune_layers: 4 } } } } } };

test('los tokens del ViT se muestran como tokens, no como un vector de 197', () => {
  const layers = model.buildTrainingLayers(vit, 'fine_tuning');
  const first = layers.find(item => item.id === 'vit0');
  assert.equal(first.outputText, '197 tokens × 768');
  assert.equal(first.tokens, 197);
  assert.equal(first.h, 14);
  assert.equal(first.volume, 197 * 768);
  assert.equal(first.description, 'Atención + MLP');
  assert.equal(layers.find(item => item.id === 'embedding').description, 'Parches 16×16 + CLS + posición');
  assert.equal(layers.find(item => item.id === 'projection').outputText, '512');
  assert.equal(layers.find(item => item.id === 'vit11').trainable, true);
  assert.equal(layers.find(item => item.id === 'vit0').trainable, false);
});

test('los chequeos del ViT cuentan bloques del encoder y verifican el conjunto entrenable contra la base', () => {
  const layers = model.buildTrainingLayers(vit, 'fine_tuning');
  const checks = model.trainingChecks(vit, layers, model.resolveTrainingParameters(run), 'fine_tuning');
  const texts = checks.map(check => `${check.level} ${check.text}`);
  assert.ok(texts.some(text => text.startsWith('ok `fine_tune_layers` = 4; en ajuste fino se entrenan 4 bloques del encoder')), texts.join('\n'));
  assert.ok(!texts.some(text => text.includes('capas con pesos del backbone')));
  assert.ok(texts.some(text => text.includes('14×14 = 196 parches; con el token de clase, 197 tokens')));
  assert.equal(texts.filter(text => text.startsWith('ok') && text.includes('coincide con el que declara la base')).length, 2);
  assert.ok(texts.some(text => text.startsWith('ok La suma de parámetros por bloque')));
});

test('la guía del encoder es propia del ViT', () => {
  const layers = model.buildTrainingLayers(vit, 'fine_tuning');
  const guide = model.tuningGuide(layers.find(item => item.id === 'vit10'), layers).join(' ');
  assert.match(guide, /autoatención/);
  assert.match(guide, /Grad-CAM no aplica/);
});

test('el explorador muestra parches, parámetros y origen derivado del ViT', () => {
  const flow = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: vit, view: 'flujo', phase: 'fine_tuning' }));
  assert.match(flow, /196 parches de 16 px \+ CLS/);
  assert.match(flow, /4 entrenados, 8 congelados/);
  assert.match(flow, /derivado de la base/);
  assert.doesNotMatch(flow, /Estructura de referencia/);
  const table = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: vit, view: 'tabla', phase: 'fine_tuning' }));
  assert.match(table, /Derivado de la base/);
  assert.match(table, /197 × 768/);
});

test('VGG16 conserva su lectura: forma espacial y sin tokens', () => {
  const vgg = { ...vit, family: 'vgg16', structure: null, blocks: [block('input', 'Entrada', 'input', [null, 200, 200, 3], 0, [], 'recorded'), block('block1', 'Bloque 1', 'convolution', [null, 100, 100, 64], 38720, [], 'recorded')] };
  const layers = model.buildTrainingLayers(vgg, 'base');
  assert.equal(layers[1].outputText, '100 × 100 × 64');
  assert.equal(layers[1].tokens, null);
});
