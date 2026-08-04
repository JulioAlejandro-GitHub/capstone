import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const hook = read('src/hooks/useSmearAnalysisWorkflow.ts');
const page = read('src/pages/SmearWorkflow.tsx');
const workspace = read('src/components/cell-review/CellReviewWorkspace.tsx');
const viewer = read('src/components/cell-review/CellImageViewer.tsx');
const gradCamPreview = read('src/components/cell-review/CellGradCamPreview.tsx');
const modal = read('src/components/cell-review/CellClassificationAuditModal.tsx');
const immersiveView = read('src/components/cell-review/SmearAnalysisImmersiveView.tsx');
const api = read('src/services/api.ts');
const types = read('src/types/cellClassification.ts');
const history = read('src/pages/SmearAnalysisHistory.tsx');
const styles = read('src/styles.css');
const feature = `${hook}\n${page}\n${workspace}\n${viewer}\n${modal}\n${api}\n${types}`;

test('workflow incorpora Clasificación IA sin agregarla a Modelo IA', () => {
  for (const label of [
    'Carga',
    'Calidad de muestra',
    'Detección',
    'Clasificación IA',
    'Revisión y resultado',
  ]) assert.match(page, new RegExp(label));
  assert.match(styles, /workflow-stage-nav[\s\S]*repeat\(5,/);
  assert.doesNotMatch(
    read('src/components/navigation/navigationConfig.ts'),
    /id: 'model-ai'[\s\S]*label: 'Clasificación IA'/,
  );
});

test('detección terminada resuelve elegibilidad e inicia clasificación productiva', () => {
  const classification = hook.slice(
    hook.indexOf('const executeClassification'),
    hook.indexOf('const executeDetection'),
  );
  assert.match(classification, /getEligibleCellClassificationRuns/);
  assert.match(classification, /productive_model/);
  assert.match(classification, /createCellClassificationRun\(detectionRun\.id\)/);
  assert.match(classification, /getCellClassificationSummary/);
  const detection = hook.slice(
    hook.indexOf('const executeDetection'),
    hook.indexOf('const evaluateQuality'),
  );
  assert.match(detection, /await executeClassification\(detectionRun\)/);
  assert.doesNotMatch(feature, /setInterval|WebSocket|EventSource|Celery|Redis/);
});

test('cliente no puede elegir modelo, checkpoint, mapping ni threshold', () => {
  const create = api.slice(
    api.indexOf('createCellClassificationRun'),
    api.indexOf('getCellClassificationRuns'),
  );
  assert.match(create, /JSON\.stringify\(\{\s*detection_run_id:\s*detectionRunId\s*\}\)/);
  assert.doesNotMatch(
    create,
    /model_id|production_model_id|checkpoint|threshold|label_mapping|preprocessing/,
  );
  assert.doesNotMatch(feature, /threshold\s*\?\?\s*0\.5|threshold\s*\|\|\s*0\.5/);
});

test('cliente preserva error HTTP estructurado y distingue abort, red y parseo', () => {
  for (const field of [
    'status',
    'code',
    'classificationRunId',
    'stage',
    'retryable',
  ]) assert.match(api, new RegExp(field));
  assert.match(api, /kind: 'http' \| 'network' \| 'timeout' \| 'abort' \| 'parse'/);
  assert.match(api, /detail\.classification_run_id/);
  assert.match(api, /error\.name === 'AbortError'/);
  assert.match(api, /error instanceof TypeError/);
  assert.match(api, /respuesta JSON inválida/);
});

test('ausencia de modelo detiene el flujo sin fallback y retry es manual', () => {
  assert.match(hook, /reasonCode\.startsWith\('PRODUCTIVE_'\)/);
  assert.match(
    hook,
    /productiveModelBlocked[\s\S]*'awaiting_productive_model'[\s\S]*'classification_failed'/,
  );
  assert.match(page, /No se seleccionó un modelo alternativo ni se aplicó un threshold por defecto/);
  assert.match(page, /Verificar nuevamente/);
  assert.match(page, /Reintentar desde esta etapa/);
  assert.match(hook, /failure\.step === 'classification'[\s\S]*executeClassification/);
  assert.doesNotMatch(hook, /setTimeout\([^)]*executeClassification|setInterval/);
});

test('URL canónica reconstruye classification y selección sólo mediante GET', () => {
  for (const key of [
    'classification',
    'selected_detection',
    'selected_prediction',
  ]) assert.match(hook, new RegExp(`'${key}'`));
  const recovery = hook.slice(
    hook.indexOf('const recover ='),
    hook.indexOf('useEffect(() => {', hook.indexOf('const recover =')),
  );
  for (const query of [
    'getCellPrediction',
    'getCellClassificationRun',
    'getCellClassificationRuns',
    'getCellClassificationSummary',
    'getSmearWorkflow',
  ]) assert.match(recovery, new RegExp(query));
  assert.doesNotMatch(
    recovery,
    /createCellClassificationRun|createCellExplanation|createCellClassificationReview/,
  );
});

test('workspace presenta modelo, threshold, predicciones y filtros científicos', () => {
  for (const text of [
    'Modelo',
    'Versión',
    'Threshold',
    'Fuente threshold',
    'Predichas parasitized',
    'Predichas uninfected',
    'Próximas al threshold',
    'Sin clasificar o fallidas',
    'Sin revisión',
    'Confirmadas',
    'Corregidas',
    'Requieren atención',
    'P\\(parasitized\\)',
    'P\\(uninfected\\)',
  ]) assert.match(workspace, new RegExp(text));
  assert.match(workspace, /classificationFilter === 'parasitized'/);
  assert.match(workspace, /classificationFilter === 'uninfected'/);
  assert.match(workspace, /classificationFilter === 'near_threshold'/);
  assert.match(workspace, /predictionByDetectionId/);
});

test('crop y bbox permanecen sincronizados y el overlay cambia por tres modos', () => {
  assert.match(workspace, /onDetectionSelect=\{selectDetection\}/);
  assert.match(workspace, /classificationAnnotations=\{predictionByDetectionId\}/);
  for (const mode of ['detection', 'prediction', 'classification_review']) {
    assert.match(viewer, new RegExp(`'${mode}'`));
  }
  for (const label of [
    'Estado de detección',
    'Predicción IA',
    'Revisión humana',
  ]) assert.match(viewer, new RegExp(label));
  assert.match(viewer, /visual\.symbol/);
});

test('detalle conserva predicción automática inmutable y revisión separada', () => {
  for (const label of [
    'Predicción automática inmutable',
    'P\\(parasitized\\)',
    'P\\(uninfected\\)',
    'Margen de decisión',
    'Próxima al threshold',
    'Checkpoint',
    'Preprocessing',
    'Revisión humana de detección',
    'Revisión humana de clasificación',
    'Historial de clasificación',
  ]) assert.match(workspace, new RegExp(label));
  assert.match(types, /CanonicalCellLabel = 'uninfected' \| 'parasitized'/);
  assert.doesNotMatch(api, /PUT|PATCH.*cell-classification/);
});

test('Grad-CAM se genera sólo por acción explícita y retry failed se declara', () => {
  assert.match(workspace, /onClick=\{onGenerateExplanation\}/);
  assert.match(workspace, /Generar explicación/);
  assert.match(workspace, /target\.explanation\?\.status === 'failed'/);
  assert.match(api, /createCellExplanation\(predictionId:\s*string,\s*retry\s*=\s*false\)/);
  assert.match(api, /JSON\.stringify\(\{\s*retry\s*\}\)/);
  assert.match(workspace, /El modelo productivo no admite Grad-CAM con la configuración registrada/);
  assert.match(workspace, /<CellGradCamPreview prediction=\{prediction\}/);
  assert.match(gradCamPreview, /role="tablist"/);
  for (const tab of ['Crop original', 'Heatmap', 'Overlay']) {
    assert.match(gradCamPreview, new RegExp(tab));
  }
  assert.match(gradCamPreview, /disabled=\{id !== 'original' && !generated\}/);
  assert.match(workspace, /onClick=\{onAudit\}>Auditar clasificación/);
  assert.doesNotMatch(gradCamPreview, /createCellExplanation/);
  assert.doesNotMatch(hook, /createCellExplanation/);
});

test('modal audita exactamente una célula con crop, predicción y Grad-CAM', () => {
  assert.match(workspace, /setAuditOpen\(true\)/);
  assert.match(workspace, /<CellClassificationAuditModal/);
  assert.match(modal, /Clasificación de \{prediction\.cell_code\}/);
  for (const panel of ['Crop fuente', 'Predicción', 'Explicación Grad-CAM']) {
    assert.match(modal, new RegExp(panel));
  }
  assert.match(modal, /getCellExplanationHeatmapBlob/);
  assert.match(modal, /getCellExplanationOverlayBlob/);
  assert.doesNotMatch(modal, /storage_key|relative_storage_key|\/Users\//);
});

test('revisión de clasificación valida corrección y atención antes del POST', () => {
  assert.match(api, /createCellClassificationReview/);
  assert.match(workspace, /decision === 'corrected' && !comment/);
  assert.match(workspace, /reviewed_label: decision === 'corrected' \? reviewedLabel : undefined/);
  assert.match(workspace, /decision === 'needs_attention' \|\| decision === 'comment_only'/);
  for (const action of [
    'Confirmar predicción',
    'Corregir clasificación',
    'Requiere atención',
    'Agregar comentario',
  ]) assert.match(workspace, new RegExp(action));
});

test('resultado agregado usa terminología experimental y disclaimers', () => {
  assert.match(workspace, /Resultado experimental del análisis/);
  for (const metric of [
    'Elegibles',
    'Clasificadas',
    'Candidatos parasitized',
    'Candidatos uninfected',
    'Fracción experimental',
    'Probabilidad máxima',
    'Resumen automático ≠ Resumen revisado',
  ]) assert.match(workspace, new RegExp(metric));
  assert.match(workspace, /no constituye un diagnóstico clínico/);
  assert.match(workspace, /Esto no descarta malaria ni reemplaza la revisión experta/);
  assert.doesNotMatch(workspace, /\bParasitemia\b|diagnóstico definitivo/i);
});

test('RBAC separa execute, read, explain y review', () => {
  for (const permission of [
    'scientific.cell_classification.execute',
    'scientific.cell_classification.read',
    'scientific.cell_classification.explain',
    'scientific.cell_classification.review',
  ]) assert.match(page, new RegExp(permission.replaceAll('.', '\\.')));
  assert.match(workspace, /canExplain && !readOnly/);
  assert.match(workspace, /canClassificationReview && !readOnly/);
});

test('historial reutiliza la vista inmersiva mediante una unión de solo lectura', () => {
  assert.match(history, /SmearAnalysisReadOnlyView/);
  const readOnlyView = page.slice(
    page.indexOf('export function SmearAnalysisReadOnlyView'),
    page.indexOf('export function SmearWorkflow'),
  );
  assert.match(readOnlyView, /<SmearAnalysisImmersiveView/);
  assert.match(readOnlyView, /classificationRunId: workflow\.classification_run\?\.id/);
  assert.match(readOnlyView, /mode="history"/);
  assert.doesNotMatch(readOnlyView, /permissions=\{/);
  assert.match(
    immersiveView,
    /type SmearAnalysisHistoryViewProps[\s\S]*mode: 'history';[\s\S]*permissions\?: never/,
  );
  assert.match(
    immersiveView,
    /SmearAnalysisImmersiveViewProps\s*=[\s\S]*SmearAnalysisLiveViewProps[\s\S]*SmearAnalysisHistoryViewProps/,
  );
  assert.match(immersiveView, /canExplain=\{livePermissions\?\.canExplain \?\? false\}/);
  assert.match(
    immersiveView,
    /canClassificationReview=\{livePermissions\?\.canReviewClassification \?\? false\}/,
  );
  assert.match(immersiveView, /readOnly=\{isHistory\}/);
  assert.doesNotMatch(
    readOnlyView,
    /createCellClassificationRun|createCellExplanation|createCellClassificationReview/,
  );
});

test('artefactos explicativos usan blobs autenticados y object URLs revocables', () => {
  const authenticated = read('src/components/cell-review/AuthenticatedCellImage.tsx');
  assert.match(api, /getCellExplanationHeatmapBlob/);
  assert.match(api, /getCellExplanationOverlayBlob/);
  assert.match(api, /requestBlob/);
  assert.match(authenticated, /URL\.createObjectURL/);
  assert.match(authenticated, /URL\.revokeObjectURL/);
  assert.match(gradCamPreview, /`\$\{explanation\.id\}:\$\{mode\}`/);
  assert.match(modal, /`\$\{explanation\.id\}:\$\{kind\}`/);
  assert.doesNotMatch(types + workspace + modal, /checkpoint_path|storage_key|relative_storage_key/);
});
