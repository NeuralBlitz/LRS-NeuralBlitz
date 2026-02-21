import * as vscode from 'vscode';

export class NBCLDocumentSymbolProvider implements vscode.DocumentSymbolProvider {
    provideDocumentSymbols(
        document: vscode.TextDocument,
        token: vscode.CancellationToken
    ): vscode.SymbolInformation[] | vscode.DocumentSymbol[] {
        const symbols: vscode.DocumentSymbol[] = [];
        const text = document.getText();
        const lines = text.split('\n');

        // Track scope hierarchy
        const rootSymbol = new vscode.DocumentSymbol(
            document.fileName,
            'NBCL Document',
            vscode.SymbolKind.File,
            new vscode.Range(0, 0, document.lineCount - 1, lines[lines.length - 1].length),
            new vscode.Range(0, 0, 0, 0)
        );
        symbols.push(rootSymbol);

        // Sections for different command types
        const systemSection = new vscode.DocumentSymbol(
            'System Commands',
            'Boot, status, and system operations',
            vscode.SymbolKind.Namespace,
            new vscode.Range(0, 0, 0, 0),
            new vscode.Range(0, 0, 0, 0)
        );

        const ethicsSection = new vscode.DocumentSymbol(
            'Ethics & Governance',
            'Charter, Judex, and SentiaGuard commands',
            vscode.SymbolKind.Namespace,
            new vscode.Range(0, 0, 0, 0),
            new vscode.Range(0, 0, 0, 0)
        );

        const drsSection = new vscode.DocumentSymbol(
            'DRS Operations',
            'Dynamic Representational Substrate commands',
            vscode.SymbolKind.Namespace,
            new vscode.Range(0, 0, 0, 0),
            new vscode.Range(0, 0, 0, 0)
        );

        const frontierSection = new vscode.DocumentSymbol(
            'Frontier Systems',
            'OQT-BOS, AQM-R, QEC-CK commands',
            vscode.SymbolKind.Namespace,
            new vscode.Range(0, 0, 0, 0),
            new vscode.Range(0, 0, 0, 0)
        );

        const ckSection = new vscode.DocumentSymbol(
            'CK Invocations',
            'Capability Kernel applications',
            vscode.SymbolKind.Namespace,
            new vscode.Range(0, 0, 0, 0),
            new vscode.Range(0, 0, 0, 0)
        );

        lines.forEach((line, index) => {
            const trimmed = line.trim();
            
            // Skip comments and empty lines
            if (!trimmed || trimmed.startsWith('#')) return;

            // Parse commands
            const commandMatch = trimmed.match(/^\/(\w+(?:\.\w+)?)/);
            if (commandMatch) {
                const command = commandMatch[1];
                const range = new vscode.Range(index, 0, index, line.length);
                const selectionRange = new vscode.Range(index, 0, index, command.length + 1);

                const symbol = new vscode.DocumentSymbol(
                    command,
                    this.getCommandDescription(command),
                    vscode.SymbolKind.Function,
                    range,
                    selectionRange
                );

                // Categorize commands
                if (this.isSystemCommand(command)) {
                    systemSection.children.push(symbol);
                } else if (this.isEthicsCommand(command)) {
                    ethicsSection.children.push(symbol);
                } else if (this.isDRSCommand(command)) {
                    drsSection.children.push(symbol);
                } else if (this.isFrontierCommand(command)) {
                    frontierSection.children.push(symbol);
                } else if (command === 'apply') {
                    ckSection.children.push(symbol);
                }
            }

            // Parse CK invocations
            const ckMatch = trimmed.match(/\/apply\s+([A-Za-z]+)\/([A-Za-z0-9_]+)/);
            if (ckMatch) {
                const family = ckMatch[1];
                const name = ckMatch[2];
                const range = new vscode.Range(index, 0, index, line.length);
                const selectionRange = new vscode.Range(
                    index,
                    trimmed.indexOf(ckMatch[0]),
                    index,
                    trimmed.indexOf(ckMatch[0]) + ckMatch[0].length
                );

                const symbol = new vscode.DocumentSymbol(
                    `${family}/${name}`,
                    'Capability Kernel invocation',
                    vscode.SymbolKind.Method,
                    range,
                    selectionRange
                );
                ckSection.children.push(symbol);
            }
        });

        // Add non-empty sections to root
        [systemSection, ethicsSection, drsSection, frontierSection, ckSection].forEach(section => {
            if (section.children.length > 0) {
                // Update section range to encompass all children
                const firstChild = section.children[0];
                const lastChild = section.children[section.children.length - 1];
                section.range = new vscode.Range(
                    firstChild.range.start,
                    lastChild.range.end
                );
                rootSymbol.children.push(section);
            }
        });

        return symbols;
    }

    private getCommandDescription(command: string): string {
        const descriptions: Record<string, string> = {
            'boot': 'Initialize NeuralBlitz OS',
            'nbos': 'Global NBOS commands',
            'status': 'Display system status',
            'verify': 'Trigger Veritas proofs',
            'export': 'Externalize artifacts',
            'charter.shade': 'Apply ethic shade policy',
            'judex.review': 'Submit for quorum adjudication',
            'sentia.scan': 'Trigger risk assessment',
            'correct_drift': 'Correct ethical drift',
            'lock_ethics': 'Freeze ethical parameters',
            'drift_field': 'Evolve DRS-F states',
            'entangle': 'Create semantic bindings',
            'collapse_trace': 'Freeze DRS for forensics',
            'ignite': 'Activate frontier systems',
            'psi': 'Run simulation',
            'apply': 'Invoke Capability Kernel'
        };
        return descriptions[command] || 'NeuralBlitz command';
    }

    private isSystemCommand(command: string): boolean {
        return ['boot', 'nbos', 'status', 'verify', 'export'].includes(command);
    }

    private isEthicsCommand(command: string): boolean {
        return ['charter.shade', 'charter.enforce', 'judex.review', 
                'sentia.scan', 'correct_drift', 'lock_ethics'].includes(command);
    }

    private isDRSCommand(command: string): boolean {
        return ['manifest_drs_field', 'drift_field', 'entangle', 
                'collapse_trace', 'merge', 'fork', 'query_drs'].includes(command);
    }

    private isFrontierCommand(command: string): boolean {
        return ['ignite', 'glyphnet.compile', 'qec.set', 'aqm.recursion.fold', 'psi'].includes(command);
    }
}