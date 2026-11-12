import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);
const source = readFileSync(new URL('../src/components/reports/ScientificParameters.tsx', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
const module = { exports: {} };
runInNewContext(compiled, { exports: module.exports, require });
const render = parameters => renderToStaticMarkup(React.createElement(module.exports.ScientificParameters, { parameters }));

test('renders nine absent values without scientific defaults', () => {
  const html = render();
  assert.equal((html.match(/<dd>—<\/dd>/g) || []).length, 9);
});

test('preserves false, zero, small decimals and per-run F2', () => {
  const first = render({ calibrate_threshold: false, threshold: 0, early_stopping_min_delta: 0.00001, val_f2_parasitized: 0.87654321 });
  for (const value of ['false', '0', '0.00001', '0.87654321']) assert.ok(first.includes(`<dd>${value}</dd>`));
  const second = render({ calibrate_threshold: true, val_f2_parasitized: 0.42 });
  assert.ok(second.includes('<dd>true</dd>'));
  assert.ok(second.includes('<dd>0.42</dd>'));
  assert.ok(!second.includes('0.87654321'));
});
