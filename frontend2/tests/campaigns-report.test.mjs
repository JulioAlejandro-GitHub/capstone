import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

// SWV2.3 source-level contract of the campaigns report (/modelo-ia/campanas).
// Mirrors the SWV2.2 test style: source files are scanned; no runtime, no DOM.

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const page = read('src/pages/CampaignsReport.tsx');
const app = read('src/App.tsx');
const router = read('src/router.ts');
const navigation = read('src/components/navigation/navigationConfig.ts');
const api = read('src/services/api.ts');
const types = read('src/types/campaign.ts');
const campaignApi = api.slice(api.indexOf('// SWV2.2 Campaña'), api.indexOf('getDatasetImages('));

test('la ruta /modelo-ia/campanas existe en el router y App renderiza el reporte', () => {
  assert.match(router, /campaigns: '\/modelo-ia\/campanas'/);
  assert.match(app, /<Route path=\{routes\.campaigns\} element=\{<CampaignsReport/);
});

test('el menú "Campaña" apunta al reporte (campanas), no a la página de configuración', () => {
  assert.match(navigation, /id: 'campaign', label: 'Campaña', path: routes\.campaigns/);
});

test('el reporte lista las campañas creadas desde el endpoint de lista del backend', () => {
  assert.match(page, /api\.getCampaigns\(\{ limit: 200 \}\)/);
  assert.match(page, /body\.items/);
  assert.match(api, /getCampaigns\(/);
  assert.match(api, /'\/api\/campaigns'/);
  assert.match(types, /CampaignListItem/);
  assert.match(types, /CampaignListResponse/);
});

test('el reporte muestra dataset, modelos, Total de Experimentos, estado y congelación', () => {
  assert.match(page, /Total de Experimentos/);
  assert.doesNotMatch(page, /Miembros de campaña/i);
  assert.match(page, /campaign-state-badge/);
  assert.match(page, /dataset_name/);
  assert.match(page, /dataset_semantic_version/);
  assert.match(page, /contract_hash/);
  assert.match(page, /frozen_at/);
  assert.match(page, /members_by_state/);
});

test('"Nueva Campaña" abre la configuración vacía; "Editar" la rellena con la campaña', () => {
  assert.match(page, /Nueva Campaña/);
  assert.match(page, /go\(routes\.campaign\)/);
  assert.match(page, /Editar/);
  assert.match(page, /go\(routes\.campaign, \{ campaignId: item\.campaign_id \}\)/);
});

test('la fila resaltada corresponde a la campaña abierta en edición (?campaignId=…)', () => {
  assert.match(page, /is-highlight/);
  assert.match(page, /isValidPublicId\(editingId\)/);
});

test('el reporte nunca ejecuta: sin acciones de ejecución en la página ni en la API de campaña', () => {
  assert.doesNotMatch(page, />\s*(Ejecutar|Iniciar|Run|Start training|Entrenar)\b/i);
  assert.doesNotMatch(campaignApi, /execute|\/run|\/start|\/train/i);
  assert.match(page, /La ejecución se inicia manualmente desde la consola\./);
});

test('el reporte documenta la inmutabilidad FROZEN y el comportamiento de "Editar"', () => {
  assert.match(page, /FROZEN son inmutables/);
  assert.match(page, /campaña derivada/);
});
