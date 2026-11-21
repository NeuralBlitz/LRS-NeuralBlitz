# Contributing to LRS-NeuralBlitz

Contributions are welcome, but this repository is **pre-production** and includes a mixture of supported extension code, experimental services, research, historical documents and generated artifacts. A pull request should specify exactly which component it changes and what evidence supports its behavior.

## Local extension development

```sh
git clone https://github.com/NeuralBlitz/LRS-NeuralBlitz.git
cd LRS-NeuralBlitz
bun install --frozen-lockfile
bun run compile
bun run lint
bun run test
```

These checks exercise the root VS Code extension and offline mocks, not every nested project. Do not assume a successful extension test certifies a research, cloud or hardware component.

## Documentation and repository static checks

```sh
python3 scripts/check_readme_contract.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/audit_repository_tree.py --out audit-output
```

The full-tree scanner reads tracked blobs and creates a path-by-path CSV plus JSON summary. It does not execute untrusted scripts or recursively read external gitlinks. Review flagged issues and document findings; the presence of a class, snippet or successful static parse is not a functional test.

Docker Compose security validation requires Docker Compose installed and uses test-only environment values:

```sh
python3 scripts/check_compose_security.py
```

## Pull request expectations

1. Name the exact files and feature surface changed, with an issue or reproducible failure.
2. Include the intended behavior, compatibility assumptions and a negative/error-path test.
3. Keep new dependencies, external accounts and network capabilities explicit. Do not commit secrets, tokens, private user data, virtual environments, database dumps, generated coverage output or artifacts by default.
4. If changing a README or research claim, distinguish *hypothesis*, *design*, *source existence*, *tested prototype*, *integration*, *benchmark*, and *production validation*. Link exact evidence.
5. If updating a reported speed, throughput or coverage figure, include scripts, datasets, machine/runner details, commit SHA, trial counts and variability. Avoid zero-time or security guarantees without qualifying proof.
6. Run all relevant tests and link the successful CI checks. Do not bypass red tests or claim successful integration based solely on mocks.
7. Do not alter gitlinks or remove historical research/binary content without confirming provenance and dependency ownership.

## Security and responsible disclosure

Please follow [SECURITY.md](SECURITY.md) to report vulnerabilities privately. Do not put credentials or exploit details into public issues or logs. Operational credential rotation and branch protection require maintainers with the appropriate access.

## Current priorities

See [production readiness](docs/production-readiness.md), the [README evidence audit](docs/readme-claim-audit.md), and the [repository-wide inspection](docs/audits/repository-wide-inspection.md). Current product status and commands are documented in the [root README](README.md).
