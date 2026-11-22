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

All direct/transitive packages in `requirements-pinned.txt` have explicit versions; **hash-pinned artifacts and a cross-platform lock are not yet provided**. Use the CI job for an actual installation validation. The repository-root `pyproject.toml` / `uv.lock` still describe a historical empty workspace, **not** the gateway installation, and should not be presented as sufficient dependencies.

## Local authenticated requests

Set a unique bearer token, generated outside the repository, with at least 32 ASCII characters (do not check it into Git or expose it in logs). For example:

```sh
export LRS_GATEWAY_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
uvicorn main:app --host 127.0.0.1 --port 8000
```

In another terminal use the same token securely supplied to the client:

```sh
curl -fsS -H "Authorization: Bearer ${LRS_GATEWAY_API_TOKEN}" \
  http://127.0.0.1:8000/api/integration/status
```

Only `GET /` (the static pre-production page) is public. **Every other HTTP path**, including OpenAPI/docs and dynamically registered routes, requires a matching Bearer token; WebSocket handshakes are checked by the same ASGI guard. If the token is missing or malformed, the API responds **503**; if configured but absent/incorrect, **401** with `WWW-Authenticate: Bearer`. The guard uses constant-time comparison, does not log tokens, and is not OAuth, JWT, RBAC, mTLS or production identity management.

The endpoint status remains `integration_verified: false`: successful authentication only proves access to a **prototype gateway**, not LRS backend availability. The workflow endpoint returns **503** when components are unavailable and **501** when a valid task request cannot be executed. The CI suite tests these behaviors through the real ASGI application without an external server or network call.

**Operational boundary:** Run only on loopback in a trusted development environment. Do not expose port 8000, enable optional experimental routes, or deploy behind a public ingress without a completed security review, TLS, secret rotation, resource limits, request-size/rate limiting, audit controls and a backend integration contract. `LRS_ENABLE_EXPERIMENTAL_ROUTES=1` may register additional unreviewed endpoints and must remain unset.

See [production readiness](../docs/production-readiness.md) and [README evidence audit](../docs/readme-claim-audit.md).
