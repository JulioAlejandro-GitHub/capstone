import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const root = fileURLToPath(new URL('../src/', import.meta.url));
function load(filename) {
  const path = resolve(root, filename);
  const module = { exports: {} };
  const code = ts.transpileModule(readFileSync(path, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true } }).outputText;
  runInNewContext(code, { exports: module.exports, module, Math, Array, JSON, Map, Set, Number, String, Object, require: () => ({}) });
  return module.exports;
}
const history = load('components/model-training/trainingHistoryModel.ts');
const plain = value => JSON.parse(JSON.stringify(value));

const curve = { epochs: [
  { epoch: 1, phase: 'base', values: { learning_rate: 1e-3, loss: 0.6 } },
  { epoch: 2, phase: 'base', values: { learning_rate: 1e-3, loss: 0.4 } },
  { epoch: 3, phase: 'base', values: { learning_rate: 5e-4, loss: 0.35 } },
  { epoch: 4, phase: 'fine_tuning', values: { learning_rate: 1e-5, loss: 0.3 } },
  { epoch: 5, phase: 'fine_tuning', values: { loss: 0.29 } },
] };

test('el learning rate sale de lo registrado y sólo se marcan cambios reales, sin atribuir causa', () => {
  const points = history.learningRateSeries(curve);
  assert.deepEqual(Array.from(points, p => p.epoch), [1, 2, 3, 4], 'la época sin learning_rate no se inventa');
  const changes = plain(history.learningRateChanges(points));
  assert.deepEqual(changes.map(c => [c.epoch, c.phaseStart]), [[3, false], [4, true]]);
  assert.equal(changes[0].factor, 0.5);
  assert.equal(history.fineTuneStart(points), 4);
});

const trajectories = {
  state: 'available', issues: [], training_threshold: 0.5,
  epochs: [{ epoch: 1, phase: 'base' }, { epoch: 2, phase: 'base' }, { epoch: 3, phase: 'fine_tuning' }],
  samples: [
    { sample: 'val/P/estable.png', label: 1, sample_id: 'id-1' },
    { sample: 'val/P/olvidada.png', label: 1, sample_id: null },
    { sample: 'val/U/nunca.png', label: 0, sample_id: null },
    { sample: 'val/U/temprana.png', label: 0, sample_id: null },
  ],
  scores: [[0.2, 0.7, 0.9], [0.8, 0.6, 0.3], [0.9, 0.8, 0.7], [0.1, 0.2, 0.1]],
};

test('cada célula se clasifica por su historia: aprendida, olvidada o nunca', () => {
  const items = plain(history.sampleTrajectories(trajectories));
  assert.deepEqual(items.map(i => [i.outcome, i.learnedAt, i.flips]), [['aprendida', 2, 1], ['olvidada', null, 1], ['nunca', null, 0], ['aprendida', 1, 0]]);
  assert.equal(history.trueClassProbability(0, 0.1), 0.9);
  assert.deepEqual(plain(history.outcomeCounts(items)), { aprendida: 2, olvidada: 1, nunca: 1, inestable: 0 });
});

test('el mapa ordena por clase y época de aprendizaje, con las nunca aprendidas al final de su clase', () => {
  const order = history.orderTrajectories(history.sampleTrajectories(trajectories));
  assert.deepEqual(Array.from(order, i => i.sample), ['val/P/estable.png', 'val/P/olvidada.png', 'val/U/temprana.png', 'val/U/nunca.png']);
});

test('la fracción bien clasificada por época se separa por clase al umbral de TRAIN', () => {
  const rows = plain(history.accuracyByEpoch(trajectories));
  assert.deepEqual(rows.map(r => [r.epoch, r.parasitized, r.uninfected]), [[1, 0.5, 0.5], [2, 1, 0.5], [3, 0.5, 0.5]]);
});

test('las pestañas desconocidas vuelven al flujo de tensores y las derivables quedan marcadas', () => {
  assert.equal(history.viewFrom('trayectorias'), 'trayectorias');
  assert.equal(history.viewFrom('otra'), 'flujo');
  assert.equal(history.viewFrom(null), 'flujo');
  assert.ok(history.CHECKPOINT_ANALYSES.some(item => item.origin === 'sin_evidencia'));
});
