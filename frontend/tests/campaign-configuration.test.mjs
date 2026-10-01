import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const page = read('src/pages/CampaignConfiguration.tsx');
const types = read('src/types/campaign.ts');
const api = read('src/services/api.ts');
const app = read('src/App.tsx');
const router = read('src/router.ts');
const navigation = read('src/components/navigation/navigationConfig.ts');
const campaignApi = api.slice(api.indexOf('// SWV2.2 Campaña'), api.indexOf('getDatasetImages('));

test('Modelo IA → Campaña aparece inmediatamente debajo de Ejecuciones y apunta al reporte', () => {
  const lines = navigation.split('\n');
  const runs = lines.findIndex((line) => line.includes("label: 'Ejecuciones'"));
  assert.ok(runs > 0);
  assert.match(lines[runs + 1], /id: 'campaign', label: 'Campaña', path: routes\.campaigns/);
  assert.match(router, /campaign: '\/modelo-ia\/campana'/);
  assert.match(router, /campaigns: '\/modelo-ia\/campanas'/);
  assert.match(app, /routes\.campaigns/);
  assert.match(app, /<CampaignsReport/);
  assert.match(app, /<CampaignConfiguration/);
});

test('una sola página contiene las seis secciones de configuración', () => {
  for (const heading of ['1. Datos generales', '2. Dataset Version', '3. Modelos', '4. Configuración de modelos',
    '5. Resumen de campaña', '6. Validación']) assert.match(page, new RegExp(heading.replace('.', '\\.')));
  assert.doesNotMatch(page, /useNavigate|navigate\(/);
});

test('no existe ninguna acción de ejecución en React', () => {
  assert.doesNotMatch(page, />\s*(Ejecutar|Iniciar|Run|Start training|Entrenar)\b/i);
  assert.doesNotMatch(campaignApi, /execute|\/run|\/start|\/train/i);
  assert.match(page, /Ejecuta este comando manualmente desde la consola para iniciar la campaña\./);
});

test('usa la terminología Total de Experimentos y no Miembros de campaña', () => {
  assert.match(page, /Total de Experimentos/);
  assert.doesNotMatch(page, /Miembros de campaña/i);
});

test('el total proviene del backend, sin un segundo algoritmo en el frontend', () => {
  assert.match(page, /api\.previewCampaign/);
  assert.match(page, /summary\.total_experiments/);
  assert.doesNotMatch(page, /models\.length\s*\*|optimizers\.length\s*\*|seeds\.length\s*\*|variants\.length\s*\*/);
});

test('modelos, parámetros y defaults se descubren desde el catálogo backend', () => {
  assert.match(page, /api\.getCampaignCatalog/);
  for (const hardcoded of ['custom_cnn', 'vgg16', 'densenet121', "'adam'", "'sgd'", "'adadelta'", "'adamw'"]) {
    assert.ok(!page.includes(hardcoded), `hardcoded ${hardcoded} in page`);
    assert.ok(!types.includes(hardcoded), `hardcoded ${hardcoded} in types`);
  }
  assert.doesNotMatch(page + types + campaignApi, /d8c0cab5-09dd-597f-9de7-7ca01aee2ec2/);
  assert.match(page, /presets/);
});

test('dataset version se elige con selector desde las versiones gobernadas', () => {
  assert.match(page, /api\.getDatasetVersions/);
  assert.match(page, /id="campaign-dataset"/);
  for (const label of ['TRAIN', 'VALIDATION', 'TEST', 'Total', 'Estado', 'UUID']) assert.match(page, new RegExp(`<dt>${label}</dt>`));
});

test('controles adecuados por tipo de parámetro', () => {
  assert.match(page, /parameter\.type === 'boolean'[\s\S]*type="checkbox"/);
  assert.match(page, /parameter\.type === 'enum'[\s\S]*<select/);
  assert.match(page, /type="number"/);
  assert.match(page, /parameter\.editable/);
});

test('guardar usa una clave idempotente y muestra campaign_id con el comando del backend', () => {
  assert.match(page, /crypto\.randomUUID\(\)/);
  assert.match(page, /campaign_id: campaignId/);
  assert.match(page, /saved\.command/);
  assert.match(page, /navigator\.clipboard\.writeText\(command\)/);
  assert.match(page, />Copiar</);
  assert.match(page, /api\.getCampaign\(result\.campaign_id\)/);
  assert.match(api, /'\/api\/campaigns'/);
});

test('guardar sólo se habilita con una validación backend vigente', () => {
  assert.match(page, /currentPreview\?\.valid/);
  assert.match(page, /previewKey === requestKey/);
  assert.match(page, /disabled=\{!canSave\}/);
});
