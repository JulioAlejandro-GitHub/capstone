import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read=(path)=>readFileSync(new URL(`../src/${path}`,import.meta.url),'utf8');

test('Etapa 2 aparece sólo en TRAIN y usa publicación persistente como fuente',()=>{
  const row=read('components/reports/RunSummaryRow.tsx');
  const child=read('components/reports/RunLineageChildCard.tsx');
  const api=read('services/api.ts');
  assert.match(row,/processKind === 'training'/);
  assert.match(row,/stage2-release-summary/);
  assert.doesNotMatch(child,/Stage2AvailabilityAction|enableStage2/);
  assert.match(api,/stage2-release-status/);
  assert.match(api,/stage2-publications/);
});

test('Ver detalle controla un acordeón accesible con confirmaciones inline',()=>{
  const row=read('components/reports/RunSummaryRow.tsx');
  const card=read('components/reports/TrainingRunGroupCard.tsx');
  const panel=read('components/reports/Stage2PublicationPanel.tsx');
  assert.match(row,/aria-expanded=\{stage2Expanded\}/);
  assert.match(row,/aria-controls=\{stage2ControlsId\}/);
  assert.match(card,/setExpanded\(current=>!current\)/);
  assert.match(panel,/Confirmar publicación/);
  assert.match(panel,/Confirmar baja/);
  assert.match(panel,/No constituye aprobación clínica ni diagnóstico automatizado/);
  assert.doesNotMatch(panel,/checkpoint_path|artifact_path|best_model\\.keras/);
});

test('la tarjeta presenta estados disponible, productivo y condición faltante',()=>{
  const row=read('components/reports/RunSummaryRow.tsx');
  assert.match(row,/Disponible para publicar/);
  assert.match(row,/Productivo Etapa 2/);
  assert.match(row,/missing_conditions/);
});

test('Despliegues identifica el modelo productivo Etapa 2 y preserva producción formal',()=>{
  const page=read('pages/Deployments.tsx');
  const panel=read('components/deployments/DeploymentReviewPanel.tsx');
  const active=read('components/deployments/ActiveStage2Model.tsx');
  assert.match(page,/environment==='production'&&row\.status==='active'&&row\.alias==='champion'/);
  assert.match(page,/production_scope==='stage2_technical'/);
  assert.match(active,/Modelo productivo para Etapa 2/);
  assert.match(active,/🔒 Inmutable/);
  assert.match(panel,/Publicar como modelo productivo/);
  assert.match(panel,/artefacto protegido y verificado por SHA-256/);
  assert.match(panel,/deployment\.metadata\?\.production_scope!=='stage2_technical'/);
});
