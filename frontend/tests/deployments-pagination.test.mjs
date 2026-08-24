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

test('el tamaño auxiliar por defecto pertenece al contrato del backend', () => {
  assert.match(config, /DEFAULT_DATASET_IMAGE_PAGE_SIZE = 12/);
});

test('un error de paginación es legible y el reintento es manual', () => {
  assert.match(page, /configuración de paginación inválida/);
  assert.match(page, /console\.error/);
  assert.match(page, /Reintentar/);
  assert.doesNotMatch(page, /setInterval|while\s*\(/);
});
