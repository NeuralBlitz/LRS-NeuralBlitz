'use strict';

// Exercise the actual transpiled Debug Adapter Protocol launch function.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const ts = require('typescript');

const source = fs.readFileSync(path.join(__dirname, '../src/debugger/debugSession.ts'), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  },
  reportDiagnostics: true,
});
assert.equal((compiled.diagnostics || []).filter(x => x.category === ts.DiagnosticCategory.Error).length, 0);

function harness({ bootError, executeError, execution = { completed: true } } = {}) {
  const clients = [];
  class FakeClient {
    constructor() {
      this.disconnected = false;
      this.calls = [];
      clients.push(this);
    }
    async boot(options) {
      this.calls.push({ operation: 'boot', options });
      if (bootError) throw new Error(bootError);
    }
    async executeFile(program, options) {
      this.calls.push({ operation: 'execute', program, options });
      if (executeError) throw new Error(executeError);
      return execution;
    }
    disconnect() {
      this.disconnected = true;
    }
  }

  class FakeDebugSession {
    constructor() {
      this.responses = [];
      this.errors = [];
      this.events = [];
    }
    setDebuggerLinesStartAt1() {}
    setDebuggerColumnsStartAt1() {}
    sendResponse(response) { this.responses.push(response); }
    sendErrorResponse(response, code, message) { this.errors.push({ response, code, message }); }
    sendEvent(event) { this.events.push(event); }
  }
  class FakeHandles {
    create() { return 1; }
    get() { return 'local'; }
  }
  class FakeTerminatedEvent {
    constructor() { this.event = 'terminated'; }
  }
  class FakeStoppedEvent {
    constructor(reason, threadId) {
      this.event = 'stopped';
      this.reason = reason;
      this.threadId = threadId;
    }
  }

  const exports = {};
  vm.runInNewContext(compiled.outputText, {
    exports,
    require: (name) => {
      if (name === 'vscode') return {};
      if (name === 'vscode-debugadapter') {
        return {
          DebugSession: FakeDebugSession,
          Handles: FakeHandles,
          TerminatedEvent: FakeTerminatedEvent,
          StoppedEvent: FakeStoppedEvent,
        };
      }
      if (name === '../util/nbosClient') return { NBOSClient: FakeClient };
      if (name === 'vscode-debugprotocol') return {};
      throw new Error('Unexpected import: ' + name);
    },
  }, { filename: 'debugSession.compiled.cjs' });

  const session = new exports.NeuralBlitzDebugSession();
  return { session, client: clients[0] };
}

async function launch(session) {
  await session.launchRequest({ command: 'launch' }, {
    program: 'test.nbcl',
    mode: 'Sentio',
    trace: false,
  });
}

test('backend-confirmed completed execution acknowledges launch and terminates', async () => {
  const { session, client } = harness();
  await launch(session);
  assert.equal(session.responses.length, 1);
  assert.equal(session.errors.length, 0);
  assert.equal(session.events.length, 1);
  assert.equal(session.events[0].event, 'terminated');
  assert.equal(client.calls[1].operation, 'execute');
});

test('backend-confirmed breakpoint stop acknowledges launch and pauses', async () => {
  const { session } = harness({ execution: { completed: false, stopped: true, line: 12 } });
  await launch(session);
  assert.equal(session.responses.length, 1);
  assert.equal(session.errors.length, 0);
  assert.equal(session.events[0].event, 'stopped');
  assert.equal(session.events[0].reason, 'breakpoint');
});

test('rejected execution is not falsely acknowledged or terminated as success', async () => {
  const { session, client } = harness({ execution: { completed: false, error: 'denied' } });
  await launch(session);
  assert.equal(session.responses.length, 0);
  assert.equal(session.events.length, 0);
  assert.equal(session.errors.length, 1);
  assert.match(session.errors[0].message, /denied/);
  assert.equal(client.disconnected, true);
});

test('network execution failure rejects the launch and disconnects', async () => {
  const { session, client } = harness({ executeError: 'backend offline' });
  await launch(session);
  assert.equal(session.responses.length, 0);
  assert.equal(session.events.length, 0);
  assert.match(session.errors[0].message, /backend offline/);
  assert.equal(client.disconnected, true);
});

test('boot failure cannot fall through into execution', async () => {
  const { session, client } = harness({ bootError: 'unauthorized' });
  await launch(session);
  assert.equal(session.responses.length, 0);
  assert.equal(client.calls.length, 1);
  assert.equal(session.errors.length, 1);
  assert.equal(client.disconnected, true);
});

test('contradictory result is rejected rather than interpreted as a success', async () => {
  const { session } = harness({ execution: { completed: true, stopped: true } });
  await launch(session);
  assert.equal(session.responses.length, 0);
  assert.equal(session.errors.length, 1);
  assert.match(session.errors[0].message, /contradictory/);
});
