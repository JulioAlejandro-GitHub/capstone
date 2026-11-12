import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read=(path)=>readFileSync(new URL(`../${path}`,import.meta.url),'utf8');
const page=read('src/pages/DatasetBrowser.tsx');
const api=read('src/services/api.ts');
const types=read('src/types/api.ts');
const navigation=read('src/components/navigation/navigationConfig.ts');

test('reutiliza Dataset y consume Dataset Versions gobernadas por FastAPI',()=>{
  assert.match(navigation,/label: 'Dataset'/);
  assert.equal((navigation.match(/label: 'Dataset Versions'/g)||[]).length,0);
  assert.match(api,/getDatasetVersions/);
  assert.match(api,/\/api\/datasets/);
  assert.match(types,/DatasetVersionDetail/);
});

test('renderiza estado, trainability, población y distribución gobernada',()=>{
  for(const token of ['FROZEN','Disponible para entrenamiento','patient_count','source_record_count','train_records','val_records','test_records','Paciente','Patient leakage 0']) assert.match(page,new RegExp(token));
  assert.doesNotMatch(page,/22046|2756/);
  assert.doesNotMatch(page,/malaria_physical_split|Split físico|Proceso de split físico/);
});

test('muestra validation, READY PASS, lineage y vacío de runs',()=>{
  for(const token of ['Validación científica','PASS','Materialización','reconciliation_status','Trazabilidad científica','source_population_fingerprint','clinical_identity_fingerprint','patient_assignment_fingerprint','record_assignment_fingerprint','Aún no existen entrenamientos nuevos asociados']) assert.match(page,new RegExp(token));
});

test('incluye loading independiente, error reintentable y empty states',()=>{
  for(const token of ['Cargando Dataset Versions','Cargando detalle del dataset','No fue posible cargar la información del dataset','Reintentar','No existen Dataset Versions disponibles','La versión aún no tiene una materialización disponible']) assert.match(page,new RegExp(token));
});

test('FROZEN es consulta inmutable sin configuración científica',()=>{
  assert.match(page,/La composición científica ya no puede modificarse/);
  assert.doesNotMatch(page,/>Editar<|Cambiar split|Modificar pacientes|Cambiar seed|Eliminar assignments/);
  assert.doesNotMatch(page,/type="(text|number)"/);
});
