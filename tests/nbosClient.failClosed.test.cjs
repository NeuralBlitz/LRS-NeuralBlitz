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

function createHarness({
  post = async () => ({ data: { ok: true } }),
  get = async () => ({ data: {} }),
  endpoint = 'http://127.0.0.1:8765',
  endpointScope = 'user',
} = {}) {
  const requests = [];
  const savedSecrets = new Map();
  const secrets = {
    get: async (key) => savedSecrets.get(key),
    store: async (key, value) => { savedSecrets.set(key, value); },
    delete: async (key) => { savedSecrets.delete(key); },
  };
  let requestInterceptor;
  const client = {
    post: async (endpoint, body, config) => {
      requests.push({ method: 'POST', endpoint, body, config });
      return post(endpoint, body);
    },
    get: async (endpoint, config) => {
      requests.push({ method: 'GET', endpoint, config });
      return get(endpoint);
    },
    interceptors: { request: { use: (handler) => { requestInterceptor = handler; } } },
  };
  const vscode = {
    workspace: {
      getConfiguration: () => ({
        get: (key, fallback) => {
          if (key === 'authToken') throw new Error('Legacy plaintext authToken setting must not be read');
          return key === 'nbosEndpoint' ? endpoint : fallback;
        },
        inspect: (key) => key === 'nbosEndpoint'
          ? {
              globalValue: endpointScope === 'user' ? endpoint : undefined,
              workspaceValue: endpointScope === 'workspace' ? endpoint : undefined,
              workspaceFolderValue: endpointScope === 'folder' ? endpoint : undefined,
            }
          : undefined,
      }),
    },
  };
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
    URL,
  }, { filename: 'nbosClient.compiled.cjs' });
  return {
    client: new exports.NBOSClient(secrets),
    requests, secrets,
    tokenKey: exports.NBOS_TOKEN_SECRET_KEY,
    interceptRequest: async (config) => requestInterceptor(config),
  };
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
  const { client, requests } = createHarness({
    get: async () => ({ data: { variables: {} } }),
  });
  await client.getVariables('local/scope space');
  assert.equal(requests[0].endpoint, '/debug/variables/local%2Fscope%20space');
  await client.boot({ mode: 'Sentio' });
  client.disconnect();
  assert.equal(client.isConnected(), false);
});


test('executeFile requires explicit backend completion evidence', async () => {
  const { client } = createHarness({
    post: async () => ({ data: { ok: true, completed: true } }),
  });
  const result = await client.executeFile('main.nbcl');
  assert.equal(result.completed, true);
  assert.equal(result.stopped, false);
});

test('backend acknowledgement alone cannot masquerade as execution completion', async () => {
  const { client } = createHarness({
    post: async () => ({ data: { ok: true } }),
  });
  await assert.rejects(client.executeFile('main.nbcl'), /did not confirm execution completion/);
});

test('contradictory completion and stopped flags are rejected', async () => {
  const { client } = createHarness({
    post: async () => ({ data: { ok: true, stopped: true, completed: true, line: 8 } }),
  });
  await assert.rejects(client.executeFile('main.nbcl'), /Contradictory NBOS execution response/);
});

test('a real stopped response never simultaneously reports completion', async () => {
  const { client } = createHarness({
    post: async () => ({ data: { ok: true, stopped: true, line: 8 } }),
  });
  const result = await client.executeFile('main.nbcl');
  assert.equal(result.completed, false);
  assert.equal(result.stopped, true);
  assert.equal(result.line, 8);
});

test('malformed backend execution responses fail closed', async () => {
  const { client } = createHarness({
    post: async () => ({ data: { ok: 'true', completed: true } }),
  });
  await assert.rejects(client.executeFile('main.nbcl'), /missing boolean ok/);
});

test('backend rejection cannot claim completion even with a conflicting completed flag', async () => {
  const { client } = createHarness({
    post: async () => ({ data: { ok: false, completed: true, error: { message: 'denied' } } }),
  });
  const result = await client.executeFile('main.nbcl');
  assert.equal(result.completed, false);
  assert.equal(result.error, 'denied');
});

test('boot does not accept a truthy nonboolean ok response', async () => {
  const { client } = createHarness({ post: async () => ({ data: { ok: 'yes' } }) });
  await assert.rejects(client.boot({ mode: 'Sentio' }), /rejected the boot request/);
  assert.equal(client.isConnected(), false);
});

test('command execution requires boolean ok without losing backend rejection details', async () => {
  const invalid = createHarness({ post: async () => ({ data: { result: 'done' } }) });
  await assert.rejects(invalid.client.executeCommand('/status'), /missing boolean ok/);

  const refused = createHarness({
    post: async () => ({ data: { ok: false, error: { message: 'not authorized' } } }),
  });
  const result = await refused.client.executeCommand('/status');
  assert.equal(result.ok, false);
  assert.equal(result.error.message, 'not authorized');
});

test('debug control actions require explicit positive backend acknowledgement', async () => {
  const negative = createHarness({
    post: async () => ({ data: { ok: false, error: { message: 'step refused' } } }),
  });
  await assert.rejects(negative.client.stepInto(), /did not positively acknowledge/);

  const ambiguous = createHarness({ post: async () => ({ data: {} }) });
  await assert.rejects(ambiguous.client.continue(), /did not positively acknowledge/);

  const successful = createHarness({ post: async () => ({ data: { ok: true } }) });
  await successful.client.pause();
});

test('missing stack frames or variables cannot be confused with empty debug state', async () => {
  const malformed = createHarness({ get: async () => ({ data: {} }) });
  await assert.rejects(malformed.client.getStackTrace(), /expected frames array/);
  await assert.rejects(malformed.client.getVariables('local'), /expected variables object/);

  const valid = createHarness({
    get: async (endpoint) => endpoint === '/debug/stack'
      ? { data: { frames: [] } }
      : { data: { variables: {} } },
  });
  assert.equal((await valid.client.getStackTrace()).length, 0);
  assert.equal(Object.keys(await valid.client.getVariables('local')).length, 0);
});

test('evaluate requires a result property, including a legitimate null result', async () => {
  const missing = createHarness({ post: async () => ({ data: { ok: true } }) });
  await assert.rejects(missing.client.evaluate('expression'), /missing result/);

  const valid = createHarness({ post: async () => ({ data: { result: null } }) });
  assert.equal(await valid.client.evaluate('expression'), null);
});

test('status and introspection reject unavailable or negative response envelopes', async () => {
  const empty = createHarness({ get: async () => ({ data: null }) });
  await assert.rejects(empty.client.getStatus(), /expected an object/);

  const rejected = createHarness({
    post: async () => ({ data: { ok: false, error: { message: 'forbidden' } } }),
  });
  await assert.rejects(rejected.client.introspect('system'), /forbidden/);
});

test('the NBOS client refuses all requests until a compatible endpoint is explicitly chosen', async () => {
  const { client, requests } = createHarness({ endpoint: '' });
  await assert.rejects(client.boot({ mode: 'Sentio' }), /NBOS endpoint is not configured/);
  await assert.rejects(client.executeCommand('/status'), /NBOS endpoint is not configured/);
  await assert.rejects(client.getStatus(), /NBOS endpoint is not configured/);
  await assert.rejects(client.getStackTrace(), /NBOS endpoint is not configured/);
  assert.equal(requests.length, 0);
  assert.equal(client.isConnected(), false);
});

test('malformed, remote HTTP and embedded-credential URLs cannot receive NBCL data', async () => {
  for (const endpoint of [
    'not a url', 'ftp://127.0.0.1:9001', 'http://example.org:9001',
    'http://user:pass@localhost:9999', 'http://localhost:8000/api',
    'http://localhost:8000/?token=test', 'http://localhost:8000/#frag',
    'http://0.0.0.0:9001',
  ]) {
    const { client, requests } = createHarness({ endpoint });
    await assert.rejects(client.executeCommand('/execute sensitive source'), /Invalid NBOS endpoint|Invalid neuralblitz.nbosEndpoint/);
    assert.equal(requests.length, 0, 'No traffic must be sent to invalid endpoint: ' + endpoint);
  }
});

test('only explicit loopback HTTP or clean HTTPS endpoints are allowed', async () => {
  for (const endpoint of ['http://127.0.0.1:8765', 'http://localhost:8765', 'http://[::1]:8765', 'https://nbos.example.org']) {
    const { client, requests } = createHarness({ endpoint });
    await client.executeCommand('/status');
    assert.equal(requests.length, 1);
    assert.equal(requests[0].endpoint, '/execute');
    assert.equal(requests[0].config.baseURL, new URL(endpoint).origin);
  }
});

test('the published VS Code settings do not assume port 8080 is an NBOS service', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, '../package.json'), 'utf8'));
  const property = manifest.contributes.configuration.properties['neuralblitz.nbosEndpoint'];
  assert.equal(property.default, '');
  assert.match(property.description, /compatible NBOS backend/);
});

test('NBOS Authorization comes only from SecretStorage and never from plaintext settings', async () => {
  const { secrets, tokenKey, interceptRequest } = createHarness();
  assert.equal(tokenKey, 'nbos.authToken');
  let headers = (await interceptRequest({ headers: {} })).headers;
  assert.equal(headers.Authorization, undefined);
  await secrets.store(tokenKey, 'test-only-secret-irreversible-placeholder');
  headers = (await interceptRequest({ headers: {} })).headers;
  assert.equal(headers.Authorization, 'Bearer test-only-secret-irreversible-placeholder');
  await secrets.delete(tokenKey);
  headers = (await interceptRequest({ headers: {} })).headers;
  assert.equal(headers.Authorization, undefined);
});

test('workspace and folder endpoints cannot redirect authentication secrets', async () => {
  for (const endpointScope of ['workspace', 'folder']) {
    const { client, requests, secrets, tokenKey } = createHarness({
      endpoint: 'https://untrusted.example.org', endpointScope,
    });
    await secrets.store(tokenKey, 'test-only-stored-token');
    await assert.rejects(client.executeCommand('secret example'), /User settings, not workspace settings/);
    assert.equal(requests.length, 0);
  }
});
