import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const page = readFileSync(new URL('../src/pages/SmearWorkflow.tsx', import.meta.url), 'utf8');
const hook = readFileSync(new URL('../src/hooks/useSmearAnalysisWorkflow.ts', import.meta.url), 'utf8');
const api = readFileSync(new URL('../src/services/api.ts', import.meta.url), 'utf8');

test('cola forma parte del workflow y usa prioridad normal 50', () => {
  assert.match(page, /Control de calidad/);
  assert.match(page, /Prioridad/);
  assert.match(page, /Normal/);
  assert.match(hook, /enqueueQuality\(analysisRun\.id,\s*50\)/);
});

test('ejecución, actualización y reintento permanecen manuales', () => {
  assert.match(page, /Ejecutar control/);
  assert.match(page, /Actualizar estado/);
  assert.match(page, /Reingresar a cola/);
  assert.match(page, /requiere una segunda acción manual/);
  assert.doesNotMatch(page + hook, /setInterval|WebSocket|EventSource/);
});

test('cliente usa endpoints persistentes de cola sin encadenar retry y execute', () => {
  assert.ok(api.includes('/api/v1/analysis/queue'));
  const retryMethod = api.slice(api.indexOf('retryQueueItem'), api.indexOf('retryQueueItem') + 500);
  assert.doesNotMatch(retryMethod, /executeQueueItem/);
  const requeue = hook.slice(hook.indexOf('const requeueQuality'), hook.indexOf('const executeRequeuedQuality'));
  assert.match(requeue, /retryQueueItem/);
  assert.doesNotMatch(requeue, /executeQueueItem|executeQueuedQuality/);
});
