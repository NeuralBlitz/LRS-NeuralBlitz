# NeuralBlitz IDE — VS Code Extension Release Candidate

This VSIX candidate includes the NeuralBlitz VS Code extension's NBCL editor
language support, command and capability-kernel views, and an **optional**
NBOS client/debugger interface.

**Status: pre-production testing.** This candidate is not a verified
production release. Installing it does not install a NeuralBlitz backend.
A compatible authenticated backend is required for booting, execution,
debugging, or live status features, and is not packaged here.

Some syntax highlighting rules for ReflexælLang and LoN are provisional;
the local CK catalog is descriptive metadata, not proof that the associated
operations can execute. Debugger breakpoints and asynchronous events remain
limited pending complete backend integration.

## For test users

Install the candidate through VS Code's **Extensions: Install from VSIX**
command. Configure `neuralblitz.nbosEndpoint` for an independently verified
compatible backend, if one is available. Do not send credentials or sensitive
commands to an unverified endpoint. Test editor activation and language
features separately from backend-dependent functionality.

For verified implementation status, open the repository's
[production-readiness checklist](https://github.com/NeuralBlitz/LRS-NeuralBlitz/blob/main/docs/production-readiness.md).

The archive contains only the bundled extension runtime, its declared
language and view assets, an icon, this README, its manifest, and the
applicable MIT LICENSE. It excludes research notebooks, datasets, CI
configuration, and the telemetry development stack.
