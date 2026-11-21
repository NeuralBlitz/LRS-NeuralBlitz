# Root-file-by-file review — November 21, 2026

**Repository:** [NeuralBlitz/LRS-NeuralBlitz](https://github.com/NeuralBlitz/LRS-NeuralBlitz) only.

**Source evidence:** [110-row root file review register](root-file-review.csv). Each row records a tracked path, its reviewed Git blob SHA, Git mode, content type, review scope and concrete observation. [The CI root review checker](../../scripts/check_root_review.py) compares both path coverage **and current blob hashes** with Git; any root change requires review-register refresh.

## Exactly what was inspected

The root-level tracked Git index contains 110 entries:

| Type | Entries | Review method | Limit |
| --- | ---: | --- | --- |
| Python `.py` | 39 | Retrieved text; examined imports, classes, top-level functions, demonstrations, dependencies and risky success claims | No blanket runtime execution or external service verification |
| Markdown `.md` | 44 | Retrieved full text; examined report scope, headings, production/empirical assertions, and references | Scientific accuracy, all examples and each individual assertion are not validated |
| JSON `.json` | 9 | Retrieved and parsed JSON; examined top-level structures and schema roles | Schema interoperability and data provenance not tested |
| Other root text/configuration | 14 | Inspected `.replit`, `.gitmodules`, `.env.example`, Node/Bun/Python metadata, Compose and diagram/document text; includes `.coverage` binary | Binary coverage contents not semantically audited |
| Special root entries | 4 | MIT license text retrieved; icon identified as binary; symlink identified; Gitlink reference identified | Icon content, symlink destination and external Gitlink source are not deeply inspected |

**Arithmetic clarification:** the groups above total 110 because `.coverage` belongs to the 14 other-configuration items and the four special entries include the license. The two binary files (`.coverage` and `generated-icon.png`) were recognized as binary and their Git tree metadata was inspected; the text-only connector cannot decode them as source. The external `lrs_agents` Gitlink has no checked-out source in the root tree.

This is a *source-informed structural/content review*, not 110 independently successful executable tests. Full-text retrieval permits analysis, but it does not itself prove all code paths or every sentence.

## High-priority findings and remediation

| Priority | Evidence | Finding | Status |
| --- | --- | --- | --- |
| P0 — misleading API status | [`main.py`](../../main.py) | The HTML gateway claimed a 264,447× speedup, active cognition, and enterprise security with no runtime evidence; `integration_active` was unconditionally true | Corrected on this audit branch; independent end-to-end auth/health checks still needed |
| P0 — root preview mismatch | [`.replit`](../../.replit), [`index.js`](../../index.js) | Replit advertised deployment of an entrypoint that only logged metadata; required Replit files were absent | Replaced by a metadata-only fail-closed diagnostic; no HTTP server, published port, or automatic deployment is advertised |
| P0 — simulation described as actual deployment | [`deployment_summary.py`](../../deployment_summary.py), [`stage_clusters_5000_9999_deployment.py`](../../stage_clusters_5000_9999_deployment.py) | Agent totals are simulated/accounting values; no evidence of 500 million provisioned agents | Added explicit simulation/no-live-deployment labels; cloud scale remains unverified |
| P0 — missing deployment dependency contract | [`pyproject.toml`](../../pyproject.toml), [`server.py`](../../server.py), [`main.py`](../../main.py) | Root Python project specifies no dependencies, but gateway imports FastAPI/Pydantic and optional LRS modules | Gateway guards missing optional LRS modules; reproducible installation matrix and real startup tests outstanding |
| P0 — unsafe/unknown route exposure | [`main.py`](../../main.py) | Importing legacy benchmarking/enterprise route registrations automatically could expose unverified endpoints; direct launch default bound all interfaces | Legacy route registration now opt-in; direct Python launch defaults to loopback; auth is **not** certified |
| P1 — orphaned nested Gitlinks | [`.gitmodules`](../../.gitmodules) and nested tree | Root describes only `lrs_agents` but three more nested references exist and can break git checkout; no URLs verified | Open dependency-integrity defect, not repaired by inventing module URLs |
| P1 — telemetry privilege | [`docker-compose.yml`](../../docker-compose.yml) | Privileged cAdvisor, host mounts and mutable image tags remain | Existing Compose baseline guards drift but **does not remediate** legacy risk |
| P1 — committed generated artifacts | [`.gitignore`](../../.gitignore), `.coverage`, `htmlcov/` | Tracked coverage and caches despite ignore rules; reports need provenance/secret inspection | Open review, no destructive deletion without provenance |
| P1 — large research reports | [`OMEGA_CTOS_ARCHITECTURE.md`](../../OMEGA_CTOS_ARCHITECTURE.md), [`BLOCKCHAIN_INTEGRATION_REPORT.md`](../../BLOCKCHAIN_INTEGRATION_REPORT.md), [`NEURALBLITZ_COMPREHENSIVE_ACHIEVEMENTS.md`](../../NEURALBLITZ_COMPREHENSIVE_ACHIEVEMENTS.md) | Operational, benchmark, cryptographic and scale assertions are not backed by verified deployments or peer review | Added prominent notices while preserving historical text; evaluation remains open |
| P2 — optional integrations | Root `*integration.py`, CK and BCI/vision modules | External APIs, PyTorch/NumPy/SciPy/scikit-learn and other dependencies absent from the root lock; performance, DP, identity/security and clinical claims need specialized tests | Cataloged as experimental, not independently certified |
| P2 — testing completeness | [`test_neuralblitz_federated_learning.py`](../../test_neuralblitz_federated_learning.py) | Standalone ML tests require Torch etc and are not covered by the root's dependency-free CI job | Need isolated dependency-pinned CI suites per component |

## Root documentation categories

The 44 root Markdown files include engineering guidance, historical achievement reports, implementation reports, design specifications, mathematical proposals and deployment stories. Files such as `AGENTS.md`, `gg.md`, and `OMEGA_CTOS_ARCHITECTURE.md` are **architectural/research texts**, not executable state or proof of extraordinary computational capabilities.

The complete filename-level classification and evidence boundary for every item, including apparently ordinary files like `README_SIMPLE.md`, `CODE_OF_CONDUCT.md`, `LICENSE`, `uv.lock`, and `voting_systems_report_metadata.json`, are in the [root register](root-file-review.csv).

## Reproducible evidence and acceptance gates

```sh
# Verifies every root-level tracked file is registered, with matching content SHA.
python3 scripts/check_root_review.py

# Executes dependency-free tests of the source-level gateway truth contract.
python3 -m unittest discover -s tests -p 'test_*.py' -v

# Tests the actual minimal Node preview over HTTP; includes all extension tests.
bun install --frozen-lockfile
bun run compile
bun run lint
bun run test

# Crawls all tracked files, not only the root, and uploads CSV/JSON findings.
python3 scripts/audit_repository_tree.py --out audit-output
```

These commands are source and offline regression gates. They do not test an operational backend, hardware, large-scale agent deployment, cryptographic protocol efficacy or third-party cloud integrations.

## Next engineering actions

1. Validate the gateway startup with pinned FastAPI/uvicorn dependencies and an initialized `lrs_agents` Gitlink; test authenticated requests, lifecycle and route exposure.
2. Classify and resolve all nested Gitlink paths without editing other repositories or inventing dependency origins.
3. Add separate install/build/test matrices for the root Python capability families: AI/CKs, federated learning, vector DB, blockchain, security, smart city, governance, agent runtime and research demos.
4. Review data/credential provenance in binary artifacts and tracked caches before safe removal, and implement secrets-scanning policy.
5. Reconcile nested extension, mobile, Go, Rust, cloud, deployment, research and dashboard files using the existing [entire-tree scanner](../../scripts/audit_repository_tree.py), then close each finding with measured evidence.

**Verification boundary:** This audit has improved traceability and removed several directly false claims; it does **not** establish complete scientific or functional verification of the entire repository.
