import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const page = read('src/pages/SmearAnalysisHistory.tsx');
const workflow = read('src/pages/SmearWorkflow.tsx');
const hook = read('src/hooks/useSmearAnalysisHistoryDetail.ts');
const results = read('src/components/cell-review/SmearAnalysisResultsView.tsx');
const api = read('src/services/api.ts');
const navigation = read('src/components/navigation/navigationConfig.ts');
const router = read('src/router.ts');
const app = read('src/App.tsx');

test('Historial de análisis está bajo Análisis de frotis y fuera de Modelo IA', () => {
  assert.match(navigation, /id: 'smear-analysis'[\s\S]*Historial de análisis/);
  assert.match(navigation, /path: routes\.smearHistory/);
  assert.doesNotMatch(navigation, /id: 'model-ai'[\s\S]*Historial de análisis[\s\S]*groups: modelAiGroups/);
});

test('listado usa una fila por analysis run con filtros, orden backend y paginación', () => {
  assert.match(page, /item\.analysis_run_id/);
  assert.match(page, /key=\{item\.analysis_run_id\}/);
  for (const filter of ['run_code', 'subject_code', 'sample_code', 'status', 'quality_gate_status', 'ready_for_analysis', 'created_from', 'created_to']) {
    assert.match(page, new RegExp(filter));
  }
  assert.match(page, /Anterior/);
  assert.match(page, /Siguiente/);
  assert.match(page, /Limpiar filtros/);
  assert.match(page, /No existen análisis registrados/);
  assert.match(page, /No hay análisis que coincidan con los filtros/);
});

test('detalle es deep link validado y reutiliza la presentación del workflow', () => {
  assert.match(router, /smearHistory: '\/frotis\/historial'/);
  assert.match(app, /smearHistory.*:analysisRunId/);
  assert.match(app, /isValidPublicId\(analysisRunId\)/);
  assert.match(page, /SmearAnalysisReadOnlyView/);
  assert.match(workflow, /WorkflowProcessing[\s\S]*readOnly/);
  assert.match(workflow, /SmearAnalysisResultsView[\s\S]*mode="history"/);
  assert.match(results, /readOnly=\{mode === 'history'\}/);
  assert.match(workflow, /Vista histórica · Solo lectura/);
  assert.match(workflow, /Volver al historial/);
});

test('hook histórico y su API realizan exclusivamente consultas GET', () => {
  assert.match(hook, /getSmearAnalysisHistoryDetail/);
  assert.doesNotMatch(hook, /\bpost\b|method:\s*['"](?:POST|PUT|PATCH|DELETE)/i);
  const historyApi = api.slice(api.indexOf('getSmearAnalysisHistory(params'), api.indexOf('async getMicroscopyImageBlob'));
  assert.match(historyApi, /\/api\/v1\/scientific\/workflows/);
  assert.match(historyApi, /\/api\/v1\/scientific\/analysis-history/);
  assert.doesNotMatch(historyApi, /method:/);
});

test('modo histórico no presenta acciones de mutación', () => {
  const historyView = workflow.slice(workflow.indexOf('export function SmearAnalysisReadOnlyView'), workflow.indexOf('export function SmearWorkflow'));
  for (const action of ['Aprobar con advertencias', 'Bloquear análisis', 'Reingresar a cola', 'Ejecutar control', 'Iniciar detección', 'Nuevo análisis']) {
    assert.doesNotMatch(historyView, new RegExp(action));
  }
});
