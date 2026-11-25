'use strict';

// Positive read-only reference integration across REAL Axios and Uvicorn TCP.
// This is not evidence of NBCL, file execution, agents or debugger support.
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


test('read-only NBOS reference responds to actual Axios client without inventing an engine', {
  timeout: 35_000,
}, async t => {
  const port = await unusedLoopbackPort();
  const baseURL = 'http://127.0.0.1:' + port;
  const token = 'reference-test-only-strong-token-not-for-live-deployment-' + String(port);
  const python = process.env.PYTHON || 'python';
  const env = { ...process.env, LRS_GATEWAY_API_TOKEN: token };
  delete env.LRS_ENABLE_EXPERIMENTAL_ROUTES;
  const child = spawn(python, [
    '-m', 'uvicorn', 'gateway.nbos_reference:app', '--host', '127.0.0.1',
    '--port', String(port), '--no-access-log',
  ], {
    cwd: ROOT, env, stdio: ['ignore', 'pipe', 'pipe'],
  });

  let output = '';
  const collect = data => { output += String(data).slice(0, 4000); };
  child.stdout.on('data', collect);
  child.stderr.on('data', collect);
  try {
    await awaitReady(baseURL, child);

    await t.test('versioned discovery reports only three read-only operations', async () => {
      const response = await axios.get(baseURL + '/nbos/v1/capabilities', {
        headers: { Authorization: 'Bearer ' + token },
        timeout: 3000, proxy: false, maxRedirects: 0,
      });
      assert.equal(response.status, 200);
      assert.equal(response.data.protocol, 'nbos/1');
      assert.equal(response.data.compatible, true);
      assert.deepEqual(response.data.operations, [
        'GET /status', 'POST /introspect', 'POST /execute',
      ]);
      assert.equal(response.data.execution_engine_available, false);
      assert.equal(response.data.agent_boot_available, false);
      assert.equal(response.data.subset_interpreter_available, true);
      assert.equal(response.data.local_state_scope, 'single_inline_program');
      assert.equal(response.data.max_local_registers, 8);
      assert.deepEqual(response.data.execution_modes, ['command', 'source']);
    });

    await t.test('actual client reads status and introspection after preflight', async () => {
      const client = makeActualClient(baseURL, token);
      const paths = [];
      client.client.interceptors.request.use(config => {
        paths.push(config.url);
        return config;
      });

      const status = await client.getStatus();
      assert.equal(status.system_status, 'read_only_reference');
      assert.equal(status.agent_booted, false);
      assert.equal(status.integration_verified, false);
      const system = await client.introspect('system');
      assert.equal(system.ok, true);
      assert.equal(system.status.system_status, 'read_only_reference');
      assert.deepEqual(paths, [
        '/nbos/v1/capabilities', '/status',
        '/nbos/v1/capabilities', '/introspect',
      ]);
    });

    await t.test('actual client completes status, help and bounded integer calculation', async () => {
      const client = makeActualClient(baseURL, token);
      const status = await client.executeCommand('/status');
      const help = await client.executeCommand('/help');
      const calc = await client.executeCommand('/calc --a=12 --op=mul --b=-3');
      assert.equal(status.ok, true);
      assert.equal(status.completed, true);
      assert.equal(status.result.system_status, 'read_only_reference');
      assert.equal(help.ok, true);
      assert.equal(help.completed, true);
      assert.deepEqual(help.result.supported_commands, [
        '/status', '/help', '/calc', '/local.set', '/local.get', '/local.add',
      ]);
      assert.equal(calc.ok, true);
      assert.equal(calc.completed, true);
      assert.equal(calc.result.value, -36);
    });

    await t.test('actual client executes bounded source with real step-level evidence', async () => {
      const client = makeActualClient(baseURL, token);
      const paths = [];
      client.client.interceptors.request.use(config => {
        paths.push(config.url);
        return config;
      });
      const program = '# safe arithmetic\n/status\n/calc --a=19 --op=sub --b=6\n/help\n';
      const result = await client.executeSource(program);
      assert.equal(result.ok, true);
      assert.equal(result.completed, true);
      assert.equal(result.instruction_count, 3);
      assert.deepEqual(result.steps.map(step => step.line), [2, 3, 4]);
      assert.equal(result.steps[1].result.value, 13);
      assert.deepEqual(paths, ['/nbos/v1/capabilities', '/execute']);
      await assert.rejects(
        client.executeSource('/status\n/boot\n/help'),
        error => error?.response?.status === 422,
      );
      await assert.rejects(
        client.executeCommand('/calc --a=1 --op=pow --b=999999'),
        error => error?.response?.status === 422,
      );
      assert.equal(client.isConnected(), false);
    });

    await t.test('real Axios observes isolated local state and rejects cross-request reads', async () => {
      const first = makeActualClient(baseURL, token);
      const source = [
        '/local.set --name=counter --value=21',
        '/local.add --name=counter --value=4',
        '/local.get --name=counter',
      ].join('\n');
      const result = await first.executeSource(source);
      assert.equal(result.ok, true);
      assert.equal(result.completed, true);
      assert.equal(result.instruction_count, 3);
      assert.deepEqual(JSON.parse(JSON.stringify(result.final_locals)), { counter: 25 });
      assert.deepEqual(result.steps.map(step => step.result.value), [21, 25, 25]);
      const other = makeActualClient(baseURL, token);
      await assert.rejects(
        other.executeSource('/local.get --name=counter'),
        error => error?.response?.status === 422 &&
          error?.response?.data?.completed === false,
      );
      await assert.rejects(
        other.executeCommand('/local.get --name=counter'),
        error => error?.response?.status === 422,
      );
    });

    await t.test('state overflow or register-capacity failure rejects whole source', async () => {
      const client = makeActualClient(baseURL, token);
      const programs = [
        '/status\n/local.set --name=x --value=1000000\n/local.add --name=x --value=1',
        'abcdefghi'.split('').map(name =>
          '/local.set --name=' + name + ' --value=1'
        ).join('\n'),
      ];
      for (const source of programs) {
        await assert.rejects(
          client.executeSource(source),
          error => error?.response?.status === 422 &&
            !Object.prototype.hasOwnProperty.call(error.response.data, 'steps') &&
            !Object.prototype.hasOwnProperty.call(error.response.data, 'final_locals'),
        );
      }
    });

    await t.test('agent boot and debug are rejected at preflight', async () => {
      const client = makeActualClient(baseURL, token);
      const paths = [];
      client.client.interceptors.request.use(config => {
        paths.push(config.url);
        return config;
      });
      await assert.rejects(
        client.boot({ mode: 'Sentio' }),
        /does not advertise POST \/boot/,
      );
      await assert.rejects(client.getStackTrace(), /does not advertise GET \/debug\/stack/);
      assert.equal(client.isConnected(), false);
      assert.deepEqual(paths, ['/nbos/v1/capabilities', '/nbos/v1/capabilities']);
    });

    await t.test('unsupported commands fail and file paths never leave the client', async () => {
      const client = makeActualClient(baseURL, token);
      for (const command of ['/apply --modify-file=private', '/status; ls', '/status\n/boot']) {
        await assert.rejects(
          client.executeCommand(command),
          error => error?.response?.status === 422,
        );
      }
      const paths = [];
      client.client.interceptors.request.use(config => {
        paths.push(config.url);
        return config;
      });
      await assert.rejects(
        client.executeFile('/tmp/secret.nbcl'),
        /does not advertise file execution/,
      );
      assert.deepEqual(paths, ['/nbos/v1/capabilities']);
      const directBoot = await axios.post(baseURL + '/boot', { mode: 'Sentio' }, {
        headers: { Authorization: 'Bearer ' + token },
        timeout: 3000, proxy: false, maxRedirects: 0,
        validateStatus: () => true,
      });
      assert.equal(directBoot.status, 404);
      assert.equal(client.isConnected(), false);
    });

    await t.test('secret absent causes authenticated discovery to fail', async () => {
      const client = makeActualClient(baseURL, undefined);
      await assert.rejects(
        client.executeCommand('/status'),
        error => error?.response?.status === 401,
      );
      assert.equal(client.isConnected(), false);
    });

    assert.ok(!output.includes(token), 'Child process must not log bearer token');
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
