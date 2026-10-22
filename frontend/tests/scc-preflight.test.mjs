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
        if (name.endsWith('.css')) return {};
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
  const props = { selections: [{training_run_id:'a'}, {training_run_id:'b'}], ids: ['a', 'b'], datasource: 'malaria', maximum: 7 };
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
  assert.equal((html.match(/scope="col"/g) ?? []).length, 4 * count + 12);
  for (const value of ['A1','A2','A3','A4','A5','A6','Curvas de aprendizaje','Métricas VAL/TEST','Consenso y desacuerdo','XAI','Embeddings','PCA','UMAP','CKA','Sin evidencia','No verificado','referencia-individual','random_seed: ']) assert.ok(html.includes(value), value);
  assert.doesNotMatch(html, /Comparación controlada válida|Protocolo TESTED/);
});
test('observation states preserve not_checked, unknown, non-applicable and query_error', () => {
  const load = loader({ '../../auth': {}, '../../services/api': {}, './AssessmentXAI': {} });
  const { observationText } = load('components/reports/ScientificPreflight.tsx');
  for (const [state, label] of [['not_checked','No verificado'], ['unknown','Sin evidencia'], ['not_applicable','No disponible']]) assert.match(observationText({ state, reason: 'motivo', evidence_ids: [] }), new RegExp(label));
  assert.match(observationText({ state: 'query_error', error_ids: ['error-1'] }), /ERROR_DE_CONSULTA.*error-1/);
});
test('initial summary loads once; switching sections reuses it; refresh queries again', async () => {
  let calls = 0;
  const s = screen({ getComparisonPreflight: async () => { calls++; return fixture(); } });
  let tree = s.render(); await flush(); tree = s.render();
  assert.equal(calls, 1);
  assert.ok(find(tree, n => n.props?.['aria-label'] === 'Resumen metodológico'));
  const nav = () => find(tree, n => typeof n.type === 'function' && n.type.name === 'AnalysisSectionNav');
  nav().props.onSelect('trazabilidad'); tree = s.render();
  assert.equal(nav().props.section, 'trazabilidad');
  assert.ok(find(tree, n => typeof n.type === 'function' && n.type.name === 'PreflightEvidence'));
  nav().props.onSelect('resumen'); tree = s.render(); await flush(); assert.equal(calls, 1);
  const refresh = find(tree, n => n.type === 'button' && n.props.children === 'Actualizar evidencia');
  refresh.props.onClick(); s.render(); await flush(); s.render(); assert.equal(calls, 2); s.h.dispose();
});
test('sections mount on first visit and only the visible section is active; XAI starts unmounted', () => {
  const s = screen(); let tree = s.render();
  const panel = id => find(tree, n => typeof n.type === 'function' && n.type.name === 'AnalysisPanel' && n.props.id === id);
  assert.deepEqual(Array.from(panel('explicabilidad').props.visited), ['resumen']);
  assert.equal(panel('explicabilidad').props.children.props.active, false);
  find(tree, n => typeof n.type === 'function' && n.type.name === 'AnalysisSectionNav').props.onSelect('explicabilidad'); tree = s.render(); tree = s.render();
  assert.ok(panel('explicabilidad').props.visited.includes('explicabilidad'));
  assert.equal(panel('explicabilidad').props.children.props.active, true);
  assert.equal(panel('aprendizaje').props.children.props.active, false); s.h.dispose();
});
test('analysis panel renders nothing before its first visit and hides retained sections', () => {
  const { AnalysisPanel } = loader()('components/reports/AnalysisWorkspace.tsx');
  assert.equal(AnalysisPanel({ id: 'errores', section: 'resumen', visited: ['resumen'], children: 'contenido' }), null);
  const html = renderToStaticMarkup(React.createElement(AnalysisPanel, { id: 'errores', section: 'resumen', visited: ['resumen', 'errores'] }, 'contenido'));
  assert.match(html, /role="tabpanel"/); assert.match(html, /hidden=""/); assert.match(html, /Errores y consenso/);
});
test('evidence stays inline without the traceability drawer provider', () => {
  const { EvidenceButton } = loader()('components/reports/AnalysisWorkspace.tsx');
  const html = renderToStaticMarkup(React.createElement(EvidenceButton, { title: 'Protocolo' }, 'json'));
  assert.match(html, /<details><summary>Protocolo<\/summary>json<\/details>/);
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

test('evaluation navigation defaults to latest and retains historical identity without an invented attempt', async () => {
  const h = harness(); const applied = [];
  const evaluations = [1,2].map(n => ({evaluation_id: `e${n}`, training_run_id: 'a', checkpoint_artifact_id: `c${n}`, split: 'val', evaluation_role: 'training_validation_final', purpose: 'development', attempt_id: null, identity_id: null, created_at: '2026-10-16'}));
  const catalog = {training_run_id: 'a', evaluations, governance: {name:'Dataset', checks:[], counts:{}}, checkpoint:{}};
  let calls = 0;
  const load = loader({react:h.react, '../../services/api':{api:{getComparisonReport:async () => {calls++; return {data:[catalog]};}}}});
  const {EvaluationNavigation} = load('components/reports/ScientificReport.tsx');
  const props = {id:'a', datasource:'malaria', onChange: s => applied.push(s)};
  const render = () => h.render(() => EvaluationNavigation(props));
  render(); await flush(); let tree = render();
  assert.equal(applied[0].evaluation.evaluation_id, 'e1');
  assert.equal(applied[0].evaluation.source, 'evaluations');
  assert.equal(applied[0].evaluation.attempt_id, undefined);
  const menu = find(tree, n => typeof n.type === 'function' && n.type.name === 'SlotChoice' && n.props.label === 'TRAIN · VAL');
  assert.equal(menu.props.items.length, 2);
  menu.props.onPick('e2'); render();
  assert.equal(applied.at(-1).evaluation.evaluation_id, 'e2');
  assert.equal(applied.at(-1).checkpoint_artifact_id, 'c2'); assert.equal(calls,1);
  h.dispose();
});
test('changed attempt, split and checkpoint reach a fresh Preflight request', async () => {
  const bodies = []; const s = screen({ getComparisonPreflight: async (_ds, body) => { bodies.push(JSON.parse(JSON.stringify(body))); return fixture(); } });
  let tree = s.render(); await flush(); tree = s.render();
  for (const selection of [
    { training_run_id: 'a', evaluation: { source: 'assessment', identity_id: 'i', attempt_id: 'one' } },
    { training_run_id: 'a', evaluation: { source: 'assessment', identity_id: 'i', attempt_id: 'two' }, split: 'test' },
    { training_run_id: 'a', checkpoint_artifact_id: 'other' },
  ]) {
    s.props.selections = [selection, {training_run_id:'b'}];
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
  assert.equal((head.match(/scope="col"/g) ?? []).length, count + 1);
  data.selections.forEach((selection, index) => {
    assert.ok(head.includes(`RUN ${String.fromCharCode(65 + index)}`));
    assert.ok(!head.includes(selection.training_run_id));
    assert.ok(html.includes(selection.training_run_id));
  });
  assert.match(html, /random_seed: /);
  assert.match(html, /Sin diferencias/);
  assert.match(html, /Trazabilidad técnica/);
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
  nodes(tree).filter(node => node.props?.role === 'tab')[1].props.onClick();
  tree = h.render(() => ComparisonPython({ data }));
  let copy = find(tree, node => node.props?.label === 'Copiar código');
  assert.match(copy.props.text, /sgd/); assert.doesNotMatch(copy.props.text, /adam/);
  controls[0].props.onChange({ target: { value: 'reconstruction' } });
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
  assert.doesNotMatch(html, /<td>Diferencia experimental<\/td>/);
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

test('scientific modules query on first opening, reuse cache and defer changed selections while closed', async () => {
  const h = harness(); let calls = 0;
  const load = loader({react:h.react, '../../services/api': {api: {getComparisonReport: async () => {calls++; return {module:'curves', data:[], warnings:[]};}}}});
  const {LazyScientificModule} = load('components/reports/ScientificReport.tsx');
  const props = {title:'Curvas', module:'curves', datasource:'malaria', selections:[{training_run_id:'a'}], cache:load('utils/comparisonCache.ts').createComparisonCache(), children: () => null};
  const render = () => h.render(() => LazyScientificModule(props));
  let tree = render(); await flush(); assert.equal(calls,0);
  tree.props.onToggle({currentTarget:{open:true}}); render(); await flush(); tree=render(); assert.equal(calls,1);
  tree.props.onToggle({currentTarget:{open:false}}); render();
  tree.props.onToggle({currentTarget:{open:true}}); render(); await flush(); assert.equal(calls,1);
  tree.props.onToggle({currentTarget:{open:false}}); render();
  props.selections=[{training_run_id:'a',evaluation:{source:'evaluations',evaluation_id:'changed'}}];
  tree=render(); await flush(); assert.equal(calls,1);
  tree.props.onToggle({currentTarget:{open:true}}); render(); await flush(); assert.equal(calls,2); h.dispose();
});

test('one evaluation needs no pagination and absence is specific', async () => {
  const h = harness();
  const evaluation = {evaluation_id:'e', training_run_id:'a', split:'val', evaluation_role:'training_validation_final', purpose:'development', created_at:'2026-10-16'};
  const load = loader({react:h.react, '../../services/api':{api:{getComparisonReport:async () => ({data:[{evaluations:[evaluation],governance:{checks:[],counts:{}}}]})}}});
  const {EvaluationNavigation}=load('components/reports/ScientificReport.tsx');
  const props={id:'a', datasource:'malaria', onChange() {}};
  h.render(() => EvaluationNavigation(props)); await flush(); const tree=h.render(() => EvaluationNavigation(props));
  assert.equal(find(tree,n => typeof n.type === 'function' && n.type.name === 'SlotChoice' && n.props.label === 'TRAIN · VAL').props.items.length,1); h.dispose();
});

test('scalar rows have no expansion and groups retain requested defaults', () => {
  const h=harness(); const data=fixture(4);
  const {PreflightEvidence}=loader({react:h.react, '../../auth':{}, '../../services/api':{}, './AssessmentXAI':{}})('components/reports/ScientificPreflight.tsx');
  const tree=h.render(() => PreflightEvidence({data}));
  const groups=nodes(tree).filter(n => n.type === 'button' && Array.isArray(n.props.children) && ['Con diferencias','Comparables','Sin diferencias'].includes(n.props.children[0]));
  assert.deepEqual(groups.map(n=>n.props['aria-expanded']),[true,true,false]);
  assert.equal(find(tree,n=>n.type === 'button' && n.props.children?.includes('Versión del dataset')),undefined);
  assert.equal(find(tree,n=>n.props?.className === 'scc-expanded-row'),undefined);
  h.dispose();
});

test('Recharts curves retain missing values, distinguish TRAIN and VAL and reference selected epoch', () => {
  const h=harness(); const load=loader({react:h.react});
  const {TrainingCurves}=load('components/reports/ScientificReport.tsx');
  const data=[{training_run_id:'a',epochs:[{epoch:1,phase:'base',values:{loss:.5,val_loss:.6,accuracy:.8,val_accuracy:.7}},{epoch:3,phase:'base',values:{loss:.2,val_loss:.4}}],executed_epochs:2,final_epoch:3,max_epochs:10,checkpoint:{selected_epoch:1,logical_lineage:true},issues:[]}];
  let tree=h.render(()=>TrainingCurves({data}));
  find(tree,n=>n.type === 'select').props.onChange({target:{value:'0'}}); tree=h.render(()=>TrainingCurves({data}));
  assert.ok(nodes(tree).some(n=>n.props?.x === 1 && n.props?.label === 'Checkpoint RUN A'));
  const chart=find(tree,n=>Array.isArray(n.props?.data) && n.props.data[0]?.epoch === 1);
  assert.equal(chart.props.data[1].epoch,2); assert.equal(chart.props.data[1].r0_loss,undefined);
  let lines=nodes(tree).filter(n=>n.props?.connectNulls === false);
  assert.equal(lines.length,2); assert.ok(lines.some(n=>n.props.strokeDasharray)); assert.ok(lines.every(n=>n.props.isAnimationActive === false));
  assert.deepEqual(lines.map(n=>n.props.dataKey),['r0_loss','r0_val_loss']);
  find(tree,n=>n.type === 'button' && n.props.role === 'tab' && n.props.children === 'Accuracy').props.onClick(); tree=h.render(()=>TrainingCurves({data}));
  lines=nodes(tree).filter(n=>n.props?.connectNulls === false);
  assert.deepEqual(lines.map(n=>n.props.dataKey),['r0_accuracy','r0_val_accuracy']); h.dispose();
});

test('clinical metrics preserve nulls, confusion orientation and backend highlights', () => {
  const {ClinicalMetrics}=loader()('components/reports/ScientificReport.tsx');
  const data={highlights:[{label:'Mayor sensibilidad observada',value:.9,runs:[0]}],comparable:true,runs:[{training_run_id:'a',state:'available',issues:[],evaluation:{split:'val'},clinical:{sample_count:10,threshold_used:.5,tn:4,fp:1,fn:2,tp:3,metrics:{accuracy:{value:.7},roc_auc:{value:null}}}}]};
  const html=renderToStaticMarkup(React.createElement(ClinicalMetrics,{data}));
  for(const expected of ['TN 4','FP 1','FN 2','TP 3','Sin evidencia','Mayor sensibilidad observada','RUN A','VAL']) assert.ok(html.includes(expected),expected);
});

test('consensus shows backend results and a bounded sample page without client calculations', () => {
  const {ConsensusResults}=loader()('components/reports/ScientificReport.tsx');
  const data={state:'available',common_count:3,union_count:3,label_conflicts:0,coverage:[{population:3,common:3,missing:0,exclusive:0}],oracle:{numerator:2,denominator:3,ratio:2/3},all_wrong:1,distribution:{CONSENSUS_FN:1},agreement:[[3]],error_overlap:[[1]],samples:[{sample:'val/example.png',label:1,category:'CONSENSUS_FN',runs:[{score:.1,prediction:0,correct:false}]}],total:1};
  const html=renderToStaticMarkup(React.createElement(ConsensusResults,{data}));
  // One RUN: the model's own errors, no comparison indicators.
  for(const expected of ['Aciertos','Falsos negativos','example.png','Falso negativo','Error','N = 3 muestras evaluadas','Muestras · 1 resultados']) assert.ok(html.includes(expected),expected);
  assert.doesNotMatch(html,/Oracle descriptivo|Aciertos y errores exclusivos/);
  const pair=renderToStaticMarkup(React.createElement(ConsensusResults,{data:{...data,coverage:[...data.coverage,...data.coverage],agreement:[[3,2],[2,3]],error_overlap:[[1,0],[0,1]],exclusive_errors:[1,0],exclusive_correct:[0,1],samples:[{...data.samples[0],runs:[...data.samples[0].runs,...data.samples[0].runs]}]}}));
  for(const expected of ['Oracle descriptivo','no desplegable','Todos fallan · FN','N común = 3']) assert.ok(pair.includes(expected),expected);
});

test('section 01 equality is structural, position independent and excludes missing evidence', () => {
  const { compareValues } = loader()('utils/preflightPresentation.ts');
  const check = values => compareValues(values.map(value => value === undefined ? undefined : known(value)));
  for (const count of [2,3,4]) assert.equal(check(Array(count).fill(0)).group, 'Sin diferencias');
  for (const values of [[1,1,2,2], [1,2,2,2], [1,2,3,4], [1,2,1,3]]) assert.equal(check(values).group, 'Con diferencias');
  assert.equal(JSON.stringify(check([2,1,2,1]).matches), '["AC","BD","AC","BD"]');
  assert.equal(JSON.stringify(check([1,2,3,4]).matches), '[null,null,null,null]');
  assert.equal(check([{a:1,b:2},{b:2,a:1}]).group, 'Sin diferencias');
  assert.equal(check([[1,2],[2,1]]).group, 'Con diferencias');
  for (const values of [[null,null],[undefined,undefined],[1,undefined],[{},{}],[{a:null},{a:null}]]) assert.equal(check(values).group, 'Comparables');
  assert.equal(compareValues([{state:'query_error',error_ids:['sql']},known(1)]).group, 'Comparables');
});

test('projection retains SQL errors and conflicting sources rather than selecting arbitrary evidence', () => {
  const { projectField } = loader()('utils/preflightPresentation.ts');
  const data = fixture();
  data.evidence.push({...data.evidence[0], evidence_id:'conflict', value:known({architecture:'another'})});
  assert.equal(projectField(data,'A4','train:0','architecture').state,'unknown');
  data.evidence.push({...data.evidence[0], evidence_id:'failed',value:{state:'query_error',error_ids:['sql-1']}});
  assert.equal(projectField(data,'A4','train:0','architecture').state,'query_error');
});

for (const count of [2,3,4]) test(`section 01 shared table, dynamic counts and no redundant expansion for ${count} participants`, () => {
  const h = harness(); const data = fixture(count);
  const {PreflightEvidence} = loader({react:h.react,'../../auth':{},'../../services/api':{},'./AssessmentXAI':{}})('components/reports/ScientificPreflight.tsx');
  const render = () => h.render(() => PreflightEvidence({data}));
  let tree = render();
  const shared = find(tree,n => n.type === 'button' && n.props.children?.[0] === 'Sin diferencias');
  shared.props.onClick(); tree = render();
  const table = find(tree,n => n.type === 'table' && nodes(n).some(child => child.type === 'th' && child.props.children === 'Valor compartido'));
  assert.equal(nodes(table).filter(n=>n.type === 'th' && n.props.scope === 'col').length,3);
  assert.ok(nodes(table).some(n => n.props?.className === 'scc-equal' && n.props.children === Array.from({length:count},(_,i)=>String.fromCharCode(65+i)).join('=')));
  assert.equal(find(table,n => n.type === 'button' && n.props.children?.includes('Arquitectura')),undefined);
  assert.equal(find(tree,n=>n.props?.className === 'scc-expanded-row'),undefined);
  const before = find(tree,n=>n.type === 'button' && n.props.children?.[0] === 'Con diferencias').props.children[2];
  data.evidence[0].value.value.architecture = 'changed'; tree = render();
  assert.equal(find(tree,n=>n.type === 'button' && n.props.children?.[0] === 'Con diferencias').props.children[2],before+1);
  h.dispose();
});

test('concrete optimizer/checkpoint/evaluation evidence and consolidated warnings preserve traceability', () => {
  const data = fixture(4);
  data.selections.forEach((selection,i) => {
    data.evidence[i].value.value.optimizer_parameters = {beta_1:0.9,epsilon:1e-7};
    selection.checkpoint = known(`${i}2345678-1234-1234-1234-123456789012`);
    selection.evaluation = known({source:'evaluations',evaluation_id:`${i}aaaaaaa-1234-1234-1234-123456789012`,source_assessment_attempt_id:null});
    data.evidence.push({...data.evidence[i], evidence_id:`checkpoint-${i}`, source:'A5',value:known({selected_epoch:i+1,phase:'base',checksum_registered:'a'.repeat(63)+i})});
    data.evidence.push({...data.evidence[i], evidence_id:`evaluation-${i}`, source:'A6',value:known({evaluation_role:'training_validation_final',protocol_hash:i%2 ? 'protocol-b' : 'protocol-a'})});
    data.dimensions[5].findings.push({reason_id:`reason-${i}`,code:'DEVELOPMENT_VALIDATION',kind:'warning',message:'VALIDATION final de desarrollo; no equivale a TEST independiente.',condition:'historical',affected_selection_ids:[selection.selection_id],evidence_ids:[`evaluation-${i}`]});
  });
  const {PreflightEvidence} = loader({'../../auth':{},'../../services/api':{},'./AssessmentXAI':{}})('components/reports/ScientificPreflight.tsx');
  const html = renderToStaticMarkup(React.createElement(PreflightEvidence,{data}));
  assert.match(html,/época/); assert.match(html,/phase/); assert.doesNotMatch(html,/Valor completo/); assert.match(html,/Copiar identificador/);
  assert.match(html,/afecta a RUN A, RUN B, RUN C, RUN D/);
  assert.equal((html.match(/VALIDATION final de desarrollo;/g)||[]).length,1); // consolidated original cause in technical trace
  for (let i=0;i<4;i++) { assert.ok(html.includes(`reason-${i}`)); assert.ok(html.includes(`evaluation-${i}`)); }
  assert.match(html,/Detalle técnico y trazabilidad/);
  const matrix=html.split('<summary>Detalle técnico y trazabilidad</summary>')[0];
  assert.doesNotMatch(matrix, /A5 · Checkpoint atribuido|A5 · Checksum registrado|A6 · Evaluación e intento/);
  for(let i=0;i<4;i++) assert.ok(html.includes(`${i}aaaaaaa-1234-1234-1234-123456789012`));
  assert.doesNotMatch(html,/<td>Identidad registrada|<td>Configuración persistida/);
});

for (const count of [2,3,4]) test(`A6 consolidates structured fields and provenance for ${count} RUN`, () => {
  const h = harness(); const data = fixture(count);
  data.selections.forEach((selection,i) => {
    selection.evaluation = known({source:'evaluations',evaluation_id:`evaluation-${i}`,source_assessment_attempt_id:null});
    data.evidence.push({...data.evidence[i], source:'A6', evidence_id:`eval-ref-${i}`, value:known({evaluation_role:'training_validation_final',purpose:'development',threshold:0.5,sample_count:2693,metric_definition:'binary_nullable_v2',protocol:'Persisted protocol',decision:'Persisted decision',protocol_hash:i===count-1?'different':'shared'})});
    data.evidence.push({...data.evidence[i], source:'A2', evidence_id:`split-ref-${i}`, value:known({campaign_id:`campaign-${i}`,campaign_snapshot:{counts:{train:10,val:2}}})});
  });
  const {PreflightEvidence} = loader({react:h.react,'../../auth':{},'../../services/api':{},'./AssessmentXAI':{}})('components/reports/ScientificPreflight.tsx');
  const render = () => h.render(() => PreflightEvidence({data}));
  let tree = render();
  const toggle = find(tree,n=>n.type === 'button' && n.props.children?.includes('Protocolo y regla de decisión'));
  assert.ok(toggle); toggle.props.onClick(); tree=render();
  let row=find(tree,n=>n.props?.className === 'scc-expanded-row');
  assert.equal(find(row,n=>n.type === 'td').props.colSpan,count+2);
  assert.equal(nodes(row).filter(n=>n.type?.name === 'EvidenceCell').length,0);
  let html=renderToStaticMarkup(row);
  assert.match(html, /Persisted protocol/); assert.match(html, /Persisted decision/);
  assert.doesNotMatch(html, /evaluation_id|checkpoint_artifact_id|protocol_hash|sample_count/);
  const full = renderToStaticMarkup(tree);
  for (let i=0;i<count;i++) assert.ok(full.includes(`evaluation-${i}`));
  find(tree,n=>n.type === 'button' && n.props.children?.[0]==='Sin diferencias').props.onClick();tree=render();
  const cards = find(tree,n=>n.type?.name === 'PartitionCards');
  html=renderToStaticMarkup(React.createElement(cards.type,cards.props));
  assert.ok(!html.includes('campaign-0'));assert.ok(html.includes('procedencia'));
  assert.ok(full.includes('campaign-0')); assert.match(html, /Consultar identificadores y fuentes/);
  assert.ok(!html.includes('campaign_snapshot'));
  data.selections[0]={...data.selections[0],evaluation:known({evaluation_id:'new-selection'})}; tree=render();
  assert.equal(find(tree,n=>n.props?.className === 'scc-expanded-row'),undefined);
  h.dispose();
});

test('equality partitions carry semantic aliases and distinguish type, absence and order', () => {
  const {compareValues}=loader()('utils/preflightPresentation.ts');
  for (const [values,expected] of [[[1,1,2,2],['AB','AB','CD','CD']],[[1,2,1,2],['AC','BD','AC','BD']],[[1,1,1,2],['ABC','ABC','ABC',null]],[[1,'1',null,null],[null,null,null,null]]]) {
    assert.deepEqual(JSON.parse(JSON.stringify(compareValues(values.map(known)).matches)),expected);
  }
});

test('evidence navigation opens every ancestor and focuses the exact target', () => {
  const {openEvidenceTarget}=loader()('utils/preflightPresentation.ts');
  const outer={tagName:'DETAILS',open:false,parentElement:null};
  const inner={tagName:'DETAILS',open:false,parentElement:outer};
  const calls=[]; const target={tagName:'DIV',parentElement:inner,scrollIntoView:()=>calls.push('scroll'),focus:()=>calls.push('focus')};
  openEvidenceTarget(target); assert.equal(outer.open,true); assert.equal(inner.open,true); assert.deepEqual(calls,['scroll','focus']);
  openEvidenceTarget(null);
});

test('availability matrix preserves backend verdicts, individual errors and missing evidence', () => {
  const data=fixture(3);
  data.analyses[0].individual_data[0].availability=known(false);
  data.analyses[0].individual_data[1].availability={state:'query_error',error_ids:['failure']};
  data.analyses[0].individual_data.pop();
  const {PreflightEvidence}=loader({'../../auth':{},'../../services/api':{},'./AssessmentXAI':{}})('components/reports/ScientificPreflight.tsx');
  const html=renderToStaticMarkup(React.createElement(PreflightEvidence,{data}));
  const matrix=html.slice(html.indexOf('<caption>Diagnóstico por análisis'));
  assert.equal((matrix.match(/<th scope="row">/g)||[]).length,8);
  assert.match(matrix,/ERROR_DE_CONSULTA.*failure/); assert.match(matrix,/Sin evidencia/);assert.match(matrix,/Comparable con advertencias/);
  assert.ok(!matrix.includes('train-0'));
});

test('technical registry preserves exact references and RUN associations after matrix links are removed', () => {
  const data=fixture(2);
  data.evidence[0].evidence_id='arbitrary:reference/a';
  data.evidence[1].evidence_id='arbitrary:reference/b';
  const {PreflightEvidence}=loader({'../../auth':{},'../../services/api':{},'./AssessmentXAI':{}})('components/reports/ScientificPreflight.tsx');
  const html=renderToStaticMarkup(React.createElement(PreflightEvidence,{data}));
  const [matrix, trace] = html.split('<summary>Detalle técnico y trazabilidad</summary>');
  assert.doesNotMatch(matrix, /Evidencia: RUN|scc-dimension-summary|[0-9] RUN seleccionados/);
  for (let i=0;i<2;i++) {
    assert.ok(trace.includes(`scc-evidence-${encodeURIComponent(data.selections[i].selection_id)}-${encodeURIComponent(data.evidence[i].evidence_id)}`));
    assert.ok(trace.includes(data.evidence[i].operation));
  }
});

const presentation = () => loader({'../../auth':{},'../../services/api':{},'./AssessmentXAI':{}})('components/reports/ScientificPreflight.tsx');
const plain = html => html.replace(/<[^>]*>/g, '');

test('methodological differences use real projected values for every participant; missing configuration stays in A4', () => {
  const data = fixture(4);
  const fields = {random_seed:[11,47,8,0], max_epochs:[40,3,20,8], l2:[.001,.0001,0,.1]};
  const findings = Object.keys(fields).map(field => ({reason_id:field, code:`CONFIGURATION_DIFFERENCE_${field.toUpperCase()}`, kind:'difference', message:'generic',condition:'actual',affected_selection_ids:data.selections.map(s=>s.selection_id),evidence_ids:['original']}));
  findings.push({reason_id:'missing',code:'CONFIGURATION_INCOMPLETE',kind:'missing',message:'Configuración no acreditada: internal_preprocessing',condition:'missing',affected_selection_ids:['train:0'],evidence_ids:['original']});
  data.dimensions[3].findings = findings;
  data.summary.warning_reason_ids = findings.map(f=>f.reason_id);
  data.evidence.forEach((ref,i)=>Object.entries(fields).forEach(([field,values])=>ref.value.value[field]=values[i]));
  const {MethodologicalWarnings,PreflightEvidence}=presentation();
  const html = renderToStaticMarkup(React.createElement(MethodologicalWarnings,{data,findings}));
  for (const [label, values] of [['Semilla',fields.random_seed],['Épocas máximas',fields.max_epochs],['Regularización L2',fields.l2]]) {
    assert.ok(plain(html).includes(label+values.map((value,i)=>` · RUN ${String.fromCharCode(65+i)}: ${value}`).join('')));
  }
  assert.doesNotMatch(html,/Configuración experimental incompleta|diferencia experimental|Solamente existe/);
  assert.match(html,/incluidas las independientes/);
  const detail=renderToStaticMarkup(React.createElement(PreflightEvidence,{data}));
  assert.match(detail,/Preprocesamiento interno/); assert.match(detail,/internal_preprocessing/);
});

for (const state of ['COMPARABLE','COMPARABLE_CON_ADVERTENCIAS','NO_COMPARABLE','EVIDENCIA_INSUFICIENTE','ERROR_DE_CONSULTA']) test(`methodological analyses preserve accessible state ${state}`,()=>{
  const data=fixture();
  [...data.dimensions,...data.analyses].forEach(item=>item.verdict={evaluation_status:state==='ERROR_DE_CONSULTA'?'not_evaluated':'evaluated',scientific_state:state==='ERROR_DE_CONSULTA'?null:state,error_ids:[]});
  const html=renderToStaticMarkup(React.createElement(presentation().MethodologicalWarnings,{data,findings:[]}));
  assert.ok(html.includes(`data-state="${state}"`)); assert.match(html,/<details[^>]*><summary>/);
});

test('structured values preserve nulls, false, zero, empty objects, long strings and collapsed list entries',()=>{
  const {CompactValue}=presentation();
  const value={missing:null, zero:0, disabled:false,empty:'',object:{},array:Array.from({length:12},(_,i)=>`entry-${i}`),long:'x'.repeat(400)};
  const html=renderToStaticMarkup(React.createElement(CompactValue,{value}));
  for(const text of ['missing:', 'Sin evidencia','zero:','disabled:','No','sin entradas','Más datos','entry-11','x'.repeat(400)]) assert.ok(html.includes(text),text);
  assert.doesNotMatch(html,/style=|cursor|Valor completo/);
});

test('compact identifier copies the complete original with accessible icon, success and failure fallback',async()=>{
  const id='338136db-a207-47fc-bbf3-d17ce85c0dc2';
  const html=renderToStaticMarkup(React.createElement(presentation().CompactValue,{value:id}));
  assert.ok(html.includes('338136db…5c0dc2')); assert.ok(html.includes(`title="${id}"`));
  assert.match(html,/aria-label="Copiar identificador"/);assert.match(html,/<svg[^>]*aria-hidden="true"/);assert.doesNotMatch(html,/Valor completo/);
  const h=harness();let copied;let fail=false;
  const {CopyText}=loader({react:h.react},{navigator:{clipboard:{writeText:async text=>{if(fail)throw Error();copied=text;}}}})('components/reports/ComparisonPython.tsx');
  const props={text:id,label:'Copiar identificador',iconOnly:true};
  let tree=h.render(()=>CopyText(props));await find(tree,n=>n.type==='button').props.onClick();
  assert.equal(copied,id);tree=h.render(()=>CopyText(props));assert.equal(find(tree,n=>n.props?.role==='status').props.children,'Copiado');
  fail=true;await find(tree,n=>n.type==='button').props.onClick();tree=h.render(()=>CopyText(props));
  assert.equal(find(tree,n=>n.type==='code').props.children,id);h.dispose();
});

function governedFixture() {
  const data=fixture();
  data.selections.forEach((s,i)=>{
    s.dataset_version_id=known('11111111-2222-3333-4444-555555555555');
    data.evidence.push({...data.evidence[i],source:'A1',evidence_id:`dataset-${i}`,value:known({name:'Shared governed dataset',status:'ready',random_seed:11,grouping_strategy:'patient',split_algorithm:'stratified',source_record_count:100})});
    data.evidence.push({...data.evidence[i],source:'A2',evidence_id:`split-${i}`,value:known({counts:{train:70,val:20,test:10},checks:[{check_name:'identity',status:'PASS',observed_value:0,expected_value:0}],consumed_images:0})});
  });
  return data;
}
test('partition cards show common data once, structured checks and explicit dataset/split differences',()=>{
  const {PartitionCards}=presentation();const data=governedFixture();
  let html=renderToStaticMarkup(React.createElement(PartitionCards,{data}));
  assert.equal((html.match(/Shared governed dataset/g)||[]).length,1);
  for(const label of ['Dataset','Partición','Distribución','Materialización','Integridad','Trazabilidad','TRAIN','VAL','TEST','PASS','Número de verificaciones']) assert.ok(html.includes(label));
  assert.match(html,/no acredita por sí sola el consumo/);assert.doesNotMatch(html,/\{"counts"/);
  data.selections[1].dataset_version_id=known('different-dataset');data.selections[1].split=known('test');
  html=renderToStaticMarkup(React.createElement(PartitionCards,{data}));
  assert.match(html,/Diferencias y evidencia parcial por RUN/);assert.match(html,/RUN A/);assert.match(html,/RUN B/);assert.match(html,/different-dataset/);
});
test('missing and failed integrity checks never become PASS',()=>{
  const data=fixture();
  const {PartitionCards}=presentation();let html=renderToStaticMarkup(React.createElement(PartitionCards,{data}));
  assert.doesNotMatch(html,/PASS/);assert.match(html,/Sin evidencia/);
  data.evidence.push({...data.evidence[0],source:'A2',value:{state:'query_error',error_ids:['sql-error']}});
  html=renderToStaticMarkup(React.createElement(PartitionCards,{data}));assert.match(html,/ERROR_DE_CONSULTA/);assert.match(html,/sql-error/);assert.doesNotMatch(html,/PASS/);
});
test('methodological summary retains dynamic references and refresh without duplicated navigation or SQL date',async()=>{
  const data=fixture();data.consistency.limitations=['El snapshot SQL no verifica bytes de archivos.'];
  const s=screen({getComparisonPreflight:async()=>data});s.render();await flush();const tree=s.render();
  const summary=find(tree,n=>n.props?.['aria-label']==='Resumen metodológico');
  const html=renderToStaticMarkup(summary);
  assert.match(html,/2 referencias/);assert.match(html,/2 TRAIN participantes/);assert.match(html,/Actualizar evidencia/);
  assert.doesNotMatch(html,/Consulta:|snapshot SQL|¿Qué estamos comparando\?/);s.h.dispose();
});
test('structured value CSS is scoped, tokenized, responsive and respects reduced motion',()=>{
  const css=readFileSync(resolve(root,'styles/report-components.css'),'utf8').split('/* SCC-UI-PREFLIGHT.2:')[1];
  assert.match(css,/repeat\(auto-fit, minmax\(min\(100%, 280px\), 1fr\)\)/);
  assert.match(css,/prefers-reduced-motion: reduce/);assert.doesNotMatch(css,/#[a-f\d]{3,8}\b|cursor:\s*pointer/);
  assert.doesNotMatch(readFileSync(resolve(root,'styles.css'),'utf8'),/^\.scc-composite-value/m);
  for(const selector of ['.scc-key','.scc-val','li:hover'])assert.ok(css.includes(selector));
});

test('SCC synthesis preserves mixed scopes and updates with selected evidence without global precedence', () => {
  const {MethodologicalSynthesis, MethodologicalWarnings} = presentation();
  const data = fixture();
  data.analyses[0].verdict.scientific_state = 'COMPARABLE';
  data.analyses[1].verdict = {...data.analyses[1].verdict, scientific_state: 'NO_COMPARABLE'};
  const before = JSON.stringify(data);
  let html = renderToStaticMarkup(React.createElement(MethodologicalSynthesis, {data}));
  assert.match(plain(html), /Comparable: Curvas de aprendizaje/);
  assert.match(plain(html), /No comparable: Métricas VAL\/TEST/);
  assert.match(plain(html), /Evidencia insuficiente: Consenso/);
  const warnings = renderToStaticMarkup(React.createElement(MethodologicalWarnings, {data, findings: []}));
  assert.doesNotMatch(warnings.match(/<summary>.*?<\/summary>/)?.[0] ?? '', /data-state/);
  assert.equal(JSON.stringify(data), before);
  data.analyses = [data.analyses[0]];
  html = renderToStaticMarkup(React.createElement(MethodologicalSynthesis, {data}));
  assert.doesNotMatch(html, /No comparable|Métricas VAL/);
});

test('missing inventory merges identical causes per RUN, preserves errors, non-applicability and evidence links', () => {
  const {missingEvidence} = loader()('utils/preflightPresentation.ts');
  const data = fixture();
  data.technical_errors = [{error_id:'err',message:'Consulta interrumpida',operation:'read',scope_ids:['scope'],selection_ids:['train:0'],state:'ERROR_DE_CONSULTA'}];
  const fields = [
    {label:'A',values:[missing, known(0)]},
    {label:'B',values:[missing, known(false)]},
    {label:'C',values:[{state:'query_error',error_ids:['err']}, {state:'not_applicable',reason:'No aplica a esta fuente',evidence_ids:[]}]},
    {label:'SHA físico',values:[{state:'not_checked',reason:'No comprobado',evidence_ids:[]}, known('registered')]},
  ];
  const before=JSON.stringify(data);
  const entries=missingEvidence(data,fields);
  const absent=entries.find(entry=>entry.cause==='No registrado');
  assert.deepEqual(Array.from(absent.evidence),['A','B']);
  assert.deepEqual(Array.from(absent.selectionIds),['train:0']);
  assert.equal(entries.filter(entry=>entry.state==='Error de consulta').length,1);
  assert.ok(entries.find(entry=>entry.state==='No aplicable'));
  assert.ok(entries.find(entry=>entry.state==='No verificado'));
  assert.equal(JSON.stringify(data),before);
  const html=renderToStaticMarkup(React.createElement(presentation().EvidenceInventory,{data,fields}));
  assert.match(html,/Consulta interrumpida/);assert.match(html,/Métricas VAL/);
  assert.doesNotMatch(html,/No ejecutado|RUN @/);
});

test('partial protocol has no empty expansion; identifiers remain consultable and groups retain initial state', () => {
  const h=harness();
  const {PreflightEvidence}=loader({react:h.react,'../../auth':{},'../../services/api':{},'./AssessmentXAI':{}})('components/reports/ScientificPreflight.tsx');
  for (const count of [1,2,7]) {
    h.reset();
    const tree=h.render(()=>PreflightEvidence({data:fixture(count)}));
    assert.equal(find(tree,n=>n.type==='button' && n.props.children?.includes('Protocolo y regla de decisión')),undefined);
    for(const group of ['Con diferencias','Comparables','Sin diferencias']) {
      const button=find(tree,n=>n.type==='button' && n.props.children?.[0]===group);
      assert.equal(button.props['aria-expanded'],group!=='Sin diferencias');
      assert.ok(button.props['aria-controls']);
    }
  }
  const html=renderToStaticMarkup(React.createElement(presentation().CompactValue,{value:'12345678-1234-1234-1234-123456789012'}));
  assert.match(html,/title="12345678-1234-1234-1234-123456789012"/);
  assert.match(html,/aria-label="12345678-1234-1234-1234-123456789012"/);
  assert.match(html,/12345678…789012/);
  assert.match(html,/aria-label="Copiar identificador"/);
  assert.doesNotMatch(html,/<details>|Consultar identificador/);
  h.dispose();
});

test('CompactValue displays every populated entry and collapses only normalized empty values', () => {
  const {CompactValue}=presentation();
  const value={nil:null, absent:undefined, blank:'', spaces:'  ', unknown:' SIN EVIDENCIA ', na:' N/A ', zero:0, disabled:false,
    ...Object.fromEntries(Array.from({length:8},(_,i)=>[`field${i}`,`value${i}`]))};
  const html=renderToStaticMarkup(React.createElement(CompactValue,{value}));
  const [visible,collapsed]=html.split('<details>');
  for(const key of ['zero','disabled',...Array.from({length:8},(_,i)=>`field${i}`)]) {
    assert.ok(visible.includes(`${key}:`)); assert.ok(!collapsed.includes(`${key}:`));
  }
  for(const key of ['nil','absent','blank','spaces','unknown','na']) {
    assert.ok(!visible.includes(`${key}:`)); assert.ok(collapsed.includes(`${key}:`));
  }
  assert.match(collapsed,/<summary>Más datos \(6\)<\/summary>/);
  assert.doesNotMatch(collapsed,/<details[^>]*open/);
  assert.match(collapsed,/absent:.*Sin evidencia/);
});

test('CompactValue applies empty grouping recursively and avoids empty accordions', () => {
  const {CompactValue}=presentation();
  const render=value=>renderToStaticMarkup(React.createElement(CompactValue,{value}));
  assert.doesNotMatch(render({a:0,b:false,c:'present'}),/<details>/);
  assert.match(render({only:null}),/^<div><details><summary>Más datos \(1\)/);
  assert.match(render({nested:{available:1,missing:null}}),/available:.*<details><summary>Más datos \(1\).*missing:/);
  const array=render([null,0,false,' N/A ','available']);
  assert.match(array, /Más datos \(2\)/);
  assert.match(array.split('<details>')[0], /available/);
  assert.doesNotMatch(render(Array.from({length:12},(_,i)=>i)), /Más datos/);
});

const integrityNames = ['assignment_count','class_presence_test','class_presence_train','class_presence_val',
  'duplicate_cross_split_overlap','identity_conflicts','identity_coverage','patient_train_test_overlap',
  'patient_train_val_overlap','patient_val_test_overlap','source_record_count','split_completeness'];
function integrityFixture(checks) {
  const data=governedFixture();
  for(const ref of data.evidence.filter(ref=>ref.source==='A2')) ref.value.value.checks=checks;
  return data;
}
const integrityComponent = () => loader()('components/reports/DatasetIntegrity.tsx').DatasetIntegrity;

test('dataset integrity: twelve persisted PASS checks reconcile, preserve order and use one shared closed table', () => {
  const checks=integrityNames.map(check_name=>({check_name,status:'PASS',observed_value:27558,expected_value:27558}));
  const data=integrityFixture(checks);
  const before=JSON.stringify(data);
  const html=renderToStaticMarkup(React.createElement(integrityComponent(),{data}));
  assert.match(html,/12\/12 PASS/);
  assert.match(html,/<dt>Aprobadas<\/dt><dd>12<\/dd>/);
  for(const label of ['Fallidas','Sin evidencia']) assert.ok(html.includes(`<dt>${label}</dt><dd>0</dd>`));
  assert.match(html,/<details class="ds-accordion"><summary>Comprobaciones registradas/);
  assert.doesNotMatch(html,/<details[^>]*open/);
  assert.match(html,/12 controles/);
  assert.equal((html.match(/<th scope="row">/g)||[]).length,12);
  assert.equal((html.match(/scope="col"/g)||[]).length,4);
  assert.equal((html.match(/27\.558/g)||[]).length,24);
  assert.match(html,/RUN A, RUN B/);
  let previous=-1;
  for(const name of integrityNames) {const position=html.indexOf(`title="${name}"`);assert.ok(position>previous);previous=position;}
  assert.match(html,/Asignaciones completas/);
  assert.match(html,/title="class_presence_train"/);
  assert.match(html,/aria-label="Clases presentes en TRAIN · class_presence_train"/);
  assert.doesNotMatch(html,/Identificador técnico/);
  assert.doesNotMatch(html.match(/<tbody>([\s\S]*?)<\/tbody>/)?.[1] ?? '', /<details>/);
  assert.equal(JSON.stringify(data),before);
});

test('dataset integrity: failed, missing, WARNING and unknown states reconcile without inferring PASS from equal values', () => {
  const states=['PASS','FAIL',null,undefined,'WARNING','FUTURE_STATUS'];
  const checks=states.map((status,index)=>({check_name:`custom_${index}`,status,observed_value:0,expected_value:0}));
  const html=renderToStaticMarkup(React.createElement(integrityComponent(),{data:integrityFixture(checks)}));
  assert.match(html,/1\/6 PASS/);
  for(const [label,total] of [['Aprobadas',1],['Fallidas',1],['Sin evidencia',2],['Advertencias',1],['No clasificados',1]]) assert.ok(html.includes(`<dt>${label}</dt><dd>${total}</dd>`));
  assert.match(html,/FUTURE_STATUS/);assert.match(html,/custom_5/);
  assert.doesNotMatch(html,/Las 6 comprobaciones registradas del split tienen estado PASS/);
});

test('dataset integrity: values keep zero, null, absent fields, booleans and complete structured evidence', () => {
  const checks=[
    {check_name:'identity_conflicts',status:'PASS',observed_value:0,expected_value:null},
    {check_name:'class_presence_val',status:'PASS',observed_value:'both',expected_value:'both'},
    {check_name:'split_completeness',status:'WARNING',observed_value:'complete',expected_value:'complete'},
    {check_name:'unknown_original_name',status:'FUTURE',observed_value:'both',expected_value:false},
    {check_name:'partial',observed_value:{nested:[0,null,'kept']},expected_value:['x','y'],extra:'original-extra'},
    null,
  ];
  const html=renderToStaticMarkup(React.createElement(integrityComponent(),{data:integrityFixture(checks)}));
  for(const text of ['>0<','Nulo','Campo ausente','Ambas','Completo','>both<','>false<','Objeto · 1 campos','Arreglo · 2 elementos','kept','original-extra']) assert.ok(html.includes(text),text);
  assert.match(html,/title="both"/);assert.match(html,/title="complete"/);
  assert.match(html,/unknown_original_name/);
  assert.equal((html.match(/<th scope="row">/g)||[]).length,6);
});

test('dataset integrity: empty, partial and query-error responses do not fabricate successful checks', () => {
  const Component=integrityComponent();
  const render=data=>renderToStaticMarkup(React.createElement(Component,{data}));
  let html=render(integrityFixture([]));
  assert.match(html,/0\/0 PASS/);assert.match(html,/No hay comprobaciones registradas/);
  assert.doesNotMatch(html,/<th scope="row">/);
  html=render(integrityFixture([{check_name:'partial'}]));
  assert.match(html,/0\/1 PASS/);assert.match(html,/<dt>Sin evidencia<\/dt><dd>1<\/dd>/);
  const data=integrityFixture([]);
  data.evidence.filter(ref=>ref.source==='A2').forEach(ref=>ref.value={state:'query_error',error_ids:['query-error']});
  html=render(data);assert.match(html,/ERROR_DE_CONSULTA.*query-error/);assert.doesNotMatch(html,/0\/0 PASS/);
  data.evidence=data.evidence.filter(ref=>ref.source!=='A2');
  assert.match(render(data),/Sin evidencia de comprobaciones/);
});

test('dataset integrity: different dataset identities or checks keep separate scopes; opening uses native details without queries', () => {
  const Component=integrityComponent();
  const data=integrityFixture([{check_name:'identity_conflicts',status:'PASS',observed_value:0,expected_value:0}]);
  data.selections[1].dataset_version_id=known('another-dataset');
  let tree=Component({data});
  let html=renderToStaticMarkup(tree);
  assert.equal((html.match(/1\/1 PASS/g)||[]).length,2);
  data.selections[1].dataset_version_id=data.selections[0].dataset_version_id;
  data.evidence.find(ref=>ref.source==='A2' && ref.selection_ids.includes('train:1')).value.value.checks=[{check_name:'other',status:'FAIL'}];
  tree=Component({data});html=renderToStaticMarkup(tree);
  assert.match(html,/1\/1 PASS/);assert.match(html,/0\/1 PASS/);
  const checksTree=nodes(tree).find(node=>node.type?.name==='Checks');
  const renderedChecks=checksTree.type(checksTree.props);
  const accordion=find(renderedChecks,node=>node.type==='details' && node.props.className==='ds-accordion');
  assert.equal(accordion.props.open,undefined);
  assert.equal(accordion.props.onToggle,undefined);
  assert.equal(accordion.props.onClick,undefined);
  assert.match(renderToStaticMarkup(React.cloneElement(accordion,{open:true})),/<th scope="row">/);
  assert.equal(renderToStaticMarkup(tree),html);
});

test('dataset check labels retain unknown technical identifiers, including object property names', () => {
  const {datasetCheckLabel}=loader()('utils/datasetChecks.ts');
  for(const name of integrityNames) assert.notEqual(datasetCheckLabel(name),name);
  for(const name of ['new_unrecognized_check','__proto__','toString']) assert.equal(datasetCheckLabel(name),name);
});

test('consenso usa un timeout mayor que el valor por defecto de 15 s', () => {
  const report = readFileSync(new URL('../src/components/reports/ScientificReport.tsx', import.meta.url), 'utf8');
  const apiSource = readFileSync(new URL('../src/services/api.ts', import.meta.url), 'utf8');
  assert.match(report, /MODULE_TIMEOUT_MS: Partial<Record<ReportModule, number>> = \{consensus: 60000, questions: 60000\}/);
  assert.match(report, /api\.getComparisonReport<T>\(datasource, \{module, selections, \.\.\.params\}, MODULE_TIMEOUT_MS\[module\]\)/);
  assert.match(apiSource, /getComparisonReport<T>\(datasource: string, body: ReportRequest, timeoutMs\?: number\)/);
  assert.match(apiSource, /body: JSON\.stringify\(body\) \},\s*timeoutMs,/);
});

test('analysis summaries split base and fine-tuning epochs and find the most complementary pair', () => {
  const { curveSummary, consensusSummary, metricRange } = loader()('utils/analysisSummaries.ts');
  const run = {training_run_id:'a', executed_epochs:6, final_epoch:6, max_epochs:3, fine_tune_epochs:3, issues:[],
    epochs:[1,2,3].map(epoch=>({epoch, phase:'base', values:{loss:.5, val_loss:.7}})).concat([4,5,6].map(epoch=>({epoch, phase:'fine_tuning', values:{loss:.2, val_loss:.6}}))),
    checkpoint:{selected_epoch:2, phase:'base', logical_lineage:true}};
  const summary = curveSummary(run);
  assert.equal(summary.baseExecuted,3); assert.equal(summary.fineExecuted,3); assert.equal(summary.configuredTotal,6);
  assert.equal(summary.baseCheckpointAfterFineTuning,true); assert.ok(Math.abs(summary.gap-.2) < 1e-9);
  const consensus = consensusSummary({common_count:10, agreement:[[10,8,9],[8,10,7],[9,7,10]], error_overlap:[[3,2,1],[2,4,2],[1,2,3]]});
  assert.deepEqual({...consensus.fewestSharedErrors}, {i:0,j:2,count:1});
  assert.deepEqual({...consensus.agreementRange}, {min:.7,max:.9});
  assert.deepEqual({...metricRange([{state:'available',clinical:{metrics:{recall:{value:.9}}}},{state:'missing'},{state:'available',clinical:{metrics:{recall:{value:.95}}}}],'recall')}, {min:.9,max:.95});
});

test('lineage slots apply the analysis protocol, fall back when a RUN lacks it and group EXPLAIN by method', () => {
  const { groupEvaluations, effectiveSlot, groupExplanations } = loader()('utils/lineageSlots.ts');
  const choice = (split, role, id) => ({evaluation_id: role === 'independent_evaluate' ? null : id, attempt_id: role === 'independent_evaluate' ? id : null, split, evaluation_role: role, created_at: '2026-10-21'});
  const groups = groupEvaluations([choice('test','independent_evaluate','t1'), choice('val','independent_evaluate','v1'), choice('val','training_validation_final','h1'), choice('val','calibration_default','h2')]);
  assert.equal(groups.test.map(c => c.attempt_id).join(), ['t1'].join());
  assert.equal(groups.val.map(c => c.attempt_id).join(), ['v1'].join());
  assert.equal(groups.train.map(c => c.evaluation_id).join(), ['h1','h2'].join());
  assert.equal(effectiveSlot(groups, 'test', null), 'test');
  assert.equal(effectiveSlot(groups, 'test', 'train'), 'train');
  const noTest = groupEvaluations([choice('val','independent_evaluate','v1')]);
  assert.equal(effectiveSlot(noTest, 'test', null), 'val');
  assert.equal(effectiveSlot(groupEvaluations([]), 'test', null), null);
  const explains = groupExplanations([{attempt_id:'old', method:'gradcam', started_at:'2026-10-20'}, {attempt_id:'new', method:'Grad-CAM', started_at:'2026-10-21'}, {attempt_id:'s', method:'shap', started_at:'2026-10-21'}]);
  assert.equal(explains.gradcam.map(c => c.attempt_id).join(), ['new','old'].join());
  assert.equal(explains.shap.map(c => c.attempt_id).join(), ['s'].join());
});

test('per-cell EXPLAIN are always included and population EXPLAIN stay selectable', () => {
  const { splitExplanations } = loader()('utils/lineageSlots.ts');
  const parts = splitExplanations([{attempt_id:'pop', result_count:2693}, {attempt_id:'c1', result_count:1}, {attempt_id:'c2', result_count:1}]);
  assert.equal(parts.population.map(c => c.attempt_id).join(), 'pop');
  assert.equal(parts.cells.map(c => c.attempt_id).join(), 'c1,c2');
});

test('consensus sample rows open the cell in Explicabilidad and explain why TEST cells cannot', () => {
  const {ConsensusResults}=loader()('components/reports/ScientificReport.tsx');
  const data={state:'available',common_count:1,union_count:1,label_conflicts:0,coverage:[{population:1,common:1,missing:0,exclusive:0}],oracle:{numerator:1,denominator:1,ratio:1},all_wrong:0,distribution:{},agreement:[[1]],error_overlap:[[0]],samples:[{sample:'00407b51-0603-5260-a0db-1ab700451f9f',label:1,category:'CONSENSUS_TP',runs:[{score:.9,prediction:1,correct:true}]}],total:1};
  const open=renderToStaticMarkup(React.createElement(ConsensusResults,{data,onExplain(){}}));
  assert.match(open,/>XAI</); assert.match(open,/<button[^>]*title="Ver y generar[^"]*"[^>]*>Explicar/); assert.doesNotMatch(open,/disabled=""[^>]*>Explicar/);
  const blocked=renderToStaticMarkup(React.createElement(ConsensusResults,{data,onExplain(){},explainBlocked:'EXPLAIN solo está acreditado para VAL'}));
  assert.match(blocked,/disabled=""[^>]*title="EXPLAIN solo está acreditado para VAL"[^>]*>Explicar/);
  assert.doesNotMatch(renderToStaticMarkup(React.createElement(ConsensusResults,{data})),/Explicar/);
});
