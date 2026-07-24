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

test('TRAIN concentra una sola acción de liberación llamada Ver detalle',()=>{
  assert.match(row,/processKind === 'training'/);
  assert.match(row,/<Link[^>]+stage2-detail-link/);
  assert.match(row,/>Ver detalle<\/Link>/);
  assert.doesNotMatch(row,/Preparar despliegue|Habilitar para Etapa 2|Ver modelo productivo/);
  assert.doesNotMatch(child,/publishTrainingStage2|stage2-release-summary/);
});
test('estado productivo deriva del contrato y estiliza toda la tarjeta',()=>{
  assert.match(group,/is_stage2_production/);
  assert.match(group,/training-card--stage2-production/);
  assert.match(row,/stage2-production-badge/);
  for(const token of ['--stage2-production-background','--stage2-production-border','--stage2-production-badge-background'])assert.match(styles,new RegExp(token));
});
test('estado no depende solo del color',()=>{
  for(const token of ['✓','Productivo Etapa 2','Modelo activo e inmutable','production / champion'])assert.match(row,new RegExp(token));
  assert.match(row,/aria-hidden="true"/);assert.match(row,/role="status"/);
});
test('elegibilidad visible exige TRAIN y EVALUATE y no EXPLAIN',()=>{
  assert.match(row,/TRAIN completado · ✓ EVALUATE completado/);
  assert.match(row,/Se requiere un TRAIN completado y un EVALUATE completado asociado/);
  assert.doesNotMatch(row,/EXPLAIN completado/);
});
test('Ver detalle usa URL compartible y conserva datasource',()=>{
  assert.match(runs,/routes\.deploymentDetail/);
  assert.match(runs,/routes\.runReleaseDetail/);
  assert.match(runs,/withAllowedQuery/);
  assert.match(app,/Stage2ReleaseDetail/);
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
  assert.match(api,/timeoutMs:120000/);
});
test('no expone rutas físicas ni usa checkpoint como identidad',()=>{
  for(const source of [row,group,child,runs,detail,app])assert.doesNotMatch(source,/checkpoint_path|artifact_path|best_model\.keras|outputs\//);
});
