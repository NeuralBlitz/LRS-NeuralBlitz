'use strict';

// Tests the actual transpiled DAP session with a minimal VS Code host,
// without claiming that a real NBOS backend is available.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const ts = require('typescript');

const source = fs.readFileSync(path.join(__dirname, '../src/debugger/debugSession.ts'), 'utf8');
const transpiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  reportDiagnostics: true,
});
assert.equal((transpiled.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error).length, 0);

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
  convertClientLineToDebugger(line) { return line; }
  convertDebuggerLineToClient(line) { return line; }
  convertDebuggerColumnToClient(column) { return column; }
}
class FakeEvent {
  constructor(...args) {
    this.kind = this.constructor.name;
    this.args = args;
  }
}
class TerminatedEvent extends FakeEvent {}
class StoppedEvent extends FakeEvent {}
class OutputEvent extends FakeEvent {}
class InitializedEvent extends FakeEvent {}
class FakeHandles {
  create(value) { return value; }
  get(value) { return value; }
}
class FakeThread {}
class FakeFrame {}
class FakeScope {}
class FakeSource {}

const exports = {};
vm.runInNewContext(transpiled.outputText, {
  exports,
  require: (name) => {
    if (name === 'vscode') return {};
    if (name === 'vscode-debugadapter') return {
      DebugSession: FakeDebugSession,
      TerminatedEvent, StoppedEvent, OutputEvent, InitializedEvent,
      Handles: FakeHandles, Thread: FakeThread, StackFrame: FakeFrame,
      Scope: FakeScope, Source: FakeSource,
    };
    if (name === '../util/nbosClient') return { NBOSClient: class {} };
    throw new Error('Unexpected import: ' + name);
  },
}, { filename: 'debugSession.compiled.cjs' });

function harness(backend = {}) {
  const session = new exports.NeuralBlitzDebugSession();
  let disconnected = 0;
  session._nbosClient = {
    boot: async () => {},
    executeFile: async () => ({ completed: true }),
    disconnect: () => { disconnected++; },
    ...backend,
  };
  return { session, getDisconnectCount: () => disconnected };
}
const response = () => ({ body: {} });
const launchArgs = { program: 'main.nbcl', mode: 'Sentio', trace: false };
const eventCount = (session, kind) => session.events.filter(e => e.kind === kind).length;

test('failed boot sends exactly one error response and never starts execution', async () => {
  let executed = false;
  const { session } = harness({
    boot: async () => { throw new Error('offline'); },
    executeFile: async () => { executed = true; return { completed: true }; },
  });
  await session.launchRequest(response(), launchArgs);
  assert.equal(session.responses.length, 0);
  assert.equal(session.errors.length, 1);
  assert.match(session.errors[0].message, /offline/);
  assert.equal(executed, false);
});

test('confirmed completion terminates and disconnects once', async () => {
  const { session, getDisconnectCount } = harness();
  await session.launchRequest(response(), launchArgs);
  assert.equal(session.responses.length, 1);
  assert.equal(session.errors.length, 0);
  assert.equal(eventCount(session, 'TerminatedEvent'), 1);
  assert.equal(eventCount(session, 'StoppedEvent'), 0);
  assert.equal(getDisconnectCount(), 1);
});

test('confirmed breakpoint stops without declaring termination', async () => {
  const { session } = harness({ executeFile: async () => ({ completed: false, stopped: true, line: 7 }) });
  await session.launchRequest(response(), launchArgs);
  assert.equal(session.responses.length, 1);
  assert.equal(eventCount(session, 'StoppedEvent'), 1);
  assert.equal(eventCount(session, 'TerminatedEvent'), 0);
});

test('execution failure emits error and termination after one launch acknowledgement', async () => {
  const { session, getDisconnectCount } = harness({
    executeFile: async () => ({ completed: false, error: 'permission denied' }),
  });
  await session.launchRequest(response(), launchArgs);
  assert.equal(session.responses.length, 1);
  assert.equal(session.errors.length, 0);
  assert.equal(eventCount(session, 'OutputEvent'), 1);
  assert.match(session.events.find(e => e.kind === 'OutputEvent').args[0], /permission denied/);
  assert.equal(eventCount(session, 'TerminatedEvent'), 1);
  assert.equal(getDisconnectCount(), 1);
});

test('network execute failure never generates a second launch response', async () => {
  const { session } = harness({
    executeFile: async () => { throw new Error('connection refused'); },
  });
  await session.launchRequest(response(), launchArgs);
  assert.equal(session.responses.length, 1);
  assert.equal(session.errors.length, 0);
  assert.equal(eventCount(session, 'TerminatedEvent'), 1);
});

test('unknown execution state terminates instead of hanging', async () => {
  const { session } = harness({
    executeFile: async () => ({ completed: false, stopped: false }),
  });
  await session.launchRequest(response(), launchArgs);
  assert.equal(eventCount(session, 'TerminatedEvent'), 1);
  assert.equal(eventCount(session, 'OutputEvent'), 1);
});

test('breakpoints are not marked verified before backend acknowledgement', async () => {
  const { session } = harness();
  await session.setBreakPointsRequest(response(), {
    source: { path: 'main.nbcl' },
    breakpoints: [{ line: 12 }],
  });
  assert.equal(session.responses[0].body.breakpoints[0].verified, false);
  assert.match(session.responses[0].body.breakpoints[0].message, /Unverified/);
});
test('missing breakpoint path reports an error', async () => {
  const { session } = harness();
  await session.setBreakPointsRequest(response(), { source: {}, breakpoints: [{ line: 1 }] });
  assert.equal(session.responses.length, 0);
  assert.equal(session.errors.length, 1);
});

test('unsupported debug capabilities are not advertised', () => {
  const { session } = harness();
  session.initializeRequest(response(), {});
  const capabilities = session.responses[0].body;
  for (const field of [
    'supportsHitConditionalBreakpoints', 'supportsConditionalBreakpoints',
    'supportsBreakpointLocationsRequest', 'supportsRestartRequest',
    'supportsCancelRequest', 'supportsCompletionsRequest',
  ]) assert.equal(capabilities[field], false, field);
});

test('backend control failure is a DAP error, not a fake stopped event', async () => {
  const { session } = harness({
    stepInto: async () => { throw new Error('step rejected'); },
  });
  await session.stepInRequest(response(), {});
  assert.equal(session.responses.length, 0);
  assert.equal(session.errors.length, 1);
  assert.equal(eventCount(session, 'StoppedEvent'), 0);
});

test('accepted step does not fabricate immediate stopped state', async () => {
  const { session } = harness({ stepOver: async () => {} });
  await session.nextRequest(response(), {});
  assert.equal(session.responses.length, 1);
  assert.equal(eventCount(session, 'StoppedEvent'), 0);
});

test('failed evaluation and stack trace are surfaced as DAP errors', async () => {
  const { session } = harness({
    evaluate: async () => { throw new Error('evaluation offline'); },
    getStackTrace: async () => { throw new Error('stack offline'); },
  });
  await session.evaluateRequest(response(), { expression: 'x' });
  await session.stackTraceRequest(response(), {});
  assert.equal(session.responses.length, 0);
  assert.equal(session.errors.length, 2);
});

test('variables failure is not disguised as an error-named variable', async () => {
  const { session } = harness({
    getVariables: async () => { throw new Error('variables offline'); },
  });
  await session.variablesRequest(response(), { variablesReference: 'local' });
  assert.equal(session.responses.length, 0);
  assert.equal(session.errors.length, 1);
});
