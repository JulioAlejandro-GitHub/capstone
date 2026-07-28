import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const hook = read('src/hooks/useSmearAnalysisWorkflow.ts');
const page = read('src/pages/SmearWorkflow.tsx');
const upload = read('src/pages/SmearUpload.tsx');
const workspace = read('src/components/cell-review/CellReviewWorkspace.tsx');
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
    'detection_processing', 'review_ready', 'error',
  ]) assert.match(hook, new RegExp(`'${stage}'`));
  for (const id of [
    'ingestionBatchId', 'microscopyImageId', 'analysisRunId',
    'queueItemId', 'detectionRunId', 'selectedDetectionId',
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
  assert.match(upload, /Vista previa local/);
  assert.match(upload, /Quitar selección/);
  assert.match(upload, /Reemplazar imágenes/);
  assert.match(hook, /URL\.createObjectURL\(selectedFiles\[0\]\)/);
  assert.match(hook, /URL\.revokeObjectURL\(objectUrl\)/);
  assert.match(page, /if \(!active\)[\s\S]*URL\.revokeObjectURL\(url\)/);
  assert.match(page, /previewUrl/);
  assert.match(page, /AuthenticatedWorkflowImage/);
});

test('URL conserva IDs y recuperación sólo ejecuta lecturas', () => {
  for (const key of ['batch', 'image', 'analysis', 'queue', 'detection', 'selected']) {
    assert.match(hook, new RegExp(`'${key}'`));
  }
  assert.match(api, /\/api\/v1\/scientific\/workflows\//);
  assert.match(hook, /getSmearWorkflow/);
  assert.match(hook, /isValidPublicId/);
  assert.match(
    hook,
    /queryIdentifiers\.analysis,\s*queryIdentifiers\.batch,\s*queryIdentifiers\.detection,\s*recover,/,
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

test('detección completada reutiliza CellReviewWorkspace y persiste selección', () => {
  assert.match(page, /<CellReviewWorkspace/);
  assert.match(page, /initialMicroscopyImageId=\{identifiers\.microscopyImageId\}/);
  assert.match(page, /onMicroscopyImageChange=\{controller\.selectImage\}/);
  assert.match(page, /initialSelectedDetectionId=\{identifiers\.selectedDetectionId\}/);
  assert.match(page, /onSelectedDetectionChange=\{controller\.selectDetection\}/);
  assert.match(workspace, /initialSelectedDetectionId/);
  assert.match(workspace, /onSelectedDetectionChange/);
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
