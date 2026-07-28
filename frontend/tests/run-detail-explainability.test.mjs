import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8');
const runDetail = read('pages/RunDetail.tsx');
const explainability = read('pages/Explainability.tsx');
const app = read('App.tsx');

test('RunDetail abre localmente el CaseDetail con el caso seleccionado', () => {
  assert.match(runDetail, /import \{ CaseDetail \} from '\.\/Explainability';/);
  assert.match(runDetail, /useState<ExplainabilityCase \| null>\(null\)/);
  assert.match(runDetail, /onClick=\{\(\) => setSelectedExplainabilityCase\(row\)\}>Ver detalle<\/button>/);
  assert.doesNotMatch(runDetail, /Ver detalle #/);
  assert.match(runDetail, /<CaseDetail\s+item=\{selectedExplainabilityCase\}\s+datasource=\{datasource\}/);
  assert.match(runDetail, /onClose=\{\(\) => setSelectedExplainabilityCase\(null\)\}/);
});

test('cambiar el run cierra el detalle antes de cargar sus datos', () => {
  assert.match(
    runDetail,
    /useEffect\(\(\) => \{\s+setSelectedExplainabilityCase\(null\);\s+if \(!runId\) return;/,
  );
});

test('Explainability y RunDetail reutilizan el mismo CaseDetail', () => {
  assert.match(explainability, /export function CaseDetail\(/);
  assert.match(explainability, /Comparación de fuente y explicación/);
  assert.match(explainability, /item=\{selectedCase\}/);
  assert.match(explainability, /event\.key === 'Escape'/);
  assert.match(explainability, /aria-label="Cerrar detalle"/);
});

test('la ruta de detalle ya no navega a Explainability desde la fila', () => {
  assert.doesNotMatch(runDetail, /onExplainabilitySelect/);
  assert.doesNotMatch(app, /onExplainabilitySelect/);
  assert.match(app, /<RunDetail datasource=\{datasource\} runId=\{trainingRunId\} \/>/);
});
