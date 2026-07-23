import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const page = read('src/pages/Deployments.tsx');
const config = read('src/config/pagination.ts');

test('Despliegues carga la imagen auxiliar con page=1 y page_size permitido', () => {
  assert.match(page, /page:1,page_size:DEFAULT_DATASET_IMAGE_PAGE_SIZE/);
  assert.doesNotMatch(page, /page_size:1(?:\\D|$)/);
});

test('el contrato frontend solo contiene 12, 24, 48 y 96', () => {
  assert.match(config, /\[12, 24, 48, 96\] as const/);
  assert.match(config, /DEFAULT_DATASET_IMAGE_PAGE_SIZE = 12/);
  for (const invalid of [10, 20, 25, 50, 100]) {
    assert.doesNotMatch(config, new RegExp(`\\b${invalid}\\b`));
  }
});

test('normaliza valores históricos inválidos sin requerir limpiar storage', () => {
  assert.match(config, /Number\(value\)/);
  assert.match(config, /includes\(parsed as DatasetImagePageSize\)/);
  assert.match(config, /: DEFAULT_DATASET_IMAGE_PAGE_SIZE/);
});

test('un error de paginación es legible y el reintento es manual', () => {
  assert.match(page, /configuración de paginación inválida/);
  assert.match(page, /console\.error/);
  assert.match(page, /Reintentar/);
  assert.doesNotMatch(page, /setInterval|while\s*\(/);
});
