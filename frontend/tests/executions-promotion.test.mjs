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

test('TRAIN concentra la única superficie mutante Stage 2',()=>{
  assert.match(row,/processKind === 'training'/);
  assert.match(row,/<button[^]*stage2-detail-link/);
  assert.match(row,/aria-expanded=\{stage2Expanded\}/);
  assert.match(group,/Stage2PublicationPanel/);
  assert.doesNotMatch(child,/publishStage2Model|deactivateStage2Publication|stage2-release-summary/);
  assert.match(runs,/publishStage2Model/);
  assert.match(runs,/deactivateStage2Publication/);
});

test('publicación persistida determina estado y estilo de toda la tarjeta',()=>{
  assert.match(group,/publication\?\.is_active/);
  assert.match(row,/publication\?\.is_active/);
  assert.match(group,/training-card--stage2-production/);
  assert.match(row,/Publicado para Etapa 2/);
  for(const token of ['--stage2-production-background','--stage2-production-border','--stage2-production-badge-background'])assert.match(styles,new RegExp(token));
});

test('elegibilidad visible exige sólo TRAIN y EVALUATE',()=>{
  assert.match(row,/TRAIN completado · ✓ EVALUATE completado/);
  assert.match(row,/Se requiere un TRAIN completado y un EVALUATE completado asociado/);
  assert.match(panel,/TRAIN completed \+ EVALUATE completed/);
  assert.doesNotMatch(panel,/EXPLAIN completado/);
  for(const forbidden of ['status\\?\\.checkpoint','<span>Threshold','<span>Smoke','<span>Deployment','Slot productivo'])assert.doesNotMatch(panel,new RegExp(forbidden,'i'));
});

test('validaciones de ejecución no bloquean la publicación',()=>{
  for(const token of ['checksum','threshold','mapping','preprocessing','framework','forma de entrada','al iniciar la inferencia'])assert.match(panel,new RegExp(token,'i'));
  assert.doesNotMatch(runs,/getProductiveModelAvailability/);
  assert.doesNotMatch(panel,/technical_blockers|production_blockers|available_for_inference/);
});

test('acordeón publica y da de baja mediante confirmación inline',()=>{
  assert.match(panel,/Confirmar publicación/);
  assert.match(panel,/Confirmar baja/);
  assert.match(panel,/Publicar para Etapa 2/);
  assert.doesNotMatch(panel,/Publicar y desplegar|production \/ champion|stage2_technical/);
});

test('deep link de liberación redirige con replace y preserva contexto',()=>{
  assert.match(app,/Stage2ReleaseDetail/);
  assert.match(detail,/<Navigate replace/);
  assert.match(detail,/new URLSearchParams\(location\.search\)/);
  assert.match(detail,/search\.set\('datasource', datasource\)/);
  assert.match(detail,/search\.set\('run', trainingRunId\)/);
  assert.match(detail,/search\.set\('stage2', 'publicacion'\)/);
  assert.doesNotMatch(detail,/publish|deploymentDetail|Stage2EnablementModal/);
});

test('destino del redirect filtra el TRAIN y autoexpande publicación',()=>{
  assert.match(runs,/searchParams\.get\('stage2'\) === 'publicacion'/);
  assert.match(runs,/defaultStage2Open=\{stage2PublicationRunId === group\.training\.run_id\}/);
  assert.match(group,/useState\(defaultStage2Open\)/);
  assert.match(group,/if\(defaultStage2Open\)setExpanded\(true\)/);
});

test('API usa únicamente estado y ciclo de publicación ligera',()=>{
  assert.match(api,/stage2-release-status/);
  assert.match(api,/model-versions\/\$\{modelVersionId\}\/stage2-publications/);
  assert.match(api,/stage2-publications\/\$\{publicationId\}\/deactivate/);
  for(const obsolete of ['publish-technical-production','technical-production-preview','enable-stage2'])assert.doesNotMatch(api,new RegExp(obsolete));
});

test('no expone rutas físicas ni usa artefactos como regla de publicación',()=>{
  for(const source of [row,group,child,runs,detail,app])assert.doesNotMatch(source,/checkpoint_path|artifact_path|best_model\.keras|outputs\//);
});
