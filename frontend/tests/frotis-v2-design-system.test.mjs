import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import postcss from 'postcss';

const root = new URL('../src/features/analisis-frotis-v2/styles/', import.meta.url);
const read = file => readFileSync(new URL(file, root), 'utf8');
const styles = ['tokens_frotis_v2.css', 'module.css', 'layout.css', 'viewer.css'];

test('all shipped module selectors, registered properties and animations stay isolated', () => {
  for (const file of styles) {
    const css = postcss.parse(read(file));
    css.walkRules(rule => {
      if (rule.parent.type === 'atrule' && /keyframes$/.test(rule.parent.name)) return;
      for (const selector of rule.selectors) {
        assert.match(selector, /^\.frotis-v2(?:\s|$)/, `${file}: ${selector}`);
      }
    });
    css.walkAtRules(rule => {
      if (rule.name === 'property') assert.match(rule.params, /^--frotis-v2-/);
      if (/keyframes$/.test(rule.name)) assert.match(rule.params, /^frotis-v2-/);
    });
    css.walkDecls(decl => {
      if (!decl.important) return;
      // Tailwind Preflight preserves native [hidden] semantics over display utilities.
      // This existing, scoped exception is documented in DESIGN-SYSTEM.md.
      assert.equal(file, 'module.css');
      assert.equal(decl.parent.selector, '.frotis-v2 [hidden]:where(:not([hidden="until-found"]))');
      assert.equal(decl.prop, 'display');
      assert.equal(decl.value, 'none');
    });
  }
});

test('semantic token references exist and have no circular dependencies', () => {
  const values = new Map();
  postcss.parse(read('tokens_frotis_v2.css')).walkDecls(decl => {
    assert.match(decl.prop, /^--frotis-v2-/);
    assert.ok(!values.has(decl.prop), `duplicate ${decl.prop}`);
    values.set(decl.prop, decl.value);
  });
  const references = source => [...source.matchAll(/var\((--frotis-v2-(?!tw-)[\w-]+)/g)].map(match => match[1]);
  for (const file of [...styles, 'tailwind.css']) {
    for (const token of references(read(file))) assert.ok(values.has(token), `${file}: missing ${token}`);
  }
  function visit(token, ancestors = new Set()) {
    assert.ok(!ancestors.has(token), `cycle in ${token}`);
    for (const reference of references(values.get(token))) visit(reference, new Set([...ancestors, token]));
  }
  for (const token of values.keys()) visit(token);
});

test('Tailwind scans only the live module and never automatically scans the host or reference HTML', () => {
  const input = postcss.parse(read('tailwind.css'));
  input.walkAtRules('import', rule => assert.match(rule.params, /source\(none\)/));
  const sources = [];
  input.walkAtRules('source', rule => sources.push(rule.params));
  assert.deepEqual(sources.sort(), ['"../AnalisisFrotis2Page.tsx"', '"../components"', '"../pages"']);
  assert.doesNotMatch(read('module.css'), /:root|:host|--af2-tw-/);
});
