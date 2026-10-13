import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import ts from 'typescript';
const source = readFileSync(new URL('../src/pages/CampaignConfiguration.tsx', import.meta.url), 'utf8');
const parsed = ts.createSourceFile('page.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const node = parsed.statements.find(s => ts.isFunctionDeclaration(s) && s.name.text === 'campaignErrorMessage');
const code = ts.transpileModule(node.getText(parsed).replace('export ', ''), {}).outputText;
class ApiError extends Error {
  constructor(status, kind, code, correlationId) { super('private SQL payload'); Object.assign(this, {status, kind, code, correlationId}); }
}
const format = runInNewContext(`${code}; campaignErrorMessage`, {ApiError});
test('network, timeout, scientific 422 and internal 500 remain distinct and safe', () => {
  const id = '11111111-1111-4111-8111-111111111111';
  const network = format(new ApiError(null, 'network'));
  const timeout = format(new ApiError(null, 'timeout'));
  const scientific = format(new ApiError(422, 'http', 'CAMPAIGN_DATASET_EVIDENCE_CONFLICT', id));
  const internal = format(new ApiError(500, 'http', 'CAMPAIGN_DATABASE_OPERATION_FAILED', id));
  assert.equal(new Set([network,timeout,scientific,internal]).size, 4);
  assert.match(scientific, /CAMPAIGN_DATASET_EVIDENCE_CONFLICT/);
  assert.match(internal, /Error interno/);
  assert.ok(scientific.includes(id) && internal.includes(id));
  for(const text of [network,timeout,scientific,internal,format(new ApiError(400,'http','SQL private'))]) assert.ok(!text.includes('private'));
});
