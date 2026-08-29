import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const layout = read('src/components/Layout.tsx');
const styles = read('src/styles.css');
const immersiveStyles = read('src/styles/smear-analysis-immersive.css');
const upload = read('src/pages/SmearUpload.tsx');
const workflow = read('src/pages/SmearWorkflow.tsx');
const hook = read('src/hooks/useSmearAnalysisWorkflow.ts');
const history = read('src/pages/SmearAnalysisHistory.tsx');

test('elimina la topbar global y usa una fila contextual compacta sin reservar su altura', () => {
  assert.doesNotMatch(layout, /className="topbar"/);
  assert.doesNotMatch(styles, /\.topbar\b/);
  assert.match(layout, /content-context-row/);
  assert.match(styles, /\.content-context-row[\s\S]*min-height:\s*44px/);
  assert.doesNotMatch(styles, /100dvh\s*-\s*113px/);
  assert.match(immersiveStyles, /grid-template-rows:\s*auto minmax\(0, 1fr\)/);
});

test('preparación expone datos reales, límites, motivos de bloqueo y una única acción', () => {
  for (const token of [
    'Nuevo análisis de frotis', 'ID PACIENTE', 'ID MUESTRA',
    'Control de calidad', 'INICIAR ANÁLISIS', 'MAX_UPLOAD_BYTES', 'MAX_IMAGE_PIXELS',
  ]) assert.match(upload, new RegExp(token));
  assert.match(upload, /disabled=\{busy \|\| !formReady\}/);
  assert.match(upload, /aria-describedby="smear-analyze-reason"/);
  assert.match(upload, /disabledReason/);
  assert.match(hook, /if \(activeAction\.current\) return/);
  assert.equal((hook.match(/uploadMicroscopyImages\(form\)/g) ?? []).length, 1);
});

test('adapta las etapas persistidas a la máquina clínica mínima solicitada', () => {
  for (const state of [
    'idle', 'validating', 'uploading', 'quality_check', 'detecting',
    'classifying', 'loading_result', 'completed', 'quality_rejected', 'failed',
  ]) assert.match(hook, new RegExp(`'${state}'`));
  assert.match(hook, /flowPhaseFromStage/);
  assert.match(workflow, /data-flow-state=\{controller\.phase\}/);
});

test('calidad visual se deriva de métricas y códigos persistidos sin temporizadores', () => {
  for (const criterion of ['Enfoque', 'Iluminación', 'Resolución', 'Artefactos']) {
    assert.match(workflow, new RegExp(criterion));
  }
  for (const state of ['Pendiente', 'Evaluando', 'Aprobado', 'Advertencia', 'Rechazado', 'Error']) {
    assert.match(workflow, new RegExp(state));
  }
  assert.match(workflow, /failure_codes/);
  assert.match(workflow, /warning_codes/);
  assert.match(workflow, /integrity_verified/);
  assert.doesNotMatch(`${workflow}\n${hook}`, /setTimeout/);
  assert.match(hook, /quality_gate_status === 'fail'[\s\S]*setStage\('quality_failed'\)/);
});

test('escaneo usa la imagen real, sólo acompaña detección o clasificación y respeta reduced motion', () => {
  assert.match(workflow, /AuthenticatedWorkflowImage/);
  assert.match(workflow, /const showScan = \[[\s\S]*'detection_processing'[\s\S]*'classification_pending'[\s\S]*'classification_processing'/);
  assert.match(workflow, /showScan \? <div className="workflow-scan-line"/);
  assert.match(styles, /@keyframes smear-scan/);
  assert.match(styles, /translateY\(calc\(100cqh - 2px\)\)/);
  assert.match(styles, /prefers-reduced-motion:\s*reduce[\s\S]*workflow-scan-line/);
});

test('al completar navega con replace al detalle y preserva selección y datasource', () => {
  assert.match(workflow, /routes\.smearHistoryDetail\(identifiers\.analysisRunId\)/);
  assert.match(workflow, /next\.set\('image', identifiers\.microscopyImageId\)/);
  assert.match(workflow, /next\.set\('selected_detection', identifiers\.selectedDetectionId\)/);
  assert.match(workflow, /next\.set\('selected_prediction', identifiers\.selectedPredictionId\)/);
  assert.match(workflow, /replace:\s*true/);
  assert.match(history, /routes\.smearHistoryDetail\(item\.analysis_run_id\).*location\.search/);
  assert.match(hook, /new URLSearchParams\(workflowQueryRef\.current\)/);
  assert.match(hook, /getSmearWorkflow/);
});
