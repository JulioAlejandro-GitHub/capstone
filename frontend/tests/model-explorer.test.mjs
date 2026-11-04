import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const root = fileURLToPath(new URL('../src/', import.meta.url));
const read = (path) => readFileSync(resolve(root, path), 'utf8');
function load(filename, cache = new Map()) {
  const path = resolve(root, filename);
  if (cache.has(path)) return cache.get(path);
  const module = { exports: {} };
  cache.set(path, module.exports);
  const code = ts.transpileModule(readFileSync(path, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
  runInNewContext(code, { exports: module.exports, module, Math, Array, JSON, Map, require: (name) => name.startsWith('.')
    ? load(`${dirname(path).slice(root.length)}/${name}.ts${name.endsWith('Chart') ? 'x' : ''}`, cache) : require(name) });
  return module.exports;
}
const views = load('components/model-architecture/architectureViews.ts');
const { ArchitectureChart, denseUnits } = load('components/model-architecture/ArchitectureChart.tsx');

const block = (id, kind, shape, phases = ['base'], extra = {}) => ({ id, label: id, kind, layers: 2, units: null, output_shape: shape, parameters: 100, trainable_phases: phases, origin: 'recorded', ...extra });
const data = (family, blocks, layers = []) => ({ training_run_id: 'a', family, architecture: family, model_name: family, blocks, layers, phases: [{ phase: 'base' }], output: { neurons: 1, activation: 'sigmoid', loss: 'bce_with_logits', from_logits: true, embedding_features: 512 }, checkpoint: {} });
const cnn = data('custom_cnn', [block('input', 'input', [null, 200, 200, 3], []), block('block1', 'convolution', [null, 100, 100, 32]), block('output', 'output', [null, 1])],
  [{ name: 'conv2d', type: 'Conv2D', block: 'block1', output_shape: [null, 100, 100, 32], inputs: ['input_layer'], parameters: 864, trainable_phases: ['base'], settings: {} }]);

test('cada familia tiene su vista inicial y una URL inválida vuelve a ella', () => {
  assert.equal(views.resolveView('vgg16', null), 'bloques-3d');
  assert.equal(views.resolveView('custom_cnn', null), 'mapas');
  assert.equal(views.resolveView('densenet121', 'bloques-3d'), 'grafo');
  assert.equal(views.resolveView('biomedclip', 'vit'), 'vit');
  for (const family of ['custom_cnn', 'vgg16', 'densenet121', 'biomedclip', 'generic']) assert.ok(Array.from(views.viewsFor(family)).includes('tabla'));
});

test('todas las vistas de una familia muestran los mismos datos reales', () => {
  for (const view of Array.from(views.viewsFor('custom_cnn')).concat('bloques-3d')) {
    const html = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: cnn, view, phase: 'base' }));
    assert.match(html, /100 × 100 × 32/, view);
  }
  const table = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: cnn, view: 'tabla', phase: 'base' }));
  assert.match(table, /conv2d/);
  assert.match(table, /Entrenada/);
});

test('la fase decide qué bloques se marcan como entrenados', () => {
  const frozen = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: data('vgg16', [block('block5', 'convolution', [null, 6, 6, 512], ['fine_tuning'])]), view: 'bloques-3d', phase: 'base' }));
  assert.match(frozen, /data-trained="false"/);
  const trained = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: data('vgg16', [block('block5', 'convolution', [null, 6, 6, 512], ['fine_tuning'])]), view: 'bloques-3d', phase: 'fine_tuning' }));
  assert.match(trained, /data-trained="true"/);
});

test('DenseNet rotula sus conexiones como derivadas y sólo cuenta concatenaciones del bloque', () => {
  const units = [1, 2, 3].map(index => ({ name: `conv2_block${index}_concat`, type: 'Concatenate', block: 'dense2', output_shape: [null, 50, 50, 64 + index * 32], inputs: [], parameters: 0, trainable_phases: [], settings: {} }));
  const dense = data('densenet121', [block('dense2', 'dense', [null, 50, 50, 160], [], { units: 3 })],
    [...units, { name: 'conv2_block1_1_conv', type: 'Conv2D', block: 'dense2', output_shape: null, inputs: [], parameters: 1, trainable_phases: [], settings: {} }]);
  assert.equal(denseUnits(dense, 'dense2').length, 3);
  const html = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: dense, view: 'conexiones', phase: 'base' }));
  assert.match(html, /Dibujo derivado/);
  assert.match(html, /Capa 3 de 3/);
});

test('BiomedCLIP declara la estructura de referencia y no inventa capas', () => {
  const vit = data('biomedclip', [block('input', 'input', [null, 224, 224, 3], []), block('vit0', 'encoder', null, [], { origin: 'reference' }), block('head', 'head', [null, 1])]);
  assert.match(renderToStaticMarkup(React.createElement(ArchitectureChart, { data: vit, view: 'flujo', phase: 'base' })), /Estructura de referencia/);
  assert.match(renderToStaticMarkup(React.createElement(ArchitectureChart, { data: vit, view: 'tabla', phase: 'base' })), /Referencia del encoder/);
});

test('la página reutiliza el selector, conserva la selección en la URL y no toca la de comparación', () => {
  const page = read('pages/ModelExplorer.tsx');
  assert.match(page, /RunSelectorDialog/);
  assert.match(page, /search\.get\('run'\)/);
  assert.match(page, /isValidPublicId/);
  assert.doesNotMatch(page, /useComparisonSelection/);
  assert.match(read('pages/ModelComparison.tsx'), /RunSelectorDialog/);
  assert.match(read('components/navigation/navigationConfig.ts'), /Arquitectura del modelo/);
  assert.match(read('App.tsx'), /routes\.modelExplorer/);
  assert.match(read('services/api.ts'), /\/architecture`/);
});

test('el selector sin máximo permite elegir y los menús de filtro viven en el diálogo abierto', () => {
  const table = read('components/reports/TrainingRunsTable.tsx');
  assert.match(table, /selection\?\.maximum === undefined \? Number\.POSITIVE_INFINITY/);
  assert.match(table, /document\.querySelector<HTMLElement>\('dialog\[open\]'\)/);
  assert.doesNotMatch(table, /disablePortal/);
  assert.match(table, /=> \(\{ value, label \}\)/);
});

test('Análisis de Modelos reutiliza el detalle con un modelo activo a la vez', () => {
  const panel = read('components/model-architecture/ArchitecturePanel.tsx');
  assert.match(read('components/reports/AnalysisWorkspace.tsx'), /id: 'arquitectura', label: 'Arquitectura'/);
  assert.match(panel, /ArchitectureDetail/);
  assert.match(panel, /aria-pressed=\{id === run\}/);
  assert.match(panel, /ids\.length > 1/);
  assert.match(panel, /ids\.find\(id => id === selected\) \?\? ids\[0\]/);
  assert.match(panel, /cache, key, .*active\)/);
  assert.match(read('components/reports/ScientificPreflight.tsx'), /id="arquitectura"/);
  assert.match(read('pages/ModelComparison.tsx'), /search\.get\('modelo'\)/);
  assert.match(read('pages/ModelExplorer.tsx'), /ArchitectureDetail/);
});

test('todas las vistas gráficas identifican la capa de salida', () => {
  const blocks = [block('input', 'input', [null, 200, 200, 3], []), block('output', 'output', [null, 1], ['base'], { label: 'Capa de salida' })];
  const vit = [block('vit0', 'encoder', null, [], { origin: 'reference' }), ...blocks];
  for (const [family, items] of [['custom_cnn', blocks], ['vgg16', blocks], ['densenet121', blocks], ['biomedclip', vit]]) {
    for (const view of Array.from(views.viewsFor(family)).filter(item => item !== 'tabla' && item !== 'conexiones')) {
      const html = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: data(family, items), view, phase: 'base' }));
      assert.match(html, /1 neurona · Sigmoide/, `${family} ${view}`);
    }
  }
  assert.equal(views.outputText({ neurons: 2, activation: 'softmax' }), '2 neuronas · Softmax');
  assert.equal(views.lossText({ loss: 'binary_crossentropy', from_logits: false }), 'Pérdida: Binary Cross-Entropy');
  assert.match(views.lossText({ loss: 'bce_with_logits', from_logits: true }), /with Logits; la capa entrega logits/);
});

test('la función matemática respeta la configuración registrada de cada capa', () => {
  const math = load('components/model-architecture/mathOperations.tsx');
  const conv = (name, settings) => ({ name, type: 'Conv2D', block: 'block1', output_shape: [null, 200, 200, 32], inputs: [], parameters: 1, trainable_phases: [], settings: { filters: 32, kernel_size: [3, 3], strides: [1, 1], padding: 'same', ...settings } });
  const block = { id: 'block1', label: 'Bloque 1', kind: 'convolution', origin: 'recorded' };
  const model = { family: 'custom_cnn', blocks: [block], output: null, layers: [conv('a', { use_bias: false, activation: 'linear' })] };
  const noBias = renderToStaticMarkup(math.blockOperations(model, block)[0].formula);
  assert.doesNotMatch(noBias, /<mi>b<\/mi>/);
  assert.doesNotMatch(noBias, /max/);
  assert.match(math.blockOperations(model, block)[0].detail, /sin sesgo/);
  const vgg = { ...model, layers: [conv('a', { use_bias: true, activation: 'relu' }), conv('b', { use_bias: true, activation: 'relu' })] };
  const [operation] = math.blockOperations(vgg, block);
  assert.equal(operation.count, 2);
  const withBias = renderToStaticMarkup(operation.formula);
  assert.match(withBias, /<mi>b<\/mi>/);
  assert.match(withBias, /max/);
});

test('BiomedCLIP entrenado no usa similitud y el recorrido no inventa una predicción', () => {
  const math = load('components/model-architecture/mathOperations.tsx');
  const output = { neurons: 1, activation: 'sigmoid', loss: 'bce_with_logits', from_logits: true, embedding_features: 512 };
  const encoder = { id: 'vit0', kind: 'encoder', origin: 'reference' }, head = { id: 'output', kind: 'output', origin: 'recorded' };
  const model = { family: 'biomedclip', input_shape: [null, 224, 224, 3], blocks: [encoder, head], layers: [], output };
  assert.ok(math.blockOperations(model, encoder).every(item => item.origin === 'reference'));
  assert.match(renderToStaticMarkup(math.blockOperations(model, encoder)[1].formula), /softmax/);
  const titles = math.blockOperations(model, head).map(item => item.title);
  assert.deepEqual(Array.from(titles), ['Embedding L2', 'Capa de salida', 'Pérdida de entrenamiento']);
  assert.match(math.blockOperations(model, head)[1].detail, /no usa similitud/);
  assert.deepEqual(Array.from(math.tensorPath(model)), ['224 × 224 × 3', 'Parches y tokens', 'Encoder ViT · 1 bloques', 'Embedding 512', '1 logit', 'Sigmoide']);
});

test('el recorrido describe cada paso y compara solo tensores del mismo tipo', () => {
  const steps = load('components/model-architecture/traceSteps.ts');
  assert.equal(steps.outcomeOf({ label: 1, predicted: 0 }), 'Falso negativo');
  assert.equal(steps.outcomeOf({ label: null, predicted: 0 }), 'Sin evidencia');
  const trace = [{ kind: 'spatial', stats: { active: 0.8, mean: 2 } }, { kind: 'spatial', stats: { active: 0.5, mean: 1 } }, { kind: 'vector', stats: { active: 0.6, mean: 1 } }];
  assert.ok(Math.abs(steps.stepChange(trace, 1).active + 0.3) < 1e-9);
  assert.equal(steps.stepChange(trace, 2), null);
  assert.equal(steps.stepChange(trace, 0), null);
});

test('abrir el panel solo lee lo guardado y el cálculo exige una acción y permiso', () => {
  const panel = read('components/model-architecture/ActivationTracePanel.tsx');
  assert.match(panel, /next\.items\[0\]/);
  assert.match(panel, /scientific\.cell_classification\.explain/);
  assert.equal((panel.match(/createActivationTrace/g) ?? []).length, 1);
  assert.match(panel, /const calculate = async/);
  assert.match(panel, /no coincide con el guardado/);
  assert.match(panel, /window\.confirm/);
  assert.match(read('components/model-architecture/ArchitectureDetail.tsx'), /data\.family === 'vgg16' && <ActivationTracePanel/);
});

test('el código de cada paso sale de la configuración registrada del TRAIN', () => {
  const code = load('components/model-architecture/traceCode.ts');
  const layer = (name, type, block, settings, shape = null) => ({ name, type, block, settings, output_shape: shape, inputs: [], parameters: 1, trainable_phases: [] });
  const model = { input_shape: [null, 200, 200, 3], blocks: [{ id: 'block4', label: 'Bloque 4' }], layers: [
    layer('block4_conv1', 'Conv2D', 'block4', { filters: 512, kernel_size: [3, 3], strides: [1, 1], padding: 'same', activation: 'relu' }),
    layer('block4_pool', 'MaxPooling2D', 'block4', { pool_size: [2, 2], strides: [2, 2] }),
    layer('flatten', 'Flatten', 'head', {}), layer('dense', 'Dense', 'head', { units: 256, activation: 'relu' }) ] };
  const block = code.stepCode(model, { layer: 'block4_pool', block: 'block4', kind: 'spatial', shape: [12, 12, 512] });
  assert.match(block, /Conv2D\(512, \(3, 3\), padding='same', activation='relu', name='block4_conv1'\)/);
  assert.match(block, /MaxPooling2D\(\(2, 2\), name='block4_pool'\)/);
  assert.equal(code.stepCode(model, { layer: 'flatten', block: 'head', kind: 'vector', shape: [18432] }), "x = layers.Flatten(name='flatten')(x)");
  assert.equal(code.stepCode(model, null), 'inputs = layers.Input(shape=(200, 200, 3))');
  assert.equal(code.stepTitle(model, { layer: 'dense', block: 'head', kind: 'vector', shape: [256] }), 'Densa 256');
  assert.equal(code.stepTitle(model, { layer: 'block4_pool', block: 'block4', kind: 'spatial', shape: [12, 12, 512] }), 'Bloque 4');
});

test('la escala de color va de azul oscuro a amarillo y recorta fuera de rango', () => {
  const color = load('components/model-architecture/traceColor.ts');
  assert.deepEqual(Array.from(color.cividis(0)), [0, 34, 78]);
  assert.deepEqual(Array.from(color.cividis(1)), [254, 232, 56]);
  assert.deepEqual(Array.from(color.cividis(2)), Array.from(color.cividis(1)));
  assert.deepEqual(Array.from(color.cividis(Number.NaN)), Array.from(color.cividis(0)));
});

test('el panel ofrece modales, escala común y enlaces a Aprendizaje y Explicabilidad', () => {
  const panel = read('components/model-architecture/ActivationTracePanel.tsx');
  assert.match(panel, /showModal\(\)/);
  assert.match(panel, /Escala común/);
  assert.match(panel, /seccion: 'aprendizaje'/);
  assert.match(panel, /seccion: 'explicabilidad', muestra: trace\.sample_id/);
});

test('el diagrama de arquitectura es el único navegador del recorrido', () => {
  const panel = read('components/model-architecture/ActivationTracePanel.tsx');
  assert.doesNotMatch(panel, /mx-strip/);
  assert.match(panel, /blockClick\.n === handled\.current/);
  assert.match(read('components/model-architecture/ArchitectureDetail.tsx'), /blockClick=\{blockClick\}/);
});

test('VGG16 dibuja la cabeza capa por capa: un elemento por paso del recorrido', () => {
  const layer = (name, type, block, settings = {}, parameters = 0) => ({ name, type, block, settings, output_shape: [null, 1024], inputs: [], parameters, trainable_phases: ['base'] });
  const model = { family: 'vgg16', blocks: [{ id: 'input' }, { id: 'block5' }, { id: 'head', label: 'Cabeza de clasificación' }, { id: 'output' }], layers: [
    layer('block5_pool', 'MaxPooling2D', 'block5'), layer('global_avg_pool', 'GlobalAveragePooling2D', 'head'),
    layer('feature_dense_1024', 'Dense', 'head', { units: 1024 }, 525312), layer('dropout_50', 'Dropout', 'head'), layer('binary_output', 'Dense', 'output', { units: 1 }, 1025) ] };
  const split = views.splitHead(model);
  assert.deepEqual(Array.from(split.blocks, block => block.id), ['input', 'block5', 'global_avg_pool', 'feature_dense_1024', 'output']);
  assert.deepEqual(Array.from(split.blocks.slice(2, 4), block => [block.label, block.layers, block.parameters]), [['Promedio global', 1, 0], ['Densa 1024', 2, 525312]]);
  assert.equal(split.layers.find(item => item.name === 'dropout_50').block, 'feature_dense_1024');
  const code = load('components/model-architecture/traceCode.ts');
  assert.equal(code.stepTitle(split, { layer: 'feature_dense_1024', block: 'head', kind: 'vector', shape: [1024] }), 'Densa 1024');
});

test('el diagrama anota bajo cada bloque los valores activos de la célula abierta', () => {
  const blocks = [block('input', 'input', [null, 200, 200, 3], []), block('block1', 'convolution', [null, 100, 100, 64]), block('output', 'output', [null, 1])];
  const vgg = data('vgg16', blocks);
  const activity = { block1: { value: 0.171, label: '17,1 % activos', current: true }, output: { value: 0.035, label: 'p 0,035', current: false } };
  const html = renderToStaticMarkup(React.createElement(ArchitectureChart, { data: vgg, view: 'bloques-3d', phase: 'base', activity }));
  assert.match(html, /17,1 % activos/);
  assert.match(html, /p 0,035/);
  assert.match(html, /data-current="true"/);
  assert.doesNotMatch(renderToStaticMarkup(React.createElement(ArchitectureChart, { data: vgg, view: 'bloques-3d', phase: 'base' })), /mx-activity/);
});
