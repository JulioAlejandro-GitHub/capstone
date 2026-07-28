import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const page = read('src/pages/CellReview.tsx');
const workspace = read('src/components/cell-review/CellReviewWorkspace.tsx');
const viewer = read('src/components/cell-review/CellImageViewer.tsx');
const authenticatedImage = read('src/components/cell-review/AuthenticatedCellImage.tsx');
const api = read('src/services/api.ts');
const types = read('src/types/cellReview.ts');
const app = read('src/App.tsx');
const router = read('src/router.ts');
const navigation = read('src/components/navigation/navigationConfig.ts');
const styles = read('src/styles.css');
const feature = `${page}\n${workspace}\n${viewer}\n${authenticatedImage}`;

test('Revisión celular conserva la ruta legacy dentro del workflow único', () => {
  assert.match(router, /smearReview:\s*'\/frotis\/revision'/);
  assert.match(router, /smearWorkflow:\s*'\/frotis\/analizar'/);
  assert.match(app, /routes\.smearWorkflow.*<SmearWorkflow/s);
  assert.match(app, /routes\.smearReview.*<LegacySmearRedirect/s);
  const smearStart = navigation.indexOf("id: 'smear-analysis'");
  const modelStart = navigation.indexOf("id: 'model-ai'");
  const workflow = navigation.indexOf("label: 'Analizar imagen'");
  assert.ok(workflow > smearStart && workflow < modelStart);
});

test('lista elegibles, inicia manualmente y abre ejecuciones persistidas', () => {
  for (const token of [
    'getEligibleCellAnalysisRuns',
    'createCellDetectionRun',
    'getCellDetectionRuns',
    'Iniciar detección',
    'Abrir revisión',
    'detection_run_code',
    'reviewed_count',
  ]) assert.match(page + api, new RegExp(token));
  assert.doesNotMatch(page, /setInterval|WebSocket|EventSource|aprobación masiva/i);
});

test('usa permisos efectivos para lectura, ejecución y revisión', () => {
  for (const permission of [
    'scientific.cell_detection.read',
    'scientific.cell_detection.execute',
    'scientific.cell_detection.review',
  ]) assert.ok(page.includes(`permissions.includes('${permission}')`));
  assert.match(workspace, /canReview \?/);
  assert.match(workspace, /Vista de solo lectura/);
});

test('workspace tiene tres paneles amplios y pestañas móviles', () => {
  assert.match(styles, /grid-template-columns:\s*minmax\(250px,\s*300px\)\s*minmax\(330px,\s*420px\)\s*minmax\(0,\s*1fr\)/s);
  for (const panel of ['cell-summary-panel', 'cell-gallery-panel', 'cell-review-right']) {
    assert.match(workspace, new RegExp(panel));
  }
  for (const tab of ['Resumen', 'Células', 'Imagen', 'Detalle']) {
    assert.match(workspace, new RegExp(`'${tab}'`));
  }
  assert.match(styles, /data-mobile-tab="summary"/);
  assert.match(styles, /data-mobile-tab="detail"/);
});

test('workspace admite cierre contextual y sincronización segura de selección', () => {
  assert.match(workspace, /closeLabel\?: string/);
  assert.match(workspace, /initialMicroscopyImageId\?: string \| null/);
  assert.match(workspace, /onMicroscopyImageChange\?: \(microscopyImageId: string \| null\) => void/);
  assert.match(workspace, /initialSelectedDetectionId\?: string \| null/);
  assert.match(workspace, /onSelectedDetectionChange\?: \(detectionId: string \| null\) => void/);
  assert.equal((workspace.match(/\{closeLabel\}/g) || []).length, 3);
  assert.match(workspace, /initialCandidate && overlayPage\.items\.some\(\(item\) => item\.id === initialCandidate\)/);
  assert.match(workspace, /selectionDetectionRunId\.current === detectionRunId/);
  assert.match(workspace, /selectionResolved \|\| !onSelectedDetectionChange/);
  assert.doesNotMatch(workspace, /getCellDetection\(initialSelectedDetectionId\)/);
});

test('tablet conserva galería y visor en dos columnas con resumen colapsable', () => {
  const tabletStart = styles.indexOf('@media (min-width: 701px) and (max-width: 1200px)');
  const mobileStart = styles.indexOf('@media (max-width: 700px)', tabletStart);
  assert.ok(tabletStart >= 0 && mobileStart > tabletStart);
  const tablet = styles.slice(tabletStart, mobileStart);
  assert.match(tablet, /grid-template-columns: minmax\(280px, 360px\) minmax\(0, 1fr\)/);
  assert.match(tablet, /\.cell-summary-panel[\s\S]*position: absolute/);
  assert.match(tablet, /\.cell-gallery-panel[\s\S]*grid-column: 1/);
  assert.match(tablet, /\.cell-review-right[\s\S]*grid-column: 2/);
  assert.match(tablet, /is-summary-collapsed \.cell-summary-panel[\s\S]*display: none/);
});

test('filtros legacy de detección conservan estados no clínicos', () => {
  for (const status of ['all', 'unreviewed', 'accepted', 'rejected', 'needs_attention']) {
    assert.match(workspace, new RegExp(`'${status}'`));
  }
  assert.match(workspace, /percentage\.toFixed\(1\)/);
  assert.match(workspace, /review_counts/);
  assert.doesNotMatch(page, /Blast|Promyelocyte|N\/C ratio|Oil Immersion/i);
});

test('crops son lazy, autenticados y revocan todos los object URLs', () => {
  assert.match(authenticatedImage, /IntersectionObserver/);
  assert.match(authenticatedImage, /rootMargin:\s*'180px'/);
  assert.match(authenticatedImage, /URL\.createObjectURL/);
  assert.match(authenticatedImage, /URL\.revokeObjectURL\(nextUrl\)/);
  assert.match(authenticatedImage, /URL\.revokeObjectURL\(objectUrl\)/);
  assert.match(api, /getCellCropBlob/);
  assert.match(api, /Authorization.*Bearer/);
});

test('imagen original usa blob cell-analysis autenticado y nombres seguros', () => {
  assert.match(viewer, /getCellOriginalImageBlob/);
  assert.match(api, /\/api\/v1\/cell-analysis\/detection-runs\/.*\/images\/.*\/content/);
  assert.match(types, /safe_name:\s*string/);
  assert.doesNotMatch(types, /original_filename/);
  assert.doesNotMatch(feature, /original_filename|\/api\/v1\/scientific\/images/);
});

test('overlay SVG comparte viewBox y usa directamente bbox xywh', () => {
  assert.match(viewer, /<svg[\s\S]*viewBox=\{viewBox\}/);
  for (const coordinate of ['bbox_x', 'bbox_y', 'bbox_width', 'bbox_height']) {
    assert.match(viewer, new RegExp(`detection\\.${coordinate}`));
  }
  assert.match(viewer, /preserveAspectRatio="none"/);
  assert.match(types + workspace, /coordinate_space/);
});

test('selección es bidireccional, enfoca y conserva la tarjeta visible', () => {
  assert.match(workspace, /selectedDetectionId/);
  assert.match(workspace, /scrollIntoView/);
  assert.match(workspace, /onDetectionSelect=\{selectDetection\}/);
  assert.match(viewer, /onClick=\{\(event\) => selectBox/);
  assert.match(workspace, /setFocusRequest/);
  assert.match(viewer, /selected\.bbox_x \+ selected\.bbox_width \/ 2/);
});

test('visor implementa zoom, fit, pan, reset y toggles accesibles', () => {
  for (const token of [
    'Ajustar a pantalla',
    'Restablecer vista',
    'Acercar',
    'Alejar',
    'setPointerCapture',
    'movePan',
    'showBoxes',
    'showLabels',
    'showGrid',
    'aria-pressed',
  ]) assert.match(viewer, new RegExp(token));
  for (const level of ['0.25', '0.5', '1', '2']) assert.match(viewer, new RegExp(level));
});

test('navegación de detecciones incluye anterior, siguiente y siguiente sin revisar', () => {
  assert.match(viewer, /Detección anterior/);
  assert.match(viewer, /Detección siguiente/);
  assert.match(viewer, /Siguiente sin revisar/);
  assert.match(workspace, /nextUnreviewed/);
});

test('detalle corresponde a la selección y separa resultado automático de revisión humana', () => {
  for (const label of [
    'Resultado automático',
    'Revisión humana',
    'Score geométrico',
    'Bounding box',
    'Coordinate space',
    'Área',
    'Perímetro',
    'Circularidad',
    'Solidity',
    'Contacto con borde',
    'Checksum crop',
    'Historial de revisión',
  ]) assert.match(workspace, new RegExp(label));
  assert.match(workspace, /detail \?\? selected/);
});

test('revisión append-only valida comentarios y confirma rechazo', () => {
  assert.match(api, /createCellReview/);
  assert.match(api, /method:'POST'/);
  assert.doesNotMatch(api.slice(api.indexOf('createCellReview'), api.indexOf('getCellCropBlob')), /PUT|PATCH|DELETE/);
  assert.match(workspace, /decision !== 'accepted' && !comment/);
  assert.match(workspace, /decision === 'rejected'[\s\S]*window\.confirm/);
  for (const action of ['Aceptar detección', 'Rechazar detección', 'Requiere atención', 'Agregar comentario']) {
    assert.match(workspace, new RegExp(action));
  }
});

test('paginación separa metadata de overlay de la descarga lazy de crops', () => {
  assert.match(workspace, /const PAGE_SIZE = 100/);
  assert.match(workspace, /limit:\s*500/);
  assert.match(workspace, /overlayDetections/);
  assert.match(workspace, /Cargar más/);
  assert.match(workspace, /offset:\s*galleryOffset/);
  assert.doesNotMatch(workspace, /getCellCropBlob/);
});

test('estados vacíos y errores nunca dejan paneles silenciosos', () => {
  for (const message of [
    'No existen analysis runs elegibles',
    'No existen ejecuciones de detección celular',
    'Esta ejecución no contiene imágenes',
    'Esta imagen no contiene detecciones candidatas',
    'No hay detecciones para el filtro seleccionado',
    'Crop no disponible',
    'Imagen original no disponible',
    'detección fallida',
    'No fue posible guardar la revisión',
  ]) assert.match(feature, new RegExp(message));
});

test('controles de crops y cajas soportan teclado y estados no basados solo en color', () => {
  assert.match(workspace, /<button[\s\S]*aria-pressed=\{selected\}/);
  assert.match(viewer, /event\.key === 'Enter' \|\| event\.key === ' '/);
  assert.match(viewer, /role="button"/);
  assert.match(viewer, /statusSymbol/);
  assert.match(viewer, /aria-label=.*seleccionada/s);
  assert.match(workspace, /aria-live="polite"/);
});
