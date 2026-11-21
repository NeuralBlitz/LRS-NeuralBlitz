'use strict';

// Unit tests transpile the actual TypeScript panel code and mock VS Code.
// Backend/registry content must be treated as untrusted HTML text.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const ts = require('typescript');

const file = path.join(__dirname, '../src/commands/nbclCommands.ts');
const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  },
  reportDiagnostics: true,
});
assert.equal((compiled.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error).length, 0);

function harness() {
  const panels = [];
  const vscode = {
    StatusBarAlignment: { Left: 1 },
    ViewColumn: { One: 1 },
    window: {
      createOutputChannel: () => ({ appendLine: () => {} }),
      createStatusBarItem: () => ({ show: () => {} }),
      createWebviewPanel: (type, title, column, options) => {
        const panel = { type, title, options, webview: { html: '' } };
        panels.push(panel);
        return panel;
      },
      showQuickPick: async () => 'system',
      showErrorMessage: (message) => { throw new Error(message); },
    },
  };
  const exports = {};
  vm.runInNewContext(compiled.outputText, {
    exports,
    require: (name) => {
      if (name === 'vscode') return vscode;
      if (name === 'fs' || name === 'path') return {};
      if (name === '../util/nbosClient' || name === '../util/ckRegistry') return {};
      throw new Error('Unexpected import: ' + name);
    },
  }, { filename: 'nbclCommands.compiled.cjs' });
  return {
    commands: new exports.NBCLCommands({}, {}),
    panels,
  };
}

test('status panel escapes backend content and disables scripting', async () => {
  const { commands, panels } = harness();
  commands.nbosClient = {
    getStatus: async () => ({
      system_status: '<img src=x onerror=alert(1)>',
      governance_core: {
        charter_status: '<script>alert(2)</script>',
        veritas_vpce: { score: 0 },
      },
    }),
  };
  await commands.showStatus();
  assert.equal(panels.length, 1);
  assert.equal(panels[0].options.enableScripts, false);
  assert.match(panels[0].webview.html, /Content-Security-Policy/);
  assert.match(panels[0].webview.html, /&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.match(panels[0].webview.html, /&lt;script&gt;alert\(2\)&lt;\/script&gt;/);
  assert.doesNotMatch(panels[0].webview.html, /<img src=x/);
  assert.match(panels[0].webview.html, /<span>0<\/span>/);
});

test('unknown VPCE score displays unavailable rather than invented zero', () => {
  const { commands } = harness();
  const html = commands.getStatusHtml({ governance_core: {} });
  assert.match(html, /<span>Unavailable<\/span>/);
});

test('introspection response is escaped rather than interpreted as markup', async () => {
  const { commands, panels } = harness();
  commands.nbosClient = {
    introspect: async () => ({ payload: '</pre><script>alert(1)</script>' }),
  };
  await commands.introspect();
  assert.equal(panels[0].options.enableScripts, false);
  assert.match(panels[0].webview.html, /&lt;\/pre&gt;&lt;script&gt;/);
  assert.doesNotMatch(panels[0].webview.html, /<script>alert/);
});

test('capability kernel panel escapes every interpolated field', () => {
  const { commands, panels } = harness();
  commands.showCKDetails({
    family: '<img src=x>',
    name: '</h1><script>bad()</script>',
    version: '1<&',
    intent: '<iframe>',
    inputs: { '<key>': '<value>' },
    outputs: { '</td>': '<strong>' },
    riskFactors: ['<img>'],
    veritasInvariants: ['<script>'],
  });
  assert.equal(panels[0].options.enableScripts, false);
  assert.match(panels[0].webview.html, /&lt;iframe&gt;/);
  assert.match(panels[0].webview.html, /&lt;key&gt;/);
  assert.match(panels[0].webview.html, /&lt;strong&gt;/);
  assert.doesNotMatch(panels[0].webview.html, /<iframe>|<script>bad|<img src=x>/);
});
