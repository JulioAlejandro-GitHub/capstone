import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read=(path)=>readFileSync(new URL(`../src/${path}`,import.meta.url),'utf8');

test('Etapa 2 aparece sólo en TRAIN y usa endpoints separados de producción',()=>{
  const row=read('components/reports/RunSummaryRow.tsx');
  const child=read('components/reports/RunLineageChildCard.tsx');
  const api=read('services/api.ts');
  assert.match(row,/processKind==='training'&&onStage2Enable/);
  assert.doesNotMatch(child,/Stage2AvailabilityAction|enableStage2/);
  assert.match(api,/stage2-availability/);
  assert.match(api,/enable-stage2/);
  assert.match(api,/\/api\/stage2\/models/);
});

test('modal declara alcance no clínico y no expone paths físicos',()=>{
  const modal=read('components/stage2/Stage2EnablementModal.tsx');
  assert.match(modal,/No constituye validación clínica ni autorización sanitaria/);
  assert.match(modal,/production\/champion con scope técnico de Etapa 2/);
  assert.doesNotMatch(modal,/checkpoint_path|artifact_path|best_model\\.keras/);
});

test('contrato mantiene la convención clínica intacta',()=>{
  const service=read('../../malaria_dl_local_project/src/stage2_model_availability_service.py');
  assert.match(service,/"0": "uninfected"/);
  assert.match(service,/"1": "parasitized"/);
  assert.match(service,/"positive_label": "parasitized"/);
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
