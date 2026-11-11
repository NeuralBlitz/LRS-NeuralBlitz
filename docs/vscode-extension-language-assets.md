# VS Code extension language assets: support boundary

The extension manifest registers NBCL, ReflexælLang, and Language of the Nexus (LoN).

- **NBCL**: the previously tracked TextMate grammar, language configuration, and a small set of baseline command snippets. These snippets issue text only; they do not imply that a backend executed a command.
- **ReflexælLang / LoN**: provisional minimal TextMate grammars that recognize only quoted string forms and ordinary decimal numbers, plus generic bracket/quote editing pairs. They do **not** constitute complete, canonical language specifications, parsers, compilers, type systems, or syntax conformance tests. Their syntax must be replaced or expanded only with creator-approved and source-backed language rules.

The manifest asset check in CI establishes that contributed files are tracked and available after dependency installation and TypeScript compilation. It does not establish language correctness, end-to-end runtime behavior, coverage, or extension integration tests. The repository's `npm test` script still lacks a tracked VS Code test runner.

## Follow-up engineering tasks

1. Obtain source-authoritative ReflexælLang and LoN grammars and validation examples.
2. Add a language-grammar fixture suite for each syntax and configuration.
3. Build an actual VS Code extension integration harness, lint configuration, and release packaging checks.
4. Verify language identifiers, file associations, snippets, completion providers, and user-visible error handling in the Extension Development Host.
