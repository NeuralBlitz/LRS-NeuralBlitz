# Gateway process and NBOS protocol compatibility — November 22, 2026

**Status: pre-production.** The root Python API gateway and VS Code NBOS client do **not** yet speak the same execution protocol. A **separate opt-in read-only reference service** now provides narrowly supported NBOS methods and actual tested command results; it does not change the root gateway or implement the LRS engine. This document records observed source-level contracts and the reproducible loopback integration test. It is not a claim that a working NBOS agent runtime exists.

## Validated endpoints and required evidence

| Surface | Declared path(s) | Implemented behavior/evidence |
| --- | --- | --- |
| Public local gateway | `GET /` | Static pre-production explanation; public without a token |
| Gateway discovery | `GET /api/integration/status`, `GET /nbos/v1/capabilities` | Bearer-authenticated, `integration_verified: false`; versioned NBOS discovery explicitly returns `compatible: false` with no operations |
| Cognitive prototype | `GET /api/cognitive/status`, `POST /api/cognitive/analyze` | Optional components; not evaluated as a functional LRS backend |
| Multi-agent prototype | `GET /api/multi-agent/status`, `POST /api/multi-agent/execute-workflow` | Workflow fails closed: 503 if optional component unavailable, 501 if executor missing |
| VS Code NBOS client | `POST /boot`, `POST /execute`, `GET /status`, `POST /introspect`, `/debug/*` | Client-side response validation exists, **but no matching routes in root `main.py`** |

A browser page loading successfully, or the HTTP gateway accepting its token, **does not** establish that NBOS commands can execute. The VS Code client now probes `GET /nbos/v1/capabilities` before each operation. It requires `protocol: "nbos/1"`, `compatible: true`, and a matching method/path in the `operations` array. This gateway returns `compatible: false` and `operations: []`; the client refuses operations before sending source or debugger requests. Missing/invalid discovery also fails closed. A correctly authenticated request to `/boot` on the gateway must return **404**, not fabricated `ok: true`.

## Real server smoke test

`tests/test_gateway_live_process.py` launches `python -m uvicorn main:app` on a temporary `127.0.0.1` TCP port. It uses the installed FastAPI/uvicorn runtime and standard-library HTTP client, not `httpx.ASGITransport`. The test generates an ephemeral strong token, authenticates real HTTP requests, asserts unavailable NBOS paths return authenticated 404, and terminates the child process. This checks **actual local process startup and HTTP routing** on a CI Linux runner, with no external network or data.

To reproduce in a Python 3.11 environment:

```sh
python -m pip install -r gateway/requirements-pinned.txt
python -m unittest discover -s tests -p 'test_gateway_live_process.py' -v
```

This smoke test is a **development-only** gate. It does not validate TLS, mTLS, Uvicorn workers, service supervision, authenticated deployment behind a proxy, arbitrary origin controls, secret rotation, resource limits, or functionality of missing optional Gitlinks.

## Actual cross-runtime interoperability regression (new)

A second test, [`tests/nbosGateway.real.integration.cjs`](../tests/nbosGateway.real.integration.cjs), launches **the real Python Uvicorn server over a TCP socket** and exercises the actual TypeScript `NBOSClient` through **real Axios**, with only the VS Code settings/SecretStorage host API stubbed. The client is configured at user scope and uses an ephemeral test-only Bearer token stored via the simulated secret store.

It verifies that the gateway's own `/api/integration/status` authenticates successfully and still declares `integration_verified: false`. The versioned discovery route returns explicit incompatibility; the actual Axios client sends **only** capability probes and refuses to issue `/boot`, `/execute`, `/status`, `/introspect`, or debugger calls. Direct authenticated requests to those nonexistent paths still receive HTTP **404**; without a stored token the client receives HTTP **401** on discovery. No NBOS client call may fabricate execution.

CI installs pinned Python dependencies and frozen Bun dependencies before running:

```sh
node --test tests/nbosGateway.real.integration.cjs
```

This is a reproducible **negative integration contract** demonstrating incompatibility of the root gateway. A second [positive read-only adapter test](../tests/nbosReference.real.integration.cjs) starts `gateway.nbos_reference:app` on loopback and sends real Axios requests for `/status`, `/help` and system introspection. That separate service advertises only the operations it implements, including `execution_modes: ["command"]`. The real client rejects file execution **before sending a path** to that command-only adapter; it also rejects boot and debugger operations. See the [reference contract](nbos-readonly-reference.md). The real VS Code Extension Host and a full NBOS execution engine remain untested.

## Integration risks to resolve

- **Port collision remediated in the client:** the extension now defaults to **no NBOS endpoint**. Earlier releases assumed `http://localhost:8080`, overlapping with `server.py` and Compose cAdvisor. Commands fail locally until the user explicitly configures `neuralblitz.nbosEndpoint` for a verified compatible server; the gateway on 8000 remains **incompatible**.
- **Credential storage (now implemented for local client):** the extension no longer reads legacy plaintext `neuralblitz.authToken` settings. Use the password-masked commands **Save NBOS Bearer Token Securely** and **Clear Stored NBOS Bearer Token** to store/delete a token in `ExtensionContext.secrets`. Both ordinary commands and inline debugger sessions share the same extension secret. A workspace-local `neuralblitz.nbosEndpoint` override is rejected to prevent redirecting this stored token through an untrusted repository. This is **client-side secret storage**, not production backend authentication or token lifecycle certification. Remove any legacy plaintext token from user/workspace settings manually.
- **Backend provenance:** the root `lrs_agents` Gitlink is not initialized as a verified compatible NBOS service. A separate read-only protocol reference now has limited HTTP integration tests; **no LRS-backed NBCL execution engine, debugger event stream or end-to-end program execution** exists in this repo.
- **Fail closed:** until an explicit versioned bridge is implemented and tested, return errors for missing capabilities. Do not install generic catch-all `/boot` or `/execute` handlers that merely reply `ok: true`.

## Criteria for a future real NBOS bridge

The `nbos/1` discovery preflight is now implemented as a conservative contract check, **not** an implementation of the engine. A future compatible server must advertise exact operation strings (for example `POST /boot` and `POST /execute`, with `GET /debug/variables/*` for scoped variables). The client currently rechecks on every operation; this adds a round trip and does not authenticate the truthfulness of a malicious backend. Implement actual `/boot`, `/execute`, `/status`, `/introspect` and debugger functions backed by independently verified execution, not synthetic data. Add negative/auth tests, real VS Code Extension Host tests and backend event handling. Release only after route, transport, integrity and security claims have evidence.

See [NBOS client response validation](nbos-client-protocol-validation.md), [production readiness](production-readiness.md), and [gateway setup](../gateway/README.md).
