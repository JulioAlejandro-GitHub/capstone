import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';

const require = createRequire(import.meta.url);
const root = fileURLToPath(new URL('../src/', import.meta.url));
const read = (path) => readFileSync(resolve(root, path), 'utf8');

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

const attempt = 'dded6222-12ae-407a-82c6-601e265e3f7d';
const train = 'bbbd5b60-afaa-4034-a504-a60ed642aafe';
const metrics = { count: 2693, tn: 1176, fp: 192, fn: 119, tp: 1206,
  accuracy: .8845154103230598, recall: .910188679245283, specificity: .8596491228070176,
  precision: .8626609442060086, f2: .900268736936399, definition: 'binary_counts_rates_v1' };
const assessment = {
  source_kind: 'assessment_e6', attempt_id: attempt, identity_id: 'identity-fixture',
  training_run_id: train, state: 'verified', split: 'val', purpose: 'development', ordinal: 1,
  started_at: '2026-10-08T15:37:39Z', finished_at: '2026-10-08T15:37:55Z',
  verification: { count: 2693, sha256: 'a'.repeat(64), metrics },
};
const load = loader();
const { AssessmentEvaluationCard, AssessmentEvaluationSummary } = load('components/reports/AssessmentEvaluationCard.tsx');
const render = (element) => renderToStaticMarkup(React.createElement(MemoryRouter, null, element));

test('E6 renders persisted metrics and links to the attempt detail, never a RUN', () => {
  const html = render(React.createElement(AssessmentEvaluationCard, { assessment, datasource: 'malaria' }));
  for (const value of ['EVALUATE', 'E6', 'VAL', 'verified', 'Finalización', '0.9102', '0.9003', '2.693', 'TN', '1.176']) {
    assert.ok(html.includes(value), value);
  }
  assert.ok(html.includes(`/modelo-ia/evaluaciones/e6/${attempt}?datasource=malaria`));
  assert.ok(!html.includes(`/modelo-ia/ejecuciones/${attempt}`));
  assert.ok(html.includes(`Intento: ${attempt}`));
  assert.ok(!html.includes('Run ID:'));
});

for (const state of ['active', 'failed', 'interrupted']) {
  test(`${state} remains visible without claiming verified scientific metrics`, () => {
    // Even an unexpected verification payload must not be shown as verified.
    const html = render(React.createElement(AssessmentEvaluationSummary, {
      assessment: { ...assessment, state, finished_at: state === 'active' ? null : assessment.finished_at },
    }));
    assert.ok(html.includes(state));
    assert.ok(!html.includes('0.9102'));
    assert.ok(!html.includes('resultados persistidos'));
    assert.ok(html.includes(state === 'active' ? 'Evaluación en curso' : 'no tiene métricas verificadas'));
  });
}

test('E6 detail displays the API payload and links back to the original TRAIN', () => {
  const detail = { ...assessment, id: attempt, kind: 'evaluate', cause: null,
    identity: { split: 'val', purpose: 'development', model: { model_version_id: 'model-fixture', checkpoint_artifact_id: 'checkpoint-fixture' } } };
  const detailLoader = loader({
    'react-router-dom': { ...require('react-router-dom'), useParams: () => ({ attemptId: attempt }) },
    '../hooks/useAssessment': { useAssessment: () => ({ data: detail, error: null, loading: false }) },
  });
  const { AssessmentDetail } = detailLoader('pages/AssessmentDetail.tsx');
  const html = render(React.createElement(AssessmentDetail, { datasource: 'malaria' }));
  for (const value of [train, 'model-fixture', 'checkpoint-fixture', 'binary_counts_rates_v1', '0.9102', '0.9003']) {
    assert.ok(html.includes(value), value);
  }
  assert.ok(html.includes(`/modelo-ia/ejecuciones/${train}?datasource=malaria`));
});

test('detail loader requests the assessment endpoint, preserves errors and aborts on unmount', async () => {
  let effect;
  let state;
  let requested;
  const hookLoader = loader({
    react: { useState: (initial) => [initial, (next) => { state = next; }], useEffect: (next) => { effect = next; } },
    '../services/api': { api: { getAssessment: async (id, signal) => {
      requested = { id, signal };
      return { id, kind: 'evaluate', verification: assessment.verification };
    } } },
  });
  hookLoader('hooks/useAssessment.ts').useAssessment(attempt);
  const cleanup = effect();
  await Promise.resolve();
  assert.equal(requested.id, attempt);
  assert.equal(state.data.verification.metrics.recall, metrics.recall);
  assert.equal(state.loading, false);
  cleanup();
  assert.equal(requested.signal.aborted, true);
  assert.match(read('services/api.ts'), /request<AssessmentDetail>\(`\/assessments\/\$\{encodeURIComponent\(attemptId\)\}`/);
});

test('failed detail request is visible; an invalid UUID does not request data', async () => {
  let effect;
  let state;
  let calls = 0;
  const hookLoader = loader({
    react: { useState: (initial) => [initial, (next) => { state = next; }], useEffect: (next) => { effect = next; } },
    '../services/api': { api: { getAssessment: async () => { calls++; throw new Error('Not found'); } } },
  });
  const { useAssessment } = hookLoader('hooks/useAssessment.ts');
  useAssessment(undefined);
  effect();
  assert.equal(calls, 0);
  useAssessment(attempt);
  effect();
  await new Promise((done) => setImmediate(done));
  assert.equal(calls, 1);
  assert.equal(state.loading, false);
  assert.ok(state.error);
  assert.match(read('pages/AssessmentDetail.tsx'), /useAssessment\(valid \? attemptId : undefined\)/);
});

test('group dispatches E6 and legacy separately, preserving EXPLAIN and filter identity', () => {
  const group = read('components/reports/TrainingRunGroupCard.tsx');
  assert.match(group, /run.source_kind === 'assessment_e6'/);
  assert.match(group, /AssessmentEvaluationCard key=\{run.attempt_id\}/);
  assert.match(group, /kind="evaluation"/);
  assert.match(group, /kind="explainability"/);
  assert.match(group, /disabled=\{linkedCount === 0 && !childrenExpanded\}/);
  assert.match(read('pages/Runs.tsx'), /`assessment:\$\{run.attempt_id\}`/);
  assert.match(read('App.tsx'), /\/e6\/:attemptId/);
});

test('E6 count enables expansion; an empty TRAIN does not invoke the loader', () => {
  const groupLoader = loader({
    react: { useState: () => [false, () => {}] },
    './RunSummaryRow': { RunSummaryRow: () => null },
    './Stage2PublicationPanel': { Stage2PublicationPanel: () => null },
  });
  const { TrainingRunGroupCard } = groupLoader('components/reports/TrainingRunGroupCard.tsx');
  function findToggle(node) {
    if (!node || !node.props) return null;
    if (node.props.className === 'lineage-children-toggle') return node;
    return React.Children.toArray(node.props.children).map(findToggle).find(Boolean);
  }
  for (const count of [0, 1]) {
    let expanded = 0;
    const tree = TrainingRunGroupCard({
      datasource: 'malaria', training: { run_id: train, evaluation_count: count, explainability_count: 0 },
      childrenState: { data: null }, onChildrenExpand: () => { expanded++; },
    });
    const button = findToggle(tree);
    assert.ok(button);
    assert.equal(button.props.disabled, count === 0);
    button.props.onClick();
    assert.equal(expanded, count);
  }
});

test('expanded TRAIN renders the E6 card using the shared lineage response', () => {
  const groupLoader = loader({
    react: { useState: () => [true, () => {}] },
    './RunSummaryRow': { RunSummaryRow: () => null },
    './Stage2PublicationPanel': { Stage2PublicationPanel: () => null },
  });
  const { TrainingRunGroupCard } = groupLoader('components/reports/TrainingRunGroupCard.tsx');
  const html = render(React.createElement(TrainingRunGroupCard, {
    datasource: 'malaria', training: { run_id: train, evaluation_count: 1, explainability_count: 0 },
    childrenState: { status: 'success', data: {
      evaluations: [assessment], explainabilities: [], total_count: 1, truncated: false,
    } },
  }));
  assert.ok(html.includes('1 EVALUATE'));
  assert.ok(html.includes('0.9102'));
  assert.ok(html.includes(`/evaluaciones/e6/${attempt}?datasource=malaria`));
});
