import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const api = readFileSync(new URL('../src/services/api.ts', import.meta.url), 'utf8');
const auth = readFileSync(new URL('../src/auth.tsx', import.meta.url), 'utf8');
const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');

test('login y me usan el cliente HTTP central y persisten solamente el bearer', () => {
  assert.match(api, /\/api\/v1\/auth\/login/);
  assert.match(api, /\/api\/v1\/auth\/me/);
  assert.match(api, /Authorization.*Bearer/);
  assert.match(api, /localStorage\.setItem\(ACCESS_TOKEN_KEY, token\)/);
  assert.doesNotMatch(api, /localStorage\.setItem\([^,]+,\s*(?:user|JSON\.stringify)/);
});

test('401 elimina la sesión persistida y logout cancela solicitudes pendientes', () => {
  assert.match(api, /response\.status === 401/);
  assert.match(api, /localStorage\.removeItem\(ACCESS_TOKEN_KEY\)/);
  assert.match(api, /authenticationFailureHandler\?\.\(\)/);
  assert.match(auth, /logout\(\).*setAccessToken\(null\)/s);
  assert.match(auth, /logout\(\).*cancelPendingRequests\(\)/s);
});

test('las rutas existentes están protegidas y login permanece público', () => {
  assert.match(app, /path="\/login"/);
  assert.match(app, /<ProtectedRoute><Layout/);
});

test('la inicialización restaura el token y valida la sesión con el backend', () => {
  assert.match(api, /let accessToken[^=]*=\s*readStoredAccessToken\(\)/);
  assert.match(auth, /status.*'initializing'/s);
  assert.match(auth, /restoreAccessToken\(\)/);
  assert.match(auth, /authApi\.me\(\)/);
  assert.match(auth, /setStatus\('authenticated'\)/);
  assert.match(auth, /error instanceof ApiError && error\.status === 401/);
  assert.match(auth, /setStatus\('unavailable'\)/);
});

test('la guarda espera la validación y conserva la URL solicitada completa', () => {
  assert.match(auth, /status === 'initializing'.*SessionStatus/s);
  assert.match(auth, /status === 'unavailable'.*retrySession/s);
  assert.match(auth, /location\.pathname.*location\.search.*location\.hash/s);
});

test('login espera restauración y vuelve a la ruta protegida solicitada', () => {
  const login = readFileSync(new URL('../src/pages/Login.tsx', import.meta.url), 'utf8');
  assert.match(login, /status === 'initializing'.*SessionStatus/s);
  assert.match(login, /status === 'unavailable'.*retrySession/s);
  assert.match(login, /navigate\(requestedPath/);
  assert.match(login, /Navigate to=\{requestedPath\}/);
});
