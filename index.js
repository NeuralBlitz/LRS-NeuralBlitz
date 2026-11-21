'use strict';

// Replit/development preview only. This does not instantiate a NeuralBlitz AI backend.
const http = require('node:http');
const VERSION = '0.1.0-preview';

const page = [
  '<!doctype html>',
  '<html lang="en"><head><meta charset="utf-8">',
  '<meta name="viewport" content="width=device-width, initial-scale=1">',
  '<title>LRS-NeuralBlitz source preview</title>',
  '<style>body{max-width:48rem;margin:3rem auto;padding:0 1.25rem;',
  'font:1rem/1.6 system-ui,sans-serif;color:#263238}',
  '.warning{border-left:4px solid #d69e2e;padding-left:1rem}</style></head>',
  '<body><h1>LRS-NeuralBlitz</h1>',
  '<p class="warning"><strong>Research and development preview only.</strong>',
  'No AI backend, authentication, multi-agent workflow executor, or',
  'production performance benchmark is running in this Node preview.</p>',
  '<p>The separately built VS Code extension has offline regression checks',
  'and a CI-packaged pre-release candidate. Live backend integration and',
  'staging validation remain outstanding.</p>',
  '<p><a href="https://github.com/NeuralBlitz/LRS-NeuralBlitz">',
  'View the source repository and verified README</a>.</p></body></html>',
].join('\n');

function createPreviewServer() {
  return http.createServer((req, res) => {
    const route = (req.url || '').split('?')[0];
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'");
    if (req.method !== 'GET') {
      res.writeHead(405, { 'Content-Type': 'text/plain; charset=utf-8', Allow: 'GET' });
      res.end('Method not allowed');
    } else if (route === '/healthz') {
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        service: 'LRS-NeuralBlitz source preview',
        version: VERSION,
        status: 'pre-production',
        backend_connected: false,
        production_ready: false,
      }));
    } else if (route === '/') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(page);
    } else {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Not found');
    }
  });
}

function startPreview() {
  const port = Number(process.env.PORT || '8000');
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error('PORT must be an integer from 1 to 65535');
  }
  const host = process.env.HOST || '127.0.0.1';
  const server = createPreviewServer();
  server.listen(port, host, () => {
    console.log('LRS-NeuralBlitz source preview: http://' + host + ':' + port);
    console.log('PRE-PRODUCTION: no AI backend or production deployment started');
  });
  return server;
}

if (require.main === module) {
  startPreview();
}

module.exports = { createPreviewServer, startPreview, version: VERSION };
