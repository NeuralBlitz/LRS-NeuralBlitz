# Read-only NBOS protocol reference — local-development adapter

**Status: pre-production, opt-in, intentionally limited.** This repository
includes a real, bounded, read-only HTTP reference implementation of the
`nbos/1` protocol under [`gateway/nbos_reference.py`](../gateway/nbos_reference.py).
It does **not** implement the NeuralBlitz engine, agent boot, NBCL file
execution, debugger events, governance proof, or LRS-Agents integration.
It is distinct from the root [`main.py`](../main.py) gateway, which still
reports **negative** NBOS compatibility.

## Actual implemented and declared operations

| Endpoint | Actual implementation |
| --- | --- |
| `GET /nbos/v1/capabilities` | Authenticated protocol discovery: `compatible: true` **only for the operations below**. Advertises `execution_engine_available: false`, `agent_boot_available: false`, and `debugger_available: false`. |
| `GET /status` | Returns the reference process's own read-only status; `agent_booted: false`, `integration_verified: false`, governance values explicitly unverified. |
| `POST /introspect` | Accepts exactly `{"scope":"system"}` and returns its **own** status and capabilities. Other scopes get HTTP 422. |
| `POST /execute` | Executes exactly two finite pure read-only reference commands: `/status` and `/help`. Returns `ok: true, completed: true` only after the corresponding in-memory handler completes. Other commands and file-path requests return HTTP 422 with `ok: false`. |

It never evaluates input as Python, invokes a shell, reads submitted paths,
opens arbitrary files, launches a model, or fabricates successful NBCL work.
`POST /boot` and all `/debug/*` methods are **not implemented** and are not
advertised. The real extension performs capability discovery before every
operation; it refuses to send those unsupported requests to this service.

## Run on a trusted developer workstation

Use the isolated, pinned Python 3.11 dependencies described in
[the gateway installation guide](../gateway/README.md). From the
repository root and a **single terminal**:

```sh
python3.11 -m venv .venv-gateway
. .venv-gateway/bin/activate
python -m pip install -r gateway/requirements-pinned.txt

export LRS_GATEWAY_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python -m uvicorn gateway.nbos_reference:app --host 127.0.0.1 --port 8765 --no-access-log &
NBOS_REFERENCE_PID=$!

curl --retry 5 --retry-connrefused --retry-delay 1 -fsS \
  -H "Authorization: Bearer $LRS_GATEWAY_API_TOKEN" \
  http://127.0.0.1:8765/nbos/v1/capabilities

curl --retry 5 --retry-connrefused --retry-delay 1 -fsS \
  -H "Authorization: Bearer $LRS_GATEWAY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command":"/status"}' \
  http://127.0.0.1:8765/execute

kill "$NBOS_REFERENCE_PID"
```

To use the **optional** extension integration, start the reference process,
set `neuralblitz.nbosEndpoint` in **VS Code User settings** to
`http://127.0.0.1:8765`, and provision the same local bearer token using
**NeuralBlitz: Save NBOS Bearer Token Securely**. Do not commit tokens or
put them in workspace settings. The editor's Execute NBCL Command operation
will complete **only** for a selection containing exactly `/status` or
`/help`. Boot and debugger commands still fail because they are genuinely
unavailable.

## Verification and remaining limitations

Run the Python ASGI tests and the two real Axios/Uvicorn interoperability
tests (the latter requires the locked extension dependencies installed):

```sh
python -m unittest discover -s tests -p 'test_nbos_reference_adapter.py' -v
node --test tests/nbosGateway.real.integration.cjs tests/nbosReference.real.integration.cjs
```

The real client tests launch the Python reference process on an ephemeral
loopback TCP port and verify actual authenticated source-backed status and
read-only command execution as well as rejected boot, file, debugger and
unauthorized requests. The earlier test continues to prove that the root
gateway **must remain incompatible** with NBOS execution.

Passing these tests verifies only the three deliberately limited reference
operations on the tested commit and environment. There is no arbitrary NBCL
interpreter, user session isolation, production security, authenticated
identity management, TLS, traffic/rate limiting, deployed service, validated
LRS backends, or VS Code Extension Host verification.

To advance beyond this reference, design separately reviewed sandboxed
execution, per-operation authorization and user identity, workspaces and
session lifecycle, debugger event semantics, error propagation, and real
integration validation before advertising any additional capabilities.
