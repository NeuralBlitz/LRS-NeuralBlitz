'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const root = path.resolve(__dirname, '..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));

function parseAsset(filename) {
  const fullPath = path.resolve(root, filename);
  assert.ok(fullPath.startsWith(root + path.sep), 'Manifest path escaped repository');
  assert.ok(fs.existsSync(fullPath), 'Missing extension asset: ' + filename);
  assert.doesNotThrow(() => JSON.parse(fs.readFileSync(fullPath, 'utf8')),
    'Invalid JSON extension asset: ' + filename);
  return JSON.parse(fs.readFileSync(fullPath, 'utf8'));
}

test('all contributed language grammars and snippets parse as strict JSON', () => {
  const definitions = [
    ...(manifest.contributes.grammars || []).map(x => x.path),
    ...(manifest.contributes.snippets || []).map(x => x.path),
  ];
  assert.ok(definitions.length >= 4);
  for (const file of definitions) parseAsset(file);
});

test('all contributed language configurations parse and declare valid editing pairs', () => {
  const languages = manifest.contributes.languages || [];
  assert.equal(languages.length, 3);
  for (const language of languages) {
    const config = parseAsset(language.configuration);
    assert.ok(Array.isArray(config.brackets), 'Missing brackets for ' + language.id);
    for (const pair of config.brackets) {
      assert.ok(Array.isArray(pair) && pair.length === 2,
        'Invalid bracket pair for ' + language.id);
      assert.ok(pair.every(x => typeof x === 'string'));
    }
    for (const pair of config.autoClosingPairs || []) {
      assert.equal(typeof pair.open, 'string', 'Invalid autoclose opening token');
      assert.equal(typeof pair.close, 'string', 'Invalid autoclose closing token');
    }
    for (const pattern of Object.values(config.indentationRules || {})) {
      assert.doesNotThrow(() => new RegExp(pattern));
    }
    if (config.folding && config.folding.markers) {
      for (const expression of Object.values(config.folding.markers)) {
        assert.doesNotThrow(() => new RegExp(expression));
      }
    }
  }
});
