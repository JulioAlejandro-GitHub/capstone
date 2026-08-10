import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const workspace = read('src/components/cell-review/CellReviewWorkspace.tsx');
const annotations = read('src/components/cell-review/ScientificAnnotations.tsx');
const immersive = read('src/components/cell-review/SmearAnalysisImmersiveView.tsx');
const workflow = read('src/pages/SmearWorkflow.tsx');
const api = read('src/services/api.ts');
const css = read('src/styles/smear-analysis-immersive.css');

test('9.2C reutiliza el detalle existente sin modal ni formulario paralelo', () => {
  assert.match(workspace, /Detalle de la detección candidata/);
  assert.equal((workspace.match(/function CellDetailPanel/g) ?? []).length, 1);
  assert.match(workspace, /<ScientificAnnotations/);
  assert.doesNotMatch(annotations, /role="dialog"/);
});

test('predicción y clasificación humana son visibles, editables y separadas', () => {
  for (const value of ['Predicción automática', 'P\\(parasitized\\)', 'P\\(uninfected\\)', 'Threshold', 'Clasificación humana', 'Parasitized', 'Uninfected', 'Guardar cambios']) {
    assert.match(workspace, new RegExp(value));
  }
  assert.match(api, /human-classification/);
  assert.match(workspace, /humanClassification\.label !== prediction\.predicted_label/);
  assert.match(workspace, /aria-pressed=\{reviewedLabel/);
});

test('anotaciones de célula y muestra soportan altas, edición, varias notas e historial', () => {
  assert.match(workspace, /title="ANOTACIONES"[\s\S]*targetType="cell"/);
  assert.match(immersive, /title="ANOTACIONES DE LA MUESTRA"[\s\S]*targetType="sample"/);
  assert.match(annotations, /items\.map/);
  assert.match(annotations, /\+ Agregar/);
  assert.match(annotations, />Editar</);
  assert.match(annotations, /<details onToggle/);
  assert.match(api, /method: 'PATCH'/);
  assert.match(annotations, /caught\.status === 409/);
});

test('selección, carrusel, siguiente sin revisar y modo histórico comparten estado', () => {
  assert.match(workspace, /humanByPredictionId/);
  assert.match(workspace, /annotationCountByCell/);
  assert.match(workspace, /Siguiente sin revisar/);
  assert.match(workspace, /Revisada \$\{humanLabel\}/);
  assert.match(workspace, /Requiere atención/);
  assert.match(immersive, /readOnly=\{isHistory\}/);
  assert.match(immersive, /canAnnotate=\{annotationPermissions\.canAnnotateValidation\}/);
});

test('RBAC, accesibilidad y responsive se preservan sin CSS global nuevo', () => {
  assert.match(workflow, /scientific\.validation\.read/);
  assert.match(workflow, /scientific\.validation\.annotate/);
  assert.match(annotations, /aria-live="polite"/);
  assert.match(annotations, /aria-label=\{`Agregar/);
  assert.match(css, /\.smear-analysis-immersive \.scientific-annotations/);
  assert.match(css, /@media \(max-width: 720px\)/);
});
