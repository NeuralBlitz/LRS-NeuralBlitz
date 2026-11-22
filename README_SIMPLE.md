# LRS-NeuralBlitz — Quick start (verified development paths)

**Status: pre-production.** This repository is not a one-click hosted AI product. The root [`.replit`](.replit) launches a diagnostic Node command, not a web server. The steps below distinguish locally testable components from unimplemented integrations.

## Option 1: Work on the VS Code extension

The root `package.json` defines an experimental VS Code extension. These commands run TypeScript compilation, linting and **mocked/offline** regression tests; they do not prove a live NBOS backend or Extension Host integration.

```sh
git clone https://github.com/NeuralBlitz/LRS-NeuralBlitz.git
cd LRS-NeuralBlitz
bun install --frozen-lockfile
bun run compile
bun run lint
bun run test
```

Use a compatible Bun/Node development installation and VS Code `^1.80.0`. See [the extension setup and security boundary](README.md#vs-code-extension-development) and [candidate packaging](docs/vscode-candidate-packaging.md). A generated VSIX candidate is not a published or certified extension.

## Option 2: Start the isolated local FastAPI gateway

Python **3.11** is the tested CI baseline. Create a separate Python environment and install only the pinned gateway dependencies:

```sh
python3.11 -m venv .venv-gateway
. .venv-gateway/bin/activate
python -m pip install -r gateway/requirements-pinned.txt
python -m unittest discover -s tests -p 'test_gateway_asgi_integration.py' -v
```

Generate a **new, private** local Bearer token and start Uvicorn **in the background of the same shell**. This keeps the token available to the local client without printing it:

```sh
export LRS_GATEWAY_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
uvicorn main:app --host 127.0.0.1 --port 8000 &
LRS_GATEWAY_PID=$!
```

Use the **same terminal** to query the gateway. The retry options allow for local server startup; no token is committed or logged:

```sh
curl --retry 5 --retry-connrefused --retry-delay 1 -fsS \
  -H "Authorization: Bearer ${LRS_GATEWAY_API_TOKEN}" \
  http://127.0.0.1:8000/api/integration/status

# Stop the development process when finished:
kill "$LRS_GATEWAY_PID"
```

`GET /` presents an unauthenticated **pre-production status page**; API routes require the local Bearer token. The status endpoint reports component detection and `integration_verified: false`. Cognitive analysis requires currently optional dependencies, and `POST /api/multi-agent/execute-workflow` **does not execute tasks**. No compatible NBOS backend has been demonstrated. See [the current API contract](docs/API_REFERENCE.md) and [gateway setup](gateway/README.md).

## Replit and deployment status

Clicking **Run** in the current Replit configuration invokes `node index.js`, which intentionally reports that there is no deployable root HTTP application. It does **not** create an interactive public analysis dashboard or automatically produce a working Replit URL. Do not expose the gateway beyond trusted loopback development; production identity, TLS, resource controls and release certification remain open work.

The former simulation-oriented Replit instructions are retained [as historical, unverified documentation](docs/history/README_SIMPLE-legacy-2026-11-22.md). For the supported product scope and evidence boundaries, read [README.md](README.md) and [production readiness](docs/production-readiness.md).
