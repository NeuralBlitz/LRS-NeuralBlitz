# LRS-NeuralBlitz API reference — current gateway source contract

**Status: pre-production; local prototype only.** This reference describes the six explicit routes in [`main.py`](../main.py) on the current repository branch. It is **not** documentation for a deployed, authenticated production API, an NBOS backend, or the optional experimental route registrations.

The earlier specification included unimplemented JWT login, cloud URLs, request quotas, and illustrative benchmark responses. It remains [archived as historical, unverified material](history/API_REFERENCE-legacy-2026-11-22.md). Do not use that archive as an operational contract.

## Local setup and authentication

Install the [isolated pinned gateway requirements](../gateway/requirements-pinned.txt), generate a random local token, and start the app **on loopback in the background of the same shell** so the client sees the same environment:

```sh
python3.11 -m venv .venv-gateway
. .venv-gateway/bin/activate
python -m pip install -r gateway/requirements-pinned.txt
export LRS_GATEWAY_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
uvicorn main:app --host 127.0.0.1 --port 8000 &
LRS_GATEWAY_PID=$!
```

Base URL for this **local process only**: `http://127.0.0.1:8000`.

Except for `GET /`, HTTP paths require exactly one `Authorization: Bearer <token>` header matching `LRS_GATEWAY_API_TOKEN`. Configuration accepts an ASCII token of 32–512 characters with no whitespace. The gateway rejects missing/invalid token configuration with HTTP **503** and missing/incorrect credentials with HTTP **401** (with `WWW-Authenticate: Bearer`). OpenAPI and docs routes are also gated. This is a small development safeguard, **not** JWT authentication, OAuth, RBAC, a rate limiter, or a production security review. After successful authentication, the gateway bounds each HTTP request body to **1 MiB (1,048,576 bytes)**; it rejects oversized declared or streamed bodies with HTTP **413**. Invalid Content-Length headers receive HTTP **400**. This bound is not a request-rate quota, traffic-shaping system, or public-ingress defense.

Check status locally:

```sh
curl --retry 5 --retry-connrefused --retry-delay 1 -fsS \
  -H "Authorization: Bearer ${LRS_GATEWAY_API_TOKEN}" \
  http://127.0.0.1:8000/api/integration/status

# Stop the local development process after inspection:
kill "$LRS_GATEWAY_PID"
```

The token shown here is an environment variable reference, never a real credential. Do not store real secrets in Git or run the prototype behind a public ingress.

## Declared HTTP routes

| Method | Path | Current source behavior |
| --- | --- | --- |
| GET | `/` | Public HTML status page explaining pre-production limitations |
| GET | `/api/integration/status` | Component detection; `integration_active` and `integration_verified` are **false** |
| GET | `/api/cognitive/status` | Availability/status of optional cognitive analyzer |
| POST | `/api/cognitive/analyze` | Optional analyzer only; HTTP 503 if component unavailable |
| GET | `/api/multi-agent/status` | Availability/status of optional coordinator |
| POST | `/api/multi-agent/execute-workflow` | No execution: HTTP 503 if component missing; HTTP 400 for invalid task list when present; otherwise HTTP 501 |

All five `/api/` routes require the Bearer token. The existence of a route or a `200` status response does not mean the optional backend is functional, measured, or production certified.

## Request and response notes

**`GET /api/integration/status`** returns JSON containing `lrs_available`, `opencode_available`, `cognitive_available`, `multi_agent_available`, `integration_active: false`, `integration_verified: false`, and a message. Some agent values can be `null` when modules have not been installed. These are source-level detection values, not health probes.

**`GET /api/cognitive/status`** reports `cognitive_available: false` and an explanatory message when the component is absent. When present, it constructs an analyzer and returns whatever status it reports; failures are not proof of scientific or operational validity.

**`POST /api/cognitive/analyze`** accepts a JSON object with `code` and optional `file_path` (default: `unknown.py`). Without the optional analyzer it responds with HTTP 503. When available, success returns `analysis`, `cognitive_insights`, and `success: true`; source exceptions return HTTP 500. No speed, accuracy, or cognitive metric is guaranteed.

**`GET /api/multi-agent/status`** returns `multi_agent_available: false` when the coordinator dependency is absent; optional coordinator details are returned only when constructed.

**`POST /api/multi-agent/execute-workflow`** expects JSON with a nonempty `tasks` list, for example:

```json
{"tasks":[{"id":"example","description":"Illustrative only"}]}
```

The example is **not runnable execution**. The route first rejects unavailable coordinator dependencies (503), then invalid lists (400), and otherwise explicitly refuses unimplemented execution (501). It does not start agents or return completed work.

## Unsupported / not demonstrated

There is currently **no verified** `/enterprise/auth/login`, user creation API, published production API hostname, enforced request quota, JWT issuance, compatible NBOS execution interface, or independently verified model/agent performance. Setting `LRS_ENABLE_EXPERIMENTAL_ROUTES=1` may add unreviewed routes from optional dependencies; these are outside this contract and must stay disabled during ordinary development.

Read the [gateway auth and installation contract](../gateway/README.md), [gateway-to-NBOS incompatibility evidence](gateway-nbos-boundary.md), [production readiness criteria](production-readiness.md), and [root README](../README.md). Run the repository's existing tests and CI checks on the exact commit before interpreting any capability as verified.
