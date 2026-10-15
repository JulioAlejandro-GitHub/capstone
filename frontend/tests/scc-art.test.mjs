import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import ts from 'typescript';

function client(fetch) {
  const source = readFileSync(new URL('../src/services/api.ts', import.meta.url), 'utf8').replaceAll('import.meta.env', '{}');
  const module = {exports: {}};
  const context = {exports: module.exports, require: () => ({}), URL, URLSearchParams, Headers,
    AbortController, DOMException, fetch, window: {setTimeout, clearTimeout, localStorage: {getItem: () => null, setItem() {}, removeItem() {}}, dispatchEvent() {}},
    setTimeout, clearTimeout, CustomEvent: class {}};
  runInNewContext(ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS}}).outputText, context);
  return module.exports;
}

test('scientific blob uses bearer and explicit source/relationships without path', async () => {
  let sent;
  const c = client(async (url, options) => {sent = {url, options}; return new Response(new Blob(['png'], {type:'image/png'}));});
  c.setAccessToken('fixture-token');
  const blob = await c.api.getArtifactBlob('artifact', {source:'assessment', attemptId:'attempt', trainingRunId:'train'});
  assert.equal(sent.options.headers.get('Authorization'), 'Bearer fixture-token');
  assert.equal(sent.url.searchParams.get('artifact_id'),'artifact');
  assert.equal(sent.url.searchParams.get('source'),'assessment');
  assert.equal(sent.url.searchParams.get('attempt_id'),'attempt');
  assert.equal(sent.url.searchParams.get('training_run_id'),'train');
  assert.equal(sent.url.searchParams.has('path'), false);
  assert.equal(await blob.text(), 'png');
});

test('missing physical content rejects instead of generating a preview', async () => {
  const c = client(async () => new Response(JSON.stringify({error:{code:'ARTIFACT_CONTENT_MISSING'}}), {status:410}));
  await assert.rejects(c.api.getArtifactBlob('artifact',{source:'training'}), error => error.status === 410 && error.message.includes('falta el archivo físico'));
});

test('legacy client never forwards bearer to a different origin', async () => {
  let calls = 0;
  const c = client(async () => {calls++;return new Response('');});
  await assert.rejects(c.api.getLegacyArtifactBlob('https://untrusted.example/artifacts/file'));
  assert.equal(calls,0);
});

import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
const require = createRequire(import.meta.url);
const root = fileURLToPath(new URL('../src/', import.meta.url));
function loader(mocks = {}) {
  const cache = new Map();
  const load = (filename) => {
    const path = resolve(root, filename);
    if (cache.has(path)) return cache.get(path);
    const module = { exports: {} };
    cache.set(path, module.exports);
    const code = ts.transpileModule(readFileSync(path, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText;
    runInNewContext(code, { exports: module.exports, URLSearchParams, AbortController,
      require: (name) => {
        if (name in mocks) return mocks[name];
        if (name.endsWith('.css')) return {};
        if (!name.startsWith('.')) return require(name);
        const base = resolve(dirname(path), name);
        const target = [base, `${base}.tsx`, `${base}.ts`].find(existsSync);
        if (!target) throw new Error(`Cannot load ${name} from ${path}`);
        return load(target);
      },
    });
    return module.exports;
  };
  return load;
}


const detail = {id: 'attempt', training_run_id: 'train', identity_id: 'identity', ordinal: 1,
  state: 'verified', identity: {model: {checkpoint_artifact_id: 'checkpoint'},
    explanation: {method: 'shap', background: [{sample_id: 'reference'}]}}};
function report(items, state = {}) {
  const requests = [];
  const load = loader({
    '../../hooks/useAssessmentArtifacts': {useAssessmentArtifacts: (id, offset) => {
      assert.equal(id, 'attempt'); assert.equal(offset, 0);
      return {items, loading: false, error: null, ...state};
    }},
    './ScientificArtifact': {ScientificArtifact: props => {
      requests.push(props);
      return React.createElement('img', {src: `blob:${props.artifactId}`, alt: props.label});
    }},
  });
  const {AssessmentExplanationDetail} = load('components/reports/AssessmentExplanationDetail.tsx');
  return {requests, html: renderToStaticMarkup(React.createElement(AssessmentExplanationDetail, {data: detail, datasource: 'malaria'}))};
}
test('EXPLAIN renders multiple registered images with method, explained sample and separate SHAP reference', () => {
  const {requests, html} = report([{artifact_id:'a', role:'overlay', sample_id:'explained'}, {artifact_id:'b', role:'overlay'}, {artifact_id:'c', role:'map'}]);
  assert.equal(requests.length, 3);
  for (const p of requests) {
    assert.equal(p.source, 'assessment'); assert.equal(p.attemptId, 'attempt');
    assert.equal(p.trainingRunId, 'train'); assert.equal(p.autoLoad, p.artifactId !== 'c');
  }
  for (const text of ['blob:a', 'blob:b', 'SHAP', 'Muestra explicada: explained', 'Referencia SHAP: reference', 'Muestra explicada: No registrada']) assert.ok(html.includes(text), text);
});
test('report distinguishes empty evidence, loading and list errors', () => {
  assert.match(report([]).html, /Sin evidencia registrada/);
  assert.match(report([], {loading:true}).html, /Cargando referencias/);
  assert.doesNotMatch(report([], {loading:true}).html, /Sin evidencia registrada/);
  assert.match(report([], {error:'HTTP failure'}).html, /role="alert"/);
});
test('artifact list requests the attempt and public projection with authentication', async () => {
  let sent;
  const c = client(async (url, options) => {sent={url,options}; return new Response(JSON.stringify({items:[{artifact_id:'registered-id'}]}));});
  c.setAccessToken('fixture-token');
  const result = await c.api.getAssessmentArtifacts('attempt', 100);
  assert.equal(result.items[0].artifact_id, 'registered-id');
  assert.match(sent.url.pathname, /assessments\/attempt\/artifacts$/);
  assert.equal(sent.url.searchParams.get('view'), 'traceability');
  assert.equal(sent.url.searchParams.get('offset'), '100');
  assert.equal(sent.options.headers.get('Authorization'), 'Bearer fixture-token');
});
for (const [status, code, message] of [[409,'ARTIFACT_INTEGRITY_FAILED', /integridad/], [403,'FORBIDDEN', /autorización/], [500,'INTERNAL_ERROR', /HTTP 500/]]) {
  test(`artifact HTTP ${status} is distinguished`, async () => {
    const c = client(async () => new Response(JSON.stringify({error:{code}}), {status}));
    await assert.rejects(c.api.getArtifactBlob('a',{source:'assessment'}), error => error.status === status && message.test(error.message));
  });
}
test('TRAIN retains explicit source and authenticated download', async () => {
  let sent;
  const c = client(async (url, options) => {sent={url,options}; return new Response('training');});
  c.setAccessToken('fixture-token');
  assert.equal(await (await c.api.getArtifactBlob('train-artifact', {source:'training'})).text(), 'training');
  assert.equal(sent.url.searchParams.get('source'), 'training');
  assert.equal(sent.options.headers.get('Authorization'), 'Bearer fixture-token');
});
test('ScientificArtifact automatically enables authenticated object URL and renders PNG/download', async () => {
  let enabled, call;
  const load = loader({
    react: {...React, useState: initial => [initial === '' ? 'image/png' : initial, () => {}]},
    '../../services/api': {api:{getArtifactBlob: async (...args) => {call=args; return new Blob(['png'],{type:'image/png'});}}},
    '../cell-review/AuthenticatedCellImage': {useAuthenticatedObjectUrl: (load, active) => {
      enabled=active; load(new AbortController().signal);
      return {url:'blob:authenticated', loading:false, error:false};
    }},
  });
  const {ScientificArtifact} = load('components/reports/ScientificArtifact.tsx');
  const html = renderToStaticMarkup(React.createElement(ScientificArtifact, {artifactId:'a',source:'assessment',attemptId:'attempt',trainingRunId:'train',label:'Grad-CAM',preview:true,autoLoad:true}));
  assert.equal(enabled,true); assert.equal(call[0],'a'); assert.equal(call[1].source,'assessment');
  assert.match(html, /<img src="blob:authenticated"/); assert.match(html, /download="a.png"/);
  assert.doesNotMatch(html, /Ver imagen/);
});

test('registered missing image is rendered as an error rather than absent evidence', () => {
  const load = loader({
    react: {...React, useState: initial => [initial === 'Artefacto no disponible.' ? 'El artefacto está registrado, pero falta el archivo físico.' : initial, () => {}]},
    '../../services/api': {api:{}},
    '../cell-review/AuthenticatedCellImage': {useAuthenticatedObjectUrl: () => ({url:null,loading:false,error:true})},
  });
  const {ScientificArtifact} = load('components/reports/ScientificArtifact.tsx');
  const html = renderToStaticMarkup(React.createElement(ScientificArtifact, {artifactId:'registered',source:'assessment',label:'LIME',preview:true,autoLoad:true}));
  assert.match(html,/role="alert"/); assert.match(html,/falta el archivo físico/);
  assert.match(html,/La ejecución permanece registrada/); assert.doesNotMatch(html,/<img/);
});

const shapTrain = 'd3d42cf3-0800-468c-b3ed-995860967da1';
const shapAttempt = '93966b5d-5548-4b29-96f9-0b67e5c98f9f';
const shapArtifact = '2b4f68d6-2826-489c-980b-69f686223b11';
const shapChild = {source_kind:'assessment_explain_e6', training_run_id:shapTrain,
  attempt_id:shapAttempt, method:'shap', state:'verified', result_count:1};
test('TRAIN loads E6 EXPLAIN across mixed lineage pages, retaining exact attempt', async () => {
  let effect, state;
  const requests=[];
  const load=loader({
    react:{useState:initial=>[initial,value=>{state=value;}],useEffect:callback=>{effect=callback;}},
    '../services/api':{api:{getTrainingLineageChildren:async options=>{
      requests.push(options);
      return {training_run_id:shapTrain, evaluations:options.offset===0?[{attempt_id:'evaluation'}]:[],
        explainabilities:options.offset===0?[]:[shapChild],truncated:options.offset===0};
    }}},
  });
  load('hooks/useTrainingExplanations.ts').useTrainingExplanations(shapTrain,'malaria');
  const cleanup=effect();
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(requests.map(r=>r.offset),[0,1]);
  assert.ok(requests.every(r=>r.trainingRunId===shapTrain));
  assert.equal(state.items[0].attempt_id,shapAttempt); assert.equal(state.error,null);
  cleanup(); assert.equal(requests[0].signal.aborted,true);
});
test('TRAIN refuses unrelated attempts and surfaces lineage errors', async () => {
  let effect,state;
  const load=loader({
    react:{useState:initial=>[initial,value=>{state=value;}],useEffect:callback=>{effect=callback;}},
    '../services/api':{api:{getTrainingLineageChildren:async()=>({training_run_id:shapTrain,
      evaluations:[],explainabilities:[{...shapChild,training_run_id:'other'}],truncated:false})}},
  });
  load('hooks/useTrainingExplanations.ts').useTrainingExplanations(shapTrain,'malaria');
  effect(); await new Promise(resolve=>setImmediate(resolve));
  assert.match(state.error,/no pertenece/); assert.equal(state.items.length,0);
});
test('SHAP acceptance fixture opens the registered PNG inside TRAIN using assessment source', () => {
  const requests=[];
  const load=loader({
    react:{...React,useState:initial=>[typeof initial==='boolean'?true:initial,()=>{}]},
    '../../hooks/useAssessment':{useAssessment:id=>{
      assert.equal(id,shapAttempt);
      return {loading:false,error:null,data:{...detail,id:shapAttempt,kind:'explain',training_run_id:shapTrain}};
    }},
    '../../hooks/useAssessmentArtifacts':{useAssessmentArtifacts:id=>{
      assert.equal(id,shapAttempt);
      return {loading:false,error:null,items:[{artifact_id:shapArtifact,role:'overlay',sample_id:'explained'}]};
    }},
    './ScientificArtifact':{ScientificArtifact:props=>{
      requests.push(props); return React.createElement('img',{src:`blob:${props.artifactId}`,alt:props.label});
    }},
  });
  const {TrainingExplanationAttempt}=load('components/reports/TrainingExplanationAttempt.tsx');
  const html=renderToStaticMarkup(React.createElement(TrainingExplanationAttempt,{assessment:shapChild,datasource:'malaria'}));
  for(const value of ['SHAP',shapAttempt,shapTrain,shapArtifact,'verified']) assert.ok(html.includes(value),value);
  assert.equal(requests[0].artifactId,shapArtifact); assert.equal(requests[0].source,'assessment');
  assert.equal(requests[0].attemptId,shapAttempt); assert.equal(requests[0].trainingRunId,shapTrain);
  assert.equal(requests[0].autoLoad,true); assert.doesNotMatch(html,/0 resultados cargados/);
  const page=readFileSync(new URL('../src/pages/RunDetail.tsx',import.meta.url),'utf8');
  assert.match(page,/assessmentExplanations.items.map\(assessment => <TrainingExplanationAttempt/);
  assert.ok(page.indexOf('assessmentExplanations.items.length > 0') < page.indexOf('`${explainabilityTotal} resultados cargados'));
});
test('TRAIN evidence rejects a detail belonging to another parent before listing artifacts', () => {
  const load=loader({'./AssessmentExplanationDetail':{AssessmentExplanationDetail:()=>{throw new Error('Must not load unrelated artifacts');}}, '../../hooks/useAssessment':{useAssessment:()=>({loading:false,error:null,
    data:{...detail,id:shapAttempt,kind:'explain',training_run_id:'other'}})}});
  const {TrainingExplanationEvidence}=load('components/reports/TrainingExplanationAttempt.tsx');
  const html=renderToStaticMarkup(React.createElement(TrainingExplanationEvidence,{attemptId:shapAttempt,trainingRunId:shapTrain,datasource:'malaria'}));
  assert.match(html,/no corresponde al TRAIN/); assert.doesNotMatch(html,/<img/);
});
