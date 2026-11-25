import * as vscode from 'vscode';
import { NBOSClient, NBOS_TOKEN_SECRET_KEY } from '../util/nbosClient';
import { CKRegistry, CKInfo } from '../util/ckRegistry';
import * as fs from 'fs';
import * as path from 'path';

function escapeHtml(value: unknown): string {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/** Never display arbitrary backend exception text or returned error strings in UI. */
function safeNbclExecutionError(error: unknown): string {
    const record = error && typeof error === 'object'
        ? error as { message?: unknown; response?: { status?: unknown } }
        : null;
    const status = record?.response?.status;
    if (status === 401 || status === 403) {
        return 'NBCL execution authentication or authorization failed; check the stored token.';
    }
    if (status === 422) {
        return 'NBCL request rejected by the backend (HTTP 422); details withheld.';
    }
    if (typeof status === 'number' && Number.isSafeInteger(status) &&
        status >= 400 && status <= 599) {
        return 'NBCL backend request failed (HTTP ' + status + '); details withheld.';
    }
    const message = typeof record?.message === 'string' ? record.message : '';
    if (message.startsWith('NBOS endpoint is not configured') ||
        message.startsWith('Set neuralblitz.nbosEndpoint in User settings')) {
        return 'Set neuralblitz.nbosEndpoint in VS Code User settings to a verified NBOS server.';
    }
    if (message.startsWith('NBOS backend is not compatible') ||
        message.startsWith('NBOS backend does not advertise')) {
        return 'The configured NBOS backend does not support this operation.';
    }
    return 'NBCL execution request failed; raw backend details withheld.';
}

export class NBCLCommands {
    private outputChannel: vscode.OutputChannel;
    private statusBarItem: vscode.StatusBarItem;

    constructor(
        private nbosClient: NBOSClient,
        private ckRegistry: CKRegistry,
        private secrets: vscode.SecretStorage
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
        // Release extension-owned UI resources on deactivation.
        const disposables: vscode.Disposable[] = [
            this.outputChannel,
            this.statusBarItem
        ];

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

        // Debug commands forward to VS Code's native debug controls. These
        // controls must not accidentally act on another extension's session.
        disposables.push(
            vscode.commands.registerCommand('neuralblitz.debug.start', () => this.startDebug())
        );
        disposables.push(
            vscode.commands.registerCommand('neuralblitz.debug.step', () => this.debugControl('workbench.action.debug.stepInto'))
        );
        disposables.push(
            vscode.commands.registerCommand('neuralblitz.debug.continue', () => this.debugControl('workbench.action.debug.continue'))
        );

        disposables.push(
            vscode.commands.registerCommand(
                'neuralblitz.credentials.set', () => this.setBearerToken()
            )
        );
        disposables.push(
            vscode.commands.registerCommand(
                'neuralblitz.credentials.clear', () => this.clearBearerToken()
            )
        );

        return disposables;
    }

    private async setBearerToken(): Promise<void> {
        const token = await vscode.window.showInputBox({
            prompt: 'NBOS bearer token (saved in VS Code SecretStorage)',
            password: true,
            ignoreFocusOut: true
        });
        if (token === undefined) return; // Cancelled, preserve existing secret.
        if (!token.trim() || token.includes(String.fromCharCode(10)) ||
            token.includes(String.fromCharCode(13))) {
            vscode.window.showWarningMessage('Provide a non-empty single-line NBOS token');
            return;
        }
        try {
            await this.secrets.store(NBOS_TOKEN_SECRET_KEY, token);
            vscode.window.showInformationMessage('NBOS token saved in VS Code SecretStorage');
        } catch {
            vscode.window.showErrorMessage('Unable to save the NBOS token securely');
        }
    }

    private async clearBearerToken(): Promise<void> {
        try {
            await this.secrets.delete(NBOS_TOKEN_SECRET_KEY);
            vscode.window.showInformationMessage('NBOS token cleared from SecretStorage');
        } catch {
            vscode.window.showErrorMessage('Unable to clear the stored NBOS token');
        }
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
            this.statusBarItem.text = '$(symbol-interface) NBOS: Disconnected';
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

        // Full/multiline documents use explicit source mode; a single
        // command keeps the established command-mode contract. Never send a
        // local file path to a command-only source service.
        const isSource = /[\r\n]/.test(text) || text.trimStart().startsWith('#');
        try {
            this.outputChannel.appendLine(
                isSource ? 'Executing bounded NBCL source...' : 'Executing NBCL command...'
            );
            // Neither submitted text nor an untrusted backend response/error
            // may be copied to the long-lived extension output channel.
            this.outputChannel.appendLine('Submitted source and backend details omitted');

            const result = isSource
                ? await this.nbosClient.executeSource(text)
                : await this.nbosClient.executeCommand(text);
            if (result.ok === false) {
                this.outputChannel.appendLine('Execution refused (response details redacted)');
                vscode.window.showErrorMessage(
                    'NBCL operation refused by backend; response details withheld.'
                );
            } else if (result.completed === true && result.stopped !== true) {
                const count = isSource && Number.isSafeInteger(result.instruction_count) &&
                    typeof result.instruction_count === 'number' &&
                    result.instruction_count > 0 && result.instruction_count <= 16
                    ? result.instruction_count : undefined;
                this.outputChannel.appendLine(
                    count === undefined
                        ? 'Execution completion confirmed; backend result not logged'
                        : 'Source completed (' + count + ' steps); backend result not logged'
                );
                vscode.window.showInformationMessage(
                    isSource ? 'NBCL subset program completed' : 'Command execution completed'
                );
            } else if (result.stopped === true && result.completed !== true &&
                Number.isSafeInteger(result.line) && typeof result.line === 'number' &&
                result.line > 0) {
                this.outputChannel.appendLine('Execution paused; backend result not logged');
                vscode.window.showWarningMessage(
                    'Command stopped at line ' + result.line + '; execution is not complete'
                );
            } else {
                this.outputChannel.appendLine('Execution result unconfirmed');
                vscode.window.showErrorMessage('NBOS did not confirm command completion');
            }
        } catch (error) {
            this.outputChannel.appendLine('Execution request failed; details redacted');
            vscode.window.showErrorMessage(safeNbclExecutionError(error));
        }
    }

    private async showStatus(): Promise<void> {
        try {
            const status = await this.nbosClient.getStatus();
            
            const panel = vscode.window.createWebviewPanel(
                'neuralblitzStatus',
                'NeuralBlitz Status',
                vscode.ViewColumn.One,
                { enableScripts: false }
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
                { enableScripts: false }
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
            { enableScripts: false }
        );

        panel.webview.html = this.getCKHtml(ck);
    }

    private async debugControl(action: string): Promise<void> {
        if (vscode.debug.activeDebugSession?.type !== 'neuralblitz') {
            vscode.window.showWarningMessage('Start a NeuralBlitz debug session before using this command');
            return;
        }
        await vscode.commands.executeCommand(action);
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
                <meta charset="UTF-8">
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">
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
                    <h3>${escapeHtml(status?.system_status ?? 'Unknown')}</h3>
                </div>
                <h2>Governance Core</h2>
                <div class="metric">
                    <span>Charter Status:</span>
                    <span>${escapeHtml(status?.governance_core?.charter_status ?? 'Unknown')}</span>
                </div>
                <div class="metric">
                    <span>VPCE Score:</span>
                    <span>${escapeHtml(status?.governance_core?.veritas_vpce?.score ?? 'Unavailable')}</span>
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
                <meta charset="UTF-8">
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">
                <style>
                    body { font-family: var(--vscode-font-family); padding: 20px; }
                    pre { background: var(--vscode-textBlockQuote-background); padding: 10px; overflow: auto; }
                </style>
            </head>
            <body>
                <h1>Introspection Bundle</h1>
                <pre>${escapeHtml(JSON.stringify(result, null, 2) ?? 'Unavailable')}</pre>
            </body>
            </html>
        `;
    }

    private getCKHtml(ck: CKInfo): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">
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
                <h1>${escapeHtml(ck.family)}/${escapeHtml(ck.name)}</h1>
                <p><strong>Version:</strong> ${escapeHtml(ck.version)}</p>
                <p><strong>Intent:</strong> ${escapeHtml(ck.intent)}</p>
                
                <div class="section">
                    <h2>Inputs</h2>
                    <table>
                        <tr><th>Name</th><th>Type</th></tr>
                        ${Object.entries(ck.inputs).map(([k, v]) => 
                            `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`
                        ).join('')}
                    </table>
                </div>

                <div class="section">
                    <h2>Outputs</h2>
                    <table>
                        <tr><th>Name</th><th>Type</th></tr>
                        ${Object.entries(ck.outputs).map(([k, v]) => 
                            `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`
                        ).join('')}
                    </table>
                </div>

                <div class="section">
                    <h2>Risk Factors</h2>
                    <ul>
                        ${ck.riskFactors.map(r => `<li class="risk">⚠️ ${escapeHtml(r)}</li>`).join('')}
                    </ul>
                </div>

                <div class="section">
                    <h2>Veritas Invariants</h2>
                    <ul>
                        ${ck.veritasInvariants.map(i => `<li class="invariant">✅ ${escapeHtml(i)}</li>`).join('')}
                    </ul>
                </div>
            </body>
            </html>
        `;
    }
}