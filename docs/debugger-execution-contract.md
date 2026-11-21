# NBOS execution and debugger protocol contract (pre-production)

The VS Code extension requires **backend execution evidence**. HTTP success
or `ok: true` alone does not establish that a program executed.

## Program execution contract

The `POST /execute` response for a program must be an object with a boolean
`ok` property. Accepted outcomes:

| Response body | Client / debugger interpretation |
| --- | --- |
| `{"ok": true, "completed": true}` | Completed. DAP launch acknowledged, terminated event emitted, backend disconnected. |
| `{"ok": true, "stopped": true, "line": 8}` | Stopped. DAP launch acknowledged, stopped event emitted. |
| `{"ok": false, "error": {"message": "reason"}}` | Rejected; no successful launch response. |
| `{"ok": true}` | Ambiguous acceptance; fail closed. |
| Both `completed: true` and `stopped: true` | Contradictory; fail closed. |
| Missing/nonboolean `ok` or transport failure | Fail closed. |

A failed/ambiguous launch returns **one DAP error response**, and does not
also produce a successful response or a fabricated terminated/stopped event.
This preserves the merge from PR #20.

## Outstanding debugger limitations

- Breakpoints are passed to the backend, but are not marked verified in the
  editor until backend installation evidence is available; no such
  acknowledgement protocol exists in this source.
- Conditional/hit-count breakpoints, restart/cancel, breakpoint-locations,
  debugger completions and other unsupported capabilities are not advertised.
- Control operations (continue/step/pause) use DAP error responses if the
  backend rejects the request. HTTP acknowledgement does **not** mean a step
  finished; the adapter no longer fabricates stopped events from acceptance.
- A real backend state-event channel is required for asynchronous stopped,
  resumed, terminated and progress events after the initial launch.
- Failed variable, stack trace and evaluation requests produce errors rather
  than apparently successful placeholder responses.

## Local CI checks

```sh
bun install --frozen-lockfile
bun run compile
bun run lint
bun run test
```

Offline tests transpile actual TypeScript sources with mocked VS Code and
debug-adapter services. They are **not** live service or VS Code Extension
Host tests.

Before production release, add authenticated end-to-end NBOS and DAP tests,
request validation, reconnection behavior, command ordering, cancellation and
timeouts, verified breakpoint registration, state-event notifications, and
debugging in supported VS Code versions.
