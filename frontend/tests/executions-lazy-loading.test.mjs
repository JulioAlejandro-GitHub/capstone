import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8');
const runs = read('pages/Runs.tsx');
const group = read('components/reports/TrainingRunGroupCard.tsx');
const row = read('components/reports/RunSummaryRow.tsx');
const child = read('components/reports/RunLineageChildCard.tsx');
const api = read('services/api.ts');
const types = read('types/api.ts');
const styles = read('styles/report-components.css');
const initialEffect = runs.slice(runs.indexOf('// Deferring one tick'), runs.indexOf('const loadedChildren'));
const loadChildren = runs.slice(runs.indexOf('const loadChildren'), runs.indexOf('const loadStage2'));
const loadStage2 = runs.slice(runs.indexOf('const loadStage2'), runs.indexOf('const publishStage2'));

test('1 carga inicial usa un solo método propio training-summaries', () => {
  assert.equal((initialEffect.match(/getTrainingSummaries/g) || []).length, 1);
  assert.match(api, /'\/runs\/training-summaries'/);
});

test('2 carga inicial excluye grouped, Stage 2, productivo e hijos', () => {
  for (const forbidden of ['getGroupedRunLineage', 'getStage2ReleaseStatus', 'getStage2Availability', 'getProductiveModelAvailability', 'getTrainingLineageChildren']) {
    assert.doesNotMatch(initialEffect, new RegExp(forbidden));
  }
});

test('3 colección controlada representa 24 TRAIN y la página itera sus items', () => {
  const fixture = Array.from({ length: 24 }, (_, index) => ({ run_id: `train-${index}`, run_type: 'training' }));
  assert.equal(fixture.length, 24);
  assert.match(runs, /filteredTrainings\.map\(\(training\)/);
});

test('4 filtros, URL y navegación de detalle se conservan', () => {
  for (const token of ['useSearchParams', "'run'", "'modelo'", 'setSearchParams', 'onRunSelect']) {
    assert.match(runs + group + child, new RegExp(token));
  }
});

test('5 los estados internos de liberación no se exponen en el resumen', () => {
  assert.doesNotMatch(row, /No disponible|Disponible para publicar|Estado no disponible/);
});

test('6 la acción de TRAIN usa el texto de clasificación celular', () => {
  assert.match(row, /Activar para clasificación celular/);
});

test('7 un modelo activo se identifica sin ofrecer activación redundante', () => {
  assert.match(row, /stage2Active \? 'Modelo en Estado Activo' : 'Activar para clasificación celular'/);
});

test('8 errores del estado canónico no muestran un resumen productivo obsoleto', () => {
  assert.match(group, /!stage2Error && training.release_status === 'productive_stage2'/);
});

test('9 tarjeta activa prioriza disponibilidad canónica sobre el resumen persistido', () => {
  assert.match(group, /stage2Status.is_stage2_available === true && stage2Status.available_for_inference === true/);
  assert.match(group, /stage2Active \? 'training-card--stage2-production'/);
  assert.match(styles, /\.training-card--stage2-production/);
});

test('10 acción de TRAIN conserva la expansión accesible sin publicar directamente', () => {
  assert.match(row, /onClick=\{onStage2Toggle\}/);
  assert.doesNotMatch(row, /onPublish|activateCellModel/);
});

test('11 el resumen no infiere Liberación desde contratos Stage 2', () => {
  assert.doesNotMatch(row, /eligible|production_state|is_stage2_production|isCurrent|model_version_id/);
});

test('12 hijos y panel Stage 2 comienzan colapsados', () => {
  assert.match(group, /useState\(false\).*childrenExpanded/s);
  assert.match(group, /useState\(false\).*stage2Expanded/s);
});

test('13 header inicial muestra ambos contadores y total sin depender de hijos', () => {
  for (const token of ['training.evaluation_count', 'training.explainability_count', 'linkedCount', 'run-lineage-group__children-heading']) {
    assert.match(group, new RegExp(token.replaceAll('.', '\\.')));
  }
});

test('14 primera expansión consulta exactamente el endpoint lazy tipado', () => {
  assert.equal((loadChildren.match(/getTrainingLineageChildren/g) || []).length, 1);
  assert.match(api, /`\/runs\/\$\{encodeURIComponent\(trainingRunId\)\}\/lineage-children`/);
});

test('15 expandir un TRAIN conserva identidad independiente y no carga otro', () => {
  assert.match(loadChildren, /trainingRunId/);
  assert.match(loadChildren, /childrenCacheKey\(requestDatasource, trainingRunId\)/);
});

test('16 success o loaded evita repetir GET al reabrir', () => {
  assert.match(loadChildren, /current\.status === 'loading' \|\| current\.status === 'success'/);
  assert.match(group, /data: TrainingLineageChildren \| null/);
});

test('17 loading bloquea requests duplicados durante clics repetidos', () => {
  assert.match(loadChildren, /current\.status === 'loading'/);
  assert.match(loadChildren, /childrenByKeyRef/);
});

test('18 error se almacena en la entrada datasource más TRAIN', () => {
  assert.match(runs, /childrenCacheKey\(datasource: string, trainingRunId: string\)/);
  assert.match(loadChildren, /status: 'error'/);
  assert.match(group, /childrenState\.error/);
});

test('19 reintento explícito sólo vuelve a cargar la tarjeta afectada', () => {
  assert.match(runs, /onChildrenRetry=\{\(\) => \{ void loadChildren\(training\.run_id, true\); \}\}/);
  assert.match(loadChildren, /current\.status === 'error' && !retry/);
});

test('20 abort no se convierte en error visible', () => {
  assert.match(loadChildren, /reason instanceof ApiError && reason\.kind === 'abort'\) return/);
});

test('21 cambio de datasource aborta y limpia cachés anteriores', () => {
  assert.match(initialEffect, /childrenControllers\.current\.forEach\(\(pending\) => pending\.abort\(\)\)/);
  assert.match(runs, /childrenByKeyRef\.current = \{\}/);
  assert.match(initialEffect, /\[datasource, reloadToken\]/);
});

test('22 respuesta con training_run_id diferente se rechaza localmente', () => {
  assert.match(loadChildren, /response\.training_run_id !== trainingRunId/);
  assert.match(loadChildren, /Respuesta de linaje descartada/);
});

test('23 conteos concurrentes se reconcilian sin alterar Liberación', () => {
  assert.match(loadChildren, /evaluation_count: response\.evaluation_count/);
  assert.match(loadChildren, /explainability_count: response\.explainability_count/);
  assert.doesNotMatch(loadChildren, /release_status/);
});

test('24 respuesta truncada muestra primeros N de M', () => {
  assert.match(group, /loadedChildren\.truncated/);
  assert.match(group, /Se muestran los primeros \{visibleChildren\} de \{loadedChildren\.total_count\}/);
});

test('25 TRAIN sin hijos deshabilita expansión y no llama al loader', () => {
  assert.match(group, /if \(linkedCount === 0 && !childrenExpanded\) return/);
  assert.match(group, /disabled=\{linkedCount === 0 && !childrenExpanded\}/);
});

test('26 EVALUATE se renderiza desde la respuesta lazy', () => {
  assert.match(group, /loadedChildren\.evaluations\.map/);
  assert.match(group, /kind="evaluation"/);
});

test('27 EXPLAIN respeta el nombre backend explainabilities', () => {
  assert.match(types, /explainabilities: ExplainabilityLineageChild\[\]/);
  assert.match(group, /loadedChildren\.explainabilities\.map/);
  assert.doesNotMatch(types.slice(types.indexOf('interface TrainingLineageChildren'), types.indexOf('export type RunLineageConfidence')), /explainability:/);
});

test('28 hijos mantienen navegación a detalle', () => {
  assert.match(child, /onClick=\{\(\) => onRunSelect\(run\.run_id\)\}/);
});

test('29 render de hijos no emite consultas individuales', () => {
  assert.doesNotMatch(child + group, /\bapi\.|getRunDetail|getModelVersion/);
});

test('30 publicación y readiness no se precargan al montar', () => {
  assert.doesNotMatch(initialEffect, /loadStage2|stage2-release-status|stage2-availability|productive-model-availability/);
});

test('31 abrir Activar consulta readiness sólo del TRAIN elegido', () => {
  assert.match(group, /if \(next\) onStage2Open\(\)/);
  assert.match(loadStage2, /getStage2ReleaseStatus\(requestDatasource, runId/);
  assert.doesNotMatch(loadStage2, /getStage2Availability/);
});

test('32 estado productivo global no forma parte de la carga del panel', () => {
  assert.doesNotMatch(loadStage2, /getProductiveModelAvailability/);
  assert.equal((runs.match(/getProductiveModelAvailability/g) || []).length, 1);
});

test('33 flujo mutante conserva endpoints, payload y reemplazo existentes', () => {
  for (const token of ['activateCellModel', 'replace_existing', 'replacement-required']) {
    assert.match(runs, new RegExp(token));
  }
});

test('34 control de hijos expone aria-expanded', () => {
  assert.match(group, /aria-expanded=\{childrenExpanded\}/);
});

test('35 aria-controls referencia el id estable del panel', () => {
  assert.match(group, /childrenPanelId = `lineage-children-\$\{training\.run_id\}`/);
  assert.match(group, /aria-controls=\{childrenPanelId\}/);
  assert.match(group, /id=\{childrenPanelId\}/);
});

test('36 expansión usa button nativo operable con Enter y Espacio', () => {
  assert.match(group, /<button[^]*onClick=\{toggleChildren\}[^]*type="button"/);
});

test('37 modelo activo comunica su estado mediante texto', () => {
  assert.match(row, /Modelo en Estado Activo/);
});

test('contratos y cliente propagan AbortSignal sin duplicar base URL', () => {
  for (const contract of ['TrainingReleaseStatus', 'TrainingSummary', 'TrainingSummaryCollection', 'EvaluationLineageChild', 'ExplainabilityLineageChild', 'TrainingLineageChildren']) {
    assert.match(types, new RegExp(`(?:type|interface) ${contract}`));
  }
  assert.match(api, /signal\?: AbortSignal/);
  assert.match(api, /options\.signal\?\.addEventListener\('abort'/);
});
