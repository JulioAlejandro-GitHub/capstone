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
  assert.match(row,/publication\?\.is_active/);
  assert.doesNotMatch(child,/Stage2AvailabilityAction|enableStage2|publishStage2Model/);
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
  assert.doesNotMatch(panel,/checkpoint_path|artifact_path|best_model\.keras/);
});

test('la tarjeta presenta estados elegible, publicado y condición faltante',()=>{
  const row=read('components/reports/RunSummaryRow.tsx');
  assert.match(row,/Disponible para publicar/);
  assert.match(row,/Publicado para Etapa 2/);
  assert.match(row,/missing_conditions/);
});

test('Deployments conserva Stage 2 histórico sin controles obsoletos',()=>{
  const page=read('pages/Deployments.tsx');
  const panel=read('components/deployments/DeploymentReviewPanel.tsx');
  const versions=read('pages/ModelVersions.tsx');
  assert.match(page,/isLegacyStage2/);
  assert.match(panel,/Registro histórico Etapa 2/);
  assert.match(panel,/Consulta sin operaciones/);
  assert.match(panel,/Ir a la publicación vigente/);
  assert.match(versions,/Registro histórico Etapa 2/);
  for(const source of [page,panel,versions]){
    assert.match(source,/stage2_experimental/);
    assert.match(source,/stage2_technical/);
    assert.match(source,/environment==='stage2'/);
  }
  for(const source of [page,panel])assert.doesNotMatch(source,/Stage2EnablementModal|publishTechnicalProduction|getTechnicalProductionPreview|Publicar como modelo productivo|onEnableStage2|onViewStage2/);
});

test('gobierno formal no Stage 2 permanece disponible',()=>{
  const page=read('pages/Deployments.tsx');
  const panel=read('components/deployments/DeploymentReviewPanel.tsx');
  assert.match(page,/getModelProductionReadiness/);
  assert.match(page,/publishModelVersionToProduction/);
  assert.match(panel,/ProductionStepIndicator/);
  for(const label of ['Versión inmutable y contrato técnico','Validación','Aprobación','Publicación en producción'])assert.match(panel,new RegExp(label));
});
