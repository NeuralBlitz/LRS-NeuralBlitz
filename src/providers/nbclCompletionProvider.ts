import * as vscode from 'vscode';

export class NBCLCompletionProvider implements vscode.CompletionItemProvider {
    private readonly commands: Map<string, vscode.CompletionItem> = new Map();
    private readonly parameters: Map<string, vscode.CompletionItem[]> = new Map();
    private readonly flags: vscode.CompletionItem[] = [];

    constructor() {
        this.initializeCommands();
        this.initializeParameters();
        this.initializeFlags();
    }

    private initializeCommands(): void {
        const commandSpecs = [
            // System commands
            { name: '/boot', detail: 'Initialize NBOS', insertText: '/boot --charter=ϕ1..ϕ15 --goldendag=enable --mode=${1|Sentio,Dynamo|} ${2:--trace}' },
            { name: '/nbos', detail: 'Global NBOS commands', insertText: '/nbos ${1|up,down,status,config|}' },
            { name: '/status', detail: 'Display system status', insertText: '/status --scope=${1:all}' },
            { name: '/verify', detail: 'Trigger Veritas proofs', insertText: '/verify --scope=${1:system} --threshold=${2:0.985}' },
            { name: '/export', detail: 'Externalize artifacts', insertText: '/export ${1|codex,drs,logs|} --volume="${2:name}"' },
            
            // DRS commands
            { name: '/manifest_drs_field', detail: 'Initialize DRS-F', insertText: '/manifest_drs_field --schema=${1:schema.drs.json} --nodes=[${2:}]' },
            { name: '/drift_field', detail: 'Evolve DRS-F states', insertText: '/drift_field --eta=${1:0.1} --steps=${2:100} --projection=${3|ethics,standard|}' },
            { name: '/entangle', detail: 'Create semantic bindings', insertText: '/entangle --A=${1:node_A} --B=${2:node_B} --beta=${3:0.5}' },
            { name: '/collapse_trace', detail: 'Freeze DRS for forensics', insertText: '/collapse_trace --reason="${1:forensic}" --policy=${2|standard,strict|}' },
            
            // Ethics commands
            { name: '/charter.shade', detail: 'Apply ethic shade policy', insertText: '/charter.shade --policy=${1|conservative,balanced,exploration|}' },
            { name: '/judex.review', detail: 'Submit for quorum adjudication', insertText: '/judex.review --topic="${1:topic}" --context="${2:context}"' },
            { name: '/sentia.scan', detail: 'Trigger risk assessment', insertText: '/sentia.scan --depth=${1|surface,deep|} --scope=${2:system}' },
            { name: '/correct_drift', detail: 'Correct ethical drift', insertText: '/correct_drift --max-force=${1:false} --max-retries=${2:3}' },
            { name: '/lock_ethics', detail: 'Freeze ethical parameters', insertText: '/lock_ethics --freeze --timeout=${1:300}s' },
            
            // Frontier system commands
            { name: '/ignite', detail: 'Activate frontier systems', insertText: '/ignite ${1|OQT-BOS,AQM-R,QEC-CK|} --braid-lattice=${2:8} --teletopo=${3|blocked,enabled|}' },
            { name: '/psi', detail: 'Run Simulacra simulation', insertText: '/psi simulate ${1|grief,awe,test|}' },
            { name: '/qec.set', detail: 'Configure QEC', insertText: '/qec.set --code=${1|surface,toric,color|} --distance=${2:3}' },
            
            // Apply command for CKs
            { name: '/apply', detail: 'Invoke Capability Kernel', insertText: '/apply ${1|Causa,Ethics,Wisdom,Temporal,Language,Perception,Simulation,OQT,DQPK,DRS,Plan,Gov|}/${2:CK_Name} --payload=\'${3:{}}\'' }
        ];

        for (const spec of commandSpecs) {
            const item = new vscode.CompletionItem(
                spec.name,
                vscode.CompletionItemKind.Keyword
            );
            item.detail = spec.detail;
            item.insertText = new vscode.SnippetString(spec.insertText);
            item.documentation = new vscode.MarkdownString(`**${spec.name}**\n\n${spec.detail}`);
            this.commands.set(spec.name, item);
        }
    }

    private initializeParameters(): void {
        // Parameters for specific commands
        this.parameters.set('/boot', [
            this.createParam('--charter', 'Load Charter clauses', 'ϕ1..ϕ15'),
            this.createParam('--goldendag', 'Enable GoldenDAG', 'enable'),
            this.createParam('--mode', 'Cognitive mode', 'Sentio|Dynamo'),
            this.createParam('--trace', 'Enable full tracing', ''),
            this.createParam('--strict', 'Hardened governance', '')
        ]);

        this.parameters.set('/apply', [
            this.createParam('--payload', 'JSON payload', '{"key": "value"}'),
            this.createParam('--charter-lock', 'Require Charter approval', ''),
            this.createParam('--trace', 'Attach trace ID', '')
        ]);

        this.parameters.set('/drift_field', [
            this.createParam('--eta', 'Propagation rate', '0.1'),
            this.createParam('--steps', 'Number of steps', '100'),
            this.createParam('--projection', 'Projection type', 'ethics')
        ]);
    }

    private initializeFlags(): void {
        const flagSpecs = [
            { name: '--charter-lock', detail: 'Require Charter approval for privileged operations' },
            { name: '--goldendag-enable', detail: 'Enable GoldenDAG sealing' },
            { name: '--trace', detail: 'Enable execution tracing' },
            { name: '--strict', detail: 'Enable strict mode (VPCE >= 0.985)' },
            { name: '--dry-run', detail: 'Simulate execution without side effects' },
            { name: '--max-force', detail: 'Apply maximum correction force' }
        ];

        for (const spec of flagSpecs) {
            const item = new vscode.CompletionItem(
                spec.name,
                vscode.CompletionItemKind.Property
            );
            item.detail = spec.detail;
            item.documentation = new vscode.MarkdownString(spec.detail);
            this.flags.push(item);
        }
    }

    private createParam(name: string, detail: string, defaultValue: string): vscode.CompletionItem {
        const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Property);
        item.detail = detail;
        item.documentation = new vscode.MarkdownString(`${detail}\n\nDefault: \`${defaultValue}\``);
        if (defaultValue && !defaultValue.includes('|')) {
            item.insertText = new vscode.SnippetString(`${name}="\${1:${defaultValue}}"`);
        }
        return item;
    }

    provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): vscode.CompletionItem[] {
        const lineText = document.lineAt(position).text.substring(0, position.character);
        const items: vscode.CompletionItem[] = [];

        // Command completion at start of line
        if (lineText.match(/^\\s*\\/?$/)) {
            return Array.from(this.commands.values());
        }

        // Partial command completion
        if (lineText.match(/^\\s*\\/\\w*$/)) {
            const partial = lineText.trim();
            return Array.from(this.commands.values()).filter(cmd => 
                cmd.label.toString().startsWith(partial)
            );
        }

        // Parameter completion after command
        const commandMatch = lineText.match(/^\\s*(\\/\\w+)/);
        if (commandMatch) {
            const command = commandMatch[1];
            const params = this.parameters.get(command);
            if (params) {
                items.push(...params);
            }
        }

        // Flag completion anywhere
        if (lineText.match(/\\s--?$/)) {
            items.push(...this.flags);
        }

        // Mode values
        if (lineText.match(/--mode=/)) {
            const sentio = new vscode.CompletionItem('Sentio', vscode.CompletionItemKind.EnumMember);
            sentio.detail = 'Deliberative, ethics-first mode';
            const dynamo = new vscode.CompletionItem('Dynamo', vscode.CompletionItemKind.EnumMember);
            dynamo.detail = 'Exploratory, novelty-biased mode';
            const hybrid = new vscode.CompletionItem('Hybrid', vscode.CompletionItemKind.EnumMember);
            hybrid.detail = 'Balanced hybrid mode';
            return [sentio, dynamo, hybrid];
        }

        return items;
    }

    resolveCompletionItem(
        item: vscode.CompletionItem,
        token: vscode.CancellationToken
    ): vscode.CompletionItem {
        return item;
    }
}