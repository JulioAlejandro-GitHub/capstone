import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);
const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8');
const code = ts.transpileModule(read('components/reports/Stage2PublicationPanel.tsx'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
}).outputText;
const module = { exports: {} };
runInNewContext(code, { exports: module.exports, require });
const Panel = module.exports.Stage2PublicationPanel;
const status = {
  training_run_id: 'train-fixture', train_status: 'completed',
  train_finished_at: '2026-10-06T18:26:18Z',
  evaluation_source_kind: 'assessment_e6', evaluation_attempt_id: 'attempt-fixture',
  evaluation_run_id: null, evaluation_status: 'verified', evaluation_split: 'val',
  evaluation_finished_at: '2026-10-08T15:37:55Z',
  eligible: true, eligibility: { train_completed: true, evaluate_completed: true, missing_conditions: [] },
  model_version_id: 'evidence-version', model_version_registered: false,
  version_number: null, model_name: 'custom_cnn', architecture: 'Custom CNN', checkpoint: 'epoch_2.keras',
  checkpoint_artifact_id: 'checkpoint-fixture', checkpoint_sha256: 'a'.repeat(64),
  published: false, is_stage2_available: false,
  deployment_readiness: { ready: false, status: 'blocked', checkpoint_accessible: true, checkpoint_verified: true },
  technical_blockers: [{ code: 'MODEL_VERSION_NOT_REGISTERED', message: 'Registro operativo pendiente.' }],
};
const render = (props = {}) => renderToStaticMarkup(React.createElement(Panel, {
  id: 'stage2-fixture', status, explainCount: 0,
  onPublish: () => { throw new Error('Must not publish while rendering'); },
  onDeactivate: () => { throw new Error('Must not deactivate while rendering'); }, ...props,
}));

const ready = { ...status, deployment_readiness: { ready: true }, technical_blockers: [] };
const action = 'Activar para clasificación celular';

test('completed TRAIN and verified evaluation enable activation without prior registration', () => {
  const html = render();
  assert.ok(!html.includes('disabled=""'));
  assert.ok(html.includes('Cumple la regla de liberación para clasificación celular'));
  assert.ok(!html.includes('Activación pendiente.'));
  assert.ok(!html.includes('Este modelo no está disponible para activación'));
  for (const hidden of ['Elegible', 'E6', 'attempt-fixture', 'verified', 'evidence-version',
    'Número de versión', 'Registro operativo', 'checkpoint-fixture', 'a'.repeat(64), 'SHA-256',
    'Preparación para despliegue', 'Publicación', 'Etapa 2', 'MODEL_VERSION_NOT_REGISTERED']) {
    assert.ok(!html.includes(hidden), hidden);
  }
});

test('original seven fields, labels, dates and column grid are restored', () => {
  const html = render();
  assert.ok(html.includes('class="stage2-publication-grid"'));
  assert.ok(html.includes('Regla de liberación'));
  for (const label of ['Regla', 'TRAIN', 'TRAIN finalizado', 'EVALUATE finalizado',
    'EXPLAIN', 'Arquitectura', 'Modelo / checkpoint']) {
    assert.ok(html.includes(`>${label}`), label);
  }
  for (const value of ['TRAIN completed + EVALUATE completed', 'TRAIN: Completado.', 'EVALUATE: Completado.',
    'train-fixture', 'VAL', 'Custom CNN', 'custom_cnn · epoch_2.keras', 'N/A · opcional, sin ejecución asociada']) {
    assert.ok(html.includes(value), value);
  }
  for (const stamp of [status.train_finished_at, status.evaluation_finished_at]) {
    assert.ok(html.includes(new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(stamp))));
  }
});

for (const [name, override, pending] of [
  ['unfinished TRAIN', { train_status: 'running', eligibility: { train_completed: false, evaluate_completed: true } }, 'TRAIN'],
  ['absent evaluation', { evaluation_status: null, evaluation_attempt_id: null, eligibility: { train_completed: true, evaluate_completed: false } }, 'EVALUATE'],
  ['failed evaluation', { evaluation_status: 'failed', eligibility: { train_completed: true, evaluate_completed: false } }, 'EVALUATE'],
  ['unverified evaluation', { evaluation_status: 'active', eligibility: { train_completed: true, evaluate_completed: false } }, 'EVALUATE'],
  ['verified without valid link', { eligibility: { train_completed: true, evaluate_completed: false } }, 'EVALUATE'],
]) {
  test(`${name} displays the pending backend condition without recomputing eligibility`, () => {
    const html = render({ status: { ...ready, ...override, eligible: false } });
    assert.ok(html.includes(`Pendiente: ${pending}`));
    assert.ok(!html.includes('Cumple la regla de liberación'));
    assert.ok(!html.includes('Activación pendiente.'));
    assert.match(html, /<button[^>]*disabled=""/);
    if (pending === 'EVALUATE') assert.ok(!html.includes('EVALUATE: Completado'));
  });
}

test('missing operational registration never changes the displayed eligibility result', () => {
  const html = render({ status: { ...status, model_version_id: null } });
  assert.ok(html.includes('Cumple la regla de liberación para clasificación celular'));
  assert.ok(!html.includes('Activación pendiente.'));
  assert.ok(!html.includes('disabled=""'));
});

test('EXPLAIN counts and existing explanation evidence remain informational', () => {
  assert.ok(render({ explainCount: 2 }).includes('2 asociado(s) · informativo'));
  const html = render({ status: { ...status, explanations: [{ run_id: 'explain-fixture', status: 'completed' }] } });
  assert.ok(html.includes('completed · explain-fixture'));
  assert.ok(html.includes('Cumple la regla de liberación'));
});

test('conditional fields not listed for removal remain in the original grid', () => {
  const html = render({ status: { ...ready, deployment_id: 'deployment-fixture', environment: 'production', alias: 'champion',
    threshold: .5, threshold_source: 'validation', deployed_at: status.train_finished_at,
    publication: { id: 'publication-hidden', published_at: status.train_finished_at, published_by: 'operator-fixture' },
  } });
  for (const field of ['Deployment', 'Slot productivo', 'Threshold', 'Desplegado', 'Publicado', 'operator-fixture']) {
    assert.ok(html.includes(field), field);
  }
  assert.ok(!html.includes('publication-hidden'));
});

test('API failure has a generic error and retry without leaking backend details', () => {
  const html = render({ status: undefined, error: 'SQL model_versions internal UUID', onRetry: () => {} });
  assert.match(html, /role="alert"/);
  assert.ok(html.includes('Reintentar consulta'));
  assert.ok(!html.includes('SQL'));
  assert.ok(!html.includes(action));
});

test('loading does not offer an activation decision', () => {
  const html = render({ status: undefined, loading: true });
  assert.ok(html.includes('Consultando modelo'));
  assert.ok(!html.includes(action));
});

test('ready candidate without EXPLAIN can activate regardless of descriptive fields or low metrics', () => {
  const html = render({ status: { ...ready, evaluation_source_kind: 'run', evaluation_attempt_id: null,
    evaluation_run_id: 'legacy-evaluation', evaluation_status: 'completed', model_name: null, architecture: null,
    checkpoint: null, version_number: null, recall: .1, f2: .1, explanations: [],
  } });
  assert.ok(html.includes(action));
  assert.ok(!html.includes('disabled=""'));
});

for (const [name, override] of Object.entries({
  'not ready': { deployment_readiness: { ready: false } },
  'unknown readiness': { deployment_readiness: undefined },
  'missing version': { model_version_id: null },
  'operational blocker': { technical_blockers: [{ code: 'CHECKPOINT_UNAVAILABLE', message: 'internal path' }] },
})) {
  test(`${name} is checked during activation, never as an eligibility prerequisite`, () => {
    const html = render({ status: { ...ready, ...override } });
    assert.ok(!html.includes('disabled=""'));
    assert.ok(!html.includes('internal path'));
  });
}

test('activation errors remain visible and do not claim success', async () => {
  const panel = interactivePanel({ onPublish: async () => 'failed' });
  panel.click(panel.draw(), action);
  await flush();
  const html = renderToStaticMarkup(panel.draw({ error: 'No se pudo cargar el checkpoint seleccionado.' }));
  assert.ok(html.includes('No se pudo cargar el checkpoint seleccionado.'));
  assert.ok(!html.includes('Modelo en Estado Activo'));
});

test('active model shows Modelo activo and never offers redundant activation', () => {
  const html = render({ status: { ...ready, is_stage2_available: true, available_for_inference: true } });
  assert.ok(html.includes('Modelo en Estado Activo'));
  assert.ok(html.includes(action));
  assert.match(html, /disabled=""/);
});

test('publication alone does not claim that the model receives crops', () => {
  const html = render({ status: { ...status, published: true, is_stage2_available: true, available_for_inference: false } });
  assert.ok(!html.includes('Modelo en Estado Activo'));
  assert.ok(!html.includes('disabled=""'));
});

// Exercise actual component handlers with a minimal hook harness; every API is a local stub.
function interactivePanel(props = {}) {
  let state = null;
  const scope = { exports: {} };
  runInNewContext(code, { exports: scope.exports, require: (name) => name === 'react'
    ? { ...React, useState: () => [state, (next) => { state = next; }] } : require(name) });
  const draw = (extra = {}) => scope.exports.Stage2PublicationPanel({ id: 'interactive', status: ready, explainCount: 0,
    onPublish: () => { throw new Error('unexpected activation'); }, onDeactivate: () => {}, ...props, ...extra });
  const buttons = (node) => {
    if (!node || typeof node !== 'object') return [];
    if (Array.isArray(node)) return node.flatMap(buttons);
    return [...(node.type === 'button' ? [node] : []), ...buttons(node.props?.children)];
  };
  return { draw, click: (tree, label) => {
    const button = buttons(tree).find((item) => item.props.children === label);
    assert.ok(button, label);
    assert.ok(!button.props.disabled, label);
    button.props.onClick();
  } };
}
const flush = () => new Promise((resolve) => setImmediate(resolve));

test('activation requires the user click; replacement adds its own confirmation', async () => {
  const calls = [];
  const panel = interactivePanel({ onPublish: async (replace) => {
    calls.push(replace); return replace ? 'published' : 'replacement-required';
  } });
  let tree = panel.draw();
  assert.deepEqual(calls, []);
  panel.click(tree, action);
  await flush();
  assert.deepEqual(calls, [false]);
  panel.click(panel.draw(), 'Cancelar');
  assert.deepEqual(calls, [false]);
  panel.click(panel.draw(), action);
  await flush();
  assert.ok(renderToStaticMarkup(panel.draw()).includes('Ya hay otro modelo activo'));
  panel.click(panel.draw(), 'Continuar y reemplazar');
  await flush();
  assert.deepEqual(calls, [false, false, true]);
});

test('no active model activates on the user click without an additional approval step', async () => {
  const calls = [];
  const panel = interactivePanel({ onPublish: async (replace) => { calls.push(replace); return 'published'; } });
  panel.click(panel.draw(), action);
  await flush();
  assert.deepEqual(calls, [false]);
});

test('a pending replacement cannot activate a model whose eligibility changed', async () => {
  const panel = interactivePanel({ onPublish: async () => 'replacement-required' });
  panel.click(panel.draw(), action);
  await flush();
  assert.match(renderToStaticMarkup(panel.draw({ status: { ...status, eligible: false } })), /disabled=""/);
});

function publicationFlow(candidate = ready, available = { available: false }) {
  const calls = [];
  const runs = read('pages/Runs.tsx');
  const source = runs.slice(runs.indexOf('  const publishStage2 ='), runs.indexOf('  useEffect(', runs.indexOf('  const publishStage2 =')));
  const flowCode = ts.transpileModule(`${source}\nexports.publish = publishStage2;`, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText;
  const scope = { exports: {} };
  runInNewContext(flowCode, { exports: scope.exports, stage2Status: { train: candidate }, datasource: 'fixture',
    setStage2Loading: () => {}, setStage2Errors: () => {},
    loadStage2: async (runId, force) => { calls.push(['status', runId, force]); return candidate; },
    api: {
      getProductiveModelAvailability: async () => { calls.push(['current']); return available; },
      activateCellModel: async (datasource, id, payload) => { calls.push(['publish', id, payload.replace_existing]); return { available_for_inference: true }; },
    },
  });
  return { publish: scope.exports.publish, calls };
}

test('no active model uses existing publication service then reloads canonical availability', async () => {
  const flow = publicationFlow();
  assert.equal(await flow.publish('train'), 'published');
  assert.deepEqual(flow.calls, [['current'], ['publish', 'train', false], ['status', 'train', true]]);
});

test('another active model requires confirmation before using the existing replacement payload', async () => {
  const flow = publicationFlow(ready, { available: true, model: { model_version_id: 'other-version' } });
  assert.equal(await flow.publish('train'), 'replacement-required');
  assert.deepEqual(flow.calls, [['current']]);
  assert.equal(await flow.publish('train', true), 'published');
  assert.deepEqual(flow.calls, [['current'], ['current'], ['publish', 'train', true], ['status', 'train', true]]);
});

test('already active model refreshes state without redundant publication', async () => {
  const flow = publicationFlow(ready, { available: true, model: { model_version_id: ready.model_version_id } });
  assert.equal(await flow.publish('train'), 'published');
  assert.deepEqual(flow.calls, [['current'], ['status', 'train', true]]);
});

test('replacement confirmation rechecks whether this model has already become active', async () => {
  const flow = publicationFlow(ready, { available: true, model: { model_version_id: ready.model_version_id } });
  assert.equal(await flow.publish('train', true), 'published');
  assert.deepEqual(flow.calls, [['current'], ['status', 'train', true]]);
});

test('ineligible candidate cannot call the activation service even outside the panel', async () => {
  const flow = publicationFlow({ ...status, eligible: false });
  assert.equal(await flow.publish('train'), 'failed');
  assert.deepEqual(flow.calls, []);
});

test('the page consumes one canonical release response and clears stale status on errors', () => {
  const runs = read('pages/Runs.tsx');
  const load = runs.slice(runs.indexOf('const loadStage2'), runs.indexOf('const publishStage2'));
  assert.equal((load.match(/getStage2ReleaseStatus/g) || []).length, 1);
  assert.doesNotMatch(load, /getStage2Availability|Promise\.all/);
  assert.match(load, /delete next\[runId\]/);
  assert.doesNotMatch(load, /eligible:\s*false/);
  assert.match(read('components/reports/TrainingRunGroupCard.tsx'), /onRetry=\{onStage2Open\}/);
});
