import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const compatibility = read('src/components/cell-review/SmearAnalysisResultsView.tsx');
const immersive = read('src/components/cell-review/SmearAnalysisImmersiveView.tsx');
const workspace = read('src/components/cell-review/CellReviewWorkspace.tsx');
const styles = read('src/styles.css');
const immersiveStyles = read('src/styles/smear-analysis-immersive.css');
const main = read('src/main.tsx');

test('live e history comparten una sola composición React de resultados', () => {
  assert.match(compatibility, /SmearAnalysisImmersiveView as SmearAnalysisResultsView/);
  assert.match(immersive, /export function SmearAnalysisImmersiveView/);
  assert.match(immersive, /export type SmearAnalysisViewMode = 'live' \| 'history'/);
  assert.match(immersive, /mode: 'live'[\s\S]*permissions: SmearAnalysisPermissions/);
  assert.match(immersive, /mode: 'history'[\s\S]*permissions\?: never/);
  assert.equal((`${compatibility}\n${immersive}`.match(/<CellReviewWorkspace/g) ?? []).length, 1);
  assert.match(immersive, /livePermissions = props\.mode === 'live' \? props\.permissions : null/);
  assert.match(immersive, /readOnly=\{isHistory\}/);
});

test('composición y CSS reproducen el workspace inmersivo aprobado sin alterar page global', () => {
  for (const value of [
    'smear-analysis-immersive', 'smear-results-header', 'smear-results-case-panel',
    'smear-results-actions', 'cell-immersive-canvas', 'cell-gallery-search',
    'cell-status-filters', 'cell-detail-panel', 'cell-gallery-panel',
    'cell-viewer-minimap', 'cell-review-progress-ring',
  ]) {
    assert.match(`${immersive}\n${workspace}\n${immersiveStyles}`, new RegExp(value));
  }
  assert.match(immersiveStyles, /\.page\.smear-workflow\.smear-workflow--immersive/);
  assert.match(immersiveStyles, /max-width: none/);
  assert.match(immersiveStyles, /height: 100dvh/);
  assert.match(immersiveStyles, /backdrop-filter: blur\(12px\)/);
  assert.match(main, /import '\.\/styles\/smear-analysis-immersive\.css'/);

  for (const token of [
    '#0b1326', '#060e20', '#131b2e', '#171f33', '#222a3d',
    '#a4e6ff', '#4cd6ff', '#4edea3', '#ffd5a5', '#ffb4ab',
    '#dae2fd', '#bbc9cf', '#3c494e',
  ]) assert.match(immersiveStyles, new RegExp(token, 'i'));

  const globalPage = styles.slice(styles.indexOf('.page {'), styles.indexOf('.page-title {'));
  assert.match(globalPage, /gap: 22px/);
  assert.match(globalPage, /padding: 28px/);
  assert.doesNotMatch(globalPage, /max-width: none|100dvh|overflow: hidden/);
});

test('filtros son reales, incluyen cell_code y excluyen categorías ficticias', () => {
  for (const label of ['Parasitized', 'Uninfected', 'Próximas al threshold', 'Sin clasificar o fallidas', 'Sin revisión', 'Confirmadas', 'Corregidas', 'Requieren atención']) {
    assert.match(workspace.toLocaleLowerCase(), new RegExp(label.toLocaleLowerCase()));
  }
  assert.match(workspace, /placeholder="cell_code, ID o x,y"/);
  assert.match(workspace, /!prediction[\s\S]*classificationFilter === 'all' \|\| classificationFilter === 'failed'/);
  assert.match(workspace, /× Sin clasificación/);
  assert.doesNotMatch(
    `${immersive}\n${workspace}`,
    /Healthy|Promyelocyte|Blast|Myelocyte|Metamyelocyte|Segmented Neutrophil/i,
  );
});

test('responsive usa cuatro pestañas y conserva reduced motion', () => {
  for (const tab of ['Imagen', 'Células', 'Detalle', 'Resultado']) assert.match(workspace, new RegExp(tab));
  assert.match(immersiveStyles, /@media \(max-width: 700px\)/);
  assert.match(immersiveStyles, /@media \(max-width: 440px\)/);
  assert.match(immersiveStyles, /smear-status-badge::after[\s\S]*Solo lectura/);
  assert.match(immersiveStyles, /smear-results-actions \.smear-glass-button:not\(\.smear-results-context-action\)[\s\S]*font-size: 0/);
  assert.match(immersiveStyles, /prefers-reduced-motion: reduce/);
});

test('resultado mantiene disclaimer experimental y no presenta diagnóstico', () => {
  assert.match(
    immersive,
    /El resultado es experimental, requiere revisión experta y no constituye un diagnóstico clínico\./,
  );
  assert.doesNotMatch(
    `${immersive}\n${workspace}`,
    /Sign Off|50 μm|HematologyPro|Scopio|magnificación x2000|textura de cromatina/i,
  );
});
