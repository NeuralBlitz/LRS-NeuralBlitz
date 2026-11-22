'use strict';

// End-to-end NEGATIVE protocol test across real Node axios + real Uvicorn TCP.
// Passing does not mean that a compatible NBOS execution backend exists.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const { spawn } = require('node:child_process');
const test = require('node:test');
const vm = require('node:vm');
const ts = require('typescript');
const axios = require('axios');

const ROOT = path.resolve(__dirname, '..');
const SOURCE = fs.readFileSync(path.join(ROOT, 'src/util/nbosClient.ts'), 'utf8');
const COMPILED = ts.transpileModule(SOURCE, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  },
  reportDiagnostics: true,
});
assert.equal(
  (COMPILED.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error).length,
  0, 'NBOS TypeScript transpilation must not fail',
);

async function unusedLoopbackPort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(error => error ? reject(error) : resolve(port));
    });
  });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function awaitReady(baseURL, processHandle) {
  for (let attempt = 0; attempt < 120; attempt++) {
    if (processHandle.exitCode !== null) {
      throw new Error('Uvicorn exited before its HTTP endpoint became ready');
    }
    try {
      const response = await axios.get(baseURL + '/', {
        timeout: 700, proxy: false, maxRedirects: 0,
        validateStatus: () => true,
      });
      if (response.status === 200 &&
          String(response.data).includes('Pre-production research prototype')) {
        return;
      }
    } catch {
      // Process not yet listening.
    }
    await sleep(100);
  }
  throw new Error('Uvicorn did not become ready within the smoke timeout');
}

function makeActualClient(endpoint, token) {
  const vscode = {
    workspace: {
      getConfiguration: () => ({
        inspect: key => key === 'nbosEndpoint'
          ? { globalValue: endpoint, workspaceValue: undefined, workspaceFolderValue: undefined }
          : undefined,
        get: (key, fallback) => key === 'nbosEndpoint' ? endpoint : fallback,
      }),
    },
  };
  const exports = {};
  vm.runInNewContext(COMPILED.outputText, {
    exports,
    require: name => {
      if (name === 'vscode') return vscode;
      if (name === 'axios') return axios; // Real Axios. No transport mocks.
      throw new Error('Unexpected NBOS client dependency: ' + name);
    },
    URL,
    encodeURIComponent,
    console: { log: () => {} },
  }, { filename: 'nbosClient.actual-axios.cjs' });
  const secrets = {
    get: async key => key === 'nbos.authToken' ? token : undefined,
  };
  return new exports.NBOSClient(secrets);
}

test('real NBOS Axios client rejects authenticated but incompatible FastAPI gateway', {
  timeout: 35_000,
}, async t => {
  const port = await unusedLoopbackPort();
  const baseURL = 'http://127.0.0.1:' + port;
  const token = 'test-only-long-random-gateway-token-do-not-use-for-deployment-' + String(port);
  const python = process.env.PYTHON || 'python';
  const env = {
    ...process.env,
    LRS_GATEWAY_API_TOKEN: token,
  };
  delete env.LRS_ENABLE_EXPERIMENTAL_ROUTES;
  // Suppress access logging to avoid accidentally logging auth material.
  const child = spawn(python, [
    '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1',
    '--port', String(port), '--no-access-log',
  ], {
    cwd: ROOT,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  let output = '';
  const collect = data => { output += String(data).slice(0, 4000); };
  child.stdout.on('data', collect);
  child.stderr.on('data', collect);

  try {
    await awaitReady(baseURL, child);

    await t.test('Python gateway authenticates its own API without claiming integration', async () => {
      const denied = await axios.get(baseURL + '/api/integration/status', {
        timeout: 3000, proxy: false, maxRedirects: 0,
        validateStatus: () => true,
      });
      assert.equal(denied.status, 401);
      const allowed = await axios.get(baseURL + '/api/integration/status', {
        timeout: 3000, proxy: false, maxRedirects: 0,
        headers: { Authorization: 'Bearer ' + token },
      });
      assert.equal(allowed.status, 200);
      assert.equal(allowed.data.integration_verified, false);
      assert.equal(allowed.data.integration_active, false);
    });

    await t.test('gateway exposes only authenticated negative nbos/1 discovery', async () => {
      const denied = await axios.get(baseURL + '/nbos/v1/capabilities', {
        timeout: 3000, proxy: false, maxRedirects: 0,
        validateStatus: () => true,
      });
      assert.equal(denied.status, 401);
      const allowed = await axios.get(baseURL + '/nbos/v1/capabilities', {
        timeout: 3000, proxy: false, maxRedirects: 0,
        headers: { Authorization: 'Bearer ' + token },
      });
      assert.equal(allowed.status, 200);
      assert.equal(allowed.data.protocol, 'nbos/1');
      assert.equal(allowed.data.compatible, false);
      assert.deepEqual(allowed.data.operations, []);
    });

    await t.test('real NBOS boot is blocked by negative compatibility before /boot', async () => {
      const client = makeActualClient(baseURL, token);
      const paths = [];
      client.client.interceptors.request.use(config => {
        paths.push(config.url);
        return config;
      });
      await assert.rejects(
        client.boot({ mode: 'Sentio' }),
        error => /not compatible with nbos\/1/.test(error.message),
      );
      assert.deepEqual(paths, ['/nbos/v1/capabilities']);
      assert.equal(client.isConnected(), false);
    });

    await t.test('real Axios client refuses source, introspection and debugger requests before dispatch', async () => {
      const client = makeActualClient(baseURL, token);
      const paths = [];
      client.client.interceptors.request.use(config => {
        paths.push(config.url);
        return config;
      });
      const operations = [
        () => client.executeCommand('/status'),
        () => client.executeFile('test.nbcl'),
        () => client.getStatus(),
        () => client.introspect('system'),
        () => client.getStackTrace(),
      ];
      for (const operation of operations) {
        await assert.rejects(operation(), error => /not compatible with nbos\/1/.test(error.message));
      }
      assert.deepEqual(paths, operations.map(() => '/nbos/v1/capabilities'));
      assert.equal(client.isConnected(), false);
    });

    await t.test('without stored token, NBOS requests fail at gateway authentication', async () => {
      const client = makeActualClient(baseURL, undefined);
      await assert.rejects(
        client.boot({ mode: 'Sentio' }),
        error => error?.response?.status === 401,
      );
      assert.equal(client.isConnected(), false);
    });

    assert.ok(!output.includes(token), 'The child process must not print test Bearer secrets');
  } finally {
    if (child.exitCode === null && child.signalCode === null) {
      child.kill('SIGTERM');
    }
    await Promise.race([
      new Promise(resolve => child.once('close', resolve)),
      sleep(3000).then(() => { if (child.exitCode === null) child.kill('SIGKILL'); }),
    ]);
  }
});
