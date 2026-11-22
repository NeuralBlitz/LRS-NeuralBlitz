# LRS-NeuralBlitz — Documentation Index

**Status: pre-production.** The pages below describe tracked source, explicit test boundaries, and outstanding release work. This documentation does **not** certify experimental research claims, independent security review, actual cloud deployment, medical/BCI performance, or hardware interoperability.

Return to the [main README](../README.md) for the verified product scope. The original long-form README remains [archived as unverified historical material](history/README-legacy-2026-11-21.md).

## Start here

- [Verified Gitlink provenance and dependency mapping](audits/gitlink-provenance.md) — four pinned upstreams, approved source URLs and integrity tests
- [Root-file review register](audits/root-file-review-register.md) — all 110 baseline root Git entries, filename-specific risks and evidence tiers
- [README evidence audit](readme-claim-audit.md) — corrected assertions, historical claim categories, and promotion standards
- [Legacy prose claim inventory](audits/readme-legacy-claim-inventory.tsv) — source line references for substantive narrative assertions; no implication of independent verification
- [Production readiness](production-readiness.md) — required checks and unresolved release gates
- [Deployment security checklist](security-deployment.md) — operational risks, prior credential exposure, and manual remediation responsibilities

## Complete root-file inspection

- [Root-level review and outstanding issues](audits/root-review-findings.md) — 110 tracked entries, evidence boundaries, source-level defects, and release blockers
- [Root-by-root evidence register](audits/root-file-review.csv) — exact filenames, Git blob revisions, observed roles and inspection scope
- [Root review freshness checker](../scripts/check_root_review.py) — CI rejects undocumented changes to root-level tracked files

## Verified-source extension engineering

- [Extension activation contract](extension-activation-contract.md) — manifest commands, tree views, and offline activation checks
- [Debugger execution contract](debugger-execution-contract.md) — failure behavior, real execution evidence, and unsupported debugger capabilities
- [NBOS client response validation](nbos-client-protocol-validation.md) — transport acknowledgements versus completed work
- [Read-only NBOS protocol reference](nbos-readonly-reference.md) — opt-in real HTTP adapter, finite pure commands and positive Axios/Uvicorn tests; no full NBCL engine
- [Bounded NBCL subset grammar and program tests](nbcl-bounded-execution.md) — exact integer arithmetic, 16-step limit, reject-before-evaluation contract, real cross-runtime evidence
- [Language asset boundaries](vscode-extension-language-assets.md) — provisional ReflexælLang / LoN grammar support
- [VS Code webview security](vscode-webview-security.md) — tested text escaping and webview script restrictions
- [VSIX candidate packaging](vscode-candidate-packaging.md) — allowlisted bundle, artifact checksums, and no-publish boundary

## API and telemetry

- [Pinned LRS-Agents import and runtime review](audits/lrs-submodule-runtime-compatibility.md) — exact Gitlink source evidence, startup side-effect isolation and adapter blockers

- [Current FastAPI API reference](API_REFERENCE.md) — exact route list, local Bearer boundary, honest 503/400/501 failure behavior
- [Factual quick start](../README_SIMPLE.md) — extension/test and isolated gateway development instructions; no Replit deployment promise
- [Gateway/NBOS route compatibility and Uvicorn smoke](gateway-nbos-boundary.md) — real loopback negative gateway test, alongside the separate positive read-only protocol reference
- [Gateway pinned dependencies and ASGI authentication](../gateway/README.md) — actual request-level integration tests, local Bearer guard, and remaining live-backend limitations

- [Multi-agent workflow status](multi-agent-workflow-status.md) — route does **not** execute tasks
- [Compose security baseline](compose-security-baseline.md) — local development configuration checks, remaining privileged-container and image-pinning issues
- [Source API gateway](../main.py) — FastAPI route declarations; not an independently verified authenticated service

## Automated checks

- [Production gates](../.github/workflows/production-gates.yml) — TypeScript compilation/lint/offline regression, Python contract checks, Compose policy checks
- [VSIX candidate workflow](../.github/workflows/vscode-vsix-candidate.yml) — creates a checked development artifact, not a Marketplace release
- [README claim verifier](../scripts/check_readme_contract.py) — keeps links, route count, and supported claims consistent with tracked source

### Limitations

Historical descriptions of coverage percentages, test counts, working SDKs, AI capabilities, peer-reviewed results, certification, third-party service availability, and product performance have **not** been accepted as current facts without corresponding evidence. Nested experimental projects can have their own instructions; their existence does not demonstrate that they pass end-to-end tests.

For a missing or inaccurate source claim, file a reproducible [GitHub issue](https://github.com/NeuralBlitz/LRS-NeuralBlitz/issues) and include the exact source, expected behavior, test, dependency version, and observed result.
