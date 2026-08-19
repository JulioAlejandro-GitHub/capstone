import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const row = readFileSync(
  new URL('../src/components/reports/RunSummaryRow.tsx', import.meta.url),
  'utf8',
);
const types = readFileSync(
  new URL('../src/types/api.ts', import.meta.url),
  'utf8',
);

test('TRAIN muestra el dataset-version-id persistido', () => {
  assert.match(types, /dataset_version_id\?: string \| null/);
  assert.match(row, /processKind === 'training'/);
  assert.match(row, /dataset-version-id: \{run\.dataset_version_id \|\| 'No registrado'\}/);
});
