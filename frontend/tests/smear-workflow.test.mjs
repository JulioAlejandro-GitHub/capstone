import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const hook = read('src/hooks/useSmearAnalysisWorkflow.ts');
const page = read('src/pages/SmearWorkflow.tsx');
const upload = read('src/pages/SmearUpload.tsx');
const workspace = read('src/components/cell-review/CellReviewWorkspace.tsx');
const immersive = read('src/components/cell-review/SmearAnalysisImmersiveView.tsx');
const api = read('src/services/api.ts');
const app = read('src/App.tsx');
const router = read('src/router.ts');
const navigation = read('src/components/navigation/navigationConfig.ts');
const styles = read('src/styles.css');
const feature = `${hook}\n${page}\n${upload}`;

test('declara una máquina de estados central y conserva todos los identificadores', () => {
  for (const stage of [
    'setup', 'uploading', 'ingested', 'creating_analysis', 'quality_queued',
    'quality_processing', 'quality_warning', 'quality_failed', 'ready_for_detection',
    'detection_processing', 'awaiting_productive_model', 'classification_pending',
    'classification_processing', 'classification_completed', 'classification_warning',
    'classification_failed', 'review_ready', 'error',
  ]) assert.match(hook, new RegExp(`'${stage}'`));
  for (const id of [
    'ingestionBatchId', 'microscopyImageId', 'analysisRunId',
    'queueItemId', 'detectionRunId', 'classificationRunId',
    'selectedDetectionId', 'selectedPredictionId',
  ]) assert.match(hook, new RegExp(id));
  assert.match(hook, /useState<SmearWorkflowStage>\('setup'\)/);
});

test('la acción única encadena recursos reales y la cola normal antes del quality gate', () => {
  const start = hook.slice(hook.indexOf('const start ='), hook.indexOf('const decideWarning'));
  assert.match(start, /uploadMicroscopyImages/);
  assert.match(start, /createAnalysisAndContinue/);
  const analysis = hook.slice(
    hook.indexOf('const createAnalysisAndContinue'),
    hook.indexOf('const start ='),
  );
  assert.match(analysis, /createAnalysisRun/);
  assert.match(analysis, /createQueueAndAssess/);
  const queue = hook.slice(
    hook.indexOf('const createQueueAndAssess'),
    hook.indexOf('const createAnalysisAndContinue'),
  );
  assert.match(queue, /enqueueQuality\(analysisRun\.id,\s*50\)/);
  assert.match(queue, /executeQueuedQuality/);
  const quality = hook.slice(
    hook.indexOf('const executeQueuedQuality'),
    hook.indexOf('const createQueueAndAssess'),
  );
  assert.match(quality, /executeQueueItem/);
  assert.match(quality, /getAnalysisRun/);
  assert.match(quality, /evaluateQuality/);
});

test('bloquea doble envío antes del rerender y no usa procesamiento automático', () => {
  assert.match(hook, /const activeAction = useRef\(false\)/);
  assert.match(hook, /if \(activeAction\.current\) return/);
  assert.match(hook, /activeAction\.current = true/);
  assert.match(hook, /client_request_id:\s*uploadRequestId/);
  assert.match(hook, /setUploadRequestId\(createUploadRequestId\(\)\)/);
  assert.doesNotMatch(feature, /setInterval|WebSocket|EventSource|polling/i);
});

test('preview local es inmediata, reemplazable y revoca object URLs', () => {
  assert.match(upload, /Vista previa de/);
  assert.match(upload, />Quitar</);
  assert.match(upload, />Reemplazar</);
  assert.match(hook, /URL\.createObjectURL\(selectedFiles\[0\]\)/);
  assert.match(hook, /URL\.revokeObjectURL\(objectUrl\)/);
  assert.match(page, /if \(!active\)[\s\S]*URL\.revokeObjectURL\(url\)/);
  assert.match(page, /previewUrl/);
  assert.match(page, /AuthenticatedWorkflowImage/);
});

test('setup Liquid Glass conserva datos reales y estructura 4/8', () => {
  for (const text of [
    'Datos de muestra', 'ID PACIENTE', 'ID MUESTRA', 'TIPO',
    'Frotis de sangre periférica', 'Cargar imagen de frotis', 'INICIAR ANÁLISIS',
  ]) assert.match(upload, new RegExp(text));
  assert.match(upload, /automatic_new/);
  assert.match(upload, /lookupScientificSubject/);
  assert.match(upload, /getScientificSamples/);
  assert.match(styles, /\.smear-setup__sample-column[\s\S]*grid-column:\s*span 4/);
  assert.match(styles, /\.smear-setup__upload-column[\s\S]*grid-column:\s*span 8/);
});

test('dropzone admite clic, teclado, drag and drop y rechazo de formatos', () => {
  assert.match(upload, /onDragEnter/);
  assert.match(upload, /onDragOver/);
  assert.match(upload, /onDragLeave/);
  assert.match(upload, /onDrop=\{handleDrop\}/);
  assert.match(upload, /event\.key === 'Enter' \|\| event\.key === ' '/);
  assert.match(upload, /ACCEPTED_TYPES/);
  assert.match(upload, /no es compatible/);
  assert.match(upload, /aria-live="polite"/);
  assert.match(upload, /Suelte la imagen para cargarla/);
});

test('preview muestra metadatos y usa el microscopio local adjunto', () => {
  assert.match(upload, /smear-microscope\.jpg/);
  assert.match(upload, /naturalWidth/);
  assert.match(upload, /naturalHeight/);
  for (const label of ['Archivo', 'Formato', 'Dimensiones', 'Tamaño']) {
    assert.match(upload, new RegExp(`<dt>${label}</dt>`));
  }
  assert.doesNotMatch(upload, /https?:\/\//);
});

test('URL conserva IDs y recuperación sólo ejecuta lecturas', () => {
  for (const key of [
    'batch', 'image', 'analysis', 'queue', 'detection', 'classification',
    'selected_detection', 'selected_prediction',
  ]) {
    assert.match(hook, new RegExp(`'${key}'`));
  }
  assert.match(api, /\/api\/v1\/scientific\/workflows\//);
  assert.match(hook, /getSmearWorkflow/);
  assert.match(hook, /isValidPublicId/);
  assert.match(hook, /const workflowQueryRef = useRef\(searchParams\)/);
  assert.match(hook, /workflowQueryRef\.current = searchParams/);
  assert.match(hook, /new URLSearchParams\(workflowQueryRef\.current\)/);
  assert.ok(
    hook.indexOf('workflowQueryRef.current = next')
      < hook.indexOf('setSearchParams(next, { replace: true })'),
  );
  assert.match(
    hook,
    /queryIdentifiers\.analysis,\s*queryIdentifiers\.batch,\s*queryIdentifiers\.classification,\s*queryIdentifiers\.detection,\s*recover,/,
  );
  const recovery = hook.slice(hook.indexOf('const recover ='), hook.indexOf('useEffect(() => {'));
  assert.doesNotMatch(
    recovery,
    /uploadMicroscopyImages|createAnalysisRun|enqueueQuality|executeQueueItem|createCellDetectionRun/,
  );
});

test('pass continúa; warning y fail detienen; warning aprobado continúa', () => {
  const quality = hook.slice(
    hook.indexOf('const evaluateQuality'),
    hook.indexOf('const executeQueuedQuality'),
  );
  assert.match(quality, /quality_gate_status === 'warning'/);
  assert.match(quality, /setStage\('quality_warning'\)/);
  assert.match(quality, /quality_gate_status === 'fail'/);
  assert.match(quality, /setStage\('quality_failed'\)/);
  assert.match(quality, /ready_for_analysis/);
  assert.match(quality, /executeDetection/);
  assert.match(page, /Aprobación técnica/);
  assert.match(page, /Quality gate aprobado/);
  assert.match(page, /Aprobar con advertencias/);
  assert.match(page, /Bloquear análisis/);
  assert.match(hook, /decision === 'approve_with_warnings'[\s\S]*executeDetection/);
});

test('errores conservan recursos y ofrecen retry desde la etapa fallida', () => {
  assert.match(page, /Los recursos creados correctamente permanecen disponibles/);
  assert.match(page, /Reintentar desde esta etapa/);
  assert.match(hook, /failure\.step === 'analysis'/);
  assert.match(hook, /failure\.step === 'queue'/);
  assert.match(hook, /failure\.step === 'detection'/);
  assert.match(page, /Reingresar a cola/);
});

test('detección completada reutiliza SmearAnalysisImmersiveView y persiste selección', () => {
  assert.match(page, /<SmearAnalysisImmersiveView/);
  assert.match(page, /mode="live"/);
  assert.match(page, /mode === 'review' \? ' smear-workflow--immersive' : ''/);
  assert.match(page, /microscopyImageId: identifiers\.microscopyImageId/);
  assert.match(page, /onImageChange: controller\.selectImage/);
  assert.match(page, /selectedDetectionId: identifiers\.selectedDetectionId/);
  assert.match(page, /onDetectionChange: controller\.selectDetection/);
  assert.match(page, /selectedPredictionId: identifiers\.selectedPredictionId/);
  assert.match(page, /onPredictionChange: controller\.selectPrediction/);
  assert.match(workspace, /initialSelectedDetectionId/);
  assert.match(workspace, /onSelectedDetectionChange/);
  assert.match(immersive, /<CellReviewWorkspace/);
  assert.equal((immersive.match(/<CellReviewWorkspace/g) ?? []).length, 1);
});

test('ruta canónica y aliases legacy comparten el workflow sin tocar Modelo IA', () => {
  assert.match(router, /smearWorkflow:\s*'\/frotis\/analizar'/);
  assert.match(app, /routes\.smearWorkflow.*<SmearWorkflow/s);
  for (const legacy of ['smearUpload', 'smearAnalysis', 'smearReview']) {
    assert.match(app, new RegExp(`routes\\.${legacy}.*<LegacySmearRedirect`));
  }
  assert.match(app, /LegacySmearRedirect[\s\S]*Navigate replace/);
  assert.equal((navigation.match(/label: 'Analizar imagen'/g) ?? []).length, 1);
  assert.equal((navigation.match(/label: 'Modelo IA'/g) ?? []).length, 1);
});

test('muestra imagen, etapas y actividad real sin porcentajes de proceso inventados', () => {
  for (const text of [
    'Imagen recibida', 'Integridad verificada', 'Control de calidad',
    'Lista para análisis', 'Detección celular', 'Revisión disponible',
  ]) assert.match(page, new RegExp(text));
  assert.match(page, /run\?\.events/);
  assert.match(page, /milestoneTimes/);
  assert.match(page, /<time>\{milestoneTime\}<\/time>/);
  assert.doesNotMatch(page, /Math\.random|fakeProgress|simulatedProgress/);
});

test('RBAC gobierna ejecución, warnings y revisión celular', () => {
  for (const permission of [
    'scientific.images.register',
    'scientific.analysis.create',
    'scientific.analysis.queue.create',
    'scientific.analysis.queue.execute',
    'scientific.analysis.queue.retry',
    'scientific.analysis.quality.review',
    'scientific.cell_detection.execute',
    'scientific.cell_detection.read',
    'scientific.cell_detection.review',
  ]) assert.match(page, new RegExp(permission.replaceAll('.', '\\.')));
  assert.match(page, /Tu rol puede visualizar el resultado/);
});

test('estilos del workflow son scoped, responsive y respetan reduced motion', () => {
  assert.match(styles, /\.smear-workflow/);
  assert.match(styles, /\.workflow-processing-grid/);
  assert.match(styles, /\.workflow-mobile-tabs/);
  assert.match(styles, /@media\s*\(max-width:\s*1200px\)/);
  assert.match(styles, /@media\s*\(max-width:\s*700px\)/);
  assert.match(styles, /prefers-reduced-motion:\s*reduce/);
});
