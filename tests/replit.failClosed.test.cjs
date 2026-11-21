'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const test = require('node:test');

const root = path.resolve(__dirname, '..');

test('root Node entry point exports metadata but does not claim an HTTP service', () => {
  const metadata = require(path.join(root, 'index.js'));
  assert.equal(metadata.name, 'NeuralBlitz');
  assert.equal(metadata.status, 'research-prototype');
});

test('direct Replit entrypoint invocation cannot masquerade as service startup', () => {
  const invocation = spawnSync(process.execPath, [path.join(root, 'index.js')], {
    encoding: 'utf8',
    timeout: 5000,
  });
  assert.equal(invocation.status, 1);
  assert.match(invocation.stderr, /not a deployable root Node\/HTTP application/);
  assert.match(invocation.stderr, /metadata only/);
});

test('Replit configuration does not advertise autoscaled HTTP deployment', () => {
  const config = fs.readFileSync(path.join(root, '.replit'), 'utf8');
  assert.match(config, /^run = \["node", "index.js"\]$/m);
  assert.doesNotMatch(config, /^\[deployment\]$/m);
  assert.doesNotMatch(config, /^\[\[ports\]\]$/m);
  assert.doesNotMatch(config, /requiredFiles.*package-lock\.json/);
});
