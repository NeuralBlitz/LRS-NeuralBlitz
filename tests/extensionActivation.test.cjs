'use strict';

// Activation contract smoke test against the real transpiled entry point and
// command registrar. No VS Code Extension Host or live backend is claimed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const ts = require('typescript');

const ROOT = path.resolve(__dirname, '..');
const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8'));

function evaluateSource(sourcePath, dependencies) {
  const source = fs.readFileSync(path.join(ROOT, sourcePath), 'utf8');
  const js = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
    reportDiagnostics: true,
  });
  assert.equal(
    (js.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error).length,
    0,
    sourcePath + ' failed TypeScript transpilation',
  );
  const moduleExports = {};
  vm.runInNewContext(js.outputText, {
    exports: moduleExports,
    require: (name) => {
      if (!(name in dependencies)) throw new Error('Unexpected import: ' + name);
      return dependencies[name];
    },
    console: { log: () => {} },
  }, { filename: sourcePath + '.transpiled.cjs' });
  return moduleExports;
}

function createHarness() {
  const registeredCommands = new Map();
  const registeredViews = [];
  const executedCommands = [];
  const warnings = [];
  const welcomeCalls = [];
  const disposables = [];
  const manifestViewIds = new Set(
    Object.values(manifest.contributes.views || {}).flat().map(v => v.id)
  );
  const disposable = (kind) => {
    const resource = { kind, dispose: () => { resource.disposed = true; } };
    disposables.push(resource);
    return resource;
  };
  const vscode = {
    StatusBarAlignment: { Left: 1 },
    ViewColumn: { One: 1 },
    debug: {
      activeDebugSession: undefined,
      registerDebugAdapterDescriptorFactory: () => disposable('debug factory'),
      startDebugging: async () => true,
    },
    commands: {
      registerCommand: (id, handler) => {
        if (registeredCommands.has(id)) throw new Error('Duplicate command: ' + id);
        registeredCommands.set(id, handler);
        return disposable('command ' + id);
      },
      executeCommand: async (command) => {
        executedCommands.push(command);
      },
    },
    languages: {
      registerCompletionItemProvider: () => disposable('completion provider'),
      registerHoverProvider: () => disposable('hover provider'),
      registerDocumentSymbolProvider: () => disposable('symbol provider'),
    },
    window: {
      createOutputChannel: () => {
        const channel = disposable('output channel');
        channel.appendLine = () => {};
        return channel;
      },
      createStatusBarItem: () => {
        const item = disposable('status bar item');
        item.show = () => {};
        return item;
      },
      registerTreeDataProvider: (id) => {
        if (!manifestViewIds.has(id)) throw new Error('Uncontributed tree view: ' + id);
        registeredViews.push(id);
        return disposable('tree view ' + id);
      },
      showInformationMessage: (...args) => {
        welcomeCalls.push(args);
        return Promise.resolve(undefined);
      },
      showWarningMessage: (message) => { warnings.push(message); },
      showErrorMessage: (message) => { warnings.push(message); },
      showInputBox: async () => undefined,
    },
    workspace: {
      createFileSystemWatcher: () => ({
        ...disposable('watcher'),
        onDidChange: () => disposable('watcher change listener'),
        onDidCreate: () => disposable('watcher create listener'),
      }),
    },
  };
  class Stub {}
  class StubDiagnosticProvider {
    activate() {}
    validateDocument() {}
  }
  const cmdModule = evaluateSource('src/commands/nbclCommands.ts', {
    vscode,
    fs,
    path,
    '../util/nbosClient': { NBOS_TOKEN_SECRET_KEY: 'nbos.authToken' },
    '../util/ckRegistry': {},
  });

  const classes = {
    './providers/nbclCompletionProvider': { NBCLCompletionProvider: Stub },
    './providers/ckCompletionProvider': { CKCompletionProvider: Stub },
    './providers/nbclHoverProvider': { NBCLHoverProvider: Stub },
    './providers/nbclDocumentSymbolProvider': { NBCLDocumentSymbolProvider: Stub },
    './providers/nbclDiagnosticProvider': { NBCLDiagnosticProvider: StubDiagnosticProvider },
    './commands/nbclCommands': cmdModule,
    './debugger/debugAdapterFactory': { NeuralBlitzDebugAdapterFactory: Stub },
    './views/goldenDAGTreeProvider': { GoldenDAGTreeProvider: Stub },
    './views/ckRegistryTreeProvider': { CKRegistryTreeProvider: Stub },
    './util/ckRegistry': { CKRegistry: Stub },
    './util/nbosClient': { NBOSClient: Stub },
  };
  const extension = evaluateSource('src/extension.ts', { vscode, ...classes });
  const secretValues = new Map();
  const context = {
    subscriptions: [],
    secrets: {
      get: async (key) => secretValues.get(key),
      store: async (key, value) => { secretValues.set(key, value); },
      delete: async (key) => { secretValues.delete(key); },
    },
  };
  return {
    vscode, extension, context, registeredCommands, registeredViews,
    executedCommands, warnings, welcomeCalls, disposables, cmdModule,
  };
}

test('all contributed commands register exactly once at extension activation', () => {
  const h = createHarness();
  h.extension.activate(h.context);
  const advertised = manifest.contributes.commands.map(command => command.command);
  assert.equal(new Set(advertised).size, advertised.length, 'duplicate commands in manifest');
  assert.deepEqual(
    [...h.registeredCommands.keys()].sort(),
    advertised.sort(),
    'contributed commands and runtime registrations drifted',
  );
  assert.equal(h.welcomeCalls.length, 1);
  assert.deepEqual([...h.welcomeCalls[0]].slice(1), ['Open Documentation']);
});

test('each tree view is contributed and registered exactly once', () => {
  const h = createHarness();
  h.extension.activate(h.context);
  const expected = Object.values(manifest.contributes.views).flat().map(v => v.id);
  assert.deepEqual(h.registeredViews.sort(), expected.sort());
  assert.equal(new Set(expected).size, expected.length);
  assert.ok(
    manifest.contributes.viewsContainers.activitybar.some(x => x.id === 'neuralblitz'),
    'missing view container',
  );
  for (const container of manifest.contributes.viewsContainers.activitybar) {
    assert.ok(fs.existsSync(path.join(ROOT, container.icon)), 'missing activity bar icon');
  }
});

test('advertised debug controls are scoped to NeuralBlitz sessions', async () => {
  const h = createHarness();
  h.extension.activate(h.context);
  await h.registeredCommands.get('neuralblitz.debug.step')();
  await h.registeredCommands.get('neuralblitz.debug.continue')();
  assert.equal(h.executedCommands.length, 0, 'must not affect another debugger');
  assert.equal(h.warnings.length, 2);
  h.vscode.debug.activeDebugSession = { type: 'neuralblitz' };
  await h.registeredCommands.get('neuralblitz.debug.step')();
  await h.registeredCommands.get('neuralblitz.debug.continue')();
  assert.deepEqual(h.executedCommands, [
    'workbench.action.debug.stepInto',
    'workbench.action.debug.continue',
  ]);
});

test('extension disposes its status bar and output channel with subscriptions', () => {
  const h = createHarness();
  h.extension.activate(h.context);
  for (const kind of ['output channel', 'status bar item']) {
    const created = h.disposables.find(x => x.kind === kind);
    assert.ok(created, 'missing ' + kind);
    assert.ok(h.context.subscriptions.includes(created), 'leaked ' + kind);
  }
});

test('inline debugger does not reference a nonexistent adapter program', () => {
  const debuggerContribution = manifest.contributes.debuggers.find(d => d.type === 'neuralblitz');
  assert.ok(debuggerContribution, 'neuralblitz debugger missing');
  assert.equal(debuggerContribution.program, undefined);
  assert.equal(debuggerContribution.runtime, undefined);
});

test('credential commands save and remove tokens only through the secret storage API', async () => {
  const h = createHarness();
  h.extension.activate(h.context);
  const secret = 'example-placeholder-secret-that-is-not-a-real-credential';
  h.vscode.window.showInputBox = async (options) => {
    assert.equal(options.password, true, 'token prompt must mask input');
    assert.equal(options.ignoreFocusOut, true);
    return secret;
  };
  await h.registeredCommands.get('neuralblitz.credentials.set')();
  assert.equal(await h.context.secrets.get('nbos.authToken'), secret);
  await h.registeredCommands.get('neuralblitz.credentials.clear')();
  assert.equal(await h.context.secrets.get('nbos.authToken'), undefined);
  assert.ok(!JSON.stringify(h.welcomeCalls).includes(secret), 'UI feedback must never echo a token');
});

test('cancelled token entry preserves old secret, while invalid input is rejected', async () => {
  const h = createHarness();
  h.extension.activate(h.context);
  await h.context.secrets.store('nbos.authToken', 'existing-placeholder-value');
  h.vscode.window.showInputBox = async () => undefined;
  await h.registeredCommands.get('neuralblitz.credentials.set')();
  assert.equal(await h.context.secrets.get('nbos.authToken'), 'existing-placeholder-value');
  h.vscode.window.showInputBox = async () => '   ';
  await h.registeredCommands.get('neuralblitz.credentials.set')();
  assert.equal(await h.context.secrets.get('nbos.authToken'), 'existing-placeholder-value');
  assert.ok(h.warnings.some(x => /non-empty/.test(x)));
});


test('interactive NBCL UI displays completion, pause, or refusal accurately', async () => {
  const h = createHarness();
  const userSource = 'private-nbcl-source-example';
  h.vscode.window.activeTextEditor = {
    selection: { isEmpty: true },
    document: { languageId: 'nbcl', getText: () => userSource },
  };
  const logs = [];
  const notices = [];
  h.vscode.window.createOutputChannel = () => ({
    appendLine: line => logs.push(line), dispose: () => {},
  });
  h.vscode.window.showInformationMessage = message => notices.push(['info', message]);
  h.vscode.window.showWarningMessage = message => notices.push(['warning', message]);
  h.vscode.window.showErrorMessage = message => notices.push(['error', message]);
  let backendResult = { ok: true };
  const backend = { executeCommand: async command => {
    assert.equal(command, userSource);
    return backendResult;
  } };
  const commands = new h.cmdModule.NBCLCommands(backend, {}, h.context.secrets);
  commands.register(h.context);
  const execute = h.registeredCommands.get('neuralblitz.execute');

  await execute();
  assert.equal(notices.at(-1)[0], 'error');
  assert.match(notices.at(-1)[1], /did not confirm command completion/);
  assert.ok(!logs.some(line => line.includes(userSource)), 'Raw user source must not be logged');

  backendResult = { ok: true, stopped: true, line: 11 };
  await execute();
  assert.equal(notices.at(-1)[0], 'warning');
  assert.match(notices.at(-1)[1], /stopped at line 11/);

  backendResult = { ok: false, error: { message: 'not authorized' } };
  await execute();
  assert.equal(notices.at(-1)[0], 'error');
  assert.match(notices.at(-1)[1], /not authorized/);

  backendResult = { ok: true, completed: true };
  await execute();
  assert.equal(notices.at(-1)[0], 'info');
  assert.match(notices.at(-1)[1], /execution completed/);
});
