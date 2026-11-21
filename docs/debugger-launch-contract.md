# Debug adapter launch contract

`NeuralBlitzDebugSession.launchRequest` must not acknowledge a successful
debug launch merely because `/boot` responded successfully.

The debugger now waits for a backend `/execute` result:
- `completed: true` and not `stopped`: acknowledge launch, then terminate.
- `stopped: true` and not `completed`: acknowledge launch, then emit a
  breakpoint stop.
- Otherwise: send one DAP error response and disconnect the client.
- Contradictory completed-and-stopped results fail closed.
- Network, boot or execution errors fail the launch rather than claiming
  success or emitting a misleading successful termination.

This prevents a UI from reporting successful execution while the backend
rejected the program, but does not prove that a real backend can run NBCL
code. Verification uses a mocked Debug Adapter Protocol host and the
transpiled production implementation:

```sh
bun install --frozen-lockfile
bun run compile
bun run test
```

The extension entry point also avoids registering the introspection command
twice. The canonical command registration lives in `NBCLCommands.register`.

Still required before a release: Extension Host integration tests,
authenticated backend fixtures, breakpoint resolution validation, DAP
lifecycle/reconnect tests, and propagation of failures from step/continue
and other debug operations.
