import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read=(path)=>readFileSync(new URL(`../${path}`,import.meta.url),'utf8');
const app=read('src/App.tsx');
const main=read('src/main.tsx');
const router=read('src/router.ts');
const layout=read('src/components/Layout.tsx');
const sidebar=read('src/components/navigation/AppSidebar.tsx');
const routeState=read('src/components/RouteState.tsx');
const deployments=read('src/pages/Deployments.tsx');
const versions=read('src/pages/ModelVersions.tsx');

test('usa History API con un único BrowserRouter y rutas anidadas',()=>{
  assert.match(main,/BrowserRouter/);
  assert.match(app,/<Routes>/);
  assert.match(layout,/<Outlet \/>/);
  assert.doesNotMatch(app,/window\.location\s*=/);
});

test('centraliza rutas canónicas limpias y detalles gobernados',()=>{
  for(const path of ['/modelo-ia/resumen','/modelo-ia/ejecuciones','/modelo-ia/modelos-liberados','/modelo-ia/despliegues','/modelo-ia/errores-logs']){
    assert.match(router,new RegExp(path));
  }
  for(const id of ['trainingRunId','modelVersionId','deploymentId']) assert.match(app,new RegExp(id));
});

test('valida UUID antes de renderizar páginas que consultan API',()=>{
  assert.match(router,/UUID_PATTERN/);
  assert.match(app,/isValidPublicId\(trainingRunId\)/);
  assert.match(app,/isValidPublicId\(modelVersionId\)/);
  assert.match(app,/isValidPublicId\(deploymentId\)/);
});

test('preserva datasource y genera URL compartible sin host hardcodeado',()=>{
  assert.match(router,/window\.location\.origin/);
  assert.match(router,/URLSearchParams/);
  assert.match(app,/searchParams\.get\('datasource'\)/);
  assert.doesNotMatch(router,/localhost/);
});

test('menú usa enlaces nativos y estado activo derivado de URL',()=>{
  assert.match(sidebar,/NavLink/);
  assert.match(sidebar,/useLocation/);
  assert.doesNotMatch(sidebar,/onPageChange/);
});

test('run, model version y deployment exponen Copiar enlace canónico',()=>{
  assert.match(routeState,/Enlace copiado\./);
  assert.match(versions,/modelVersionDetail/);
  assert.match(deployments,/deploymentDetail/);
});

test('deployment abre y cierra su revisión mediante navegación real',()=>{
  assert.match(deployments,/onDeploymentSelect\(id\)/);
  assert.match(deployments,/onDeploymentSelect\(null\)/);
});

test('incluye 404, error de ID y redirects legacy con replace',()=>{
  assert.match(routeState,/Página no encontrada/);
  assert.match(routeState,/Identificador inválido/);
  for(const legacy of ['/runs','/evaluations','/model-versions','/deployments']) assert.match(app,new RegExp(legacy));
  assert.match(app,/Navigate replace/);
});

test('las rutas públicas no exponen paths o archivos internos',()=>{
  for(const source of [app,router,layout,routeState]){
    assert.doesNotMatch(source,/best_model\.keras|checkpoint_path|artifact_path|src\/pages|\/Users\//);
  }
});
