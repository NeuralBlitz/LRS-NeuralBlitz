import * as vscode from 'vscode';

/** Read-only local introspection panel; no backend state is fabricated. */
export class IntrospectPanel {
    static createOrShow(extensionUri: vscode.Uri): void {
        const panel = vscode.window.createWebviewPanel(
            'neuralblitzIntrospect',
            'NeuralBlitz Introspection',
            vscode.ViewColumn.One,
            { enableScripts: false, localResourceRoots: [extensionUri] }
        );
        panel.webview.html = `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body>
<h1>NeuralBlitz Introspection</h1>
<p>No live backend telemetry has been loaded.</p>
<p>Connect to a supported backend before treating runtime or attestation data as verified.</p>
</body>
</html>`;
    }
}
