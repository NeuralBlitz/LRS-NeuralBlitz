// Initial enforced lint baseline for the TypeScript VS Code extension.
// Keep this small and deterministic; expand only with validated changes.
module.exports = {
  root: true,
  env: { node: true, es2021: true },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: 'module',
  },
  plugins: ['@typescript-eslint'],
  ignorePatterns: ['out/**', 'node_modules/**', '.vscode-test/**'],
  rules: {
    'constructor-super': 'error',
    'no-const-assign': 'error',
    'no-debugger': 'error',
    'no-duplicate-case': 'error',
    'no-eval': 'error',
    'no-implied-eval': 'error',
    'no-new-func': 'error',
    'no-prototype-builtins': 'error',
    'no-unsafe-finally': 'error',
    'no-unreachable': 'error',
    'no-var': 'error',
    'valid-typeof': 'error',
  },
};
