import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const page = readFileSync(new URL('../src/pages/SmearAnalysis.tsx', import.meta.url), 'utf8');
const api = readFileSync(new URL('../src/services/api.ts', import.meta.url), 'utf8');

test('cola permanece dentro de Control de calidad y expone prioridades explícitas', () => {
  assert.match(page, /Cola de solicitudes/);
  assert.match(page, /Mínima — 1/);
  assert.match(page, /Normal — 50/);
  assert.match(page, /Máxima — 100/);
  assert.ok(page.includes('useState<QueuePriority>(50)'));
});

test('ejecución, actualización y reintento son acciones manuales', () => {
  assert.match(page, /Ejecutar ahora/);
  assert.match(page, /Actualizar cola/);
  assert.match(page, /Reintentar/);
  assert.match(page, /aún requiere “Ejecutar ahora”/);
  assert.doesNotMatch(page, /setInterval|WebSocket|EventSource/);
});

test('cliente usa endpoints persistentes de cola sin encadenar retry y execute', () => {
  assert.ok(api.includes('/api/v1/analysis/queue'));
  const retryMethod = api.slice(api.indexOf('retryQueueItem'), api.indexOf('retryQueueItem') + 500);
  assert.doesNotMatch(retryMethod, /executeQueueItem/);
});
