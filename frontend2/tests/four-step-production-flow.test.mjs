import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
const read=path=>readFileSync(new URL(`../${path}`,import.meta.url),'utf8');
const page=read('src/pages/Deployments.tsx');
const panel=read('src/components/deployments/DeploymentReviewPanel.tsx');
const steps=read('src/components/deployments/ProductionStepIndicator.tsx');
const contract=read('src/components/deployments/TechnicalContractModal.tsx');
const approval=read('src/components/deployments/ModelApprovalModal.tsx');
const api=read('src/services/api.ts');

test('renderiza exactamente cuatro pasos y smoke no es un quinto paso',()=>{
  for(const label of ['Versión inmutable y contrato técnico','Validación','Aprobación','Publicación en producción'])assert.match(steps,new RegExp(label));
  assert.doesNotMatch(steps,/Smoke/);assert.match(panel,/Incluye deployment production, smoke test, champion e inferencia de control/);
});
test('contrato presenta evidencia y bloquea valores ambiguos o ausentes',()=>{
  for(const token of ['sources_searched','proposed_source_id','Seleccione evidencia','Crear versión inmutable'])assert.match(contract,new RegExp(token));
  assert.match(contract,/!contract\.production_package\.artifact_immutable/);assert.doesNotMatch(contract,/checkpoint_path|best_model\.keras/);
});
test('validación aprobación y producción siguen estados explícitos',()=>{
  for(const token of ['validate_model_version','approve_model_version','publish_to_production','view_production_model'])assert.match(page,new RegExp(token));
  assert.match(approval,/Responsable/);assert.match(approval,/Motivo/);assert.match(approval,/Confirmar aprobación/);
});
test('producción usa el orquestador y exige smoke, active e inferencia disponible',()=>{
  assert.match(page,/publishModelVersionToProduction/);assert.match(page,/smoke_status!=='PASS'/);
  assert.match(page,/!result\.available_for_inference/);assert.match(api,/confirm_production/);
});
test('API tipada expone candidatos contrato y readiness sin cliente duplicado',()=>{
  for(const method of ['getModelVersionContractCandidates','completeModelVersionContract','getModelProductionReadiness'])assert.match(api,new RegExp(method));
});
