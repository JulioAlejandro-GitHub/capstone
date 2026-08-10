import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const page = read('src/pages/SmearWorkflow.tsx');
const immersive = read('src/components/cell-review/SmearAnalysisImmersiveView.tsx');
const workspace = read('src/components/cell-review/CellReviewWorkspace.tsx');
const annotations = read('src/components/cell-review/ScientificAnnotations.tsx');
const api = read('src/services/api.ts');

test('History habilita sólo anotaciones mediante RBAC explícito', () => {
  assert.match(page, /mode="history"[\s\S]*canReadValidation: historyPermissions\.has/);
  assert.match(page, /canAnnotateValidation: historyPermissions\.has/);
  assert.match(immersive, /livePermissions = props\.mode === 'live'/);
  assert.match(immersive, /canReview=\{livePermissions\?\.canReviewDetection \?\? false\}/);
  assert.match(immersive, /canExplain=\{livePermissions\?\.canExplain \?\? false\}/);
  assert.match(immersive, /canClassificationReview=\{livePermissions\?\.canReviewClassification \?\? false\}/);
  assert.match(immersive, /canAnnotateValidation=\{annotationPermissions\.canAnnotateValidation/);
});

test('History reutiliza un único formulario para CÉLULA y MUESTRA', () => {
  assert.equal((`${workspace}\n${immersive}`.match(/<ScientificAnnotations/g) ?? []).length, 2);
  assert.match(workspace, /targetContext=\{`CÉLULA · \$\{detection\?\.cell_code/);
  assert.match(immersive, /title="ANOTACIONES DE LA MUESTRA"/);
  assert.match(immersive, /targetContext=\{`MUESTRA · \$\{workflow\.sampleCode/);
  assert.match(immersive, /targetType="sample"/);
  assert.match(annotations, /created_by_username/);
  assert.match(annotations, /updated_by_username/);
  assert.match(annotations, /Modificada/);
});

test('optimistic locking, recarga y deep link no activan el pipeline', () => {
  assert.match(annotations, /version: current\.version/);
  assert.match(annotations, /Esta anotación fue modificada por otro usuario/);
  assert.match(annotations, /await load\(\)/);
  assert.match(page, /const next = new URLSearchParams\(selectionQueryRef\.current\)/);
  assert.match(page, /setSearchParams\(next, \{ replace: true \}\)/);
  assert.doesNotMatch(annotations, /createCellExplanation|createCellClassification|createCellDetection/);
  assert.match(api, /target_type: ScientificValidationTarget/);
  assert.match(api, /sample_id\?: string/);
});
