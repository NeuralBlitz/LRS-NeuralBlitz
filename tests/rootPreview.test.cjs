'use strict';

// This exercises the actual source preview, not an AI backend.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { once } = require('node:events');
const { createPreviewServer } = require('../index.js');

async function withPreview(check) {
  const server = createPreviewServer();
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  try {
    await check('http://127.0.0.1:' + server.address().port);
  } finally {
    await new Promise((resolve, reject) => {
      server.close((err) => err ? reject(err) : resolve());
    });
  }
}

test('root preview health response explicitly says backend is NOT ready', async () => {
  await withPreview(async (url) => {
    const response = await fetch(url + '/healthz');
    assert.equal(response.status, 200);
    assert.match(response.headers.get('content-type'), /application\/json/);
    const data = await response.json();
    assert.equal(data.status, 'pre-production');
    assert.equal(data.production_ready, false);
    assert.equal(data.backend_connected, false);
    assert.equal(response.headers.get('cache-control'), 'no-store');
  });
});

test('homepage is a static truthful preview with restrictive policy', async () => {
  await withPreview(async (url) => {
    const response = await fetch(url);
    const page = await response.text();
    assert.equal(response.status, 200);
    assert.match(page, /Research and development preview only/);
    assert.match(page, /No AI backend/);
    assert.doesNotMatch(page, /264,447|production-ready enterprise|Cognitive AI Active/i);
    assert.match(response.headers.get('content-security-policy'), /default-src 'none'/);
  });
});

test('root preview never exposes arbitrary methods or routes', async () => {
  await withPreview(async (url) => {
    assert.equal((await fetch(url + '/invalid')).status, 404);
    const method = await fetch(url, { method: 'POST' });
    assert.equal(method.status, 405);
    assert.equal(method.headers.get('allow'), 'GET');
  });
});

test('Replit configuration launches preview without advertising deploy capability', () => {
  const cfg = fs.readFileSync(path.resolve(__dirname, '../.replit'), 'utf8');
  assert.match(cfg, /run = "HOST=0\.0\.0\.0 node index\.js"/);
  assert.match(cfg, /"index\.js"/);
  assert.doesNotMatch(cfg, /\[deployment\]|deploymentTarget|package-lock\.json"\]/);
  assert.doesNotMatch(cfg, /replit\.nix/);
});
