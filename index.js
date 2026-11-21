/**
 * NeuralBlitz root metadata module, not a web server or VS Code entry point.
 * The actual extension is built from src/extension.ts.
 * This file must not silently pass a Replit run/deploy smoke test.
 */
const metadata = Object.freeze({
    version: '50.0.0',
    name: 'NeuralBlitz',
    architecture: 'Omega Singularity',
    status: 'research-prototype',
});

module.exports = metadata;

if (require.main === module) {
    console.error(
        'LRS-NeuralBlitz is not a deployable root Node/HTTP application. ' +
        'This entry point exports metadata only. ' +
        'For the tested VS Code extension, see README.md and ' +
        'docs/vscode-candidate-packaging.md. ' +
        'For the experimental Python gateway, see docs/production-readiness.md.'
    );
    process.exitCode = 1;
}
