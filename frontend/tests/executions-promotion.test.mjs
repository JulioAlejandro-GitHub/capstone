import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
const read=(path)=>readFileSync(new URL(`../${path}`,import.meta.url),'utf8');
const row=read('src/components/reports/RunSummaryRow.tsx');
const group=read('src/components/reports/TrainingRunGroupCard.tsx');
const child=read('src/components/reports/RunLineageChildCard.tsx');
const runs=read('src/pages/Runs.tsx');
const detail=read('src/pages/Stage2ReleaseDetail.tsx');
const app=read('src/App.tsx');
const api=read('src/services/api.ts');
const styles=read('src/styles/report-components.css');
const panel=read('src/components/reports/Stage2PublicationPanel.tsx');

test('TRAIN concentra la acción Activar para clasificación celular',()=>{
  assert.match(row,/processKind === 'training'/);
  assert.match(row,/<button[^]*stage2-detail-link/);
  assert.match(row,/aria-expanded=\{stage2Expanded\}/);
  assert.match(row,/Activar para clasificación celular/);
  assert.doesNotMatch(row,/Preparar despliegue|Habilitar para Etapa 2|Ver modelo productivo/);
  assert.doesNotMatch(child,/publishTrainingStage2|stage2-release-summary/);
});
test('estado activo prioriza disponibilidad canónica y estiliza toda la tarjeta',()=>{
  assert.match(group,/release_status === 'productive_stage2'/);
  assert.match(group,/training-card--stage2-production/);
  assert.match(row,/stage2Active/);
  for(const token of ['--stage2-production-background','--stage2-production-border','--stage2-production-badge-background'])assert.match(styles,new RegExp(token));
});
test('estado no depende solo del color',()=>{
  assert.match(row,/Modelo en Estado Activo/);
});
test('Liberación visible no vuelve a inferir elegibilidad',()=>{
  assert.match(row,/stage2Active/);
  assert.doesNotMatch(row,/eligible|missing_conditions|is_stage2_production|production_state/);
});
test('Activar abre el acordeón y la vista anterior permanece compatible',()=>{
  assert.match(group,/Stage2PublicationPanel/);
  assert.match(group,/setStage2Expanded/);
  assert.match(group,/onStage2Open/);
  assert.match(app,/Stage2ReleaseDetail/);
});
test('acordeón activa y confirma reemplazos inline',()=>{
  assert.match(panel,/Activar para clasificación celular/);
  assert.match(runs,/activateCellModel/);
  assert.match(api,/deactivateStage2Publication/);
});
test('detalle publica mediante confirmación y bloquea doble clic',()=>{
  assert.match(detail,/Stage2EnablementModal/);
  assert.match(detail,/publishTrainingStage2/);
  assert.match(detail,/confirm_publication: true/);
  assert.match(detail,/disabled=\{!canPublish \|\| publishing\}/);
  assert.match(detail,/El modelo productivo anterior continúa activo/);
});
test('detalle muestra TRAIN EVALUATE EXPLAIN opcional y model version',()=>{
  for(const token of ['Training run','Evaluation utilizada','EXPLAIN','opcional','Model version','stage2_technical'])assert.match(detail,new RegExp(token));
});
test('API utiliza estado y publicación de producción técnica',()=>{
  assert.match(api,/stage2-release-status/);
  assert.match(api,/publish-technical-production/);
  assert.match(api,/timeoutMs:\s*120000/);
});
test('no expone rutas físicas ni usa checkpoint como identidad',()=>{
  for(const source of [row,group,child,runs,detail,app])assert.doesNotMatch(source,/checkpoint_path|artifact_path|best_model\.keras|outputs\//);
});
