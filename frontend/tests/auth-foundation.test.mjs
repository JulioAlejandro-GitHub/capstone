import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const api = readFileSync(new URL('../src/services/api.ts', import.meta.url), 'utf8');
const auth = readFileSync(new URL('../src/auth.tsx', import.meta.url), 'utf8');
const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');

test('login y me usan el cliente HTTP central con bearer en memoria', () => {
  assert.match(api, /\/api\/v1\/auth\/login/);
  assert.match(api, /\/api\/v1\/auth\/me/);
  assert.match(api, /Authorization.*Bearer/);
  assert.doesNotMatch(api, /localStorage|sessionStorage/);
});

test('401 elimina la sesión local y logout descarta el token', () => {
  assert.match(api, /response\.status === 401/);
  assert.match(auth, /logout\(\).*setAccessToken\(null\)/s);
});

test('las rutas existentes están protegidas y login permanece público', () => {
  assert.match(app, /path="\/login"/);
  assert.match(app, /<ProtectedRoute><Layout/);
});
