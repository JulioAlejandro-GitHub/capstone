import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);
const root = fileURLToPath(new URL('../src/', import.meta.url));
function loader(mocks = {}, globals = {}) {
  const cache = new Map();
  const load = name => {
    const path = resolve(root, name);
    if (cache.has(path)) return cache.get(path);
    const module = {exports:{}};
    cache.set(path, module.exports);
    const code = ts.transpileModule(readFileSync(path,'utf8'), {compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
    runInNewContext(code, {exports:module.exports, AbortController, ...globals, require: name => {
      if (name in mocks) return mocks[name];
      if (name.endsWith('.css')) return {};
      if (!name.startsWith('.')) return require(name);
      const base = resolve(dirname(path),name);
      return load([base,`${base}.tsx`,`${base}.ts`].find(existsSync));
    }});
    return module.exports;
  };
  return load;
}
const group = loader()('components/reports/xai/comparison.ts').groupXAIComparisons;
function fixture(method='shap', overrides={}) {
  const detail = {id:`attempt-${method}`,kind:'explain',training_run_id:'train',identity_id:`identity-${method}`,state:'verified',cause:null,
    identity:{model:{model_version_id:'model',checkpoint_artifact_id:'checkpoint'},dataset:{dataset_version_id:'dataset'},split:'test',purpose:'final',
      explanation:{method,background:[{sample_id:'background-not-original'}]}},...overrides};
  return {detail,artifacts:[{artifact_id:`artifact-${method}`,role:'overlay',sample_id:'sample',attempt_id:detail.id,training_run_id:detail.training_run_id,sha256:'hash',bytes:10}]};
}
const emptyResource = {url:null,loading:false,error:false,failure:null,extension:'.png'};
const resources = Object.fromEntries(['original','gradcam','lime','shap'].map(method=>[method,emptyResource]));
function presentation(comparison, images=resources, generation) {
  const load = loader({'../../hooks/useScientificArtifact':{}});
  const {XAIComparisonContent} = load('components/reports/XAIComparisonViewer.tsx');
  return renderToStaticMarkup(React.createElement(XAIComparisonContent,{comparison,resources:images,generation,onExpand:()=>{}}));
}
test('same TRAIN/checkpoint/sample/context combines three methods and preserves each identity', () => {
  const rows = group(['gradcam','lime','shap'].map(method=>fixture(method)),'train');
  assert.equal(rows.length,1);
  assert.equal(rows[0].sampleId,'sample');
  for (const method of ['gradcam','lime','shap']) {
    assert.equal(rows[0].methods[method].attemptId,`attempt-${method}`);
    assert.equal(rows[0].methods[method].artifact.artifactId,`artifact-${method}`);
  }
  const html = presentation(rows[0]);
  const positions = ['Célula original','Grad-CAM','LIME','SHAP'].map(label=>html.indexOf(`aria-label="${label}"`));
  assert.ok(positions.every((position,i)=>position>=0 && (i===0 || position>positions[i-1])));
  assert.equal((html.match(/class="xai-panel"/g)||[]).length,4);
  for (const id of ['train','checkpoint','sample','model','attempt-shap','artifact-shap','identity-shap','hash']) assert.ok(html.includes(id),id);
});
test('SHAP-only and unexplained samples keep four panels, without generating an original from background', () => {
  const row = group([fixture()],'train')[0];
  assert.equal(row.original.originalSource.source,'dataset_sample');
  assert.equal(row.original.originalSource.sampleId,'sample');
  assert.notEqual(row.original.originalSource.sampleId,'background-not-original');
  for (const comparison of [row,{id:'empty',trainingRunId:'train',sampleId:'empty',methods:{}}]) {
    const html = presentation(comparison);
    assert.equal((html.match(/class="xai-panel"/g)||[]).length,4);
    assert.match(html,/Sin evidencia/);
    assert.match(html,/<button[^>]*disabled=""[^>]*>Generar LIME/);
    assert.doesNotMatch(html,/<img/);
  }
});
for (const change of ['train','checkpoint','model','sample','dataset','split','purpose','preprocessing','missing']) {
  test(`incompatible ${change} never joins another attempt`, () => {
    const left = fixture('gradcam'); const right = fixture('shap');
    if (change==='train') right.detail.training_run_id='other';
    if (change==='checkpoint') right.detail.identity.model.checkpoint_artifact_id='other';
    if (change==='model') right.detail.identity.model.model_version_id='other';
    if (change==='sample') right.artifacts[0].sample_id='other';
    if (change==='dataset') right.detail.identity.dataset.dataset_version_id='other';
    if (change==='split') right.detail.identity.split='val';
    if (change==='purpose') right.detail.identity.purpose='development';
    if (change==='preprocessing') right.detail.identity.preprocessing={resize:100};
    if (change==='missing') delete right.detail.identity.dataset;
    const rows = group([left,right],'train');
    assert.ok(rows.every(row=>Object.keys(row.methods).length===1));
    if (change==='missing') assert.match(rows[1].comparabilityIssue,/incompleta/);
  });
}
test('conflicting artifact relationships are non-comparable and cannot trigger a download', () => {
  const page=fixture(); page.artifacts[0].attempt_id='wrong';
  const row=group([page],'train')[0];
  assert.equal(row.methods.shap.availability,'not_comparable');
  assert.equal(row.methods.shap.artifact,undefined);
  assert.match(presentation(row),/No comparable/);
});
test('unknown sample is isolated, duplicate method preserved and duplicate artifact removed', () => {
  const one=fixture(); const two=fixture('shap',{id:'attempt-second'});
  assert.equal(group([one,two],'train').length,2);
  assert.equal(group([one,one],'train').length,1);
  delete one.artifacts[0].sample_id; delete two.artifacts[0].sample_id;
  const rows=group([one,two],'train');
  assert.equal(rows.length,2);
  assert.ok(rows.every(row=>row.comparabilityIssue));
});
test('required SHAP PK survives independently of unrelated Grad-CAM', () => {
  const train='d3d42cf3-0800-468c-b3ed-995860967da1';
  const attempt='93966b5d-5548-4b29-96f9-0b67e5c98f9f';
  const artifact='2b4f68d6-2826-489c-980b-69f686223b11';
  const shap=fixture('shap',{id:attempt,training_run_id:train}); shap.artifacts[0].artifact_id=artifact;
  const other=fixture('gradcam',{id:'4703ff9e-2d20-413f-9b9a-cd945c8dd632',training_run_id:'338136db-a207-47fc-bbf3-d17ce85c0dc2'});
  const rows=group([shap,other],train);
  assert.equal(rows.length,1); assert.equal(rows[0].methods.gradcam,undefined);
  assert.equal(rows[0].methods.shap.artifact.artifactId,artifact);
  assert.match(presentation(rows[0],{...resources,shap:{...emptyResource,url:'blob:shap'}}),/download="2b4f68d6-2826-489c-980b-69f686223b11.png"/);
});
for (const [execution,label] of [['pending','Pendiente'],['running','Ejecutándose'],['failed','Fallido'],['completed','Sin evidencia'],['not_executed','Sin evidencia']]) {
  test(`execution ${execution} is represented independently of missing evidence`, () => {
    const row={id:'row',trainingRunId:'train',methods:{shap:{method:'shap',execution,availability:'no_evidence'}}};
    assert.ok(presentation(row).includes(label));
  });
}
for (const [availability,label] of [['missing','Archivo no disponible'],['denied','Acceso denegado'],['integrity_failed','Integridad fallida'],['not_comparable','No comparable'],['error','Error de recuperación']]) {
  test(`${availability} retrieval failure is not absence of execution`, () => {
    const row=group([fixture()],'train')[0];
    const html=presentation(row,{...resources,shap:{...emptyResource,error:true,failure:{availability,message:'technical-context'}}});
    assert.ok(html.includes(label)); assert.match(html,/technical-context/); assert.match(html,/role="alert"/);
  });
}
test('generation stays disabled without a real authorized callback', () => {
  const row={id:'row',trainingRunId:'train',sampleId:'sample',methods:{}};
  assert.match(presentation(row,resources,{shap:{authorized:false,execute:async()=>{}}}),/<button[^>]*disabled=""[^>]*>Generar SHAP/);
  assert.match(presentation(row,resources,{shap:{authorized:true,execute:async()=>{}}}),/<button class="ds-button" type="button">Generar SHAP/);
});
test('image hook reuses authenticated SCC-ART access and preserves all relationship restrictions', async () => {
  let callback, enabled, key, sent;
  const load=loader({
    react:{useState:initial=>[initial,()=>{}],useCallback:fn=>fn},
    '../services/api':{api:{getArtifactBlob:async(...args)=>{sent=args;return new Blob(['png'],{type:'image/png'});}}},
    '../components/cell-review/AuthenticatedCellImage':{useAuthenticatedObjectUrl:(fn,active,id)=>{callback=fn;enabled=active;key=id;return emptyResource;}},
  });
  const hook=load('hooks/useScientificArtifact.ts').useScientificArtifact;
  hook({artifactId:'pk',source:'assessment',attemptId:'attempt',trainingRunId:'train'},'malaria',false);
  assert.equal(enabled,false);
  hook({artifactId:'pk',source:'assessment',attemptId:'attempt',trainingRunId:'train'},'malaria',true);
  const signal=new AbortController().signal; await callback(signal);
  assert.equal(enabled,true); assert.ok(key.includes('attempt'));
  assert.equal(sent[0],'pk'); assert.equal(sent[1].source,'assessment'); assert.equal(sent[1].attemptId,'attempt'); assert.equal(sent[1].trainingRunId,'train'); assert.equal(sent[2],signal);
});
test('structured artifact errors distinguish authorization, missing, integrity and other HTTP failures', () => {
  const load=loader({'../services/api':{},'../components/cell-review/AuthenticatedCellImage':{}});
  const classify=load('hooks/useScientificArtifact.ts').artifactFailure;
  for (const [status,code,expected] of [[401,null,'denied'],[403,null,'denied'],[410,'ARTIFACT_CONTENT_MISSING','missing'],[409,'ARTIFACT_INTEGRITY_FAILED','integrity_failed'],[404,'ARTIFACT_RELATION_MISMATCH','not_comparable'],[500,null,'error']]) {
    assert.equal(classify({status,code}).availability,expected);
  }
});
test('existing object URL lifecycle revokes on unmount and ignores late responses', async () => {
  let effect; const revoked=[]; let resolveBlob;
  const load=loader({react:{...React,useState:initial=>[initial,()=>{}],useEffect:fn=>{effect=fn;}},'../../services/api':{}},
    {URL:{createObjectURL:()=> 'blob:test',revokeObjectURL:url=>revoked.push(url)}});
  const hook=load('components/cell-review/AuthenticatedCellImage.tsx').useAuthenticatedObjectUrl;
  hook(()=>Promise.resolve(new Blob(['png'])),true,'pk');
  const cleanup=effect(); await new Promise(resolve=>setImmediate(resolve)); cleanup();
  assert.deepEqual(revoked,['blob:test']);
  hook(()=>new Promise(resolve=>{resolveBlob=resolve;}),true,'other');
  const cleanupLate=effect(); cleanupLate(); resolveBlob(new Blob(['late']));
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(revoked,['blob:test','blob:test']);
});
test('modal shares presentation/resources, native keyboard dialog and scoped four-column overflow', () => {
  const source=readFileSync(resolve(root,'components/reports/XAIComparisonViewer.tsx'),'utf8');
  const css=readFileSync(resolve(root,'styles/report-components.css'),'utf8');
  assert.equal((source.match(/<XAIComparisonContent comparison=/g)||[]).length,2);
  assert.match(source,/showModal\(\)/); assert.match(source,/method="dialog"/); assert.match(source,/trigger.current\?\.focus\(\)/);
  assert.match(source,/className="ds-report xai-viewer"/);
  assert.match(css,/grid-template-columns: repeat\(4, minmax\(var\(--ds-artifact-min-width\), 1fr\)\)/);
  assert.match(css,/\.ds-report \.xai-scroll \{ overflow-x: auto;/);
  assert.match(css,/\.xai-image-button:focus-visible/);
});

test('storage paths, sample selections and execution IDs do not substitute scientific identity', () => {
  const one=fixture('gradcam'), two=fixture('shap');
  one.detail.identity.execution_id='first'; two.detail.identity.execution_id='second';
  one.detail.identity.samples=['sample','other']; two.detail.identity.samples=['sample'];
  one.detail.identity.model.path='/mac/checkpoint'; two.detail.identity.model.path='/docker/checkpoint';
  one.detail.identity.dataset.dataset_root='/mac/data'; two.detail.identity.dataset.dataset_root='/docker/data';
  assert.equal(group([one,two],'train').length,1);
  two.detail.identity.dataset.record_assignment_fingerprint='different';
  assert.equal(group([one,two],'train').length,2);
});
function nodes(tree, predicate) {
  if (!tree || typeof tree!=='object' || !tree.props) return [];
  return [...(predicate(tree)?[tree]:[]),...React.Children.toArray(tree.props.children).flatMap(child=>nodes(child,predicate))];
}
test('visible observer defers image hooks; image action opens native modal and close restores focus', () => {
  const state=[false,null], refs=[]; let stateIndex=0,refIndex=0; let effects=[]; let observerCallback; let disconnected=0,shown=0,focused=0;
  const resourceCalls=[];
  class Element { focus() { focused++; } }
  const trigger=new Element();
  const load=loader({
    react:{...React,useId:()=> 'viewer-test',useMemo:fn=>fn(),useState:()=>{const i=stateIndex++;return [state[i],value=>{state[i]=value;}];},
      useRef:initial=>{const i=refIndex++;return refs[i]??(refs[i]={current:initial});},useEffect:fn=>effects.push(fn)},
    '../../hooks/useScientificArtifact':{useScientificArtifact:(artifact,source,enabled)=>{
      resourceCalls.push({artifact,enabled});return {...emptyResource,url:artifact?'blob:available':null};
    }},
  },{HTMLElement:Element,document:{activeElement:trigger},IntersectionObserver:class {
    constructor(callback) {observerCallback=callback;} observe() {} disconnect(){disconnected++;}
  }});
  const {XAIComparisonViewer}=load('components/reports/XAIComparisonViewer.tsx');
  const comparison=group([fixture()],'train')[0];
  function render() {stateIndex=0;refIndex=0;effects=[];return XAIComparisonViewer({comparison,datasource:'malaria'});}
  const first=render(); refs[0].current={}; refs[1].current={showModal(){shown++;}};
  const cleanup=effects[0]();
  assert.ok(resourceCalls.every(call=>call.enabled===false));
  observerCallback([{isIntersecting:true}]); assert.equal(state[0],true);
  const inline=nodes(first,node=>typeof node.props.onExpand==='function')[0];
  inline.props.onExpand('shap'); assert.equal(state[1],'shap');
  const modalTree=render(); effects[1](); assert.equal(shown,1);
  const contents=nodes(modalTree,node=>node.props.comparison===comparison);
  assert.equal(contents.length,2); assert.equal(contents[0].props.resources,contents[1].props.resources);
  nodes(modalTree,node=>node.type==='dialog')[0].props.onClose();
  assert.equal(state[1],null); assert.equal(focused,1); cleanup(); assert.ok(disconnected>=1);
});
test('comparison browser bounds mounted viewers to five and advances without fetching every PNG', () => {
  const page=fixture();
  page.artifacts=Array.from({length:100},(_,index)=>({...page.artifacts[0],artifact_id:`artifact-${index}`,sample_id:`sample-${index}`}));
  const state=[{}, {shap:page}, 0]; let index=0;
  function Viewer() {return null;}
  const load=loader({react:{...React,useState:()=>{const i=index++;return [state[i],value=>{state[i]=typeof value==='function'?value(state[i]):value;}];},useMemo:fn=>fn()},
    '../../hooks/useAssessment':{},'../../hooks/useAssessmentArtifacts':{},'./XAIComparisonViewer':{XAIComparisonViewer:Viewer}});
  const {TrainingXAIComparison}=load('components/reports/TrainingXAIComparison.tsx');
  function render() {index=0;return TrainingXAIComparison({assessments:[{method:'shap',attempt_id:'attempt-shap'}],trainingRunId:'train',datasource:'malaria'});}
  const first=render(); const viewers=nodes(first,node=>node.type===Viewer);
  assert.equal(viewers.length,5); assert.equal(viewers[0].props.comparison.sampleId,'sample-0');
  nodes(first,node=>node.type==='button' && node.props.children==='Muestras siguientes')[0].props.onClick();
  const next=nodes(render(),node=>node.type===Viewer);
  assert.equal(next.length,5); assert.equal(next[0].props.comparison.sampleId,'sample-5');
});

test('original and SHAP render side by side with disabled generation and compact inline density', () => {
  const row=group([fixture()],'train')[0];
  const html=presentation(row,{...resources,original:{...emptyResource,url:'blob:original'},shap:{...emptyResource,url:'blob:shap'}});
  assert.match(html,/<img[^>]*src="blob:original"/);
  assert.match(html,/<img[^>]*src="blob:shap"/);
  assert.equal((html.match(/class="xai-panel"/g)||[]).length,4);
  assert.match(html,/data-density="compact"/);
  assert.match(html,/Ampliar comparación/);
  assert.match(html,/<button[^>]*disabled=""[^>]*>Generar Grad-CAM/);
  assert.match(html,/<button[^>]*disabled=""[^>]*>Generar LIME/);
  assert.match(html,/No aplica: muestra del dataset gobernado/);
  assert.match(html,/download="sample.png"/);
  assert.match(html,/background-not-original/);
});
test('original source hook shares URL lifecycle while using sample rather than artifact identity', async () => {
  let callback,active,key,sent;
  const load=loader({react:{useState:initial=>[initial,()=>{}],useCallback:fn=>fn},
    '../services/api':{api:{getDatasetSampleBlob:async(...args)=>{sent=args;return new Blob(['original'],{type:'image/png'});},getArtifactBlob:()=>{throw new Error('Original is not an artifact PK');}}},
    '../components/cell-review/AuthenticatedCellImage':{useAuthenticatedObjectUrl:(fn,enabled,id)=>{callback=fn;active=enabled;key=id;return emptyResource;}}});
  const hook=load('hooks/useScientificArtifact.ts').useScientificArtifact;
  hook({source:'dataset_sample',trainingRunId:'train',attemptId:'attempt',datasetVersionId:'dataset',sampleId:'sample'},'malaria',true);
  await callback(new AbortController().signal);
  assert.equal(active,true);assert.ok(key.includes('dataset_sample'));assert.ok(key.includes('sample'));
  assert.equal(sent[0].sampleId,'sample');assert.equal(sent[0].trainingRunId,'train');assert.equal(sent[0].datasetVersionId,'dataset');assert.equal(sent[0].attemptId,'attempt');
});
test('compact thumbnails have bounded height while modal keeps expanded presentation', () => {
  const css=readFileSync(resolve(root,'styles/report-components.css'),'utf8');
  const source=readFileSync(resolve(root,'components/reports/XAIComparisonViewer.tsx'),'utf8');
  assert.match(css,/data-density="compact"/);
  assert.match(css,/height: var\(--ds-xai-thumbnail-height\)/);
  assert.match(source,/density="expanded"/);
});
