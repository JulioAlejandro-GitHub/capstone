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
    runInNewContext(code, { exports: module.exports, URLSearchParams, AbortController, window: {setTimeout, clearTimeout},
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
    '../hooks/useComparisonTrainingSummaries': {useComparisonTrainingSummaries: () => ({summaries: catalog ? {items: catalog.items.flatMap(model => model.training_runs.map(run => ({...run, run_id: run.training_run_id, model_name: model.model_name}))), count: 1, limit: 500} : null, error: null, retry() {}})},
    '../auth': {useAuth: () => ({user: {id: 'test'}, status: 'authenticated'})},
    '../components/reports/ScientificReport': {EvaluationNavigation: () => null},
    '../components/reports/ScientificPreflight': {ScientificPreflight: () => null},
    '../hooks/useComparisonCatalog': {useComparisonCatalog: () => ({catalog, error, retry() {}})},
    '../hooks/useComparisonSelection': {useComparisonSelection: () => ({ids, add() {}, remove() {}})},
    '../components/reports/ComparisonRunCard': {ComparisonRunCard: ({id}) => React.createElement('article', null, id)},
    'react-router-dom': {useSearchParams: () => [new URLSearchParams(), () => {}]},
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
  assert.equal(navigationItems[index + 1].label, 'Análisis de Modelos');
  assert.equal(navigationItems[index + 1].path, '/modelo-ia/analisis');
});

for (let index = 0; index < 4; index++) test(`compact card RUN ${String.fromCharCode(65 + index)} keeps UUID in closed technical details`, () => {
  const load = loader({
    '../../hooks/useComparisonRun': {useComparisonRun: () => ({run: {status: 'completed', model_name: 'Modelo', architecture: 'CNN', execution_parameters: {optimizer: 'sgd', learning_rate: 0.01}}, error: null})},
    'react-router-dom': {Link: ({children, to}) => React.createElement('a', {href: to}, children)},
  });
  const id = 'a1234567-1234-1234-1234-a12345678901';
  const html = renderToStaticMarkup(React.createElement(load('components/reports/ComparisonRunCard.tsx').ComparisonRunCard, {id, index, datasource: 'malaria', onRemove() {}}));
  assert.match(html, new RegExp(`RUN ${String.fromCharCode(65 + index)}`));
  assert.match(html, new RegExp(`<details><summary>Detalles técnicos</summary><code class="report-identifier">${id}</code>`));
  assert.match(html, /Copiar UUID/);
  const visible = html.replace(/<details>.*?<\/details>/gs, '').replace(/<[^>]+>/g, '');
  assert.ok(!visible.includes(id));
  assert.match(visible, /CNN/); assert.match(visible, /sgd/); assert.match(visible, /0.01/);
});


test('selector reuses the report row, preserving full report secondary sections', () => {
  const load = loader();
  const run = {run_id: '12345678-full-uuid', run_name: 'Ensayo', model_name: 'CNN', status: 'completed', command: '--learning-rate 0.02 --max-epochs 20', evaluation_count: 0, explainability_count: 0};
  const Row = load('components/reports/RunSummaryRow.tsx').RunSummaryRow;
  const compact = renderToStaticMarkup(React.createElement(Row, {run, processKind: 'training', variant: 'compact', onRunSelect() {}}));
  const full = renderToStaticMarkup(React.createElement(Row, {run, processKind: 'training', onRunSelect() {}}));
  assert.match(compact, /report-row--compact/);
  assert.match(compact, /Consultar UUID completo/);
  assert.match(compact, /12345678-full-uuid/);
  assert.match(compact, /0.02/);
  assert.match(compact, /run-scientific-parameters/);
  assert.doesNotMatch(compact, /stage2-release-summary|Lectura automática exploratoria|run-lineage-group__children/);
  assert.match(full, /stage2-release-summary/);
  assert.match(full, /Lectura automática exploratoria/);
  const Group = load('components/reports/TrainingRunGroupCard.tsx').TrainingRunGroupCard;
  const group = renderToStaticMarkup(React.createElement(Group, {training: run, childrenState: {data: null, status: 'idle'}, datasource: 'malaria'}));
  assert.match(group, /run-lineage-group__children/);
});

test('summary loader waits for opening and cancels obsolete read-only requests', async () => {
  let effect;
  let request;
  const writes = [];
  const load = loader({
    react: {...React, useState: initial => [initial, value => writes.push(value)], useEffect: callback => { effect = callback; }},
    '../services/api': {api: {getTrainingSummaries: options => { request = options; return Promise.resolve({items: [], count: 0, limit: 500}); }}},
  });
  const hook = load('hooks/useComparisonTrainingSummaries.ts').useComparisonTrainingSummaries;
  hook('malaria', false);
  assert.equal(effect(), undefined);
  assert.equal(request, undefined);
  hook('malaria', true);
  const cleanupBeforeStart = effect();
  cleanupBeforeStart();
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.equal(request, undefined);
  const cleanup = effect();
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.equal(request.datasource, 'malaria');
  assert.equal(request.limit, 500);
  assert.equal(writes.at(-1).count, 0);
  cleanup();
  assert.equal(request.signal.aborted, true);
});

for (const stage of ['train', 'evaluate', 'explain', 'query', 'complete']) {
  test(`eligibility ${stage}: visible stages and guarded selection`, () => {
    const eligibility = {run_id: 'exact-uuid', eligible: stage === 'complete', train: true, evaluate: true, explain: true, reasons: [], evidence: {}};
    if (stage === 'query') {
      eligibility.train = eligibility.evaluate = eligibility.explain = null;
      eligibility.reasons = [{stage: 'query', code: 'ERROR_DE_CONSULTA', message: 'Error de consulta de elegibilidad.'}];
    } else if (stage !== 'complete') {
      eligibility[stage] = false;
      eligibility.reasons = [{stage, code: 'INVALID_EVIDENCE', message: `${stage.toUpperCase()} sin evidencia válida.`}];
    }
    const data = structuredClone(catalog);
    data.items[0].training_runs[0].eligibility = eligibility;
    const html = page([], data);
    assert.match(html, /exact-uuid/);
    assert.match(html, /TRAIN/);
    assert.match(html, /EVALUATE/);
    assert.match(html, /EXPLAIN/);
    const checkbox = html.match(/<input type="checkbox"[^>]*>/)[0];
    assert.equal(checkbox.includes('disabled'), stage !== 'complete');
    if (stage === 'query') {
      assert.match(html, /role="alert"/);
      assert.doesNotMatch(html, /pendiente/);
    }
  });
}

test('additional missing analyses consolidate causes and affected RUNs', () => {
  const { ScientificRepresentations } = loader({'../../services/api': {api: {}}, './XAIComparisonViewer': {}, '../../hooks/useComparisonEvidence': {}, './ComparisonPython': {}})('components/reports/ScientificReport.tsx');
  const module = ScientificRepresentations({selections: [], datasource: 'malaria', cache: {}});
  const html = renderToStaticMarkup(module.props.children([
    {training_run_id: 'a', artifacts: []}, {training_run_id: 'b', artifacts: []},
  ]));
  assert.equal((html.match(/<h3>Sin evidencia<\/h3>/g) ?? []).length, 1);
  assert.match(html, /RUN A/);
  assert.match(html, /RUN B/);
  assert.match(html, /EXPLAIN no acredita automáticamente embeddings ni CKA/);
});
