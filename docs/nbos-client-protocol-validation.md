# NBOS client response validation (pre-production)

The VS Code client treats network transport success as distinct from a
confirmed backend operation. A successful HTTP status code alone is not an
execution or debugger success signal.

## Versioned preflight and response requirements

Before every remote NBOS operation, the client sends a **Bearer-authenticated** `GET /nbos/v1/capabilities` to the user-configured origin. A backend must respond with a JSON object containing exactly `protocol: "nbos/1"`, boolean `compatible: true`, and an array of declared operation strings such as `POST /execute` or `GET /status`. The client requires the specific operation it is about to perform, rejecting malformed discovery, missing permissions, or `compatible: false` **before transmitting command/source/debug request bodies**. For variable scopes, the declaration is `GET /debug/variables/*`.

The `/execute` path carries **three different payload types**: `{command: string}`, `{source: string}` (bounded inline multi-line program), and `{program: string, breakpoints: []}` (legacy file-path execution, not supported by the reference). Before any call, discovery must provide an explicit `execution_modes` array containing the relevant `command`, `source`, and/or `file` modes. The read-only reference advertises only `command` and `source`. Missing, malformed or unknown modes fail closed; a reference server must **never receive a local file path**. This is strict client-side permission negotiation, not proof of access-control enforcement by a remote backend.

Discovery is repeated for each operation (no stale capability cache). This is interface negotiation, **not security attestation** and not a substitute for a trusted backend identity, access controls, or executable integration evidence.

## Current response requirements

| Operation | Required backend evidence |
| --- | --- |
| `POST /boot` | `ok === true` (boolean) |
| `POST /execute` with a file | `ok` boolean and explicit completed or stopped evidence (see [debugger contract](debugger-execution-contract.md)) |
| `POST /execute` with bounded inline source | `ok === true`, `completed === true`, `instruction_count` a positive integer no greater than 16, and exactly that many well-formed step records with valid one-based line numbers; mere positive HTTP acknowledgment does not count. The reference prevalidates every instruction and local-register transition before evaluation, then returns `final_locals` for the current source request. The client validates step-record shape but does not cryptographically certify backend computations or persistent sessions. |
| `POST /execute` with a command | `ok` must be boolean; `ok: true` alone is insufficient. Completion requires `completed: true`; `stopped: true` requires a valid positive integer `line` and is displayed as a paused command. Explicit `ok: false` is shown as a refusal. Contradictory and malformed states are rejected. |
| `POST /debug/continue`, `stepOver`, `stepInto`, `stepOut`, `pause` | `ok === true` for command acknowledgement; this is **not** proof that a step finished |
| `GET /debug/stack` | A `frames` array; missing data is not silently converted into an empty stack |
| `GET /debug/variables/:scope` | A `variables` object; missing data is not silently converted into an empty scope |
| `POST /debug/evaluate` | A present `result` property (a legitimate `null` is allowed) |
| `GET /status`, `POST /introspect` | An object response; explicit `ok: false` must surface an error |

The command UI no longer duplicates raw NBCL source into the extension output channel. File and command execution require well-formed boolean state flags, and stopped debugger states must include a valid one-based line number. These are **client-side contract checks**, not proof that any connected
backend currently complies. A backend returning an empty body for a successful
debug-control request must be upgraded to return a positive acknowledgement
before it can be used with this client.

**Fail-closed endpoint selection:** `neuralblitz.nbosEndpoint` now has an empty default. The client does not contact any server until the user selects a compatible NBOS address, with HTTPS required except for loopback HTTP. URLs containing credentials, non-root paths, query strings or fragments are rejected; HTTP redirects are disabled. This avoids accidentally sending NBCL source to the project's unrelated port-8080 services. Bearer-token provisioning now uses a password-masked VS Code command and `ExtensionContext.secrets` rather than the unsupported plaintext `neuralblitz.authToken` setting. Endpoint URLs set in workspace/folder scope are rejected so a checked-out repository cannot redirect a stored token; only user-level endpoint configuration is accepted. No server-side authentication, token rotation, TLS termination or actual NBOS backend is certified.

The root Python gateway implements only a negative `GET /nbos/v1/capabilities` discovery route; it does **not** implement NBOS operations. The separate [read-only reference](nbos-readonly-reference.md) implements `GET /status`, `POST /introspect` for `system`, and `POST /execute` for the [finite, prevalidated NBCL subset](nbcl-bounded-execution.md), including `/calc` and short inline source programs, with real authenticated Axios-to-Uvicorn tests. It neither boots agents nor executes arbitrary NBCL. [Gateway/NBOS route compatibility](gateway-nbos-boundary.md) documents the missing bridge, overlapping port 8080 uses, insecure/undeclared authentication configuration, and a real loopback HTTP test for deliberate 404 results.

The original unit suite uses mocked transport responses. The new [real Node Axios ↔ Uvicorn protocol test](gateway-nbos-boundary.md) exercises an actual network connection and checks that real Axios refuses to send unsupported NBOS operations after a negative discovery result; direct authenticated calls to missing NBOS routes still return HTTP 404. This is not proof that the root gateway supports execution or that any backend supports full NBCL or debugger functionality. The separate read-only reference has its own positive, deliberately limited integration tests.

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
