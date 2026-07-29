import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const results = read('src/components/cell-review/SmearAnalysisResultsView.tsx');
const workspace = read('src/components/cell-review/CellReviewWorkspace.tsx');
const styles = read('src/styles.css');

test('live e history comparten una sola composición React de resultados', () => {
  assert.match(results, /export function SmearAnalysisResultsView/);
  assert.match(results, /export type SmearAnalysisViewMode = 'live' \| 'history'/);
  assert.equal((results.match(/<CellReviewWorkspace/g) ?? []).length, 1);
  assert.match(results, /mode === 'live' && permissions\.canExplain/);
  assert.match(results, /readOnly=\{mode === 'history'\}/);
});

test('cabecera, navegación y layout convierten la estructura del prototipo', () => {
  for (const value of ['smear-results-header', 'smear-results-nav', 'cell-summary-panel', 'cell-gallery-panel', 'cell-image-panel']) {
    assert.match(`${results}\n${workspace}`, new RegExp(value));
  }
  assert.match(styles, /grid-template-columns: minmax\(220px, 2fr\) minmax\(420px, 7fr\) minmax\(340px, 3fr\)/);
  assert.match(styles, /\.smear-glass-panel/);
  assert.match(styles, /backdrop-filter: blur\(40px\)/);
});

test('filtros son reales, incluyen cell_code y excluyen categorías ficticias', () => {
  for (const label of ['Parasitized', 'Uninfected', 'Próximas al threshold', 'Predicciones fallidas', 'Sin revisión', 'Confirmadas', 'Corregidas', 'Requieren atención']) {
    assert.match(workspace.toLocaleLowerCase(), new RegExp(label.toLocaleLowerCase()));
  }
  assert.match(workspace, /placeholder="cell_code"/);
  assert.doesNotMatch(`${results}\n${workspace}`, /Promyelocyte|Blast|Myelocyte|Metamyelocyte|Segmented Neutrophil/);
});

test('responsive usa cuatro pestañas y conserva reduced motion', () => {
  for (const tab of ['Resumen', 'Células', 'Imagen', 'Detalle']) assert.match(workspace, new RegExp(tab));
  assert.match(styles, /@media \(max-width: 700px\)/);
  assert.match(styles, /prefers-reduced-motion: reduce/);
});

test('resultado mantiene disclaimer experimental y no presenta diagnóstico', () => {
  assert.match(workspace, /no constituye un diagnóstico clínico/);
  assert.doesNotMatch(results, /Sign Off|50 μm|HematologyPro|Scopio/);
});
