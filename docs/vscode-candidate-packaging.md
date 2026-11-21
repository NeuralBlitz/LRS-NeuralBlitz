# VSIX release candidate pipeline (pre-production)

This repository contains many unrelated research and experimental files.
**Never package the repository root directly** for Marketplace distribution.

The workflow `.github/workflows/vscode-vsix-candidate.yml` implements a
source-checked, allowlisted release-candidate pipeline:

1. Compile, lint, and test the TypeScript extension with locked Bun dependencies.
2. Create a staging directory **outside the checkout** containing only
   `package.json`, a curated candidate `README.md`, `LICENSE`,
   `generated-icon.png`, and language/snippet assets.
3. Produce a **self-contained Node-target CommonJS bundle** from the real
   `src/extension.ts` entry point using Bun. The VS Code `vscode` host module
   remains external; all other runtime modules must be bundled.
4. Create a VSIX using pinned `@vscode/vsce@4.1.1` in **pre-release** mode.
   Dependencies are deliberately disabled during packaging because the
   staging manifest references the bundled runtime. No `vscode:prepublish`
   hook runs from the staging manifest.
5. Validate the resulting ZIP/VSIX contents against a strict allowlist,
   assert the main entry and contributed language/view assets exist, and
   produce a SHA-256 checksum.
6. Retain the candidate as a GitHub Actions artifact for 14 days.
   **No Marketplace publication, GitHub Release, production deployment, or
   automatic installation occurs.**

The staging script is `scripts/vscode_candidate.py`, with independent
Python tests in `tests/test_vscode_candidate.py`.

## Inspection and trial installation

Download the GitHub Actions artifact for the approved commit. Verify the
`SHA256SUMS.txt` hash before installation. Review the package metadata and
included files. In an isolated test VS Code instance, use **Extensions:
Install from VSIX** and exercise activation, language modes, command palette,
tree views, and debugger failure cases.

## Known limits

- CI packaging is **not** a real Extension Host or authenticated backend test.
- This is a candidate produced from a commit, not a product release; the source
  manifest version alone is not evidence of readiness.
- The bundler and VSCE toolchain versions, provenance and supply-chain
  validation should undergo an additional release review.
- Runtime privacy/security and VS Code compatibility remain subject to a
  staging test before user distribution.
- Do not publish a candidate merely because the archive passes the allowlist
  and compilation checks.

Official packaging reference:
https://code.visualstudio.com/api/working-with-extensions/publishing-extension
