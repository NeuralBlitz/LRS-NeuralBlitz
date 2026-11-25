# Experimental FastAPI Gateway — isolated installation and auth contract

**Pre-production.** The root `main.py` contains a small API prototype. These pinned requirements install only the standard FastAPI/ASGI stack: they intentionally do not install the missing `lrs_agents` Gitlink, research/AI components, backend model service, cloud systems, or VS Code extension.

## Reproduce the isolated gateway environment

Python **3.11** is the CI baseline. From the repository root:

```sh
python3.11 -m venv .venv-gateway
. .venv-gateway/bin/activate
python -m pip install -r gateway/requirements-pinned.txt
python -m unittest discover -s tests -p 'test_gateway_asgi_integration.py' -v
```

Run the [real-process smoke test](../docs/gateway-nbos-boundary.md) to verify that Uvicorn actually starts on loopback, enforces Bearer authentication, and returns honest 404 errors for the NBOS routes not implemented by this gateway:

```sh
python -m unittest discover -s tests -p 'test_gateway_live_process.py' -v
```

All direct/transitive packages in `requirements-pinned.txt` have explicit versions; **hash-pinned artifacts and a cross-platform lock are not yet provided**. Use the CI job for an actual installation validation. The repository-root `pyproject.toml` / `uv.lock` still describe a historical empty workspace, **not** the gateway installation, and should not be presented as sufficient dependencies.

## Separate read-only NBOS reference adapter

A distinct, opt-in [NBOS protocol reference](../docs/nbos-readonly-reference.md) can be launched using `python -m uvicorn gateway.nbos_reference:app --host 127.0.0.1 --port 8765 --no-access-log`. It shares the same bearer-token validation and bounded-body middleware but implements **only** read-only status, system introspection, three standalone pure commands (`/status`, `/help`, bounded integer `/calc`), and prevalidated short inline programs supporting at most eight request-local integer registers with no state persisted between requests. It is intentionally **not** a full NBCL engine, agent boot service, debugger or replacement for this gateway. Review the [finite subset contract](../docs/nbcl-bounded-execution.md) before sending any source. Its Python ASGI tests and real Axios-to-Uvicorn integration test are separate from this gateway's negative compatibility test.

## Local authenticated requests

Set a unique bearer token, generated outside the repository, with at least 32 ASCII characters (do not check it into Git or expose it in logs). For example:

```sh
export LRS_GATEWAY_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
uvicorn main:app --host 127.0.0.1 --port 8000 &
LRS_GATEWAY_PID=$!
```

In the **same shell**, where the generated token is still available, query the gateway (the retries cover local startup):

```sh
curl --retry 5 --retry-connrefused --retry-delay 1 -fsS \
  -H "Authorization: Bearer ${LRS_GATEWAY_API_TOKEN}" \
  http://127.0.0.1:8000/api/integration/status

# Stop the process when finished:
kill "$LRS_GATEWAY_PID"
```

Only `GET /` (the static pre-production page) is public. **Every other HTTP path**, including OpenAPI/docs and dynamically registered routes, requires a matching Bearer token; WebSocket handshakes are checked by the same ASGI guard. If the token is missing or malformed, the API responds **503**; if configured but absent/incorrect, **401** with `WWW-Authenticate: Bearer`. The guard uses constant-time comparison, does not log tokens, and is not OAuth, JWT, RBAC, mTLS or production identity management. Authenticated HTTP requests are now bounded to **1 MiB (1,048,576 bytes)** before JSON parsing, including streamed/chunked bodies; oversized requests return **413** and authenticated requests with invalid Content-Length headers return **400**. This does not provide rate limiting, request timeouts, or a public DoS defense.

The versioned authenticated `GET /nbos/v1/capabilities` route returns `protocol: "nbos/1"`, `compatible: false`, and `operations: []`. This is **negative discovery** for the actual VS Code NBOS client; it cannot execute or debug through the gateway. A successful discovery HTTP response is not evidence of functional compatibility.

The gateway does not instantiate `OpenCodeTool` during startup (the pinned helper probes external executables), and it does not import experimental benchmark or enterprise modules by default. Opting in with `LRS_ENABLE_EXPERIMENTAL_ROUTES=1` loads those unreviewed modules and fails startup if their dependencies are absent; keep that switch unset in ordinary development. See the [pinned dependency source audit](../docs/audits/lrs-submodule-runtime-compatibility.md).

The endpoint status remains `integration_verified: false`: successful authentication only proves access to a **prototype gateway**, not LRS backend availability. The workflow endpoint returns **503** when components are unavailable and **501** when a valid task request cannot be executed. The CI suite tests these behaviors through the real ASGI application without an external server or network call.

**Operational boundary:** Run only on loopback in a trusted development environment. Do not expose port 8000, enable optional experimental routes, or deploy behind a public ingress without a completed security review, TLS, secret rotation, broader resource limits, rate limiting, audit controls and a backend integration contract. `LRS_ENABLE_EXPERIMENTAL_ROUTES=1` may register additional unreviewed endpoints and must remain unset.

See [production readiness](../docs/production-readiness.md) and [README evidence audit](../docs/readme-claim-audit.md).
