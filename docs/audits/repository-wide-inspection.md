# LRS-NeuralBlitz — Entire tracked repository static inspection

**Baseline commit:** `709ffcd06bf774feaa0dfc573c8a5b6172f59c7c`, inspected on November 21, 2026. This audit applies **only to the NeuralBlitz/LRS-NeuralBlitz repository**. It does not certify the contents of other repositories referenced as Git submodules.

## Tree census from GitHub

| Item | Baseline |
| --- | ---: |
| Total Git tree entries | 889 |
| Files / Git links | 724 |
| Ordinary blob files | 720 |
| Gitlink references to other trees | 4 |
| Markdown files | 131 |
| Python source files | 188 |
| Generated HTML files | 202 |
| TypeScript files | 20 |
| JavaScript files | 16 |
| CJS test/config files | 6 |

Counts are a **baseline snapshot**: subsequent audit code and docs will increase the number of tracked files. Counts are not tests of whether modules work.

### Auditable all-files inspection

The new [tracked source scanner](../../scripts/audit_repository_tree.py) reads **every checked-out tracked Git blob**, classifies source/document/asset/compiled reports, validates Python parseability and JSON syntax without executing untrusted modules, audits local Markdown link targets, and records high-risk marketing claim markers. It emits a **per-file CSV and JSON summary** as a [GitHub Actions artifact](../../.github/workflows/repository-audit.yml) on each relevant branch build.

This is full **static file inventory** coverage when CI passes, *not* deep human review, successful import, compilation of every language, functional acceptance testing for every project, validation of third-party links, independent scientific replication, or hardware/production deployment verification. Binary files are read as bytes and classified; they are not interpreted as functional source.

Gitlinks are not ordinary blobs and are reported separately rather than incorrectly counted as inspected source. Unresolvable links require a documented upstream location and valid dependency manifest before any recursive inspection. Audit results themselves are *not* proof that all claims are true.

## Findings by boundary

### Root and project-level documentation

- The former [2,941-line README](../history/README-legacy-2026-11-21.md) contained at least twelve nonexistent local document targets and unsupported deployment/benchmark/security claims. The new root README is limited to source-backed product status.
- `README_SIMPLE.md` promises immediate Replit operation and a simulated large performance multiplier without a reproducible production proof.
- `docs/API_REFERENCE.md` describes authentication and rate-limiting behavior that is **not evidenced by root `main.py`**; it must not be used as a live API contract.
- `docs/INSTALLATION.md` includes historical environmental dependencies and assumptions without locked cross-platform testing.
- `CONTRIBUTING.md` has only an abbreviated invitation; it needs a useful contributor workflow.
- Some tiny placeholder files, such as `docs/Yea.md`, do not constitute feature documentation.

### NeuralBlitz v50 and nested subprojects

- `neuralblitz-v50/README.md`, `FEATURES_COMPLETE.md`, and `ECOSYSTEM_COMPLETE.md` assert production readiness and measured outcomes that were not independently reproduced.
- The nested `docs/API_REFERENCE.md`, `docs/IMPLEMENTATION_GUIDE.md`, and `k8s/README.md` mix proposed interfaces/deployments with claims of completion. Their tests and environments must be inspected independently.
- The tree includes three nested unresolved gitlinks beneath `neuralblitz-v50`, plus root `lrs_agents`; gitlink source and installation compatibility are **outside checkout scope** until properly resolved.
- `neuralblitz-v50/nural.md` is an approximately 1.1 MB Markdown source requiring dedicated document-level substantive review; scanning it as UTF-8 does **not** validate its assertions.

### Integrations and VS Code extensions

- The root VS Code extension in `package.json` and `src/` has automated compilation, mocked activation regression checks and a candidate bundling pipeline. These do not prove that backend operations work in the actual Extension Host.
- `vs-code/README.md` refers to a historical/different extension identity and Marketplace version, not the tested `neuralblitz-vscode` candidate.
- `serverless/README.md`, `neuralblitz_slack_bot/README.md`, and `voice_interface/QUICKSTART.md` describe cloud/Slack/AI hardware workflows that require independent deployment or credentials; they are not certified as live integrations.
- The code and supporting assets for nested dashboards, mobile, edge, IoT, federated learning, bioinformatics, governance, and smart-city components need component-specific build/runtime tests. Tracked filenames do not constitute a working multi-product suite.

### Repository hygiene and risk

- `htmlcov/` contains ~207 tracked files (mostly generated HTML coverage pages), not hand-reviewed product implementations.
- Tracked `.coverage`, `.pytest_cache/`, `.ruff_cache/`, `demo_cache/` and `neuralblitz-v50/python/neuralblitz_v50.db` warrant provenance, privacy and cleanup review. Do not blindly remove them without checking whether they contain important evidence or user data.
- Root Compose still contains privileged cAdvisor mounts and mutable image references; CI checks the current baseline but cannot prove live deployment safety.
- The Git checkout logs have shown nested gitlink warnings; a dedicated dependency integrity fix must be planned, not guessed by inventing missing submodule URLs.

## Evidence tiers for each document or feature

1. **Indexed:** A tracked file exists and was read/classified; proves existence only.
2. **Static checked:** Source parses or document links resolve; proves a limited structural property.
3. **Unit checked:** Isolated tests run and assertions pass; not end-to-end compatibility.
4. **Integrated:** A real backend, package, device or service contract has been exercised in a controlled environment.
5. **Production or independent validation:** Deployment evidence, security review or scientifically reproducible measurements have been assessed against explicit success criteria.

Historical claims currently labeled experimental cannot be promoted to tiers 4–5 simply because they have source files, simulated outputs, test-count text, a coverage HTML file, or a demo script.

## Follow-up remediation order

1. Require README source contract and repository inventory CI checks on all new changes.
2. Reconcile secondary markdowns with demonstrated source; label outdated, aspirational or hypothetical work clearly.
3. Repair broken local links discovered in nested documentation and the missing submodule linkage; preserve provenance and avoid substituting guessed URLs.
4. Address repository hygiene and potentially sensitive committed binary/cache artifacts.
5. Perform module-specific Python, Go, Rust, JavaScript, extension, API and infrastructure integration tests with documented dependency isolation.
6. Add benchmark harnesses before reintroducing numeric speed, scalability, security or scientific assertions.
7. Resolve production auth, deployment hardening and branch-protection requirements before any release.

**Documentation retention:** The historical root README and its [239-line narrative claim inventory](readme-legacy-claim-inventory.tsv) remain accessible for continued research rather than being silently deleted.
