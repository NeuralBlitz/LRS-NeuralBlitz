import * as vscode from 'vscode';
import { NBOSClient } from '../util/nbosClient';
import { CKRegistry, CKInfo } from '../util/ckRegistry';
import * as fs from 'fs';
import * as path from 'path';

export class NBCLCommands {
    private outputChannel: vscode.OutputChannel;
    private statusBarItem: vscode.StatusBarItem;

    constructor(
        private nbosClient: NBOSClient,
        private ckRegistry: CKRegistry
    ) {
        this.outputChannel = vscode.window.createOutputChannel('NeuralBlitz');
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            100
        );
        this.statusBarItem.text = '$(symbol-interface) NBOS: Disconnected';
        this.statusBarItem.command = 'neuralblitz.status';
        this.statusBarItem.show();
    }

    register(context: vscode.ExtensionContext): vscode.Disposable[] {
        const disposables: vscode.Disposable[] = [];

        // Boot command
        disposables.push(
            vscode.commands.registerCommand('neuralblitz.boot', () => this.boot())
        );

        // Execute command
        disposables.push(
            vscode.commands.registerCommand('neuralblitz.execute', () => this.execute())
        );

        // Status command
        disposables.push(
            vscode.commands.registerCommand('neuralblitz.status', () => this.showStatus())
        );

        // Introspect command
        disposables.push(
            vscode.commands.registerCommand('neuralblitz.introspect', () => this.introspect())
        );

        // CK Search command
        disposables.push(
            vscode.commands.registerCommand('neuralblitz.ck.search', () => this.searchCKs())
        );

        // CK Documentation command
        disposables.push(
            vscode.commands.registerCommand('neuralblitz.ck.documentation', () => this.showCKDocumentation())
        );

        // Debug start command
        disposables.push(
            vscode.commands.registerCommand('neuralblitz.debug.start', () => this.startDebug())
        );

        return disposables;
    }

    private async boot(): Promise<void> {
        const mode = await vscode.window.showQuickPick(
            ['Sentio', 'Dynamo', 'Hybrid'],
            { placeHolder: 'Select cognitive mode' }
        );

        if (!mode) return;

        const trace = await vscode.window.showQuickPick(
            ['Yes', 'No'],
            { placeHolder: 'Enable full tracing?' }
        );

        try {
            this.outputChannel.appendLine(`Booting NeuralBlitz in ${mode} mode...`);
            await this.nbosClient.boot({
                mode: mode as 'Sentio' | 'Dynamo' | 'Hybrid',
                trace: trace === 'Yes'
            });

            this.statusBarItem.text = `$(symbol-interface) NBOS: ${mode}`;
            this.outputChannel.appendLine('Boot successful!');
            vscode.window.showInformationMessage('NeuralBlitz booted successfully');
        } catch (error) {
            vscode.window.showErrorMessage(`Boot failed: ${error}`);
        }
    }

    private async execute(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== 'nbcl') {
            vscode.window.showWarningMessage('Please open an NBCL file first');
            return;
        }

        const selection = editor.selection;
        const text = selection.isEmpty
            ? editor.document.getText()
            : editor.document.getText(selection);

        try {
            this.outputChannel.appendLine('Executing NBCL command...');
            this.outputChannel.appendLine(text);
            this.outputChannel.appendLine('---');

            const result = await this.nbosClient.executeCommand(text);
            
            this.outputChannel.appendLine(JSON.stringify(result, null, 2));
            
            if (result.ok) {
                vscode.window.showInformationMessage('Command executed successfully');
            } else {
                vscode.window.showErrorMessage(`Execution failed: ${result.error?.message}`);
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Execution error: ${error}`);
        }
    }

    private async showStatus(): Promise<void> {
        try {
            const status = await this.nbosClient.getStatus();
            
            const panel = vscode.window.createWebviewPanel(
                'neuralblitzStatus',
                'NeuralBlitz Status',
                vscode.ViewColumn.One,
                { enableScripts: true }
            );

            panel.webview.html = this.getStatusHtml(status);
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to get status: ${error}`);
        }
    }

    private async introspect(): Promise<void> {
        const scope = await vscode.window.showQuickPick(
            ['system', 'drs', 'governance', 'frontier'],
            { placeHolder: 'Select introspection scope' }
        );

        if (!scope) return;

        try {
            const result = await this.nbosClient.introspect(scope);
            
            const panel = vscode.window.createWebviewPanel(
                'neuralblitzIntrospect',
                `Introspect: ${scope}`,
                vscode.ViewColumn.One,
                { enableScripts: true }
            );

            panel.webview.html = this.getIntrospectHtml(result);
        } catch (error) {
            vscode.window.showErrorMessage(`Introspection failed: ${error}`);
        }
    }

    private async searchCKs(): Promise<void> {
        const query = await vscode.window.showInputBox({
            prompt: 'Search Capability Kernels',
            placeHolder: 'e.g., causal, ethics, wisdom'
        });

        if (!query) return;

        const results = await this.ckRegistry.search(query);
        
        if (results.length === 0) {
            vscode.window.showInformationMessage('No CKs found matching your query');
            return;
        }

        const items = results.map(ck => ({
            label: `${ck.family}/${ck.name}`,
            description: ck.intent,
            detail: `v${ck.version}`,
            ck: ck
        }));

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: `Found ${results.length} CKs`
        });

        if (selected) {
            this.showCKDetails(selected.ck);
        }
    }

    private async showCKDocumentation(): Promise<void> {
        const family = await vscode.window.showQuickPick(
            await this.ckRegistry.getFamilies(),
            { placeHolder: 'Select CK family' }
        );

        if (!family) return;

        const cks = await this.ckRegistry.getCKsInFamily(family);
        
        const items = cks.map(ck => ({
            label: ck.name,
            description: ck.intent,
            ck: ck
        }));

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: `Select a ${family} CK`
        });

        if (selected) {
            this.showCKDetails(selected.ck);
        }
    }

    private showCKDetails(ck: CKInfo): void {
        const panel = vscode.window.createWebviewPanel(
            'neuralblitzCK',
            `${ck.family}/${ck.name}`,
            vscode.ViewColumn.One,
            { enableScripts: true }
        );

        panel.webview.html = this.getCKHtml(ck);
    }

    private startDebug(): void {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('Please open a file to debug');
            return;
        }

        vscode.debug.startDebugging(undefined, {
            type: 'neuralblitz',
            name: 'Debug NeuralBlitz',
            request: 'launch',
            program: editor.document.uri.fsPath,
            mode: 'Sentio',
            trace: true
        });
    }

    private getStatusHtml(status: any): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: var(--vscode-font-family); padding: 20px; }
                    .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
                    .ok { background: var(--vscode-testing-iconPassed); }
                    .warning { background: var(--vscode-testing-iconQueued); }
                    .metric { display: flex; justify-content: space-between; margin: 5px 0; }
                </style>
            </head>
            <body>
                <h1>NeuralBlitz System Status</h1>
                <div class="status ok">
                    <h3>${status.system_status || 'Unknown'}</h3>
                </div>
                <h2>Governance Core</h2>
                <div class="metric">
                    <span>Charter Status:</span>
                    <span>${status.governance_core?.charter_status || 'Unknown'}</span>
                </div>
                <div class="metric">
                    <span>VPCE Score:</span>
                    <span>${status.governance_core?.veritas_vpce?.score || 0}</span>
                </div>
            </body>
            </html>
        `;
    }

    private getIntrospectHtml(result: any): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: var(--vscode-font-family); padding: 20px; }
                    pre { background: var(--vscode-textBlockQuote-background); padding: 10px; overflow: auto; }
                </style>
            </head>
            <body>
                <h1>Introspection Bundle</h1>
                <pre>${JSON.stringify(result, null, 2)}</pre>
            </body>
            </html>
        `;
    }

    private getCKHtml(ck: CKInfo): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: var(--vscode-font-family); padding: 20px; }
                    h1 { color: var(--vscode-symbolIcon-classForeground); }
                    .section { margin: 20px 0; }
                    .risk { color: var(--vscode-errorForeground); }
                    .invariant { color: var(--vscode-testing-iconPassed); }
                    table { width: 100%; border-collapse: collapse; }
                    th, td { padding: 8px; text-align: left; border-bottom: 1px solid var(--vscode-panel-border); }
                    th { background: var(--vscode-list-hoverBackground); }
                </style>
            </head>
            <body>
                <h1>${ck.family}/${ck.name}</h1>
                <p><strong>Version:</strong> ${ck.version}</p>
                <p><strong>Intent:</strong> ${ck.intent}</p>
                
                <div class="section">
                    <h2>Inputs</h2>
                    <table>
                        <tr><th>Name</th><th>Type</th></tr>
                        ${Object.entries(ck.inputs).map(([k, v]) => 
                            `<tr><td>${k}</td><td>${v}</td></tr>`
                        ).join('')}
                    </table>
                </div>

                <div class="section">
                    <h2>Outputs</h2>
                    <table>
                        <tr><th>Name</th><th>Type</th></tr>
                        ${Object.entries(ck.outputs).map(([k, v]) => 
                            `<tr><td>${k}</td><td>${v}</td></tr>`
                        ).join('')}
                    </table>
                </div>

                <div class="section">
                    <h2>Risk Factors</h2>
                    <ul>
                        ${ck.riskFactors.map(r => `<li class="risk">⚠️ ${r}</li>`).join('')}
                    </ul>
                </div>

                <div class="section">
                    <h2>Veritas Invariants</h2>
                    <ul>
                        ${ck.veritasInvariants.map(i => `<li class="invariant">✅ ${i}</li>`).join('')}
                    </ul>
                </div>
            </body>
            </html>
        `;
    }
}