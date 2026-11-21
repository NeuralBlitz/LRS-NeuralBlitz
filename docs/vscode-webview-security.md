# VS Code webview content safety

The NeuralBlitz status, introspection, and capability-kernel panels display
backend/registry-derived data. Such data is not trusted HTML.

The panels must:
- Disable webview scripts (no script execution is needed for these views).
- Send a restrictive document Content Security Policy.
- Escape text derived from API responses and capability-kernel metadata,
  including map keys, values, and lists.
- Represent unavailable telemetry as unknown/unavailable rather than zero.
- Be covered by offline injection-regression tests.

Validation:
```sh
bun install --frozen-lockfile
bun run compile
bun run test
```

These static panels are not proof of backend authenticity or authorization.
A release still requires integration tests with a real authenticated backend.
