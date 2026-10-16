import assert from 'node:assert/strict';
import test from 'node:test';
import { existsSync, readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';
const require = createRequire(import.meta.url);
const root = fileURLToPath(new URL('../src/', import.meta.url));
function loader(mocks = {}) {
  const cache = new Map();
  const load = (filename) => {
    const path = resolve(root, filename);
    if (cache.has(path)) return cache.get(path);
    const module = { exports: {} };
    cache.set(path, module.exports);
    const code = ts.transpileModule(readFileSync(path, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText;
    runInNewContext(code, { exports: module.exports, URLSearchParams, AbortController,
      require: (name) => {
        if (name in mocks) return mocks[name];
        if (name.endsWith('.css')) return {};
        if (!name.startsWith('.')) return require(name);
        const base = resolve(dirname(path), name);
        const target = [base, `${base}.tsx`, `${base}.ts`].find(existsSync);
        if (!target) throw new Error(`Cannot load ${name} from ${path}`);
        return load(target);
      },
    });
    return module.exports;
  };
  return load;
}

test('selection retains exact identities, order, capacity from server, removal and replacement', () => {
  let state = [];
  const load = loader({react: {...React, useState: () => [state, update => { state = update(state); }]}});
  const { ComparisonSelectionProvider } = load('hooks/useComparisonSelection.tsx');
  const selection = ComparisonSelectionProvider({children: null}).props.value;
  for (let i = 0; i < 7; i++) selection.add(`uuid-${i}`, 7);
  selection.add('uuid-0', 7);
  selection.add('overflow', 7);
  assert.deepEqual(Array.from(state), Array.from({length: 7}, (_, i) => `uuid-${i}`));
  selection.remove('uuid-2');
  selection.add('replacement', 7);
  assert.equal(state.at(-1), 'replacement');
  assert.equal(state.length, 7);
  selection.add('blocked-by-new-capacity', 2);
  assert.equal(state.length, 7);
});

function page(ids, catalog, error = null) {
  const load = loader({
    '../hooks/useComparisonCatalog': {useComparisonCatalog: () => ({catalog, error, retry() {}})},
    '../hooks/useComparisonSelection': {useComparisonSelection: () => ({ids, add() {}, remove() {}})},
    '../components/reports/ComparisonRunCard': {ComparisonRunCard: ({id}) => React.createElement('article', null, id)},
  });
  return renderToStaticMarkup(React.createElement(load('pages/ModelComparison.tsx').ModelComparison, {datasource: 'malaria'}));
}
const catalog = {comparison: {scc_max_comparison_runs: 2}, items: [{model_name: 'Modelo real', architecture: 'Arquitectura real', training_runs: [{training_run_id: 'exact-uuid', status: 'failed', run_name: 'Ensayo', started_at: null}]}]};
for (const ids of [[], ['a'], ['a', 'b']]) test(`selection page renders ${ids.length} selected runs`, () => {
  const html = page(ids, catalog);
  assert.match(html, new RegExp(`${ids.length} / 2`));
  assert.equal((html.match(/scc-empty-slot/g) ?? []).length, 2 - ids.length);
  assert.match(html, /exact-uuid/);
  assert.match(html, /failed/);
  assert.match(html, ids.length < 2 ? /Todavía no existe/ : /Capacidad máxima alcanzada/);
  assert.match(html, /aria-labelledby="scc-selector-title"/);
});
test('capacity stays unavailable while loading or when catalog query fails', () => {
  assert.match(page([], null), /Cargando catálogo/);
  assert.match(page([], null), /disabled=""/);
  assert.match(page([], null, 'Error de consulta'), /role="alert"/);
});

test('card reads persisted E2 configuration and epochs, keeps zero seed and complete identity', () => {
  const load = loader({
    './AssessmentXAI': {TrainingAssessmentXAI: () => null},
    '../../hooks/useComparisonRun': {useComparisonRun: () => ({run: {status: 'completed', model_name: 'Real', random_seed: 0, completed_epochs: 12, total_epochs: 20, duration_seconds: 60, execution_parameters: {runtime_environment: {device: 'CPU'}, model_configuration_e2: {configuration: {resolved: {optimizer: {name: 'sgd', parameters: {learning_rate: 0.02}}}}}}}, error: null})},
    'react-router-dom': {Link: ({children, to}) => React.createElement('a', {href: to}, children)},
  });
  const html = renderToStaticMarkup(React.createElement(load('components/reports/ComparisonRunCard.tsx').ComparisonRunCard, {id: 'full-training-uuid', index: 1, datasource: 'malaria', onRemove() {}}));
  for (const text of ['RUN B', 'full-training-uuid', 'sgd', '0.02', '12 / 20', '00:01:00', 'Sin evidencia', 'datasource=malaria']) assert.ok(html.includes(text), text);
  assert.match(html, /Semilla<\/dt><dd>0<\/dd>/);
});

test('navigation reuses the public route immediately after campaign', () => {
  const load = loader();
  const {navigationItems} = load('components/navigation/navigationConfig.ts');
  const index = navigationItems.findIndex(item => item.id === 'campaign');
  assert.equal(navigationItems[index + 1].label, 'Comparar Modelos');
  assert.equal(navigationItems[index + 1].path, '/modelo-ia/comparacion');
});
