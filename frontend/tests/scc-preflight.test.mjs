import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync, existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';
const require = createRequire(import.meta.url);
const root = fileURLToPath(new URL('../src/', import.meta.url));
function loader(mocks = {}, globals = {}) {
  const cache = new Map();
  const load = name => {
    const path = resolve(root, name);
    if (cache.has(path)) return cache.get(path);
    const module = { exports: {} }; cache.set(path, module.exports);
    const code = ts.transpileModule(readFileSync(path, 'utf8').replaceAll('import.meta.env', '({})'), {
      compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText;
    runInNewContext(code, { exports: module.exports, AbortController, URL, URLSearchParams, Headers, DOMException, setTimeout, clearTimeout, ...globals,
      require: name => {
        if (name in mocks) return mocks[name];
        if (!name.startsWith('.')) return require(name);
        const base = resolve(dirname(path), name);
        return load([base, `${base}.tsx`, `${base}.ts`].find(existsSync));
      },
    });
    return module.exports;
  };
  return load;
}
function harness() {
  const slots = []; let cursor = 0; let effects = [];
  const same = (a, b) => a && b && a.length === b.length && a.every((item, i) => Object.is(item, b[i]));
  const react = { ...React,
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial;
      return [slots[i], value => { slots[i] = typeof value === 'function' ? value(slots[i]) : value; }]; },
    useMemo(fn, deps) { const i = cursor++; if (!same(slots[i]?.deps, deps)) slots[i] = { deps, value: fn() }; return slots[i].value; },
    useRef(value) { const i = cursor++; return slots[i] ??= { current: value }; },
    useEffect(fn, deps) { const i = cursor++; if (!same(slots[i]?.deps, deps)) { slots[i]?.cleanup?.(); slots[i] = { deps }; effects.push(() => { slots[i].cleanup = fn(); }); } },
  };
  react.useCallback = (fn, deps) => react.useMemo(() => fn, deps);
  return { react, render(fn) { cursor = 0; const value = fn(); const pending = effects; effects = []; pending.forEach(fn => fn()); return value; },
    dispose() { slots.forEach(slot => slot?.cleanup?.()); }, reset() { slots.forEach(slot => slot?.cleanup?.()); slots.length = 0; effects = []; } };
}
const flush = () => new Promise(resolve => setImmediate(resolve));
function nodes(tree) { if (!tree || typeof tree !== 'object') return []; if (Array.isArray(tree)) return tree.flatMap(nodes); return [tree, ...nodes(tree.props?.children)]; }
const find = (tree, predicate) => nodes(tree).find(predicate);
const known = value => ({ state: 'known', value, evidence_ids: [] });
const missing = { state: 'unknown', reason: 'No registrado', evidence_ids: [] };
function fixture(count = 2) {
  const selections = Array.from({ length: count }, (_, i) => ({ selection_id: `train:${i}`, training_run_id: `train-${i}`, dataset_version_id: known(`dataset-${i}`), evaluation: missing, split: known('val'), checkpoint: known(`checkpoint-${i}`), selection_reason: 'Sin selección automática.' }));
  const scope = { scope_id: 'scope', requested_training_run_ids: selections.map(s => s.training_run_id), participating_training_run_ids: selections.map(s => s.training_run_id), selection_ids: selections.map(s => s.selection_id), population: 'original', question: 'Alcance real' };
  const verdict = { evaluation_status: 'evaluated', scientific_state: 'EVIDENCIA_INSUFICIENTE', error_ids: [] };
  return { contract_version: 'scc_pre_1', generated_at: '2026-10-16', correlation_id: 'correlation', selections,
    consistency: { mode: 'repeatable_read', started_at: '', completed_at: '', limitations: [] },
    dimensions: ['A1','A2','A3','A4','A5','A6'].map(dimension => ({ dimension, scope: { ...scope, scope_id: dimension }, verdict, findings: [], evidence_ids: [] })),
    analyses: ['curves','metrics','consensus','xai','embeddings','pca','umap','cka'].map((module_id, i) => ({ analysis_id: module_id, module_id, scope, verdict: i === 0 ? { ...verdict, scientific_state: 'COMPARABLE_CON_ADVERTENCIAS' } : verdict, dimension_refs: [], evidence_ids: [], findings: [], interpretation_limits: ['Límite real'], individual_data: selections.map(s => ({ selection_id: s.selection_id, availability: known(true), references: ['referencia-individual'] })) })),
    evidence: selections.map(s => ({ evidence_id: s.selection_id, source: 'A4', operation: 'preflight_configuration', record_keys: {}, field: null, selection_ids: [s.selection_id], observed_at: '2026-10-16', verification: 'operational', value: known({ architecture: 'Arquitectura real', random_seed: 0, learning_rate: null }) })),
    populations: [], checkpoints: selections.map(s => ({ selection_id: s.selection_id, artifact_id: 'checkpoint', registered: known(true), lineage: missing, availability: 'not_checked', integrity: 'not_checked', checked_at: null, evidence_ids: [], error_ids: [] })),
    technical_errors: [], summary: { by_state: { COMPARABLE: 0, COMPARABLE_CON_ADVERTENCIAS: 1, NO_COMPARABLE: 0, EVIDENCIA_INSUFICIENTE: 7 }, not_evaluated: 0, analysis_count: 8, warning_reason_ids: [], technical_error_ids: [] } };
}
function screen(api = {}, user = { id: 'user', permissions: ['read'] }) {
  const h = harness();
  const load = loader({ react: h.react, '../../auth': { useAuth: () => ({ user, status: 'authenticated' }) },
    '../../services/api': { api, ApiError: class extends Error {} }, './AssessmentXAI': { TrainingAssessmentXAI: () => null } });
  const component = load('components/reports/ScientificPreflight.tsx').ScientificPreflight;
  const props = { ids: ['a', 'b'], datasource: 'malaria', maximum: 7 };
  const session = component(props).props.children;
  return { h, load, component, props, render: () => h.render(() => session.type(props)) };
}

test('HTTP POST uses the real shared client, bearer, datasource and exact scientific identities', async () => {
  const calls = [];
  const load = loader({}, { window: { localStorage: { getItem: () => 'session-token' }, setTimeout, clearTimeout }, fetch: async (url, init) => { calls.push({ url, init }); return { ok: true, status: 200, json: async () => fixture() }; } });
  const { api } = load('services/api.ts');
  const body = { selections: [{ training_run_id: 'train', evaluation: { source: 'assessment', identity_id: 'identity', attempt_id: 'attempt' }, split: 'test', checkpoint_artifact_id: 'checkpoint' }] };
  await api.getComparisonPreflight('malaria', body);
  assert.equal(calls[0].url.pathname, '/models/comparison/preflight'); assert.equal(calls[0].url.searchParams.get('datasource'), 'malaria');
  assert.equal(calls[0].init.method, 'POST'); assert.equal(calls[0].init.headers.get('Authorization'), 'Bearer session-token');
  assert.deepEqual(JSON.parse(calls[0].init.body), body);
});
for (const count of [2, 3, 7]) test(`A1–A6 render ${count} TRAIN columns, partial evidence and all analyses`, () => {
  const load = loader({ '../../auth': {}, '../../services/api': {}, './AssessmentXAI': {} });
  const { PreflightEvidence } = load('components/reports/ScientificPreflight.tsx');
  const html = renderToStaticMarkup(React.createElement(PreflightEvidence, { data: fixture(count) }));
  assert.equal((html.match(/scope="col"/g) ?? []).length, count + 2);
  for (const value of ['A1','A2','A3','A4','A5','A6','Curvas de aprendizaje','Métricas VAL/TEST','Consenso y desacuerdo','XAI','Embeddings','PCA','UMAP','CKA','Sin evidencia','No verificado','referencia-individual','random_seed: 0']) assert.ok(html.includes(value), value);
  assert.doesNotMatch(html, /Comparación controlada válida|Protocolo TESTED/);
});
test('observation states preserve not_checked, unknown, non-applicable and query_error', () => {
  const load = loader({ '../../auth': {}, '../../services/api': {}, './AssessmentXAI': {} });
  const { observationText } = load('components/reports/ScientificPreflight.tsx');
  for (const [state, label] of [['not_checked','No verificado'], ['unknown','Sin evidencia'], ['not_applicable','No disponible']]) assert.match(observationText({ state, reason: 'motivo', evidence_ids: [] }), new RegExp(label));
  assert.match(observationText({ state: 'query_error', error_ids: ['error-1'] }), /ERROR_DE_CONSULTA.*error-1/);
});
test('initial summary loads once; opening and closing detail reuses it; refresh queries again', async () => {
  let calls = 0;
  const s = screen({ getComparisonPreflight: async () => { calls++; return fixture(); } });
  let tree = s.render(); await flush(); tree = s.render();
  assert.equal(calls, 1);
  assert.ok(find(tree, n => n.props?.['aria-label'] === 'Resumen metodológico'));
  const detail = find(tree, n => n.type === 'details' && n.props.open === false);
  assert.ok(detail); detail.props.onToggle({ currentTarget: { open: true } }); tree = s.render();
  find(tree, n => n.type === 'details' && n.props.open === true).props.onToggle({ currentTarget: { open: false } });
  s.render(); await flush(); assert.equal(calls, 1);
  const refresh = find(tree, n => n.type === 'button' && n.props.children === 'Actualizar evidencia');
  refresh.props.onClick(); s.render(); await flush(); s.render(); assert.equal(calls, 2); s.h.dispose();
});
test('initial modules are independent; history alone starts open and XAI is not mounted', () => {
  const s = screen(); const tree = s.render(); const modules = find(tree, n => typeof n.type === 'function' && n.type.name === 'ComparisonModules');
  s.h.reset();
  const rendered = s.h.render(() => modules.type(modules.props));
  const details = nodes(rendered).filter(n => n.type === 'details');
  assert.equal(details.filter(n => n.props.open).length, 1);
  assert.match(details[0].props.children[0].props.children, /Historia de aprendizaje/);
  assert.equal(nodes(rendered).filter(n => typeof n.type === 'function').length, 0);
  assert.ok(details.every(n => !n.props.name)); s.h.dispose();
});
test('no initial query with insufficient selection or selection exceeding configured capacity', async () => {
  let calls = 0; const s = screen({ getComparisonPreflight: async () => { calls++; return fixture(); } });
  for (const ids of [[], ['a'], ['a','b','c','d','e','f','g','h']]) { s.props.ids = ids; s.render(); await flush(); }
  assert.equal(calls, 0); s.h.dispose();
});
test('cache deduplicates concurrent calls, retains success, evicts failure, and isolates contexts', async () => {
  const { createComparisonCache } = loader()('utils/comparisonCache.ts');
  const cache = createComparisonCache(); let calls = 0;
  const load = async () => { calls++; return 'evidence'; };
  const a = cache.read('same', load); assert.equal(cache.read('same', load), a); await a;
  assert.equal(await cache.read('same', load), 'evidence'); assert.equal(calls, 1);
  await assert.rejects(cache.read('failure', async () => { throw Error('HTTP'); }));
  assert.equal(await cache.read('failure', load), 'evidence');
  cache.clear(); await cache.read('same', load); assert.equal(calls, 3);
  await createComparisonCache().read('same', load); assert.equal(calls, 4);
});
test('late responses cannot replace current TRAIN, attempt, checkpoint, split or datasource', async () => {
  const h = harness(); const load = loader({ react: h.react });
  const { useComparisonEvidence } = load('hooks/useComparisonEvidence.ts');
  const cache = load('utils/comparisonCache.ts').createComparisonCache(); let resolveOld; let key = 'old';
  const old = () => new Promise(resolve => { resolveOld = resolve; });
  h.render(() => useComparisonEvidence(cache, key, old)); await flush();
  for (const changed of ['train', 'attempt', 'checkpoint', 'split', 'datasource']) {
    key = changed;
    const initial = h.render(() => useComparisonEvidence(cache, key, async () => changed)); assert.equal(initial.data, undefined);
    await flush(); assert.equal(h.render(() => useComparisonEvidence(cache, key, async () => changed)).data, changed);
  }
  resolveOld('stale'); await flush(); assert.equal(h.render(() => useComparisonEvidence(cache, key, old)).data, 'datasource'); h.dispose();
});
test('HTTP errors remain errors and a new revision retries successfully', async () => {
  let fail = true; const s = screen({ getComparisonPreflight: async () => { if (fail) throw Error('HTTP'); return fixture(); } });
  s.render(); await flush(); let tree = s.render();
  const error = find(tree, n => typeof n.type === 'function' && n.type.name === 'ErrorMessage'); assert.ok(error);
  fail = false; error.props.retry(); s.render(); await flush(); tree = s.render();
  assert.equal(find(tree, n => typeof n.type === 'function' && n.type.name === 'ErrorMessage'), undefined); s.h.dispose();
});
test('authorization, permission, datasource and TRAIN changes remount the evidence scope', () => {
  const s = screen(); const before = s.component(s.props).key;
  assert.notEqual(s.component({ ...s.props, datasource: 'other' }).key, before);
  assert.notEqual(s.component({ ...s.props, ids: ['b','c'] }).key, before);
  assert.notEqual(screen({}, { id: 'other', permissions: ['read'] }).component(s.props).key, before);
  assert.notEqual(screen({}, { id: 'user', permissions: [] }).component(s.props).key, before);
});
test('XAI first opening mounts once; closing preserves content and disables background work', () => {
  const h = harness(); const load = loader({ react: h.react, '../../services/api': { api: {} }, './GeneratedXAIComparison': {} });
  const { TrainingAssessmentXAI } = load('components/reports/AssessmentXAI.tsx');
  const render = () => h.render(() => TrainingAssessmentXAI({ trainingRunId: 'train', datasource: 'malaria', active: true }));
  let tree = render(); assert.equal(nodes(tree).filter(n => typeof n.type === 'function').length, 0);
  tree.props.onToggle({ currentTarget: { open: true } }); tree = render();
  const content = find(tree, n => typeof n.type === 'function'); assert.equal(content.props.active, true);
  tree.props.onToggle({ currentTarget: { open: false } }); tree = render();
  const retained = find(tree, n => typeof n.type === 'function'); assert.equal(retained.key, content.key); assert.equal(retained.props.active, false);
  tree.props.onToggle({ currentTarget: { open: true } }); tree = render(); assert.equal(find(tree, n => typeof n.type === 'function').key, content.key);
});
test('closed retained hook does not fetch changed evidence until reopened', async () => {
  const h = harness(); const load = loader({ react: h.react }); const cache = load('utils/comparisonCache.ts').createComparisonCache();
  const { useComparisonEvidence } = load('hooks/useComparisonEvidence.ts'); let calls = 0;
  const request = async () => ++calls;
  h.render(() => useComparisonEvidence(cache, 'new', request, false)); await flush(); assert.equal(calls, 0);
  h.render(() => useComparisonEvidence(cache, 'new', request, true)); await flush(); assert.equal(calls, 1);
  h.render(() => useComparisonEvidence(cache, 'new', request, false)); h.render(() => useComparisonEvidence(cache, 'new', request, true)); await flush(); assert.equal(calls, 1); h.dispose();
});

test('evaluation control paginates, never defaults to latest, and applies the explicit identity and attempt', async () => {
  const calls = []; let applied;
  const detail = { id: 'attempt-1', identity_id: 'identity-1', training_run_id: 'a', kind: 'evaluate', identity: { split: 'val', model: { checkpoint_artifact_id: 'attributed-checkpoint' } } };
  const s = screen({ getTrainingAssessments: async (id, offset) => { calls.push(['list', id, offset]); return { items: [{ attempt_id: 'attempt-1', training_run_id: 'a', kind: 'evaluate', split: 'val', state: 'verified' }] }; },
    getAssessment: async attempt => { calls.push(['detail', attempt]); return detail; } });
  const tree = s.render(); const selector = find(tree, n => typeof n.type === 'function' && n.type.name === 'EvaluationSelector');
  s.h.reset(); const props = { ...selector.props, onChange: value => { applied = value; } };
  const render = () => s.h.render(() => selector.type(props));
  let selected = render(); await flush(); assert.equal(calls.length, 0);
  find(selected, n => n.type === 'button').props.onClick(); render(); await flush(); selected = render();
  assert.equal(calls.length, 1);
  const select = find(selected, n => n.type === 'select'); assert.equal(select.props.value, '');
  select.props.onChange({ target: { value: 'attempt-1' } }); render(); await flush(); selected = render();
  find(selected, n => n.type === 'input').props.onChange({ target: { value: 'explicit-checkpoint' } });
  const splits = nodes(selected).filter(n => n.type === 'select'); splits[1].props.onChange({ target: { value: 'test' } }); selected = render();
  find(selected, n => n.type === 'form').props.onSubmit({ preventDefault() {} });
  assert.deepEqual(JSON.parse(JSON.stringify(applied)), { training_run_id: 'a', evaluation: { source: 'assessment', identity_id: 'identity-1', attempt_id: 'attempt-1' }, split: 'test', checkpoint_artifact_id: 'explicit-checkpoint' }); s.h.dispose();
});
test('changed attempt, split and checkpoint reach a fresh Preflight request', async () => {
  const bodies = []; const s = screen({ getComparisonPreflight: async (_ds, body) => { bodies.push(JSON.parse(JSON.stringify(body))); return fixture(); } });
  let tree = s.render(); await flush(); tree = s.render();
  for (const selection of [
    { training_run_id: 'a', evaluation: { source: 'assessment', identity_id: 'i', attempt_id: 'one' } },
    { training_run_id: 'a', evaluation: { source: 'assessment', identity_id: 'i', attempt_id: 'two' }, split: 'test' },
    { training_run_id: 'a', checkpoint_artifact_id: 'other' },
  ]) {
    find(tree, n => typeof n.type === 'function' && n.type.name === 'EvaluationSelector').props.onChange(selection);
    tree = s.render(); await flush(); tree = s.render(); assert.deepEqual(bodies.at(-1).selections[0], selection);
  }
  assert.equal(bodies.length, 4); s.h.dispose();
});
test('retained XAI polling stops when closed and idle reopening reuses the response', async () => {
  const h = harness(); let calls = 0;
  const load = loader({ react: h.react, '../services/api': { api: { getExplainState: async () => { calls++; return { training_run_id: 'train', dataset_version_id: 'dataset', sample_id: 'sample', authorized: true, methods: [] }; } } } });
  const { useExplainGeneration } = load('hooks/useExplainGeneration.ts');
  const comparison = { id: 'xai', trainingRunId: 'train', datasetVersionId: 'dataset', split: 'val', purpose: 'development', sampleId: 'sample', original: { attemptId: 'attempt' }, methods: {} };
  h.render(() => useExplainGeneration(comparison, false)); await flush(); assert.equal(calls, 0);
  h.render(() => useExplainGeneration(comparison, true)); await flush(); assert.equal(calls, 1);
  h.render(() => useExplainGeneration(comparison, false)); h.render(() => useExplainGeneration(comparison, true)); await flush(); assert.equal(calls, 1); h.dispose();
});
test('mixed summary retains valid individual evidence alongside a technical failure', () => {
  const data = fixture(); data.analyses[1].verdict = { evaluation_status: 'not_evaluated', scientific_state: null, error_ids: ['query-1'] };
  data.technical_errors = [{ error_id: 'query-1', state: 'ERROR_DE_CONSULTA', message: 'Fallo parcial', operation: 'metrics', scope_ids: [], selection_ids: [], correlation_id: 'id', retryable: true }];
  const load = loader({ '../../auth': {}, '../../services/api': {}, './AssessmentXAI': {} });
  const html = renderToStaticMarkup(React.createElement(load('components/reports/ScientificPreflight.tsx').PreflightEvidence, { data }));
  assert.match(html, /ERROR_DE_CONSULTA/); assert.match(html, /COMPARABLE_CON_ADVERTENCIAS/); assert.match(html, /referencia-individual/);
});

test('a stale failed request cannot evict a newer successful cache entry after refresh', async () => {
  const cache = loader()('utils/comparisonCache.ts').createComparisonCache(); let rejectOld;
  const old = cache.read('identity', () => new Promise((_resolve, reject) => { rejectOld = reject; }));
  const handled = assert.rejects(old); await flush(); cache.clear();
  await cache.read('identity', async () => 'new evidence'); rejectOld(Error('old HTTP error')); await handled;
  assert.equal(await cache.read('identity', async () => 'incorrect reload'), 'new evidence');
});
test('HTTP 403 is preserved by the client and never becomes scientific incompatibility', async () => {
  const load = loader({}, { window: { localStorage: { getItem: () => 'session-token' }, setTimeout, clearTimeout }, fetch: async () => ({ ok: false, status: 403, text: async () => JSON.stringify({ detail: 'Permiso insuficiente' }) }) });
  const { api, ApiError } = load('services/api.ts');
  let failure;
  try { await api.getComparisonPreflight('malaria', { selections: [] }); } catch (error) { failure = error; }
  assert.ok(failure instanceof ApiError); assert.equal(failure.status, 403);
  const h = harness();
  const ui = loader({ react: h.react, '../../auth': { useAuth: () => ({ user: { id: 'user' }, status: 'authenticated' }) }, '../../services/api': { api: { getComparisonPreflight: async () => { throw failure; } }, ApiError }, './AssessmentXAI': {} });
  const session = ui('components/reports/ScientificPreflight.tsx').ScientificPreflight({ ids: ['a','b'], datasource: 'malaria', maximum: 2 }).props.children;
  h.render(() => session.type(session.props)); await flush(); const tree = h.render(() => session.type(session.props));
  const errorElement = find(tree, n => typeof n.type === 'function' && n.type.name === 'ErrorMessage');
  const html = renderToStaticMarkup(errorElement); assert.match(html, /Error de autorización/); assert.doesNotMatch(html, /NO_COMPARABLE/); h.dispose();
});

for (const count of [2, 3, 4]) test(`UX matrix preserves ${count} aliases and exposes identities only in details`, () => {
  const { PreflightEvidence } = loader({ '../../auth': {}, '../../services/api': {}, './AssessmentXAI': {} })('components/reports/ScientificPreflight.tsx');
  const data = fixture(count);
  const html = renderToStaticMarkup(React.createElement(PreflightEvidence, { data }));
  const head = html.match(/<thead>(.*?)<\/thead>/s)[1];
  assert.equal((head.match(/scope="col"/g) ?? []).length, count + 2);
  data.selections.forEach((selection, index) => {
    assert.ok(head.includes(`RUN ${String.fromCharCode(65 + index)}`));
    assert.ok(!head.includes(selection.training_run_id));
    assert.ok(html.includes(selection.training_run_id));
  });
  assert.match(html, /Semilla<\/th>.*?<td><div>0<\/div><\/td>/s);
  assert.match(html, /Copiar UUID/);
  assert.match(html, /Ver modelo en Python/);
  assert.match(html, /Comparable con advertencias/);
  assert.match(html, /COMPARABLE_CON_ADVERTENCIAS/);
});

test('warning grouping preserves all reasons and separates conditions, codes and kinds', () => {
  const { groupWarnings } = loader({ '../../auth': {}, '../../services/api': {}, './AssessmentXAI': {} })('components/reports/ScientificPreflight.tsx');
  const first = { reason_id: 'a', code: 'SPLIT_UNKNOWN', kind: 'missing', message: 'Partición no acreditada', condition: 'condition', affected_selection_ids: ['one'], evidence_ids: ['e1'] };
  const second = { ...first, reason_id: 'b', affected_selection_ids: ['two'], evidence_ids: ['e2'] };
  const groups = groupWarnings([first, second, { ...first, reason_id: 'c', condition: 'other' }, { ...first, reason_id: 'd', code: 'OTHER' }, { ...first, reason_id: 'e', kind: 'warning' }]);
  assert.equal(groups.length, 4);
  assert.deepEqual(Array.from(groups[0], item => item.reason_id), ['a', 'b']);
  assert.deepEqual(Array.from(groups[0].flatMap(item => item.evidence_ids)), ['e1', 'e2']);
});

test('Python only projects available persisted parameters, preserving zero/false and excluding private or unknown fields', () => {
  const { configurationCode, pythonLiteral } = loader()('components/reports/ComparisonPython.tsx');
  const data = fixture();
  data.evidence[0].value.value = { architecture: 'real_model', random_seed: 0, no_augment: false, learning_rate: null, optimizer: 'sgd', checkpoint_path: '/private/model.keras', injected: 'hp.Choice', dropout: 0 };
  const code = configurationCode(data, data.selections[0].selection_id);
  assert.match(code, /"random_seed": 0/);
  assert.match(code, /"no_augment": False/);
  assert.match(code, /"optimizer": "sgd"/);
  assert.doesNotMatch(code, /learning_rate|checkpoint_path|\/private|hp\.Choice|Adam|keras|Dense/);
  assert.equal(pythonLiteral('quote"\n'), '"quote\\"\\n"');
  assert.equal(pythonLiteral([true, null, { key: false }]), '[True, None, {"key": False}]');
  assert.match(configurationCode({ ...data, evidence: [] }, 'missing'), /Sin parámetros acreditados/);
});

test('Python RUN selector and reconstruction view use current evidence without executing or fetching models', () => {
  const h = harness();
  const { ComparisonPython } = loader({ react: h.react })('components/reports/ComparisonPython.tsx');
  const data = fixture(); data.evidence[0].value.value.optimizer = 'adam'; data.evidence[1].value.value.optimizer = 'sgd';
  let tree = h.render(() => ComparisonPython({ data }));
  const controls = nodes(tree).filter(node => node.type === 'select');
  controls[0].props.onChange({ target: { value: data.selections[1].selection_id } });
  tree = h.render(() => ComparisonPython({ data }));
  let copy = find(tree, node => node.props?.label === 'Copiar código');
  assert.match(copy.props.text, /sgd/); assert.doesNotMatch(copy.props.text, /adam/);
  controls[1].props.onChange({ target: { value: 'reconstruction' } });
  tree = h.render(() => ComparisonPython({ data }));
  copy = find(tree, node => node.props?.label === 'Copiar código');
  assert.match(copy.props.text, /Reconstrucción no acreditada/);
  assert.match(copy.props.text, /Nivel 2.*constructor/);
  assert.match(copy.props.text, /Nivel 3.*integridad/);
  assert.doesNotMatch(copy.props.text, /load_model|eval\(|exec\(/);
  h.dispose();
});

test('copy button copies exact visible text and reports clipboard failures accessibly', async () => {
  const h = harness(); let copied; let fail = false;
  const { CopyText } = loader({ react: h.react }, { navigator: { clipboard: { writeText: async text => { if (fail) throw Error('denied'); copied = text; } } } })('components/reports/ComparisonPython.tsx');
  const props = { text: '# visible\nconfig = {"seed": 0}', label: 'Copiar código' };
  let tree = h.render(() => CopyText(props));
  await find(tree, node => node.type === 'button').props.onClick();
  assert.equal(copied, props.text);
  tree = h.render(() => CopyText(props)); assert.equal(find(tree, node => node.props?.role === 'status').props.children, 'Copiado');
  fail = true; await find(tree, node => node.type === 'button').props.onClick();
  tree = h.render(() => CopyText(props)); assert.match(find(tree, node => node.props?.role === 'status').props.children, /No se pudo copiar/);
  h.dispose();
});

test('friendly labels and experimental differences retain original backend findings without deriving verdicts', () => {
  const { PreflightEvidence, findingLabel } = loader({ '../../auth': {}, '../../services/api': {}, './AssessmentXAI': {} })('components/reports/ScientificPreflight.tsx');
  const data = fixture();
  const finding = { reason_id: 'difference-original', code: 'CONFIGURATION_DIFFERENCE_OPTIMIZER', kind: 'warning', message: 'Original scientific reason', condition: 'Original condition', affected_selection_ids: ['train:0','train:1'], evidence_ids: ['ref-original'] };
  data.dimensions[3].findings.push(finding);
  data.evidence[0].value.value.optimizer = 'adam'; data.evidence[1].value.value.optimizer = 'sgd';
  const html = renderToStaticMarkup(React.createElement(PreflightEvidence, { data }));
  assert.match(html, /Diferencia experimental/);
  for (const text of ['Original scientific reason', 'Original condition', 'CONFIGURATION_DIFFERENCE_OPTIMIZER', 'ref-original', 'Evidencia insuficiente']) assert.ok(html.includes(text));
  assert.equal(findingLabel({ ...finding, code: 'SPLIT_UNKNOWN' }), 'Partición no acreditada');
  assert.equal(findingLabel({ ...finding, code: 'UNRECOGNIZED' }), finding.message);
});

test('Python syntax spans preserve exact copy text and render persisted strings as text', () => {
  const data = fixture(); data.evidence[0].value.value.architecture = '<script>alert("text")</script>';
  const { ComparisonPython } = loader()('components/reports/ComparisonPython.tsx');
  const html = renderToStaticMarkup(React.createElement(ComparisonPython, { data }));
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
  const h = harness(); const { ComparisonPython: viewer } = loader({ react: h.react })('components/reports/ComparisonPython.tsx');
  const tree = h.render(() => viewer({ data }));
  const code = find(tree, node => node.type === 'pre').props.children;
  assert.equal(code.props.children.map(span => span.props.children).join(''), find(tree, node => node.props?.label === 'Copiar código').props.text);
  h.dispose();
});
