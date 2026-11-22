# VS Code extension activation contract

This document describes the verified *source-level* activation contract, not
a completed VS Code Extension Host integration certification.

## Contributed commands and runtime handlers

Every command in `package.json` under `contributes.commands` must register
exactly once during extension activation.

- `neuralblitz.boot`, `neuralblitz.execute`, `neuralblitz.status`,
  `neuralblitz.introspect`, `neuralblitz.ck.search`,
  `neuralblitz.ck.documentation`, and `neuralblitz.debug.start`
  register in `NBCLCommands`.
- `neuralblitz.credentials.set` and `neuralblitz.credentials.clear` expose a
  password-masked SecretStorage workflow; they do not write tokens into
  workspace settings, logs or committed files.
- `neuralblitz.debug.step` and `neuralblitz.debug.continue` delegate to
  VS Code's built-in debugger commands, but only when the active debug
  session type is `neuralblitz`. They do not claim backend step completion.

## Views and debugger

The manifest contributes the `neuralblitz` Activity Bar container with
`neuralblitzGoldenDAG` and `neuralblitzCKRegistry` views. The IDs must
exactly match those passed to `registerTreeDataProvider`.

The debugger uses `DebugAdapterInlineImplementation`; an old manifest
reference to `out/debugAdapter.js` was removed because this repository
does not build that standalone entry point.

The welcome prompt does not offer an unimplemented tutorial command. It
provides a link to the repository's checked-in readiness documentation.

## Verification

```sh
bun install --frozen-lockfile
bun run compile
bun run lint
bun run test
```

The test `tests/extensionActivation.test.cjs` transpiles the real extension
entry point and command registrar and uses a strict fake VS Code API to check:

1. Exact match between contributed and registered commands, with no duplicate IDs.
2. Exact match between contributed views and registered tree data providers.
3. Debug command scoping, so these commands never act on unrelated debug sessions.
4. Inclusion of the status bar and output channel in disposables.
5. Inline debugger manifest compatibility and tracked view icon existence.

This offline smoke test does **not** start the real Extension Development Host,
install a VSIX, validate rendering, or verify backend/debugger interoperability.
Those remain independent release gates.
