# NBOS client response validation (pre-production)

The VS Code client treats network transport success as distinct from a
confirmed backend operation. A successful HTTP status code alone is not an
execution or debugger success signal.

## Current response requirements

| Operation | Required backend evidence |
| --- | --- |
| `POST /boot` | `ok === true` (boolean) |
| `POST /execute` with a file | `ok` boolean and explicit completed or stopped evidence (see [debugger contract](debugger-execution-contract.md)) |
| `POST /execute` with a command | `ok` must be boolean; a rejected command (`ok: false`) is returned to the UI as a failure |
| `POST /debug/continue`, `stepOver`, `stepInto`, `stepOut`, `pause` | `ok === true` for command acknowledgement; this is **not** proof that a step finished |
| `GET /debug/stack` | A `frames` array; missing data is not silently converted into an empty stack |
| `GET /debug/variables/:scope` | A `variables` object; missing data is not silently converted into an empty scope |
| `POST /debug/evaluate` | A present `result` property (a legitimate `null` is allowed) |
| `GET /status`, `POST /introspect` | An object response; explicit `ok: false` must surface an error |

These are **client-side contract checks**, not proof that any connected
backend currently complies. A backend returning an empty body for a successful
debug-control request must be upgraded to return a positive acknowledgement
before it can be used with this client.

**Fail-closed endpoint selection:** `neuralblitz.nbosEndpoint` now has an empty default. The client does not contact any server until the user selects a compatible NBOS address, with HTTPS required except for loopback HTTP. URLs containing credentials, non-root paths, query strings or fragments are rejected; HTTP redirects are disabled. This avoids accidentally sending NBCL source to the project's unrelated port-8080 services. Bearer-token provisioning now uses a password-masked VS Code command and `ExtensionContext.secrets` rather than the unsupported plaintext `neuralblitz.authToken` setting. Endpoint URLs set in workspace/folder scope are rejected so a checked-out repository cannot redirect a stored token; only user-level endpoint configuration is accepted. No server-side authentication, token rotation, TLS termination or actual NBOS backend is certified.

The Python gateway does **not** implement these NBOS endpoints. [Gateway/NBOS route compatibility](gateway-nbos-boundary.md) documents the missing bridge, overlapping port 8080 uses, insecure/undeclared authentication configuration, and a real loopback HTTP test for deliberate 404 results.

The isolated test suite uses mocked transport responses. API authentication,
real server interoperability, error format versioning, DAP events and
timeouts must be validated in an end-to-end staging environment.

Run the offline suite with:

```sh
bun install --frozen-lockfile
bun run compile
bun run lint
bun run test
```
