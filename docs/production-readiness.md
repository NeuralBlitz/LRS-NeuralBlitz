# LRS-NeuralBlitz — Production readiness and release gates

**Current status: pre-production.** A successful workflow is evidence that its
listed checks passed; it is **not** a certification that every repository
component, backend, container, or research claim works in production.

## Defined product surfaces

1. **VS Code extension**: TypeScript editor commands, diagnostics, language
   contributions, debugging, and NBOS client integration.
2. **API/interface**: Python FastAPI gateway in `main.py`; optional
   `lrs_agents` functionality requires compatible installed dependencies.
3. **Bounded read-only NBOS reference**: separate opt-in FastAPI process supporting a finite deterministic NBCL subset, short inline programs with up to eight **request-local** registers, status and system introspection. Actual Axios/Uvicorn tests verify these operations; it cannot boot an agent, execute arbitrary NBCL or debug programs.
4. **Telemetry stack**: Compose development configuration for monitoring
   and databases. It is not an approved production deployment manifest.

The root repository also contains research demos, nested projects, and
legacy experiments. Those are not covered by the release gates below.

## Automated required checks to configure in GitHub

`.github/workflows/production-gates.yml` runs on **every pull request targeting
main**, every push to main, and manual dispatch:

- `Extension compile lint and regression`: locked dependencies, TypeScript
  compile, lint baseline, offline Node regression tests, manifest asset checks.
- `Python API contracts, ASGI integration and live Uvicorn smoke`: installs a pinned
  FastAPI/httpx environment and sends real HTTP requests through the application
  through an in-process transport; a separate [real Uvicorn loopback smoke
  test](gateway-nbos-boundary.md) launches the process and exercises HTTP over
  TCP. Tests local Bearer token enforcement and fail-closed error contracts,
  but **does not validate any live LRS/NBOS backend**.
- `Real NBOS client versus live gateway protocol`: starts **two separate** real Python Uvicorn services and sends Axios requests from the transpiled VS Code NBOS client. The root gateway must **reject incompatible NBOS operations**; the opt-in read-only reference must **successfully complete only** its three safe instructions and bounded inline programs, return actual status/introspection, and reject boot, files and debugging. Neither proves a full NBCL engine.
- `Compose security regression`: policy unit tests and `docker compose config`
  validation with disposable test-only credentials.

The lint policy starts with objective bug/security rules. It does not assert
that the codebase is stylistically clean or type-safe beyond compilation.

**Repository configuration needed:** enable `main` branch protection or a
ruleset requiring these three job names, review approval, and current-branch
checks before merge. Workflows running do not by themselves block unreviewed
merges; the GitHub integration may lack branch-protection administration scope.

## Release blockers to close before a production release

- Implement and integration-test actual workflow execution rather than
  returning false success, and define authentication/authorization.
- Validate security hardening beyond the tested 1 MiB authenticated request-body limit and sanitized optional-component error responses: rate limiting, reverse proxy limits, slow-client timeouts, operational monitoring and external ingress remain unverified.
- Resolve the [pinned LRS-Agents import and dependency risks](audits/lrs-submodule-runtime-compatibility.md), including subprocess-based OpenCode probing and optional enterprise middleware, before enabling any execution adapter.
- Preserve explicit `execution_modes` (`command`, `source`, or `file`) preflight when adding new backends; the limited reference advertises only command and inline source, never file-path execution.
- Define and validate **persistent session identity, authorization, concurrency control, expiry and cleanup** separately; the bounded reference registers are deliberately discarded after each request and are not real multi-user sessions.
- Implement a full backend supporting the versioned `nbos/1` capability contract with independently verified agent boot, program execution and debugger states. The read-only reference verifies a **strict subset** only; the root gateway remains incompatible. A positive capability declaration alone does not prove execution or production security.
- Verify backend startup and contracts using the checked-out `lrs_agents`
  dependency and real request/response fixtures. The [gateway developer
  installation](../gateway/README.md) covers only isolated HTTP/ASGI behavior;
  the optional Gitlink backend and external authorization are not integrated.
- Add real VS Code Extension Host integration tests and debugger tests.
  The NBOS client now requires an explicit secure endpoint; there is no compatible
  default service; local token management now uses `ExtensionContext.secrets`
  with explicit set/clear commands. This does not certify remote identity,
  token rotation or a real NBOS backend, and execution remains unavailable
  without an independently verified compatible runtime.
- Review all webviews/command surfaces and secrets handling, not just
  the three hardened static panels.
- Confirm optional `host-metrics` cAdvisor remains absent from the default Compose profile; explicitly opted-in deployments are still privileged and require separate host-hardening review.
- Pin container image versions/digests, address cAdvisor privileged mounts,
  audit the full dependency inventory, and validate runtime health.
- Confirm whether previously committed demonstration credentials were ever
  deployed; rotate and revoke them wherever used.
- Establish deployment environments, rollback and incident procedures,
  security support policy, monitoring and alert ownership.
- Build/install and smoke-test a versioned `.vsix` release candidate with a
  supported VS Code version before publishing.
- Reconcile README claims with measured, reproducible benchmark evidence;
  avoid presenting prototypes as verified production functionality.

## Release procedure (once blockers are resolved)

1. Review PR diff, threat model and user-facing changes.
2. Require all production-quality jobs and relevant targeted workflows to pass.
3. Obtain human review and verify branch-protection requirements.
4. Build a candidate artifact from the tested commit, record its SHA/checksum.
5. Run authenticated staging smoke tests and rollback rehearsal.
6. Approve and publish a tagged release with clear changes, compatibility,
   known limitations, deployment instructions and rollback guidance.
7. Monitor live errors and security alerts; retain deployment evidence.

Do not claim a production release solely because these workflows pass.
