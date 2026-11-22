# README truth audit — November 21, 2026

**Scope:** the original 2,941-line root `README.md` and the former `docs/README.md`, compared against `main.py`, `package.json`, extension entry points, root Compose configuration, tracked test files, and CI definitions at Git commit `709ffcd06bf774feaa0dfc573c8a5b6172f59c7c`.

**Method:** static source inspection and reproducible repository/CI contract checks, plus a limited classification of historical prose. **Not a comprehensive executable validation of every example or research assertion.** No physical devices, cloud deployments, BCI hardware, quantum hardware, full production backend, or third-party benchmark environment was supplied. Claims requiring those conditions were marked **unverified**, not silently accepted as facts or declared disproved.

## Scope and inventory

| Original document property | Count / finding | Interpretation |
| --- | --- | --- |
| Root README | 2,941 lines | Original preserved at [historical README](history/README-legacy-2026-11-21.md) with a prominent warning |
| Highlighted capability assertions (initial inventory) | 215 candidate list entries | Not the complete statement count; headings/code/comments also imply claims |
| Substantive non-code prose/list assertions extracted into the [line inventory](audits/readme-legacy-claim-inventory.tsv) | 239 | Every extracted entry labeled `not-verified-as-product` pending evidence; source line numbers preserved |
| Python import references in legacy examples | 71 occurrences | No claim that these are all importable; installation paths and dependencies require independent tests |
| Broken local Markdown link targets | 12 | All removed from the active README; absent target files were **not** invented |
| Originally numbered ecosystem components | At least 17 | The legacy summary advertised 16; no count of functioning systems is established by numbering |
| Root HTTP route declarations | 6 | Static source count only; not six proven running services |

### Broken references that were removed from the active README

- `docs/api/rest.md`, `docs/api/websocket.md`, `docs/api/grpc.md`, `docs/api/auth.md`
- `docs/sdk/python.md`, `docs/sdk/javascript.md`, `docs/sdk/go.md`, `docs/sdk/rust.md`
- `docs/deployment/docker.md`, `docs/deployment/kubernetes.md`, `docs/deployment/cloud.md`, `docs/deployment/edge.md`

The active README now links to tracked, relevant engineering documents. Their existence does not imply that an entire SDK or production deployment guide has been implemented.

## Corrected unsupported or contradictory claims

| Legacy claim | Verification outcome | What would count as evidence |
| --- | --- | --- |
| 18 production API endpoints | **Contradicted for the root gateway**: `main.py` declares six decorated HTTP routes. It is not an exhaustive audit of nested experimental servers | Route inventory from a running authenticated app, request/response integration tests, OpenAPI schema and versioned coverage |
| Fully working multi-agent workflow execution | **Contradicted for the documented root endpoint**: the `/api/multi-agent/execute-workflow` route explicitly returns HTTP 501 when components are present and tasks are valid | Real executor binding, side-effect-safe staging execution, results persisted with task IDs, error/retry/timeout and authorization tests |
| 95% test coverage, 257 documented tests, 100% API documentation | **Unsubstantiated:** no audited repository-wide coverage report or consolidated test evidence supports these numbers. The previous `docs/README.md` repeated other unsupported metrics | Instrumented coverage by component with source and report artifacts, discovered test inventory and truthful docs coverage calculation |
| 24.11s → 0.000s analysis, sub-millisecond inference, 10,000+ device/network capacity | **Not measured in this audit**; no reproducible test configuration and raw trial data examined | Benchmark harness, dataset and load generation, machine specs, commit SHA, repeated trials, variance/percentiles and independent reproduction |
| Quantum-safe or quantum-resistant cryptographic guarantees, “quantum supremacy” or Bell-inequality validation | **No qualifying evidence established**; hash length and mathematical terminology are not security proofs | Standardized cryptographic algorithms, threat model, independent cryptanalysis/certification as appropriate; for physical quantum claims, equipment/methods, data, statistical analysis and controls |
| Consciousness, 11D processing, multiverse reality simulation, BCI integration and self-evolution | **Research descriptions / hypotheses, not product-validated performance** | Defined measurable constructs, valid implementation, controls, data, replicated peer review where applicable |
| JWT/RBAC/mTLS security, complete rate limiting, zero-trust, complete audit logs | **Not established for this gateway**. The presence of security vocabulary or configuration examples is not evidence of enforcement | Actual authenticated endpoint integration tests, authorization matrix, secrets handling, independent threat modeling and penetration testing |
| Fully integrated cloud, IoT, federated/DP, bioinformatics, voice, edge and smart-city functionality | **Not validated as integrated products**. Some relevant directories and example source files exist | Dependency-locked build + integration tests for each product boundary, realistic fixtures/devices and measured acceptance criteria |
| “Production ready” and enterprise availability | **Not supported:** branch protection is disabled, some Compose images are mutable, cAdvisor is privileged, and live credential rotation / staging validation remain pending | Secure release gates, verified branch controls, artifact provenance, production/staging runbooks, deployment rehearsals and monitoring evidence |

**Code snippets:** the old README is not an executable cookbook. Some examples rely on absent names/hardware, unavailable dependencies or unsupported interfaces; one used an invalid Python keyword form such as `256_realities=True`. No old example may be promoted to “working” without a dependency-pinned test fixture and observed execution result. Archived demonstrations should not be copied into production.

## What we can positively verify

| Claim in the replacement README | Evidence | Automated guard |
| --- | --- | --- |
| Extension declares NBCL, ReflexælLang, LoN | `package.json` contributes three language identifiers | `scripts/check_readme_contract.py` validates manifest entries |
| Nine contributed extension commands, two tree views | `package.json`, `src/extension.ts`, `src/commands/nbclCommands.ts` | Offline activation tests plus README contract check |
| Inline debugger and fail-closed NBOS client behavior | `src/debugger/debugAdapterFactory.ts` and `src/util/nbosClient.ts` | Node tests, TypeScript build/lint in production gates |
| Python gateway source has six declared routes | FastAPI decorators in `main.py` | Python AST route/README consistency check |
| Workflow execution endpoint is deliberately unimplemented | `main.py` response contract; `tests/test_multi_agent_workflow.py` | Isolated behavioral contract tests + AST check |
| Compose defaults to localhost ports and requires injected credentials | `docker-compose.yml` | Compose regression and policy checks with disposable values |
| VSIX candidate is created from an allowlisted bundle | `.github/workflows/vscode-vsix-candidate.yml` and `scripts/vscode_candidate.py` | Packaging tests and CI-generated archive/checksum |
| The repository includes research and prototype directories | Tracked Git tree | On-disk path existence checks; **not feature-performance tests** |

**Current certification boundary:** CI proves that particular code/test/build/packaging checks pass for the stated revision. Mocked tests and static inspection cannot certify secure deployment, stable service behavior, scientific discoveries, real-world performance, or an end-to-end shipping product.

## Promotion rules for future README assertions

A proposed feature/benchmark/security claim should have:

1. **Precisely defined behavior and scope**, including what would falsify the assertion.
2. **A directly tracked implementation** with stable imports and dependency/environment specification.
3. **Repeatable tests** that check behavior rather than only the existence of an object or class.
4. **Recorded empirical results**, versioned data where applicable, confidence/variance and negative cases.
5. **Explicit verification tier**: static inventory, isolated unit, integration, staging deployment, benchmark, external review.
6. **Known limitations** and whether the work is a hypothesis, plan, prototype, or released capability.
7. **A source-linked change** to the evidence ledger and successful continuous integration.

### Runnable checks

~~~sh
python3 scripts/check_readme_contract.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
bun install --frozen-lockfile
bun run compile
bun run lint
bun run test
~~~

Running `python3 scripts/check_compose_security.py` additionally requires Docker Compose. The VSIX workflow packages a **test artifact**, not a public release. The release criteria remain in [production readiness](production-readiness.md).

## Remaining high-priority audits

- Confirm current and historical Python/module imports through a **locked, isolated environment**, including nested experimental repositories. Exclude modules that cannot legally or safely be executed from automated tests.
- Create representative performance benchmarks (baseline, hardware, workload, variance) before restoring numerical claims.
- **2026-11-22 update:** A local authenticated ASGI transport suite now checks the actual FastAPI application through pinned gateway dependencies. This does **not** exercise a real `lrs_agents` or NBOS backend, OAuth, JWT or production transport security. Implement authenticated **external-backend** integration tests and a real VS Code Extension Host smoke test.
- Produce an exhaustive module-by-module research ledger with runnable examples and unresolved scientific hypotheses; the historical TSV is a **review queue**, not 239 passing tests.
- Repair container privilege and image-pinning issues, rotate credentials where deployed, and enable enforced GitHub branch protection.
