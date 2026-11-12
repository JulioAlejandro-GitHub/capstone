import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);
const source = readFileSync(new URL('../src/components/ScientificResults.tsx', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
const module = { exports: {} };
runInNewContext(compiled, { exports: module.exports, require: name => name === '../services/api' ? { api: {} } : require(name) });
const view = module.exports.ScientificResultsView;

test('v2 renders undefined reasons, real zero, orientation, lineage and specialist review', () => {
  const html = renderToStaticMarkup(React.createElement(view, { result: {
    contract_version: 'scientific_results_v2', release_status: 'not_available',
    evaluations: [{ id: 'e', split: 'val', training_run_id: 'train-fixture', model_version_id: 'model-fixture', checkpoint_artifact_id: 'checkpoint-fixture' }],
    run_clinical_metrics: [{ evaluation_id: 'e', tn: 2, fp: 0, fn: 0, tp: 0, metrics: {
      recall: { value: null, undefined_reason: 'zero_denominator' },
      roc_auc: { value: null, undefined_reason: 'single_class' },
      f1: { value: 0, undefined_reason: null },
    } }],
    xai_evidence: [{ id: 'x', method: 'gradcam', method_version: 'v1', checkpoint_artifact_id: 'checkpoint-fixture' }],
    xai_interpretations: [{ id: 'i', interpretation: 'Observación sintética', limitations: 'Sin validez clínica' }],
    xai_specialist_reviews: [{ id: 'r', interpretation_id: 'i', decision: 'needs_revision', rationale: 'Fixture de revisión' }],
  } }));
  for (const expected of ['Indefinida (zero_denominator)', 'Indefinida (single_class)', '0.0000', 'TN 2', 'FP 0', 'FN 0', 'TP 0',
    'filas reales, columnas predichas', 'train-fixture', 'model-fixture', 'checkpoint-fixture', 'not_available', 'needs_revision', 'Sin validez clínica']) {
    assert.ok(html.includes(expected), expected);
  }
});

test('legacy does not claim typed v2 evidence', () => {
  assert.equal(renderToStaticMarkup(React.createElement(view, { result: { contract_version: 'legacy_e10_v1', release_status: null } })), '');
});
