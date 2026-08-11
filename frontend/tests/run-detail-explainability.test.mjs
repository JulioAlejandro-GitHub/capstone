import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8');
const runDetail = read('pages/RunDetail.tsx');
const explainability = read('pages/Explainability.tsx');
const canonical = read('components/explainability/CaseExplainabilityView.tsx');
const adapters = read('components/explainability/explainabilityCaseAdapters.ts');
const smearAudit = read('components/cell-review/CellClassificationAuditModal.tsx');
const styles = read('styles.css');
const app = read('App.tsx');

test('RunDetail abre localmente el CaseDetail con el caso seleccionado', () => {
  assert.match(runDetail, /import \{ CaseDetail \} from '\.\/Explainability';/);
  assert.match(runDetail, /useState<ExplainabilityCase \| null>\(null\)/);
  assert.match(runDetail, /onClick=\{\(\) => setSelectedExplainabilityCase\(row\)\}>Ver detalle<\/button>/);
  assert.doesNotMatch(runDetail, /Ver detalle #/);
  assert.match(runDetail, /<CaseDetail[\s\S]*\?\? selectedExplainabilityCase\}[\s\S]*datasource=\{datasource\}/);
  assert.match(runDetail, /onClose=\{\(\) => setSelectedExplainabilityCase\(null\)\}/);
});

test('el detalle prefiere el Grad-CAM hermano ya generado para la misma predicción', () => {
  assert.match(runDetail, /getRunExplainability\(datasource, runId, \{ limit: 500 \}\)/);
  assert.match(runDetail, /candidate\.prediction_id === selectedExplainabilityCase\.prediction_id/);
  assert.match(runDetail, /candidate\.run_id === selectedExplainabilityCase\.run_id/);
  assert.match(runDetail, /toLowerCase\(\) === 'gradcam'/);
  assert.match(runDetail, /candidate\.success === true/);
  assert.match(runDetail, /\) \?\? selectedExplainabilityCase\}/);
});

test('cambiar el run cierra el detalle antes de cargar sus datos', () => {
  assert.match(
    runDetail,
    /useEffect\(\(\) => \{\s+setSelectedExplainabilityCase\(null\);\s+if \(!runId\) return;/,
  );
});

test('Modelo IA y frotis reutilizan la vista canónica de explicabilidad', () => {
  assert.match(explainability, /export function CaseDetail\(/);
  assert.match(explainability, /<CaseExplainabilityView/);
  assert.match(explainability, /toModelExecutionExplainabilityCase\(item, datasource\)/);
  assert.match(smearAudit, /<CaseExplainabilityView/);
  assert.match(smearAudit, /toSmearCellExplainabilityCase\(prediction, run\)/);
  assert.equal((canonical.match(/className="audit-detail-grid"/g) ?? []).length, 1);
  for (const section of ['01', 'Crop fuente', '02', 'Predicción', '03', 'Explicación Grad-CAM']) {
    assert.match(canonical, new RegExp(section));
  }
  assert.match(adapters, /ExplainabilityCaseViewModel/);
  assert.match(canonical, /className="audit-modal case-explainability-view"/);
  assert.match(styles, /\.case-explainability-view \.audit-detail-image/);
  assert.doesNotMatch(styles, /\.cell-classification-audit \.audit-detail-image/);
  assert.match(explainability, /item=\{selectedCase\}/);
  assert.match(canonical, /event\.key === 'Escape'/);
  assert.match(canonical, /aria-label="Cerrar auditoría"/);
});

test('la ruta de detalle ya no navega a Explainability desde la fila', () => {
  assert.doesNotMatch(runDetail, /onExplainabilitySelect/);
  assert.doesNotMatch(app, /onExplainabilitySelect/);
  assert.match(app, /<RunDetail datasource=\{datasource\} runId=\{trainingRunId\} \/>/);
});

test('resolver compartido distingue Grad-CAM, LIME y artefactos faltantes', () => {
  assert.match(adapters, /export function resolveExplanationArtifact/);
  assert.match(adapters, /canonicalMethod\(method\) === 'gradcam'/);
  assert.match(adapters, /status: 'not_requested'.*otherMethods/s);
  assert.match(adapters, /status: 'artifact_missing'/);
  assert.match(adapters, /explanation_artifact_availability === 'available'/);
  assert.match(adapters, /sourceAvailability === 'missing' \|\| sourceAvailability === 'not_registered'/);
  assert.match(adapters, /item\.crop_url \?\? item\.source_image_url \?\? item\.image_url/);
  assert.match(canonical, /El artefacto Grad-CAM ya no está disponible\./);
  assert.match(canonical, /La explicación visual Grad-CAM no está generada\./);
  assert.match(canonical, /Otras explicaciones disponibles:/);
});

test('generación Grad-CAM manual y síncrona vive en el render canónico', () => {
  assert.match(canonical, /onGenerate\?: \(regenerate: boolean\) => Promise<ExplainabilityCaseViewModel>/);
  assert.match(canonical, /Generar Grad-CAM/);
  assert.match(canonical, /Regenerar Grad-CAM/);
  assert.match(canonical, /Generando…/);
  assert.match(canonical, /disabled=\{!generationAllowed \|\| generationPending\}/);
  assert.match(canonical, /Grad-CAM generada/);
  assert.match(canonical, /Grad-CAM no disponible/);
  assert.match(canonical, /No cuenta con permiso para generar explicaciones Grad-CAM/);
  assert.match(canonical, /setGeneratedCase\(await onGenerate\(explanationStatus === 'artifact_missing'\)\)/);
  assert.match(canonical, /aria-live="polite"/);
  assert.doesNotMatch(explainability, />Generar Grad-CAM</);
  assert.doesNotMatch(smearAudit, />Generar Grad-CAM</);
  assert.match(explainability, /api\.generateCaseGradCam\(item\.explainability_id\)/);
  assert.match(smearAudit, /const explanation = await onGenerate\(regenerate\)/);
});
