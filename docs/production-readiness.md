# LRS-NeuralBlitz — Production readiness and release gates

**Current status: pre-production.** A successful workflow is evidence that its
listed checks passed; it is **not** a certification that every repository
component, backend, container, or research claim works in production.

## Defined product surfaces

1. **VS Code extension**: TypeScript editor commands, diagnostics, language
   contributions, debugging, and NBOS client integration.
2. **API/interface**: Python FastAPI gateway in `main.py`; optional
   `lrs_agents` functionality requires compatible installed dependencies.
3. **Telemetry stack**: Compose development configuration for monitoring
   and databases. It is not an approved production deployment manifest.

The root repository also contains research demos, nested projects, and
legacy experiments. Those are not covered by the release gates below.

## Automated required checks to configure in GitHub

`.github/workflows/production-gates.yml` runs on **every pull request targeting
main**, every push to main, and manual dispatch:

- `Extension compile lint and regression`: locked dependencies, TypeScript
  compile, lint baseline, offline Node regression tests, manifest asset checks.
- `Python API contract regression`: isolated standard-library regression
  tests for the multi-agent endpoint, not end-to-end FastAPI tests.
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
- Verify backend startup and contracts using the checked-out `lrs_agents`
  dependency and real request/response fixtures.
- Add real VS Code Extension Host integration tests and debugger tests.
- Review all webviews/command surfaces and secrets handling, not just
  the three hardened static panels.
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
