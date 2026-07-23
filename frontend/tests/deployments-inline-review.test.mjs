import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
const read=path=>readFileSync(new URL(`../${path}`,import.meta.url),'utf8');
const page=read('src/pages/Deployments.tsx');const table=read('src/components/DataTable.tsx');
const panel=read('src/components/deployments/DeploymentReviewPanel.tsx');
const modal=read('src/components/deployments/ProductionActivationModal.tsx');
const summary=read('src/components/deployments/ActiveProductionModel.tsx');
const api=read('src/services/api.ts');const styles=read('src/styles.css');

test('DataTable inserta una única fila expandida inmediatamente después de su fila',()=>{
  assert.match(table,/Fragment key=\{rowKey\}/);assert.match(table,/expanded-table-row/);
  assert.match(table,/colSpan=\{columns\.length\}/);assert.match(table,/expandedRowKey===rowKey/);
});
test('la página no conserva un panel global y alterna la selección',()=>{
  assert.doesNotMatch(page,/className="panel detail-panel"/);assert.match(page,/selectedId===id/);
  assert.match(page,/setSelectedId\(null\)/);assert.match(page,/Cerrar revisión/);
});
test('selectedDeploymentId abre, desplaza y enfoca la revisión contextual',()=>{
  assert.match(page,/if\(selectedDeploymentId\)/);assert.match(page,/scrollIntoView/);
  assert.match(panel,/tabIndex=\{-1\}/);assert.match(panel,/\.focus\(\{preventScroll:true\}\)/);
});
test('el modelo permanece identificado con versión, ambiente, alias e IDs',()=>{
  for(const token of ['Está revisando','model_name','version_number','deployment_name','environment','alias','model_version_id','training_run_id','threshold_value','Smoke'])assert.match(panel,new RegExp(token));
});
test('refresh y operaciones conservan selectedId y vuelven a consultar readiness',()=>{
  assert.match(page,/completeAction/);assert.match(page,/await refresh\(\);await loadReadiness\(id,false\);setSelectedId\(id\)/);
});
test('smoke PASS y FAIL muestran mensajes específicos junto al modelo',()=>{
  assert.match(page,/Validación aprobada/);assert.match(page,/La validación de/);
  assert.match(panel,/inline-operation-notice/);
});
test('readiness de model version gobierna la acción y smoke queda dentro de producción',()=>{
  assert.match(panel,/workflow\.next_action/);assert.match(panel,/can_complete_contract/);
  assert.match(page,/publishModelVersionToProduction/);assert.match(page,/smoke_status!=='PASS'/);
});
test('producción abre un modal y la secuencia confirmada activa con true',()=>{
  assert.match(page,/setProductionModal\(true\)/);assert.match(page,/onConfirm=\{publishToProduction\}/);
  assert.match(page,/confirm_production:true/);assert.match(modal,/Confirmo la publicación en producción/);
});
test('el modal identifica champion reemplazado, Escape y focus trap',()=>{
  assert.match(modal,/currentChampion/);assert.match(modal,/se conservará para rollback/);
  assert.match(modal,/event\.key==='Escape'/);assert.match(modal,/event\.key!=='Tab'/);assert.match(modal,/aria-modal="true"/);
});
test('el resumen distingue champion activo de ausencia de producción',()=>{
  assert.match(page,/environment==='production'&&row\.status==='active'&&row\.alias==='champion'/);
  assert.match(summary,/Modelo activo en producción/);assert.match(summary,/No existe un modelo activo en producción/);
});
test('la lista está ordenada y separada sin duplicar registros',()=>{
  for(const heading of ['Pendientes de activación','Activos','Historial'])assert.match(page,new RegExp(heading));
  assert.match(page,/priority\(a\)-priority\(b\)/);
});
test('la revisión funciona como tarjeta contextual en mobile y no expone paths',()=>{
  assert.match(styles,/deployment-table thead \{ display: none/);assert.match(styles,/deployment-row--selected/);
  for(const source of [page,panel,modal])assert.doesNotMatch(source,/checkpoint_path|best_model\.keras|outputs\//);
});
