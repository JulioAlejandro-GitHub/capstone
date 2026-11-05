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
const read = (path) => readFileSync(resolve(root, path), 'utf8');
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
const chart = load(resolve(root, 'components/model-architecture/ArchitectureChart.tsx'));

// Bloques de DenseNet121 03c7b1a1 tal como los arma GET /runs/{id}/architecture.
const block = (id, label, kind, shape, units = null) => ({ id, label, kind, layers: 4, units, output_shape: shape, parameters: 1, trainable_phases: ['base'], origin: 'recorded' });
const densenet = { family: 'densenet121', architecture: 'densenet121', output: { neurons: 1, activation: 'sigmoid' }, layers: [], phases: [], blocks: [
  block('input', 'Entrada', 'input', [null, 200, 200, 3]), block('stem', 'Convolución inicial', 'convolution', [null, 50, 50, 64]),
  block('dense2', 'Bloque denso 1', 'dense', [null, 50, 50, 256], 6), block('transition2', 'Transición 1', 'transition', [null, 25, 25, 128]),
  block('dense3', 'Bloque denso 2', 'dense', [null, 25, 25, 512], 12), block('head', 'Cabeza de clasificación', 'head', [null, 1024]),
  block('output', 'Capa de salida', 'output', [null, 1])] };

test('los nombres largos del grafo denso se dividen en líneas que caben en su columna', () => {
  assert.deepEqual(Array.from(chart.wrapLabel('Cabeza de clasificación', 16)), ['Cabeza de', 'clasificación']);
  assert.deepEqual(Array.from(chart.wrapLabel('Convolución inicial', 16)), ['Convolución', 'inicial']);
  assert.deepEqual(Array.from(chart.wrapLabel('Entrada', 16)), ['Entrada']);
  const svg = renderToStaticMarkup(React.createElement(chart.ArchitectureChart, { data: densenet, view: 'grafo', phase: 'base',
    activity: { dense2: { value: 0.47, label: '47 % activos', current: true } } }));
  assert.match(svg, /<tspan[^>]*>Cabeza de<\/tspan><tspan[^>]*dy="16"[^>]*>clasificación<\/tspan>/);
  // «N capas densas» va bajo el nombre y la actividad bajo esa línea, sin compartir altura.
  const name = Number(/<text class="mx-name"[^>]*y="(\d+)"[^>]*><tspan[^>]*>Bloque denso 1/.exec(svg)[1]);
  const detail = Number(/<text class="mx-dimension"[^>]*y="(\d+)"[^>]*>6 capas densas/.exec(svg)[1]);
  const activity = Number(/<g class="mx-activity"[^>]*><rect class="mx-activity-track"[^>]*y="(\d+)"/.exec(svg)[1]);
  assert.ok(name < detail && detail < activity, `${name} < ${detail} < ${activity}`);
  assert.match(svg, /viewBox="0 0 \d+ (\d+)"/);
  assert.ok(Number(/viewBox="0 0 \d+ (\d+)"/.exec(svg)[1]) > 312, 'el marco crece con la segunda línea y la actividad');
});

test('toda imagen de célula de los reportes abre «Vista ampliada»', () => {
  const panel = read('components/model-architecture/ActivationTracePanel.tsx');
  assert.equal((panel.match(/<img src=\{png\(trace\.input_image\)\}/g) ?? []).length, 1, 'una sola imagen, dentro de CellImage');
  assert.match(panel, /<CellImage trace=\{trace\} alt=\{`Célula \$\{trace\.sample_id\}`\} onOpen=\{openCell\}/);
  assert.match(panel, /<CellImage trace=\{trace\} alt="Célula original a tamaño de entrada" onOpen=\{onOpen\}/);
  assert.match(panel, /variant="modal" lazy/);
  const page = read('pages/ModelTraining.tsx');
  assert.match(page, /useExpandRequest\(Boolean\(cellState\.comparison\)\)/);
  assert.match(page, /const openCell = cell && !cellState\.contextError \? openExpanded : undefined;/);
  assert.match(page, /className="mt-cell-thumb-button" onClick=\{openCell\}/);
  const viewer = read('components/reports/XAIComparisonViewer.tsx');
  assert.match(viewer, /variant === 'modal' \? null :/);
});
