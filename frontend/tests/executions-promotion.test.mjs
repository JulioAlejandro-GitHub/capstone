import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read=(path)=>readFileSync(new URL(`../${path}`,import.meta.url),'utf8');
const action=read('src/components/reports/RunPromotionAction.tsx');
const row=read('src/components/reports/RunSummaryRow.tsx');
const group=read('src/components/reports/TrainingRunGroupCard.tsx');
const child=read('src/components/reports/RunLineageChildCard.tsx');
const runs=read('src/pages/Runs.tsx');
const versions=read('src/pages/ModelVersions.tsx');
const deployments=read('src/pages/Deployments.tsx');
const app=read('src/App.tsx');
const api=read('src/services/api.ts');
const styles=read('src/styles/report-components.css');

test('renderiza promoción sólo para TRAIN y conserva Ver detalle',()=>{
  assert.match(row,/processKind === 'training'/);
  assert.match(row,/RunPromotionAction/);
  assert.match(row,/Ver detalle/);
  assert.match(group,/processKind="training"/);
  assert.doesNotMatch(child,/RunPromotionAction|prepareTrainingRelease|Preparar despliegue/);
});

test('consulta estado y muestra loading y unavailable',()=>{
  assert.match(runs,/getTrainingPromotionStatus/);
  assert.match(action,/Consultando…/);
  assert.match(action,/No disponible/);
  assert.match(action,/disabled=\{disabled\}/);
});

test('presenta bloqueadores legibles y estados unresolved',()=>{
  for(const code of ['EVALUATION_REQUIRED','CLINICAL_THRESHOLD_REQUIRED','UNRESOLVED_LINEAGE','CHECKPOINT_HASH_MISMATCH','MODEL_VERSION_CONFLICT']){
    assert.match(action,new RegExp(code));
  }
  assert.match(action,/blocking_reasons/);
  assert.match(action,/details/);
});

test('prepara una vez, bloquea doble click y refresca al fallar',()=>{
  assert.match(runs,/prepareTrainingRelease/);
  assert.match(runs,/if \(preparingRunId\) return/);
  assert.match(runs,/setPreparingRunId\(runId\)/);
  assert.match(runs,/await loadPromotionStatus\(runId\)/);
  assert.match(action,/Preparando…/);
});

test('navega por model_version_id y deployment_id',()=>{
  assert.match(runs,/onModelVersionSelect\(status\.model_version_id\)/);
  assert.match(runs,/onDeploymentSelect\(status\.deployment_id\)/);
  assert.match(app,/selectedModelVersionId/);
  assert.match(app,/selectedDeploymentId/);
  assert.match(versions,/selectedModelVersionId/);
  assert.match(deployments,/selectedDeploymentId/);
});

test('representa candidate, validated, pending y active desde contrato backend',()=>{
  for(const token of ['review_model_version','approve_model_version','create_deployment','review_pending_deployment','view_active_deployment']){
    assert.match(runs,new RegExp(token));
  }
  assert.match(action,/deployment_status === 'active'/);
});

test('maneja timeout y error de API sin perder la causa',()=>{
  assert.match(api,/AbortController/);
  assert.match(api,/tiempo de espera/);
  assert.match(runs,/La consulta tardó demasiado/);
  assert.match(action,/role="alert"/);
});

test('incluye accesibilidad, teclado nativo y progreso no dependiente del color',()=>{
  for(const token of ['aria-label','aria-disabled','aria-describedby','role="status"']){
    assert.match(action+styles,new RegExp(token));
  }
  assert.match(action,/type="button"/);
  assert.match(action,/✓/);
  assert.match(action,/○/);
  assert.match(styles,/:focus-visible/);
});

test('adapta acción a mobile',()=>{
  assert.match(styles,/@media \(max-width: 700px\)/);
  assert.match(styles,/\.run-promotion__button[\s\S]*width: 100%/);
});

test('no expone rutas físicas ni usa best_model como identidad',()=>{
  for(const source of [action,row,group,child,runs,versions,deployments,app]){
    assert.doesNotMatch(source,/checkpoint_path|model_path|best_model\.keras|outputs\//);
  }
});

test('mantiene separación de responsabilidades y rutas actuales',()=>{
  assert.doesNotMatch(runs,/activate|retire|rollback|createDeployment/);
  assert.doesNotMatch(child,/deploy|release|promotion/i);
  for(const key of ['runs','model-versions','deployments','run-detail']){
    assert.match(app,new RegExp(`'${key}'`));
  }
});

test('Modelos liberados muestra evidencia y conecta transiciones explícitas',()=>{
  for(const token of ['evaluation_run_id','explainability_run_ids','threshold','preprocessing_profile_snapshot','artifact_sha256','can_deploy','blocking_reasons']){
    assert.match(versions,new RegExp(token));
  }
  for(const action of ['validateModelVersion','approveModelVersion','createDeployment']){
    assert.match(versions,new RegExp(`api\\.${action}`));
  }
  assert.match(versions,/actor|Responsable/);
  assert.match(versions,/motivo|Motivo/);
});
