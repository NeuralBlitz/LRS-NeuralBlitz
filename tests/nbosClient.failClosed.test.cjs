'use strict';

// Regression tests for the TypeScript NBOS client without requiring a running VS Code host.
// TypeScript is a declared development dependency; axios and vscode are isolated here.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const ts = require('typescript');

const source = fs.readFileSync(path.join(__dirname, '../src/util/nbosClient.ts'), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
  reportDiagnostics: true,
});
assert.equal((compiled.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error).length, 0);

function createHarness({ post = async () => ({ data: { ok: true } }), get = async () => ({ data: {} }) } = {}) {
  const requests = [];
  const client = {
    post: async (endpoint, body) => { requests.push({ method: 'POST', endpoint, body }); return post(endpoint, body); },
    get: async (endpoint) => { requests.push({ method: 'GET', endpoint }); return get(endpoint); },
    interceptors: { request: { use: () => {} } },
  };
  const vscode = { workspace: { getConfiguration: () => ({ get: (_key, fallback) => fallback }) } };
  const exports = {};
  vm.runInNewContext(compiled.outputText, {
    exports,
    require: (name) => {
      if (name === 'vscode') return vscode;
      if (name === 'axios') return { __esModule: true, default: { create: () => client } };
      throw new Error('Unexpected import: ' + name);
    },
    console,
    encodeURIComponent,
  }, { filename: 'nbosClient.compiled.cjs' });
  return { client: new exports.NBOSClient(), requests };
}

test('successful boot connects only after backend confirmation', async () => {
  const { client, requests } = createHarness();
  assert.equal(client.isConnected(), false);
  await client.boot({ mode: 'Sentio' });
  assert.equal(client.isConnected(), true);
  assert.equal(requests[0].endpoint, '/boot');
});

test('rejected boot remains disconnected and surfaces the backend error', async () => {
  const { client } = createHarness({
    post: async () => ({ data: { ok: false, error: { message: 'boot denied' } } }),
  });
  await assert.rejects(client.boot({ mode: 'Sentio' }), /boot denied/);
  assert.equal(client.isConnected(), false);
});

test('network boot failure is never converted to mock success', async () => {
  const { client } = createHarness({
    post: async () => { throw new Error('offline'); },
  });
  await assert.rejects(client.boot({ mode: 'Dynamo' }), /offline/);
  assert.equal(client.isConnected(), false);
});

test('a failed second boot clears previously connected state', async () => {
  let attempts = 0;
  const { client } = createHarness({
    post: async () => (++attempts === 1 ? { data: { ok: true } } : Promise.reject(new Error('offline'))),
  });
  await client.boot({ mode: 'Hybrid' });
  assert.equal(client.isConnected(), true);
  await assert.rejects(client.boot({ mode: 'Hybrid' }), /offline/);
  assert.equal(client.isConnected(), false);
});

test('unavailable execute, status, introspect and debug endpoints propagate failure', async () => {
  const offline = async () => { throw new Error('backend unavailable'); };
  const { client } = createHarness({ post: offline, get: offline });
  const operations = [
    () => client.executeFile('main.nbcl'),
    () => client.executeCommand('/status'),
    () => client.getStackTrace(),
    () => client.getVariables('local'),
    () => client.continue(),
    () => client.stepOver(),
    () => client.stepInto(),
    () => client.stepOut(),
    () => client.pause(),
    () => client.evaluate('a'),
    () => client.getStatus(),
    () => client.introspect('local'),
  ];
  for (const operation of operations) {
    await assert.rejects(operation(), /backend unavailable/);
  }
});

test('execution must not report completed for a rejected backend response', async () => {
  const { client } = createHarness({
    post: async () => ({ data: { ok: false, error: { message: 'not authorized' } } }),
  });
  const result = await client.executeFile('main.nbcl');
  assert.equal(result.completed, false);
  assert.equal(result.error, 'not authorized');
});

test('debug scope is URL-encoded and disconnect resets local state', async () => {
  const { client, requests } = createHarness();
  await client.getVariables('local/scope space');
  assert.equal(requests[0].endpoint, '/debug/variables/local%2Fscope%20space');
  await client.boot({ mode: 'Sentio' });
  client.disconnect();
  assert.equal(client.isConnected(), false);
});
