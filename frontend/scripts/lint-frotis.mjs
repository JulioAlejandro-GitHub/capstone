// Optional audit tooling: keep ESLint outside the application's dependency graph.
// FROTIS_LINT_PREFIX=/tmp/frotis-design-tools npm run lint:frotis
import { createRequire } from 'node:module';
import path from 'node:path';
const require = createRequire(process.env.FROTIS_LINT_PREFIX
  ? path.resolve(process.env.FROTIS_LINT_PREFIX, 'package.json') : import.meta.url);
const { ESLint } = require('eslint');
const js = require('@eslint/js');
const tseslint = require('typescript-eslint');

const eslint = new ESLint({
  cwd: path.resolve(import.meta.dirname, '..'),
  overrideConfigFile: true,
  overrideConfig: [{
    files: ['src/features/analisis-frotis-v2/**/*.{ts,tsx}'],
    languageOptions: { parser: tseslint.parser, parserOptions: { ecmaFeatures: { jsx: true } } },
    rules: {
      ...js.configs.recommended.rules,
      // TypeScript checks undefined references; unused legacy imports are outside this visual refactor.
      'no-undef': 'off',
      'no-unused-vars': 'off',
    },
  }],
});
const results = await eslint.lintFiles(['src/features/analisis-frotis-v2/**/*.{ts,tsx}']);
console.log(await (await eslint.loadFormatter('stylish')).format(results));
const errors = results.reduce((total, result) => total + result.errorCount, 0);
console.log(`ESLint: ${results.length} files, ${errors} errors.`);
if (errors) process.exitCode = 1;
