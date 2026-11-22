# Gitlink provenance and repair — 2026-11-22

**Repository:** `NeuralBlitz/LRS-NeuralBlitz` only. The root Git index contains four `160000` Gitlinks. Before this repair, `.gitmodules` declared only `lrs_agents`, leaving three nested links without a URL and causing GitHub checkout cleanup to report `fatal: No url found for submodule path ...`.

## Verified upstream identifiers and pinned commits

Each GitHub **repository metadata endpoint** and the matching **exact commit endpoint** was checked on November 22, 2026. The following values refer to the *existing Gitlink SHAs*; **none were advanced or replaced**.

| Gitlink path in this repository | Verified upstream | Existing pinned commit SHA |
| --- | --- | --- |
| `lrs_agents` | [NeuralBlitz/lrs-agents](https://github.com/NeuralBlitz/lrs-agents) | `52ae62ed1f83ba1a798c3235287d5ee46d3bbc76` |
| `neuralblitz-v50/Advanced-Research/Advanced-Research` | [NeuralBlitz/Advanced-Research](https://github.com/NeuralBlitz/Advanced-Research) | `4d759671403852088f84ed2b183db28436fc3f9e` |
| `neuralblitz-v50/ComputationalAxioms/ComputationalAxioms` | [NeuralBlitz/ComputationalAxioms](https://github.com/NeuralBlitz/ComputationalAxioms) | `672b71038d3cda4640e0746d5be01329b0e076ea` |
| `neuralblitz-v50/Emergent-Prompt-Architecture/Emergent-Prompt-Architecture` | [NeuralBlitz/Emergent-Prompt-Architecture](https://github.com/NeuralBlitz/Emergent-Prompt-Architecture) | `994a0d12014722301b16f8e5d2be5f0f7bfb2494` |

## Exact remediation

- Added the three missing URL/path declarations to root [`.gitmodules`](../../.gitmodules), retaining the existing `lrs_agents` declaration.
- Created [`scripts/check_submodule_integrity.py`](../../scripts/check_submodule_integrity.py). It compares *every Git-index gitlink* with `.gitmodules`, disallows duplicate, missing, stale, malicious or unapproved Gitlink mappings, checks pinned Git SHA formatting, and requires the four explicitly verified upstream HTTPS URLs.
- Added mutation-focused [regression tests](../../tests/test_submodule_integrity.py) and a required [repository-audit CI gate](../../.github/workflows/repository-audit.yml).

To run static checks from the root checkout:

```sh
python3 scripts/check_submodule_integrity.py
python3 -m unittest discover -s tests -p 'test_submodule_integrity.py' -v
```

## What this does **not** verify

The Gitlink revisions now have real, verified upstream identities, but CI does **not** clone or execute them. The root repository's audited checkout remains intentionally shallow with respect to Gitlinks. Exact commit existence is evidenced by the date-stamped manual API verification above, not a fresh network request on every run. Upstream history, files, licensing, security, build compatibility, secret exposure and runtime integration have **not** been certified. In particular, linking `lrs_agents` does not establish that a working NBOS backend or an `/execute` API exists.

**Next safe release gate:** review each approved dependency's license, environment, code and tested interface before enabling recursive initialization in CI. Do not auto-execute third-party submodule setup as a workaround for a previous missing path declaration. No other repository was modified as part of this repair.
