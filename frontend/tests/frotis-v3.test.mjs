// CAPSTONE-MICROSCOPE-01B.1 — Análisis de frotis v3: integración, navegación y coexistencia v1/v2/v3.
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const { MemoryRouter } = require('react-router-dom');
const root = fileURLToPath(new URL('../src/', import.meta.url));
const v3Root = resolve(root, 'features/analisis-frotis-v3');
const read = (path) => readFileSync(resolve(root, path), 'utf8');

function loader(mocks = {}) {
  const cache = new Map();
  const load = (filename) => {
    const path = resolve(root, filename);
    if (cache.has(path)) return cache.get(path);
    const module = { exports: {} };
    cache.set(path, module.exports);
    const code = ts.transpileModule(readFileSync(path, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText;
    runInNewContext(code, {
      exports: module.exports,
      URLSearchParams,
      URL,
      window: { location: { origin: 'http://capstone.test' } },
      require: (name) => {
        if (name in mocks) return mocks[name];
        if (name.endsWith('.css')) return {};
        if (!name.startsWith('.')) return require(name);
        const base = resolve(dirname(path), name);
        const target = [base, `${base}.tsx`, `${base}.ts`].find(existsSync);
        if (!target) throw new Error(`Cannot load ${name} from ${path}`);
        return load(target);
      },
    });
    return module.exports;
  };
  return load;
}

const walk = (dir) => readdirSync(dir, { withFileTypes: true }).flatMap((entry) => (
  entry.isDirectory() ? walk(resolve(dir, entry.name)) : [resolve(dir, entry.name)]
));
const v3Files = walk(v3Root);
const v3Sources = v3Files.filter((file) => /\.(ts|tsx)$/.test(file));
const v3Styles = v3Files.filter((file) => file.endsWith('.css'));

const load = loader();
const router = load('router.ts');
const v3Routes = load('features/analisis-frotis-v3/routes.ts');
const navigation = load('components/navigation/navigationConfig.ts');
const deepLink = load('features/analisis-frotis-v3/adapters/deepLink.ts');
const model = load('features/analisis-frotis-v3/adapters/analysisModel.ts');
const liveActions = load('features/analisis-frotis-v3/adapters/liveActions.ts');

const app = read('App.tsx');
const history = read('pages/SmearAnalysisHistory.tsx');
const REAL_ANALYSIS = '0eaed5d3-9e9a-4aac-8003-d207be388823';
const IMAGE_A = '11111111-1111-4111-8111-111111111111';
const IMAGE_B = '22222222-2222-4222-8222-222222222222';

// ---------------------------------------------------------------- Navegación principal

test('menú: «Análisis de frotis v3» es una opción propia inmediatamente debajo de v2', () => {
  const items = navigation.navigationModules
    .find((module) => module.id === 'smear-analysis').groups.flatMap((group) => group.items);
  const v2 = items.findIndex((item) => item.label === 'Análisis de frotis v2');
  assert.ok(v2 >= 0, 'v2 sigue en el menú');
  assert.equal(items[v2 + 1].label, 'Análisis de frotis v3');
  assert.equal(items[v2 + 1].path, '/frotis/microscopio');
  assert.equal(items[v2 + 1].icon, 'microscope');
});

test('menú: v1, v2 y v3 coexisten con ids, etiquetas y destinos distintos', () => {
  const items = navigation.navigationItems;
  const byLabel = (label) => ({ map: (pick) => [...items].filter((item) => item.label === label).map(pick) });
  assert.deepEqual(byLabel('Analizar imagen').map((item) => item.path), ['/frotis/analizar']);
  assert.deepEqual(byLabel('Análisis de frotis v2').map((item) => item.path), ['/frotis/analisis-2']);
  assert.deepEqual(byLabel('Análisis de frotis v3').map((item) => item.path), ['/frotis/microscopio']);
  assert.deepEqual(byLabel('Historial de análisis').map((item) => item.path), ['/frotis/historial']);
  assert.equal(new Set(items.map((item) => item.id)).size, items.length);
  assert.equal(new Set(items.map((item) => item.path)).size, items.length);
});

test('menú: cada ruta de frotis resuelve su propia sección (ninguna versión absorbe a otra)', () => {
  const section = (path) => navigation.sectionForPath(path)?.label;
  assert.equal(section('/frotis/analizar'), 'Analizar imagen');
  assert.equal(section('/frotis/analisis-2/review-cells'), 'Análisis de frotis v2');
  assert.equal(section('/frotis/microscopio'), 'Análisis de frotis v3');
  assert.equal(section(`/frotis/microscopio/${REAL_ANALYSIS}`), 'Análisis de frotis v3');
  assert.equal(section(`/frotis/historial/${REAL_ANALYSIS}`), 'Historial de análisis');
});

// ---------------------------------------------------------------- Rutas

test('rutas: v3 añade solo /frotis/microscopio y /frotis/microscopio/:analysisId', () => {
  assert.equal(router.routes.smearMicroscope, '/frotis/microscopio');
  assert.equal(router.routes.smearMicroscopeAnalysis(REAL_ANALYSIS), `/frotis/microscopio/${REAL_ANALYSIS}`);
  assert.equal(v3Routes.frotis3Base, router.routes.smearMicroscope);
  assert.equal(v3Routes.microscopeAnalysisPath(REAL_ANALYSIS), router.routes.smearMicroscopeAnalysis(REAL_ANALYSIS));
  assert.equal(v3Routes.frotis3RoutePattern, '/frotis/microscopio/:analysisId?');
  assert.match(app, /<Route path=\{frotis3RoutePattern\} element=\{<MicroscopioPage \/>\} \/>/);
});

test('rutas: v1, v2 e historial conservan sus rutas y elementos originales', () => {
  assert.equal(router.routes.smearWorkflow, '/frotis/analizar');
  assert.equal(router.routes.smearAnalysis2, '/frotis/analisis-2');
  assert.equal(router.routes.smearHistory, '/frotis/historial');
  assert.equal(router.routes.smearHistoryDetail(REAL_ANALYSIS), `/frotis/historial/${REAL_ANALYSIS}`);
  assert.match(app, /<Route path=\{routes\.smearWorkflow\} element=\{<SmearWorkflow \/>\} \/>/);
  assert.match(app, /<Route path=\{routes\.smearAnalysis2\} element=\{<AnalisisFrotis2Page \/>\}>/);
  assert.match(app, /<Route path=\{routes\.smearHistory\} element=\{<SmearAnalysisHistory \/>\} \/>/);
  assert.match(app, /<Route path=\{`\$\{routes\.smearHistory\}\/:analysisRunId`\} element=\{<SmearHistoryDetailRoute \/>\} \/>/);
});

test('rutas: no existen redirects de v1/v2/historial hacia v3', () => {
  assert.doesNotMatch(app, /Navigate[^\n]*(smearMicroscope|frotis3|microscopio)/);
  const legacy = app.slice(app.indexOf('function LegacySmearRedirect'), app.indexOf('function App()'));
  assert.match(legacy, /routes\.smearWorkflow/);
  assert.doesNotMatch(legacy, /microscop/i);
});

test('rutas: el workspace valida el UUID antes de consultar la API', () => {
  const page = read('features/analisis-frotis-v3/MicroscopioPage.tsx');
  assert.match(page, /routeAnalysisId && !isValidPublicId\(routeAnalysisId\)/);
  assert.ok(page.indexOf('isValidPublicId(routeAnalysisId)') < page.indexOf('<ExistingAnalysisSession'));
  assert.equal(router.isValidPublicId(REAL_ANALYSIS), true);
  assert.equal(router.isValidPublicId('no-es-uuid'), false);
});

// ---------------------------------------------------------------- Historial

test('historial: conserva «Ver detalle» intacto y suma el acceso al microscopio', () => {
  assert.match(
    history,
    /<Link className="history-detail-link" to=\{`\$\{routes\.smearHistoryDetail\(item\.analysis_run_id\)\}\$\{location\.search\}`\}>Ver detalle<\/Link>/,
  );
  assert.match(history, /Ver detalle<\/Link><MicroscopeAccessLink analysisId=\{item\.analysis_run_id\} \/><\/td>/);
});

test('historial: el icono usa el UUID real de la fila, tooltip, nombre accesible y solo datasource', () => {
  const { MicroscopeAccessLink } = load('features/analisis-frotis-v3/components/MicroscopeAccessLink.tsx');
  const html = renderToStaticMarkup(React.createElement(
    MemoryRouter,
    { initialEntries: ['/frotis/historial?datasource=malaria&image=x&selected_detection=y'] },
    React.createElement(MicroscopeAccessLink, { analysisId: REAL_ANALYSIS }),
  ));
  assert.match(html, new RegExp(`href="/frotis/microscopio/${REAL_ANALYSIS}\\?datasource=malaria"`));
  assert.match(html, /aria-label="Abrir análisis en Microscopio Digital"/);
  assert.match(html, /title="Abrir en Microscopio Digital"/);
  assert.match(html, /<svg[^>]*aria-hidden="true"/);
  assert.doesNotMatch(html, /image=|selected_detection=/);
});

test('historial: sin identificador válido el acceso queda deshabilitado y no navega', () => {
  const { MicroscopeAccessLink } = load('features/analisis-frotis-v3/components/MicroscopeAccessLink.tsx');
  const html = renderToStaticMarkup(React.createElement(
    MemoryRouter,
    { initialEntries: ['/frotis/historial'] },
    React.createElement(MicroscopeAccessLink, { analysisId: 'fila-sin-uuid' }),
  ));
  assert.match(html, /aria-disabled="true"/);
  assert.doesNotMatch(html, /href=/);
  const source = read('features/analisis-frotis-v3/components/MicroscopeAccessLink.tsx');
  assert.doesNotMatch(source, /[0-9a-f]{8}-[0-9a-f]{4}-/i, 'sin UUID fijo ni simulado');
});

// ---------------------------------------------------------------- Deep links

test('deep link: lee image/selected_detection/selected_prediction y descarta formatos inválidos', () => {
  const params = new URLSearchParams({
    image: IMAGE_A, selected_detection: 'roto', selected_prediction: IMAGE_B, datasource: 'malaria',
  });
  const request = deepLink.readDeepLink(params, router.isValidPublicId);
  assert.equal(request.imageId, IMAGE_A);
  assert.equal(request.detectionId, null);
  assert.equal(request.predictionId, IMAGE_B);
  assert.equal(request.issues.length, 1);
  assert.equal(request.issues[0].param, 'selected_detection');
  assert.equal(request.issues[0].reason, 'invalid_format');
});

test('deep link: prioridad URL → contexto persistido → selección inicial determinista', () => {
  const imageIds = [IMAGE_A, IMAGE_B];
  const resolve_ = (urlImageId, persistedImageId) => deepLink.resolveActiveImage({ urlImageId, persistedImageId, imageIds });
  assert.deepEqual({ ...resolve_(IMAGE_B, IMAGE_A) }, { imageId: IMAGE_B, source: 'url', issue: null });
  assert.equal(resolve_(null, IMAGE_B).source, 'persisted');
  assert.equal(resolve_(null, IMAGE_B).imageId, IMAGE_B);
  assert.equal(resolve_(null, null).source, 'initial');
  assert.equal(resolve_(null, null).imageId, IMAGE_A);
});

test('deep link: una imagen de otro análisis se rechaza con aviso y no se adopta', () => {
  const foreign = '99999999-9999-4999-8999-999999999999';
  const resolution = deepLink.resolveActiveImage({ urlImageId: foreign, persistedImageId: foreign, imageIds: [IMAGE_A] });
  assert.equal(resolution.imageId, IMAGE_A);
  assert.equal(resolution.source, 'initial');
  assert.equal(resolution.issue.reason, 'not_in_analysis');
  assert.match(deepLink.describeDeepLinkIssue(resolution.issue), /no pertenece a este análisis/);
  assert.equal(deepLink.resolveActiveImage({ urlImageId: null, persistedImageId: null, imageIds: [] }).source, 'none');
});

// ---------------------------------------------------------------- Modelo de presentación

const workflowResponse = (overrides = {}) => ({
  stage: 'classification_completed',
  batch: { id: 'batch-1', status: 'complete', created_at: '2026-10-01T10:00:00Z' },
  subject: { id: 's', subject_code: 'SUBJ-1', status: 'active' },
  case: { id: 'c', case_code: 'CASE-1', status: 'active' },
  sample: { id: 'm', sample_code: 'SAMP-1', status: 'active' },
  slide: { id: 'l', slide_code: 'SLIDE-1', status: 'active' },
  images: [
    { id: IMAGE_B, original_filename: 'b.png', width_px: 200, height_px: 100, image_sequence_number: 2, mime_type: 'image/png' },
    { id: IMAGE_A, original_filename: 'a.png', width_px: 400, height_px: 300, image_sequence_number: 1, mime_type: 'image/png' },
  ],
  analysis_run: { id: REAL_ANALYSIS, run_code: 'RUN-1', quality_gate_status: 'pass', created_at: '2026-10-01T10:01:00Z', completed_at: null },
  queue_item: null,
  detection_run: {
    id: 'det-1', status: 'completed', detection_count: 37, reviewed_count: 5, pending_review_count: 32,
    images: [{ microscopy_image_id: IMAGE_A, detection_count: 30 }, { microscopy_image_id: IMAGE_B, detection_count: 7 }],
  },
  classification_run: { id: 'cls-1', status: 'completed', model_name: 'cnn', model_version: '3' },
  classification_summary: { classified_cell_count: 37, parasitized_candidate_count: 4, uninfected_candidate_count: 33, near_threshold_count: 1 },
  ...overrides,
});

test('modelo: conserva identificadores y conteos reales, y ordena las imágenes por secuencia', () => {
  const analysis = model.analysisFromWorkflow(workflowResponse());
  assert.equal(analysis.analysisRunId, REAL_ANALYSIS);
  assert.equal(analysis.slideCode, 'SLIDE-1');
  assert.deepEqual(analysis.images.map((image) => image.id), [IMAGE_A, IMAGE_B]);
  assert.equal(analysis.images[0].detectionCount, 30);
  assert.equal(analysis.detection.detectionCount, 37);
  assert.equal(analysis.detection.pendingReviewCount, 32);
  assert.equal(analysis.classification.parasitizedCandidateCount, 4);
  assert.equal(analysis.phase, 'microscope');
});

test('modelo: lo que el backend no entrega queda en null (no se inventan métricas)', () => {
  const analysis = model.analysisFromWorkflow(workflowResponse({
    stage: 'review_ready', classification_run: null, classification_summary: null,
  }));
  assert.equal(analysis.classification, null);
  const withoutSummary = model.analysisFromWorkflow(workflowResponse({ classification_summary: null }));
  assert.equal(withoutSummary.classification.classifiedCount, null);
  assert.equal(withoutSummary.classification.parasitizedCandidateCount, null);
  const withoutDetection = model.analysisFromWorkflow(workflowResponse({
    stage: 'quality_processing', detection_run: null, classification_run: null, classification_summary: null,
  }));
  assert.equal(withoutDetection.detection, null);
  assert.equal(withoutDetection.images[0].detectionCount, null);
});

test('modelo: cada estado científico cae en una fase del instrumento; lo desconocido nunca es resultado', () => {
  assert.equal(model.phaseForStage('quality_processing'), 'technical_review');
  assert.equal(model.phaseForStage('ready_for_detection'), 'technical_review');
  assert.equal(model.phaseForStage('quality_warning'), 'attention');
  assert.equal(model.phaseForStage('quality_failed'), 'halted');
  assert.equal(model.phaseForStage('error'), 'halted');
  assert.equal(model.phaseForStage('classification_completed'), 'microscope');
  assert.equal(model.phaseForStage('awaiting_productive_model'), 'microscope');
  assert.equal(model.phaseForStage('estado_futuro'), 'halted');
  assert.match(model.stageLabel('estado_futuro'), /no reconocido/);
});

test('modelo: la línea de escaneo solo corresponde a procesos activos informados por el backend', () => {
  for (const stage of ['quality_processing', 'detection_processing', 'classification_processing']) {
    assert.equal(model.isActivelyProcessing(stage), true, stage);
  }
  for (const stage of ['classification_completed', 'review_ready', 'ready_for_detection', 'quality_warning', 'error']) {
    assert.equal(model.isActivelyProcessing(stage), false, stage);
  }
});

test('modelo: el motivo de una interrupción es el persistido por el backend', () => {
  const failed = workflowResponse({
    stage: 'error', classification_run: null,
    detection_run: { id: 'det-1', status: 'failed', error_message: 'detector sin memoria', detection_count: 0, reviewed_count: 0, pending_review_count: 0 },
  });
  assert.equal(model.failureMessageFromWorkflow(failed), 'detector sin memoria');
  assert.equal(model.failureMessageFromWorkflow(workflowResponse()), null);
});

// ---------------------------------------------------------------- Acciones del análisis en curso

const noPermissions = liveActions.capabilitiesFromPermissions(new Set());
const allPermissions = liveActions.capabilitiesFromPermissions(new Set([
  'scientific.analysis.create', 'scientific.analysis.queue.create', 'scientific.analysis.queue.execute',
  'scientific.analysis.queue.retry', 'scientific.analysis.quality.review',
  'scientific.cell_detection.execute', 'scientific.cell_classification.execute',
]));
const liveState = (overrides) => ({
  stage: 'setup', failureStep: null, queueStatus: null, hasAnalysisRun: false,
  hasQueueItem: false, readyForAnalysis: false, hasDetectionRun: false, ...overrides,
});

test('acciones: iniciar un análisis exige los mismos permisos que el workflow existente', () => {
  const workflow = read('pages/SmearWorkflow.tsx');
  for (const permission of liveActions.INTAKE_PERMISSIONS) assert.ok(workflow.includes(`'${permission}'`), permission);
  assert.equal(liveActions.canStartAnalysis(new Set(liveActions.INTAKE_PERMISSIONS)), true);
  assert.equal(liveActions.canStartAnalysis(new Set(['scientific.images.register'])), false);
  assert.deepEqual([...liveActions.missingIntakePermissions(new Set(liveActions.INTAKE_PERMISSIONS.slice(1)))], ['scientific.images.register']);
});

test('acciones: cada decisión humana respeta su permiso y explica la restricción', () => {
  const warning = liveState({ stage: 'quality_warning', hasAnalysisRun: true });
  assert.equal(liveActions.liveActionFor(warning, allPermissions).kind, 'decide_quality_warning');
  assert.equal(liveActions.liveActionFor(warning, allPermissions).allowed, true);
  assert.equal(liveActions.liveActionFor(warning, noPermissions).allowed, false);
  assert.match(liveActions.liveActionFor(warning, noPermissions).denial, /no resolver esta advertencia/);

  const failedDetection = liveState({ stage: 'error', failureStep: 'detection', hasAnalysisRun: true });
  assert.equal(liveActions.liveActionFor(failedDetection, allPermissions).kind, 'retry_failed_step');
  assert.equal(liveActions.liveActionFor(failedDetection, noPermissions).allowed, false);

  const failedQueue = liveState({ stage: 'error', failureStep: 'quality', queueStatus: 'failed' });
  assert.equal(liveActions.liveActionFor(failedQueue, allPermissions).kind, 'requeue_quality');

  const paused = liveState({ stage: 'ready_for_detection', hasAnalysisRun: true, readyForAnalysis: true });
  assert.equal(liveActions.liveActionFor(paused, allPermissions).buttonLabel, 'Iniciar detección');
  assert.equal(liveActions.liveActionFor(paused, noPermissions).allowed, false);
});

test('acciones: un análisis completado o en proceso automático no ofrece acciones', () => {
  for (const stage of ['classification_completed', 'review_ready', 'detection_processing', 'classification_processing']) {
    assert.equal(liveActions.liveActionFor(liveState({ stage, hasAnalysisRun: true, hasDetectionRun: true }), allPermissions), null, stage);
  }
  assert.equal(liveActions.isResumableStage('classification_completed'), false);
  assert.equal(liveActions.isResumableStage('review_ready'), false);
  assert.equal(liveActions.isResumableStage('ready_for_detection'), true);
});

// ---------------------------------------------------------------- Reutilización científica y solo lectura

test('análisis existente: abrirlo es una consulta GET; no carga imágenes ni lanza procesos', () => {
  const hook = read('features/analisis-frotis-v3/hooks/useExistingAnalysis.ts');
  const session = read('features/analisis-frotis-v3/components/ExistingAnalysisSession.tsx');
  assert.match(hook, /api\.getSmearAnalysisHistoryDetail\(analysisId\)/);
  assert.deepEqual([...hook.matchAll(/api\.(\w+)/g)].map((match) => match[1]), ['getSmearAnalysisHistoryDetail']);
  assert.doesNotMatch(session, /api\.|useSmearAnalysisWorkflow|IntakeStage|FormData/);
  const historyApi = read('services/api.ts');
  const detail = historyApi.slice(historyApi.indexOf('getSmearAnalysisHistoryDetail('), historyApi.indexOf('async getMicroscopyImageBlob'));
  assert.doesNotMatch(detail, /method:/);
});

test('análisis nuevo: reutiliza el workflow existente y no define un pipeline paralelo', () => {
  const live = read('features/analisis-frotis-v3/components/LiveAnalysisSession.tsx');
  assert.match(live, /import \{ useSmearAnalysisWorkflow \} from '..\/..\/..\/hooks\/useSmearAnalysisWorkflow'/);
  assert.match(live, /onStart=\{controller\.start\}/);
  const writes = /api\.(upload|create|enqueue|execute|retry|review|save)\w*\(/;
  const transport = /\bfetch\(|XMLHttpRequest|axios/;
  for (const file of v3Sources) {
    const source = readFileSync(file, 'utf8');
    assert.doesNotMatch(source, writes, `${file} no ejecuta operaciones científicas por su cuenta`);
    assert.doesNotMatch(source, transport, `${file} no abre transporte propio`);
  }
  const intake = read('features/analisis-frotis-v3/components/IntakeStage.tsx');
  const upload = read('pages/SmearUpload.tsx');
  for (const field of ["form.append('files', file)", "'subject_mode'", "'sample_mode'", "'acquisition_origin'"]) {
    assert.ok(intake.includes(field) && upload.includes(field), `mismo contrato de formulario: ${field}`);
  }
});

test('la URL canónica se adopta sin desmontar el workspace de la sesión en curso', () => {
  const page = read('features/analisis-frotis-v3/MicroscopioPage.tsx');
  const live = read('features/analisis-frotis-v3/components/LiveAnalysisSession.tsx');
  assert.match(live, /navigate\(`\$\{microscopeAnalysisPath\(analysisRunId\)\}\?\$\{searchParams\.toString\(\)\}`, \{ replace: true \}\)/);
  assert.match(page, /routeAnalysisId !== liveRef\.current/);
  assert.match(page, /<LiveAnalysisSession routeAnalysisId=\{routeAnalysisId\} onClaim=\{claim\} \/>/);
  assert.doesNotMatch(page, /<LiveAnalysisSession key=/);
});

// ---------------------------------------------------------------- Aislamiento v1 / v2 / v3

test('aislamiento: v3 no importa v2 (ni sus mocks) y v2 no importa v3', () => {
  for (const file of v3Sources) {
    const source = readFileSync(file, 'utf8');
    assert.doesNotMatch(source, /analisis-frotis-v2|mockData|useFrotisDemo/, file);
  }
  for (const file of walk(resolve(root, 'features/analisis-frotis-v2')).filter((path) => /\.(ts|tsx)$/.test(path))) {
    assert.doesNotMatch(readFileSync(file, 'utf8'), /analisis-frotis-v3/, file);
  }
  for (const path of ['pages/SmearWorkflow.tsx', 'pages/SmearUpload.tsx', 'hooks/useSmearAnalysisWorkflow.ts', 'components/Layout.tsx']) {
    assert.doesNotMatch(read(path), /analisis-frotis-v3|frotis\/microscopio|smearMicroscope/, `${path} no conoce v3`);
  }
});

test('aislamiento CSS: toda regla de v3 está bajo .frotis-v3 y no hay selectores globales', () => {
  assert.ok(v3Styles.length >= 3);
  for (const file of v3Styles) {
    const css = readFileSync(file, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/@media[^{]*\{/g, '}');
    assert.doesNotMatch(css, /:root|(^|[\s,}])(html|body)\b|(^|[\s,}])\*\s*[{,]/m, file);
    const selectors = [...css.matchAll(/(^|\})\s*([^{}@]+)\{/g)]
      .flatMap((match) => match[2].split(','))
      .map((selector) => selector.trim())
      .filter((selector) => selector && !/^(from|to|\d+%)$/.test(selector));
    assert.ok(selectors.length > 0, file);
    for (const selector of selectors) {
      assert.match(selector, /^\.frotis-v3[\s.:\[-]|^\.frotis-v3$/, `${file}: ${selector}`);
    }
    for (const [, name] of css.matchAll(/@keyframes\s+([\w-]+)/g)) assert.match(name, /^frotis-v3-/);
  }
  assert.ok(existsSync(resolve(v3Root, 'styles/tokens_frotis_v3.css')));
  assert.doesNotMatch(readFileSync(resolve(v3Root, 'styles/tokens_frotis_v3.css'), 'utf8'), /--frotis-v2-/);
});

test('aislamiento de estado: la persistencia local de v3 usa solo el namespace capstone:frotis:v3:', () => {
  assert.equal(v3Routes.FROTIS_V3_STORAGE_NAMESPACE, 'capstone:frotis:v3:');
  for (const file of v3Sources) {
    const source = readFileSync(file, 'utf8');
    if (!/localStorage|sessionStorage/.test(source)) continue;
    assert.ok(file.endsWith('state/presentationStorage.ts'), `${file} no debe tocar el almacenamiento local`);
    assert.match(source, /FROTIS_V3_STORAGE_NAMESPACE/);
    assert.doesNotMatch(source, /(getItem|setItem|removeItem)\(\s*['"`]/, 'sin claves literales fuera del namespace');
  }
});

// ---------------------------------------------------------------- Workspace

// El viewport real descarga la imagen autenticada y la capa celular consulta la
// API; en el render estático se sustituyen por marcadores sin red.
class ApiErrorStub extends Error {}
const loadWorkspace = () => loader({
  './SmearViewport': { SmearViewport: ({ image }) => React.createElement('figure', { 'data-image': image?.id }) },
  '../../../services/api': { api: {}, ApiError: ApiErrorStub },
})('features/analisis-frotis-v3/components/MicroscopeWorkspace.tsx');
const renderWorkspace = (props, entry = '/frotis/microscopio') => renderToStaticMarkup(React.createElement(
  MemoryRouter,
  { initialEntries: [entry] },
  React.createElement(loadWorkspace().MicroscopeWorkspace, props),
));

test('workspace: header único con las tres vistas y los dos instrumentos', () => {
  assert.deepEqual([...v3Routes.MICROSCOPE_VIEWS].map((view) => view.label), ['FULL FIELD REVIEW', 'REVIEW CELLS', 'REPORT']);
  const html = renderWorkspace({
    analysis: null,
    status: { label: 'Nuevo análisis', tone: 'idle' },
    takeover: React.createElement('div', { id: 'carga' }, 'Incorporar imágenes de frotis'),
  });
  assert.equal((html.match(/<header class="frotis-v3-header"/g) ?? []).length, 1);
  assert.equal((html.match(/<h1/g) ?? []).length, 1);
  assert.match(html, /class="frotis-v3"/);
  assert.match(html, /aria-current="page"[^>]*>FULL FIELD REVIEW/);
  assert.match(html, /Mostrar u ocultar Imagen y Óptica/);
  assert.match(html, /Mostrar u ocultar IA y Revisión/);
  assert.match(html, /Incorporar imágenes de frotis/);
});

test('workspace: sin frotis en el visor, las vistas e instrumentos se declaran no disponibles', () => {
  const html = renderWorkspace({
    analysis: null,
    status: { label: 'Nuevo análisis', tone: 'idle' },
    takeover: React.createElement('div', null, 'carga'),
  });
  assert.match(html, /aria-disabled="true"[^>]*>REVIEW CELLS/);
  assert.match(html, /aria-disabled="true"[^>]*>REPORT/);
  assert.equal((html.match(/class="frotis-v3-instrument-toggle"[^>]*aria-disabled="true"/g) ?? []).length, 2);
});

test('workspace: con detección real se habilitan REVIEW CELLS, REPORT y los instrumentos', () => {
  const analysis = model.analysisFromWorkflow(workflowResponse());
  const html = renderWorkspace(
    { analysis, status: { label: 'Clasificación completada', tone: 'ok' }, activeImageId: IMAGE_B },
    `/frotis/microscopio/${REAL_ANALYSIS}`,
  );
  assert.doesNotMatch(html, /aria-disabled="true"[^>]*>REVIEW CELLS/);
  assert.doesNotMatch(html, /aria-disabled="true"[^>]*>REPORT/);
  assert.doesNotMatch(html, /class="frotis-v3-instrument-toggle"[^>]*aria-disabled="true"/);
  const withoutDetection = model.analysisFromWorkflow(workflowResponse({
    stage: 'quality_failed', detection_run: null, classification_run: null, classification_summary: null,
  }));
  const blocked = renderWorkspace({ analysis: withoutDetection, status: { label: 'Bloqueado', tone: 'blocked' } });
  assert.match(blocked, /aria-disabled="true"[^>]*title="Disponible cuando exista detección celular"[^>]*>REVIEW CELLS/);
});

test('workspace: un análisis muestra solo datos entregados por el backend', () => {
  const analysis = model.analysisFromWorkflow(workflowResponse());
  const html = renderWorkspace(
    { analysis, status: { label: 'Clasificación completada', tone: 'ok' }, activeImageId: IMAGE_B },
    `/frotis/microscopio/${REAL_ANALYSIS}`,
  );
  assert.match(html, new RegExp(`data-image="${IMAGE_B}"`));
  assert.match(html, /RUN-1/);
  assert.match(html, /SLIDE-1/);
  assert.match(html, /37 células detectadas/);
  assert.match(html, /\(7 en esta imagen\)/);
  assert.match(html, /32 pendientes de revisión/);
  assert.match(html, /4 candidatas parasitadas/);
  assert.match(html, /no constituye un diagnóstico clínico/);
  assert.match(html, /aria-label="Imagen 2 de 2: b\.png"/);
});

// ---------------------------------------------------------------- 01B.2 · Visor

const math = load('features/analisis-frotis-v3/state/viewportMath.ts');
const IMAGE = { width: 2000, height: 1000 };
const STAGE = { width: 800, height: 600 };
const near = (actual, expected, message) => assert.ok(Math.abs(actual - expected) < 1e-6, `${message}: ${actual} ≠ ${expected}`);

test('visor: ajustar a pantalla muestra la imagen completa, también rotada', () => {
  const fit = math.fitViewport(IMAGE, STAGE);
  near(fit.scale, 0.4, 'escala de ajuste');
  near(fit.cx, 1000, 'centro x'); near(fit.cy, 500, 'centro y');
  near(math.fitScale(IMAGE, STAGE, 90), 0.3, 'ajuste con 90°');
  near(math.fitScale({ width: 1000, height: 1000 }, STAGE, 0), 0.6, 'ajuste cuadrado');
});

test('visor: el zoom mantiene fijo el punto bajo el cursor y respeta los límites', () => {
  const start = math.fitViewport(IMAGE, STAGE);
  const anchor = { x: 200, y: 150 };
  const before = math.screenToImage(anchor, start, STAGE);
  const zoomed = math.zoomAt(start, 2.5, anchor, IMAGE, STAGE);
  const after = math.screenToImage(anchor, zoomed, STAGE);
  near(zoomed.scale, 1, 'escala'); near(after.x, before.x, 'ancla x'); near(after.y, before.y, 'ancla y');
  const limits = math.scaleLimits(IMAGE, STAGE);
  near(math.zoomAt(start, 1e6, anchor, IMAGE, STAGE).scale, limits.max, 'límite superior');
  near(math.zoomAt(start, 1e-6, anchor, IMAGE, STAGE).scale, limits.min, 'límite inferior');
});

test('visor: pan y rotación son coherentes y el centro nunca sale de la imagen', () => {
  const start = { cx: 1000, cy: 500, scale: 2, rotation: 0 };
  const panned = math.panBy(start, 100, -40, IMAGE);
  near(panned.cx, 950, 'pan x'); near(panned.cy, 520, 'pan y');
  const rotated = math.panBy({ ...start, rotation: 90 }, 100, 0, IMAGE);
  near(rotated.cx, 1000, 'pan rotado x'); near(rotated.cy, 550, 'pan rotado y');
  const clamped = math.panBy(start, 1e6, 1e6, IMAGE);
  near(clamped.cx, 0, 'límite x'); near(clamped.cy, 0, 'límite y');
  assert.equal(math.rotateBy(start, -90).rotation, 270);
  const point = { x: 321, y: 123 };
  const view = { cx: 700, cy: 400, scale: 1.7, rotation: 90 };
  const back = math.screenToImage(math.imageToScreen(point, view, STAGE), view, STAGE);
  near(back.x, point.x, 'ida y vuelta x'); near(back.y, point.y, 'ida y vuelta y');
});

test('visor: el centro de observación se conserva al cambiar el tamaño del viewport', () => {
  const view = { cx: 640, cy: 410, scale: 1.5, rotation: 0 };
  for (const stage of [STAGE, { width: 480, height: 900 }, { width: 1400, height: 300 }]) {
    const center = math.screenToImage({ x: stage.width / 2, y: stage.height / 2 }, view, stage);
    near(center.x, 640, 'centro x'); near(center.y, 410, 'centro y');
  }
});

test('visor: centrar una región la deja en el centro y legible', () => {
  const start = math.fitViewport(IMAGE, STAGE);
  const focused = math.focusRegion(start, { x: 1500, y: 200, width: 40, height: 20 }, IMAGE, STAGE);
  near(focused.cx, 1520, 'centro x'); near(focused.cy, 210, 'centro y');
  assert.ok(focused.scale * 40 >= 95.9, 'la región alcanza un tamaño legible');
  const quad = math.visibleQuad(start, STAGE);
  assert.equal(quad.length, 4);
  near(quad[0].x, 0, 'esquina visible x');
});

test('visor: los ajustes ópticos son filtros de presentación reversibles, sin escritura', () => {
  const viewportSource = read('features/analisis-frotis-v3/components/SmearViewport.tsx');
  const optics = read('features/analisis-frotis-v3/components/panels/OpticsPanel.tsx');
  assert.match(viewportSource, /style=\{filters \? \{ filter: filters \} : undefined\}/);
  assert.match(viewportSource, /feFuncR type="gamma"/);
  assert.doesNotMatch(viewportSource, /canvas|toBlob|toDataURL|api\./);
  assert.match(optics, /Restaurar imagen original/);
  assert.match(optics, /onOpticsChange\(DEFAULT_OPTICS\)/);
  assert.match(optics, /no indica aumento óptico/);
  assert.doesNotMatch(optics, /api\.|\b\d+x\b/i);
});

// ---------------------------------------------------------------- 01B.2 · Layout Manager

const layout = load('features/analisis-frotis-v3/state/floatingLayout.ts');
const panel = (id, side, height, extra = {}) => ({ id, side, width: 260, height, ...extra });
const noOverlaps = (placements) => {
  for (let i = 0; i < placements.length; i += 1) {
    for (let j = i + 1; j < placements.length; j += 1) {
      assert.equal(layout.placementsOverlap(placements[i], placements[j]), false, `${placements[i].id} × ${placements[j].id}`);
    }
  }
};
const inside = (placements, stage, reserved = {}) => {
  for (const item of placements) {
    assert.ok(item.x >= (reserved.left ?? 0) && item.x + item.width <= stage.width - (reserved.right ?? 0) + 1e-6, `${item.id} horizontal`);
    assert.ok(item.y >= (reserved.top ?? 0), `${item.id} superior`);
  }
};

test('layout: los instrumentos ocupan columnas opuestas sin superponerse', () => {
  const stage = { width: 1200, height: 700 };
  const placements = layout.computeFloatingLayout({
    stage,
    panels: [panel('optics', 'left', 320), panel('minimap', 'left', 120, { anchor: 'bottom' }), panel('ai', 'right', 300), panel('actions', 'right', 180)],
  });
  assert.equal(placements.length, 4);
  noOverlaps(placements); inside(placements, stage);
  const byId = Object.fromEntries(placements.map((item) => [item.id, item]));
  assert.ok(byId.optics.x < byId.ai.x);
  assert.ok(byId.minimap.y + byId.minimap.maxHeight <= stage.height);
  assert.ok(byId.minimap.y > byId.optics.y);
});

test('layout: una zona reservada por un panel fijo desplaza a los instrumentos', () => {
  const stage = { width: 1200, height: 700 };
  const reserved = { right: 340, top: 50 };
  const placements = layout.computeFloatingLayout({ stage, reserved, panels: [panel('optics', 'left', 300), panel('ai', 'right', 300)] });
  noOverlaps(placements); inside(placements, stage, reserved);
  const ai = placements.find((item) => item.id === 'ai');
  assert.ok(ai.x + ai.width <= stage.width - 340);
});

test('layout: sin ancho para dos columnas, IA se integra bajo Óptica y se reparte el alto', () => {
  const stage = { width: 520, height: 420 };
  const placements = layout.computeFloatingLayout({ stage, panels: [panel('optics', 'left', 320), panel('ai', 'right', 300)] });
  noOverlaps(placements); inside(placements, stage);
  const [optics, ai] = ['optics', 'ai'].map((id) => placements.find((item) => item.id === id));
  assert.equal(optics.x, ai.x);
  assert.ok(ai.y >= optics.y + optics.maxHeight);
  assert.ok(ai.y + ai.maxHeight <= stage.height);
  assert.ok(optics.maxHeight < 320, 'el contenido hace scroll dentro del alto asignado');
});

test('layout: en pantallas estrechas los instrumentos pasan a franjas de ancho completo', () => {
  const stage = { width: 380, height: 640 };
  const placements = layout.computeFloatingLayout({ stage, panels: [panel('optics', 'left', 200), panel('ai', 'right', 200)] });
  assert.ok(placements.every((item) => item.mode === 'sheet'));
  noOverlaps(placements); inside(placements, stage);
});

test('layout: el workspace delega la posición en el Layout Manager, no en z-index', () => {
  const workspace = read('features/analisis-frotis-v3/components/MicroscopeWorkspace.tsx');
  const floating = read('features/analisis-frotis-v3/components/panels/FloatingPanel.tsx');
  assert.match(workspace, /computeFloatingLayout\(\{/);
  assert.match(floating, /left: placement\.x,\s*top: placement\.y/);
  for (const file of v3Styles) assert.doesNotMatch(readFileSync(file, 'utf8'), /z-index/, `${file} no resuelve superposiciones con z-index`);
});

// ---------------------------------------------------------------- 01B.2 · Capa celular, inspector y reporte

const cellLayer = load('features/analisis-frotis-v3/adapters/cellLayer.ts');
const detection = (id, index, review = 'unreviewed') => ({
  id, cell_code: `C-${index}`, cell_index: index, bbox_x: index * 10, bbox_y: 5, bbox_width: 20, bbox_height: 22,
  detector_score: 0.9, review_status: review, crop: { id: `crop-${id}`, content_url: `/crops/${id}` },
});
const prediction = (id, detectionId, label, probability, extra = {}) => ({
  id, cell_detection_id: detectionId, prediction_status: 'completed', predicted_label: label,
  probability_parasitized: probability, threshold_used: 0.5, near_threshold: false, review_status: 'unreviewed',
  latest_review: null, ...extra,
});

test('capa celular: une detección y predicción por identificador sin alterar valores', () => {
  const cells = cellLayer.mergeCells(
    [detection('d2', 2), detection('d1', 1), detection('d3', 3, 'accepted')],
    [prediction('p1', 'd1', 'parasitized', 0.93), prediction('p2', 'd2', 'uninfected', 0.48, { near_threshold: true, review_status: 'confirmed' })],
  );
  assert.deepEqual([...cells].map((cell) => cell.detectionId), ['d1', 'd2', 'd3']);
  assert.equal(cells[0].prediction.probabilityParasitized, 0.93);
  assert.equal(cells[0].prediction.threshold, 0.5);
  assert.deepEqual({ ...cells[0].bbox }, { x: 10, y: 5, width: 20, height: 22 });
  assert.equal(cells[2].prediction, null);
  assert.deepEqual([...cells].map(cellLayer.cellKind), ['parasitized', 'uninfected', 'unclassified']);
  assert.equal(cellLayer.formatProbability(0.934), '93.4 %');
  assert.equal(cellLayer.formatProbability(null), '—');
});

test('capa celular: filtros y navegación recorren solo células reales', () => {
  const cells = cellLayer.mergeCells(
    [detection('d1', 1), detection('d2', 2), detection('d3', 3, 'accepted')],
    [prediction('p1', 'd1', 'parasitized', 0.93), prediction('p2', 'd2', 'uninfected', 0.48, { near_threshold: true, review_status: 'confirmed' })],
  );
  const ids = (filter) => [...cellLayer.filterCells(cells, filter)].map((cell) => cell.detectionId);
  assert.deepEqual(ids('all'), ['d1', 'd2', 'd3']);
  assert.deepEqual(ids('parasitized'), ['d1']);
  assert.deepEqual(ids('near_threshold'), ['d2']);
  assert.deepEqual(ids('pending_review'), ['d1']);
  assert.equal(cellLayer.neighbourCell(cells, 'd3', 1).detectionId, 'd1');
  assert.equal(cellLayer.neighbourCell(cells, 'd1', -1).detectionId, 'd3');
  assert.equal(cellLayer.neighbourCell(cells, null, 1).detectionId, 'd1');
  assert.equal(cellLayer.neighbourCell([], null, 1), null);
});

test('capa celular y reporte: solo lecturas paginadas de los contratos existentes', () => {
  const layerHook = read('features/analisis-frotis-v3/hooks/useCellLayer.ts');
  const reportHook = read('features/analisis-frotis-v3/hooks/useReportFindings.ts');
  const cropHook = read('features/analisis-frotis-v3/hooks/useCellCrop.ts');
  const calls = (source) => [...new Set([...source.matchAll(/api\.(\w+)/g)].map((match) => match[1]))].sort();
  assert.deepEqual(calls(layerHook), ['getCellClassificationPredictions', 'getCellDetections']);
  assert.deepEqual(calls(reportHook), ['getCellClassificationPredictions']);
  assert.deepEqual(calls(cropHook), ['getCellCropBlob']);
  assert.match(layerHook, /limit: PAGE_SIZE,\s*offset/);
  const workspace = read('features/analisis-frotis-v3/components/MicroscopeWorkspace.tsx');
  assert.deepEqual(calls(workspace), ['getCellDetection', 'getCellPrediction']);
});

test('reporte: presenta el resumen persistido, «—» para lo ausente y navegación al hallazgo', () => {
  const { ReportView } = loader({ '../../../services/api': { api: {}, ApiError: ApiErrorStub } })(
    'features/analisis-frotis-v3/components/ReportView.tsx',
  );
  const analysis = model.analysisFromWorkflow(workflowResponse({
    classification_summary: {
      classified_cell_count: 37, parasitized_candidate_count: 4, uninfected_candidate_count: 33, near_threshold_count: 1,
      failed_prediction_count: 0, eligible_cell_count: 37, parasitized_candidate_fraction: 0.108, outcome: 'suspicious_cells_detected',
    },
  }));
  const finding = {
    predictionId: 'p1', detectionId: 'd1', imageId: IMAGE_A, imageSequence: 1, cellCode: 'C-1',
    probabilityParasitized: 0.93, threshold: 0.5, nearThreshold: false, label: 'parasitized', reviewStatus: 'unreviewed',
  };
  const html = renderToStaticMarkup(React.createElement(ReportView, {
    analysis, findings: { status: 'ready', findings: [finding] }, onOpenFinding() {},
  }));
  assert.match(html, /Se detectaron células sospechosas/);
  assert.match(html, /Candidatas parasitadas<\/dt><dd>4</);
  assert.match(html, /10\.8 %/);
  assert.match(html, /93\.0 %/);
  assert.match(html, /Ver en microscopio/);
  assert.match(html, /no constituye un diagnóstico clínico/);
  const empty = renderToStaticMarkup(React.createElement(ReportView, {
    analysis: model.analysisFromWorkflow(workflowResponse({ stage: 'review_ready', classification_run: null, classification_summary: null })),
    findings: { status: 'idle', findings: [] }, onOpenFinding() {},
  }));
  assert.match(empty, /Células clasificadas<\/dt><dd>—</);
  assert.match(empty, /no tiene clasificación celular registrada/);
});

test('preferencias de v3: vista, paneles, óptica y capas viven bajo el namespace propio', () => {
  const storage = read('features/analisis-frotis-v3/state/presentationStorage.ts');
  assert.match(storage, /const PREFERENCES_KEY = `\$\{FROTIS_V3_STORAGE_NAMESPACE\}preferences`/);
  assert.match(storage, /export const DEFAULT_OPTICS: OpticsSettings = \{ brightness: 100, contrast: 100, saturation: 100, gamma: 1 \}/);
});

test('layout: la capa flotante se mide al montarse, también si el frotis aparece tras una carga', () => {
  const workspace = read('features/analisis-frotis-v3/components/MicroscopeWorkspace.tsx');
  assert.match(workspace, /<div ref=\{setLayerElement\} className="frotis-v3-floating-layer">/);
  assert.match(workspace, /\}, \[layerElement\]\);/);
  assert.doesNotMatch(workspace, /layerRef/);
});
