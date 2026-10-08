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

test('E6 verified is displayed as technically eligible, separately from readiness and availability', () => {
  const html = render();
  for (const value of ['Elegible', 'E6 · intento', 'attempt-fixture', 'verified', 'VAL',
    'Custom CNN', 'epoch_2.keras', 'evidence-version', 'Sin evidencia', 'N/A · opcional',
    'Preparación para despliegue', 'Pendiente', 'Sin publicación activa', 'No disponible actualmente']) {
    assert.ok(html.includes(value), value);
  }
  assert.ok(!html.includes('No elegible'));
  assert.match(html, /<button disabled=""[^>]*>Publicar y desplegar en Etapa 2/);
});

test('API failure has an explicit error and retry, without a false ineligibility decision', () => {
  const html = render({ status: undefined, error: 'No fue posible consultar el estado de liberación', onRetry: () => {} });
  assert.match(html, /role="alert"/);
  assert.ok(html.includes('Reintentar consulta'));
  assert.ok(html.includes('No se ha determinado la elegibilidad'));
  for (const forbidden of ['No elegible', 'No disponible actualmente', 'no cumple la regla', 'Publicar y desplegar']) {
    assert.ok(!html.includes(forbidden), forbidden);
  }
});

test('loading never makes an eligibility decision', () => {
  const html = render({ status: undefined, loading: true });
  assert.ok(html.includes('Consultando disponibilidad'));
  assert.ok(!html.includes('No elegible'));
});

test('missing descriptive values and low clinical metrics do not disable an eligible ready legacy candidate', () => {
  const html = render({ status: { ...status, evaluation_source_kind: 'run', evaluation_attempt_id: null,
    evaluation_run_id: 'legacy-evaluation', evaluation_status: 'completed', model_name: null, architecture: null,
    checkpoint: null, version_number: null, recall: .1, f2: .1,
    deployment_readiness: { ready: true }, technical_blockers: [],
  } });
  assert.ok(html.includes('Elegible'));
  assert.ok(html.includes('legacy-evaluation'));
  assert.match(html, /<button class="primary-action"[^>]*>Publicar y desplegar en Etapa 2/);
  assert.ok(!html.includes('disabled=""'));
});

test('an inaccessible checkpoint keeps eligibility visible and blocks deployment only', () => {
  const html = render({ status: { ...status, deployment_readiness: { ready: false, checkpoint_accessible: false },
    technical_blockers: [{ code: 'CHECKPOINT_UNAVAILABLE', message: 'Checkpoint inaccesible.' }],
  } });
  assert.ok(html.includes('Elegible'));
  assert.ok(html.includes('Checkpoint inaccesible.'));
  assert.match(html, /<button disabled=""/);
});

test('failed evaluation reflects the backend decision; EXPLAIN remains optional', () => {
  const html = render({ status: { ...status, eligible: false, evaluation_status: 'failed',
    eligibility: { train_completed: true, evaluate_completed: false, missing_conditions: ['EVALUATE no completado'] },
  } });
  assert.ok(html.includes('No elegible'));
  assert.ok(html.includes('EVALUATE no completado'));
  assert.ok(html.includes('N/A · opcional'));
});

test('published but inaccessible model does not claim productive availability', () => {
  const html = render({ status: { ...status, published: true, is_stage2_available: false } });
  assert.ok(html.includes('Publicación activa'));
  assert.ok(html.includes('No disponible actualmente'));
  assert.ok(!html.includes('✓ Productivo Etapa 2'));
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
