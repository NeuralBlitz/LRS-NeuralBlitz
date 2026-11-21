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
    '../util/nbosClient': {},
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
  const context = { subscriptions: [] };
  return {
    vscode, extension, context, registeredCommands, registeredViews,
    executedCommands, warnings, welcomeCalls, disposables,
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
