# NBOS debugger execution contract — pre-production

The VS Code debug adapter uses the backend responses from `src/util/nbosClient.ts`.
A successful HTTP request or `ok: true` field alone is **not** proof that an
NBCL program completed.

## Explicit execution states

The `POST /execute` file-execution response must supply a boolean `ok`
field and one of these outcomes:

| Response | Adapter behavior |
| --- | --- |
| `{"ok": true, "completed": true}` | Emits DAP terminated; disconnects |
| `{"ok": true, "stopped": true, "line": 8}` | Emits DAP stopped at the reported line |
| `{"ok": false, "error": {"message": "reason"}}` | Emits an error output and terminates |
| Missing `ok`, unsupported shape, ambiguous `ok: true` | Throws a contract error, emits error output, terminates |
| Request rejected/network unavailable | Emits error output and terminates |

A stopped response takes precedence over `completed` when both are set, to
avoid reporting a paused debugger as already terminated. Backend response
contracts should ultimately reject such contradictory payloads.

## DAP safety and known limitations

- Launch is acknowledged once, after a confirmed backend boot. Later execution
  failures are events, not a second launch response.
- Step/continue/pause requests return an error response when the backend
  rejects them. A successful HTTP acknowledgement **does not** generate a
  fabricated stopped event; a real asynchronous state notification is required.
- Breakpoints remain *unverified* until a backend installation/verification
  acknowledgement protocol is implemented.
- Unsupported DAP capabilities (conditional/hit-count breakpoints, restart,
  cancel, breakpoint locations, completion suggestions, etc.) are not
  advertised as supported.
- Unavailable stack, evaluation, or variables data produces a DAP error
  response rather than a misleading success payload.

## Verification

```sh
bun install --frozen-lockfile
bun run compile
bun run lint
bun run test
```

The Node tests transpile the actual TypeScript client/debugger classes into
isolated mocks. They do not prove that a real NBOS backend implements the
specified contract or emits the needed asynchronous state changes.

**Before production**: integrate a real authenticated backend; prove response
schemas, breakpoint installation, DAP event ordering, cancellation, stepping,
disconnections, timeout recovery, and VS Code Extension Host behavior under
integration tests. This improvement intentionally favors explicit errors
over unsound legacy mock-success behavior.
