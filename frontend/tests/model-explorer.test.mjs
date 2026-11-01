import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
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
const read = (path) => readFileSync(resolve(root, path), 'utf8');
function load(filename, cache = new Map()) {
  const path = resolve(root, filename);
  if (cache.has(path)) return cache.get(path);
  const module = { exports: {} };
  cache.set(path, module.exports);
  const code = ts.transpileModule(readFileSync(path, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
  runInNewContext(code, { exports: module.exports, module, Math, Array, require: (name) => name.startsWith('.')
    ? load(`${dirname(path).slice(root.length)}/${name}.ts${name.endsWith('Chart') ? 'x' : ''}`, cache) : require(name) });
  return module.exports;
}
const views = load('components/model-architecture/architectureViews.ts');
const { ArchitectureChart, denseUnits } = load('components/model-architecture/ArchitectureChart.tsx');

const block = (id, kind, shape, phases = ['base'], extra = {}) => ({ id, label: id, kind, layers: 2, units: null, output_shape: shape, parameters: 100, trainable_phases: phases, origin: 'recorded', ...extra });
const data = (family, blocks, layers = []) => ({ training_run_id: 'a', family, architecture: family, model_name: family, blocks, layers, phases: [{ phase: 'base' }], output: { embedding_features: 512 }, checkpoint: {} });
const cnn = data('custom_cnn', [block('input', 'input', [null, 200, 200, 3], []), block('block1', 'convolution', [null, 100, 100, 32]), block('output', 'output', [null, 1])],
  [{ name: 'conv2d', type: 'Conv2D', block: 'block1', output_shape: [null, 100, 100, 32], inputs: ['input_layer'], parameters: 864, trainable_phases: ['base'], settings: {} }]);

test('cada familia tiene su vista inicial y una URL inválida vuelve a ella', () => {
  assert.equal(views.resolveView('vgg16', null), 'bloques-3d');
  assert.equal(views.resolveView('custom_cnn', null), 'mapas');
  assert.equal(views.resolveView('densenet121', 'bloques-3d'), 'grafo');
  assert.equal(views.resolveView('biomedclip', 'vit'), 'vit');
  for (const family of ['custom_cnn', 'vgg16', 'densenet121', 'biomedclip', 'generic']) assert.ok(Array.from(views.viewsFor(family)).includes('tabla'));
});

test('todas las vistas de una familia muestran los mismos datos reales', () => {
  for (const view of Array.from(views.viewsFor('custom_cnn')).concat('bloques-3d')) {
    const html = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: cnn, view, phase: 'base' }));
    assert.match(html, /100 × 100 × 32/, view);
  }
  const table = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: cnn, view: 'tabla', phase: 'base' }));
  assert.match(table, /conv2d/);
  assert.match(table, /Entrenada/);
});

test('la fase decide qué bloques se marcan como entrenados', () => {
  const frozen = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: data('vgg16', [block('block5', 'convolution', [null, 6, 6, 512], ['fine_tuning'])]), view: 'bloques-3d', phase: 'base' }));
  assert.match(frozen, /data-trained="false"/);
  const trained = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: data('vgg16', [block('block5', 'convolution', [null, 6, 6, 512], ['fine_tuning'])]), view: 'bloques-3d', phase: 'fine_tuning' }));
  assert.match(trained, /data-trained="true"/);
});

test('DenseNet rotula sus conexiones como derivadas y sólo cuenta concatenaciones del bloque', () => {
  const units = [1, 2, 3].map(index => ({ name: `conv2_block${index}_concat`, type: 'Concatenate', block: 'dense2', output_shape: [null, 50, 50, 64 + index * 32], inputs: [], parameters: 0, trainable_phases: [], settings: {} }));
  const dense = data('densenet121', [block('dense2', 'dense', [null, 50, 50, 160], [], { units: 3 })],
    [...units, { name: 'conv2_block1_1_conv', type: 'Conv2D', block: 'dense2', output_shape: null, inputs: [], parameters: 1, trainable_phases: [], settings: {} }]);
  assert.equal(denseUnits(dense, 'dense2').length, 3);
  const html = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: dense, view: 'conexiones', phase: 'base' }));
  assert.match(html, /Dibujo derivado/);
  assert.match(html, /Capa 3 de 3/);
});

test('BiomedCLIP declara la estructura de referencia y no inventa capas', () => {
  const vit = data('biomedclip', [block('input', 'input', [null, 224, 224, 3], []), block('vit0', 'encoder', null, [], { origin: 'reference' }), block('head', 'head', [null, 1])]);
  assert.match(renderToStaticMarkup(React.createElement(ArchitectureChart, { data: vit, view: 'flujo', phase: 'base' })), /Estructura de referencia/);
  assert.match(renderToStaticMarkup(React.createElement(ArchitectureChart, { data: vit, view: 'tabla', phase: 'base' })), /Referencia del encoder/);
});

test('la página reutiliza el selector, conserva la selección en la URL y no toca la de comparación', () => {
  const page = read('pages/ModelExplorer.tsx');
  assert.match(page, /RunSelectorDialog/);
  assert.match(page, /search\.get\('run'\)/);
  assert.match(page, /isValidPublicId/);
  assert.doesNotMatch(page, /useComparisonSelection/);
  assert.match(read('pages/ModelComparison.tsx'), /RunSelectorDialog/);
  assert.match(read('components/navigation/navigationConfig.ts'), /Explorador de Modelos/);
  assert.match(read('App.tsx'), /routes\.modelExplorer/);
  assert.match(read('services/api.ts'), /\/architecture`/);
});

test('el selector sin máximo permite elegir y los menús de filtro viven en el diálogo abierto', () => {
  const table = read('components/reports/TrainingRunsTable.tsx');
  assert.match(table, /selection\?\.maximum === undefined \? Number\.POSITIVE_INFINITY/);
  assert.match(table, /document\.querySelector<HTMLElement>\('dialog\[open\]'\)/);
  assert.doesNotMatch(table, /disablePortal/);
  assert.match(table, /=> \(\{ value, label \}\)/);
});

test('Análisis de Modelos reutiliza el detalle con un modelo activo a la vez', () => {
  const panel = read('components/model-architecture/ArchitecturePanel.tsx');
  assert.match(read('components/reports/AnalysisWorkspace.tsx'), /id: 'arquitectura', label: 'Arquitectura'/);
  assert.match(panel, /ArchitectureDetail/);
  assert.match(panel, /aria-pressed=\{id === run\}/);
  assert.match(panel, /ids\.length > 1/);
  assert.match(panel, /ids\.find\(id => id === selected\) \?\? ids\[0\]/);
  assert.match(panel, /cache, key, .*active\)/);
  assert.match(read('components/reports/ScientificPreflight.tsx'), /id="arquitectura"/);
  assert.match(read('pages/ModelComparison.tsx'), /search\.get\('modelo'\)/);
  assert.match(read('pages/ModelExplorer.tsx'), /ArchitectureDetail/);
});
