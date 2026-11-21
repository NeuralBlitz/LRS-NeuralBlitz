# LRS-NeuralBlitz

**Status: pre-production research and development — not a deployed or certified AI product.**

LRS-NeuralBlitz is a repository of experimental AI and software-engineering projects, including an actively tested **NeuralBlitz VS Code extension**, a **Python FastAPI gateway prototype**, and a **local telemetry Compose configuration**. Repository presence does not establish working integration, scientific validity, benchmark performance, production security, or deployment readiness.

The former ~2,900-line README mixed executable interfaces, sketches, numerical performance claims, scientific hypotheses, and future goals without sufficient evidence. It has been [preserved as unverified historical material](docs/history/README-legacy-2026-11-21.md), not discarded. Read the [claim-by-claim audit and evidence requirements](docs/readme-claim-audit.md) before relying on historical descriptions.

## What is actually checked

| Surface | Evidence available in this repository | Boundary |
| --- | --- | --- |
| VS Code extension | `package.json` defines three language IDs (`nbcl`, `reflexaellang`, `lon`), nine commands, two contributed tree views, and an inline debug adapter; TypeScript compilation, lint, and offline regression tests run in CI | Real VS Code Extension Host operation and authenticated NBOS integration are **not yet certified** |
| VSIX packaging | A [GitHub Actions workflow](.github/workflows/vscode-vsix-candidate.yml) bundles the extension, creates a minimal pre-release candidate, verifies its contents, and records SHA-256 integrity metadata | A downloadable CI test artifact is **not** Marketplace publication or a production release |
| Python gateway | `main.py` contains six declared FastAPI routes; a dependency-free suite checks the fail-closed behavior of the multi-agent execution endpoint | These isolated checks do **not** establish real server startup, token security, or an operational multi-agent executor |
| Telemetry configuration | `docker-compose.yml` configures InfluxDB, TimescaleDB, Prometheus, Grafana, Node Exporter, and cAdvisor; CI checks root Compose interpolation and default loopback port binding | Services have **not** been verified as a production deployment; image pinning, cAdvisor privileges, and previously committed credential rotation require work |
| Other research directories | Source trees and proposals exist under folders such as `neuralblitz-v50/`, `iot_mesh_system/`, `voice_interface/` and `edge_computing/` | Presence of a directory or example does **not** establish implementation completeness, accuracy, performance, or hardware compatibility |

This is a **source-backed inventory**, not a claim that every module has been installed, executed, or benchmarked. The documentation [evidence audit](docs/readme-claim-audit.md) explains exactly what was checked and what remains untested.

## VS Code extension development

Requirements: a compatible Node/Bun development environment; the VS Code extension declares `engines.vscode: ^1.80.0`. CI uses locked Bun dependencies and a test runner with mocked VS Code APIs.

~~~sh
git clone https://github.com/NeuralBlitz/LRS-NeuralBlitz.git
cd LRS-NeuralBlitz
bun install --frozen-lockfile
bun run compile
bun run lint
bun run test
~~~

Editor language support and command contributions are defined in `package.json` and implemented under `src/`. The extension exposes an NBOS client; commands that require a backend do not work merely by installing the extension.

To inspect the **unpublished** test VSIX candidate, open the [VSIX release-candidate workflow](https://github.com/NeuralBlitz/LRS-NeuralBlitz/actions/workflows/vscode-vsix-candidate.yml), select a successful run from an approved commit, and review the artifact and checksum. See [candidate packaging and test-install instructions](docs/vscode-candidate-packaging.md). Do not treat this candidate as a verified production release.

## Gateway API prototype

`main.py` defines the following **source-level** HTTP routes, which are not represented here as authenticated production services:

| Method | Path |
| --- | --- |
| GET | `/` |
| GET | `/api/integration/status` |
| GET | `/api/cognitive/status` |
| POST | `/api/cognitive/analyze` |
| GET | `/api/multi-agent/status` |
| POST | `/api/multi-agent/execute-workflow` |

The multi-agent execution route explicitly **does not execute tasks**. It rejects unavailable components (HTTP 503), invalid task lists (HTTP 400), and otherwise reports that the executor is not implemented (HTTP 501). Any earlier example describing successful workflow execution through this route is outdated. See [workflow implementation status](docs/multi-agent-workflow-status.md).

There is **no repo-wide verified coverage percentage**, no supported assurance of complete JWT/RBAC or multi-cloud deployment, and no authenticated end-to-end FastAPI smoke test in the current release gates.

## Local telemetry configuration

The root `docker-compose.yml` is a **development configuration**, not a hardened deployment recipe. Published ports default to `127.0.0.1`, and database/dashboard secrets must be supplied through environment values. The Compose policy tests verify configuration shape with disposable CI values; they do **not** start containers or inspect live authentication.

Before even considering external exposure or production use, read [deployment security](docs/security-deployment.md) and the [Compose security baseline](docs/compose-security-baseline.md). cAdvisor privileges, mutable image references, operational secret rotation, and runtime hardening remain unresolved.

## Reproducible checks

~~~sh
# Check source-backed README statements and all local Markdown links
python3 scripts/check_readme_contract.py

# Python contract and policy regression tests (offline)
python3 -m unittest discover -s tests -p 'test_*.py' -v

# VS Code extension compilation, lint, and mocked regression checks
bun run compile
bun run lint
bun run test
~~~

The Compose security checker additionally requires Docker Compose and uses disposable interpolation values:

~~~sh
python3 scripts/check_compose_security.py
~~~

CI reports reflect *specific checks at a particular commit*, not universal system validation. See [production quality gates](.github/workflows/production-gates.yml) and [production readiness](docs/production-readiness.md).

## Research claims and evidence policy

The historical README includes ambitious statements concerning artificial consciousness, quantum computation, post-quantum cryptography, brain-computer interfaces, large-scale IoT/edge performance, differential privacy, and enterprise readiness. None should be interpreted as measured or independently validated merely because an example, class, configuration, or study title appears in this repository.

To promote a claim into the supported README, require: a precise definition, relevant tracked implementation, reproducible test or experiment, declared dependencies/hardware/data, recorded results with provenance, failure cases, and review appropriate to the scientific or security consequence. Claims that cannot currently be tested remain **research hypotheses or intended directions**.

The [legacy claim inventory](docs/audits/readme-legacy-claim-inventory.tsv) preserves extracted original prose assertions with line numbers; **unverified does not mean disproved**. The source archive remains available for systematic follow-up.

## Root-level source and research inspection

The root includes 110 tracked entries spanning code, research specifications,
metadata, binary artifacts, a symlink and a Gitlink. The
[filename-indexed root review](docs/audits/root-review-findings.md) and
[110-entry evidence register](docs/audits/root-file-review.csv) record what
was inspected, defects found, and the limits of verification. A passing source
scan is **not** equivalent to running or independently validating every
subsystem. The [reproducible root review check](scripts/check_root_review.py)
requires source-hash updates after any root-level change.

The root `index.js` is **not an HTTP application**. Running `node index.js`
intentionally exits with a diagnostic message rather than implying a server
started. Replit does not advertise an autoscaled deployment or HTTP port.
The tested VS Code extension and optional experimental Python gateway are
separate components; neither is made production-ready by this root entry point.

## Documentation and contributing

The [root-file review register](docs/audits/root-file-review-register.md) identifies each of the 110 baseline tracked root entries and its verification limits. The [repository-wide audit](docs/audits/repository-wide-inspection.md) covers nested files at an inventory/structural level, **not** automatic proof that they work.

**Replit status:** The old autoscale configuration invoked a metadata-only Node entry point. The root Replit development command now reports that no deployable root HTTP app exists; it is not a production launch path. Stage-cluster figures in the repository are hypothetical arithmetic simulations, not measured deployment counts.

Start with the [documentation index](docs/README.md), [product release gates](docs/production-readiness.md), [README evidence audit](docs/readme-claim-audit.md), [extension activation contract](docs/extension-activation-contract.md), [debugger execution contract](docs/debugger-execution-contract.md), and [VSIX candidate packaging guide](docs/vscode-candidate-packaging.md).

Use [GitHub Issues](https://github.com/NeuralBlitz/LRS-NeuralBlitz/issues) for reproducible defects and missing evidence. A substantive product-capability claim needs a testable pull request, not just updated marketing copy.

**License:** [MIT](LICENSE). The repository is evolving; verify the latest commit and CI run before relying on it.
