import * as vscode from 'vscode';

export class NBCLDiagnosticProvider {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private enabled: boolean = true;

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('nbcl');
    }

    activate(context: vscode.ExtensionContext): void {
        context.subscriptions.push(this.diagnosticCollection);

        // Validate all open NBCL documents
        vscode.workspace.textDocuments.forEach(doc => {
            if (doc.languageId === 'nbcl') {
                this.validateDocument(doc.uri);
            }
        });
    }

    validateDocument(uri: vscode.Uri): void {
        if (!this.enabled) return;

        vscode.workspace.openTextDocument(uri).then(document => {
            const diagnostics: vscode.Diagnostic[] = [];
            const text = document.getText();
            const lines = text.split('\n');

            lines.forEach((line, lineIndex) => {
                const lineDiagnostics = this.validateLine(line, lineIndex);
                diagnostics.push(...lineDiagnostics);
            });

            this.diagnosticCollection.set(uri, diagnostics);
        });
    }

    private validateLine(line: string, lineIndex: number): vscode.Diagnostic[] {
        const diagnostics: vscode.Diagnostic[] = [];
        const trimmed = line.trim();

        // Skip comments and empty lines
        if (!trimmed || trimmed.startsWith('#')) return diagnostics;

        // Check for command syntax
        if (trimmed.startsWith('/')) {
            // Validate command structure
            const commandMatch = trimmed.match(/^\/(\w+(?:\.\w+)?)(?:\s+|$)/);
            if (!commandMatch) {
                const range = new vscode.Range(
                    lineIndex,
                    0,
                    lineIndex,
                    line.length
                );
                diagnostics.push(
                    new vscode.Diagnostic(
                        range,
                        'Invalid command syntax',
                        vscode.DiagnosticSeverity.Error
                    )
                );
            }

            // Check for unclosed JSON payloads
            const openBraces = (line.match(/\{/g) || []).length;
            const closeBraces = (line.match(/\}/g) || []).length;
            if (openBraces !== closeBraces) {
                const range = new vscode.Range(
                    lineIndex,
                    line.indexOf('{'),
                    lineIndex,
                    line.length
                );
                diagnostics.push(
                    new vscode.Diagnostic(
                        range,
                        'Unclosed JSON object',
                        vscode.DiagnosticSeverity.Error
                    )
                );
            }

            // Check for unclosed quotes
            const quoteMatches = line.match(/"/g);
            if (quoteMatches && quoteMatches.length % 2 !== 0) {
                const range = new vscode.Range(
                    lineIndex,
                    line.lastIndexOf('"'),
                    lineIndex,
                    line.length
                );
                diagnostics.push(
                    new vscode.Diagnostic(
                        range,
                        'Unclosed string',
                        vscode.DiagnosticSeverity.Error
                    )
                );
            }

            // Check for deprecated commands
            const deprecatedCommands = [
                '/old_boot',
                '/legacy_verify'
            ];
            
            for (const deprecated of deprecatedCommands) {
                if (trimmed.startsWith(deprecated)) {
                    const range = new vscode.Range(
                        lineIndex,
                        line.indexOf(deprecated),
                        lineIndex,
                        line.indexOf(deprecated) + deprecated.length
                    );
                    diagnostics.push(
                        new vscode.Diagnostic(
                            range,
                            `Command ${deprecated} is deprecated. Use /boot instead.`,
                            vscode.DiagnosticSeverity.Warning
                        )
                    );
                }
            }

            // Check for potential security issues
            if (trimmed.includes('judex_quorum=false') && trimmed.includes('teletopo')) {
                const range = new vscode.Range(
                    lineIndex,
                    0,
                    lineIndex,
                    line.length
                );
                diagnostics.push(
                    new vscode.Diagnostic(
                        range,
                        'Security Warning: Teletopological transfers require Judex Quorum approval (ϕ5)',
                        vscode.DiagnosticSeverity.Warning
                    )
                );
            }

            // Validate parameter syntax
            const paramPattern = /--([\w-]+)(?:=(["'][^"']*["']|\S+))?/g;
            let paramMatch;
            while ((paramMatch = paramPattern.exec(line)) !== null) {
                const paramName = paramMatch[1];
                const paramValue = paramMatch[2];

                // Check for deprecated parameters
                if (paramName === 'goldendag' && paramValue !== 'enable') {
                    const range = new vscode.Range(
                        lineIndex,
                        paramMatch.index,
                        lineIndex,
                        paramMatch.index + paramMatch[0].length
                    );
                    diagnostics.push(
                        new vscode.Diagnostic(
                            range,
                            'GoldenDAG must be enabled for Charter compliance',
                            vscode.DiagnosticSeverity.Error
                        )
                    );
                }
            }
        }

        return diagnostics;
    }

    setEnabled(enabled: boolean): void {
        this.enabled = enabled;
        if (!enabled) {
            this.diagnosticCollection.clear();
        }
    }
}