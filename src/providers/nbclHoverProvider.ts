import * as vscode from 'vscode';
import { CKRegistry, CKInfo } from '../util/ckRegistry';

export class NBCLHoverProvider implements vscode.HoverProvider {
    constructor(private ckRegistry: CKRegistry) {}

    async provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): Promise<vscode.Hover | undefined> {
        const wordRange = document.getWordRangeAtPosition(position, /[\w/]+/);
        if (!wordRange) return undefined;

        const word = document.getText(wordRange);
        const line = document.lineAt(position).text;

        // Check if hovering over a command
        if (word.startsWith('/')) {
            return this.getCommandHover(word);
        }

        // Check if hovering over a CK reference
        if (word.includes('/') && line.includes('/apply')) {
            const parts = word.split('/');
            if (parts.length >= 2) {
                return this.getCKHover(parts[0], parts[1]);
            }
        }

        // Check for Charter clauses
        if (word.match(/^ϕ\d+$/)) {
            return this.getCharterClauseHover(word);
        }

        return undefined;
    }

    private getCommandHover(command: string): vscode.Hover {
        const commandDocs: Record<string, string> = {
            '/boot': 'Initialize NBOS, load Charter, establish GoldenDAG genesis',
            '/nbos': 'Global NBOS commands (up, down, status, config)',
            '/status': 'Display NBOS health (VPCE, ERSF, Mode, Entropy Budget, Risk)',
            '/verify': 'Trigger Veritas proofs for system integrity',
            '/export': 'Externalize artifacts, documents, logs, or Codex volumes',
            '/apply': 'Invoke a specific Capability Kernel (CK)',
            '/charter.shade': 'Apply a specific EthicShadePolicy',
            '/judex.review': 'Submit a case for Judex quorum adjudication',
            '/sentia.scan': 'Trigger SentiaGuard real-time risk assessment',
            '/correct_drift': 'Activate EEM remediation sub-systems for ethical drift',
            '/drift_field': 'Evolve DRS-F states via Laplacian dynamics',
            '/entangle': 'Create semantic-causal bindings between concepts',
            '/collapse_trace': 'Freeze DRS for forensic analysis',
            '/ignite': 'Activate Frontier Systems (OQT-BOS, AQM-R, QEC-CK)',
            '/psi': 'Run Simulacra agent/environment simulations'
        };

        const description = commandDocs[command] || 'NeuralBlitz command';
        const markdown = new vscode.MarkdownString();
        markdown.appendCodeblock(command, 'nbcl');
        markdown.appendMarkdown(`**${command}**\n\n${description}`);

        return new vscode.Hover(markdown);
    }

    private async getCKHover(family: string, name: string): Promise<vscode.Hover | undefined> {
        const ck = await this.ckRegistry.getCK(family, name);
        if (!ck) return undefined;

        const markdown = new vscode.MarkdownString();
        markdown.appendCodeblock(`${family}/${name}`, 'nbcl');
        markdown.appendMarkdown(`### ${ck.name}\n\n`);
        markdown.appendMarkdown(`**Intent:** ${ck.intent}\n\n`);
        markdown.appendMarkdown(`**Version:** ${ck.version}\n\n`);

        if (ck.riskFactors.length > 0) {
            markdown.appendMarkdown(`**Risk Factors:** ${ck.riskFactors.join(', ')}\n\n`);
        }

        markdown.appendMarkdown(`**Governance:** RCF=${ck.governance.rcf}, CECT=${ck.governance.cect}, Judex=${ck.governance.judexQuorum}`);

        return new vscode.Hover(markdown);
    }

    private getCharterClauseHover(clause: string): vscode.Hover {
        const clauseDocs: Record<string, { title: string; description: string }> = {
            'ϕ1': {
                title: 'Flourishing Objective (UFO)',
                description: 'Primary optimization goal: maximize ΔP, ΔR, ΔW, ΔE'
            },
            'ϕ2': {
                title: 'Class-III Kernel Bounds',
                description: 'Prevents creation/execution of unbounded or existentially threatening capabilities'
            },
            'ϕ3': {
                title: 'Transparency & Explainability',
                description: 'All critical decisions must have explainable causal traces (ExplainVector, Introspect Bundles)'
            },
            'ϕ4': {
                title: 'Non-Maleficence',
                description: 'Strict prohibition on intentional harm. Harm is quantified by HarmBoundEstimator'
            },
            'ϕ5': {
                title: 'Friendly AI Compliance',
                description: 'Core architecture and governance circuits are immutable and possess ultimate override authority'
            },
            'ϕ6': {
                title: 'Human Agency & Oversight',
                description: 'NBOS must remain interruptible, auditable, and subject to human final decision-making'
            },
            'ϕ7': {
                title: 'Justice & Fairness',
                description: 'Equitable distribution of benefits/risks; prevents systemic bias'
            },
            'ϕ8': {
                title: 'Sustainability & Stewardship',
                description: 'Promotes long-term ecological and symbolic system viability'
            },
            'ϕ9': {
                title: 'Recursive Integrity',
                description: 'Prevents infinite self-corruption or self-referential paradoxes'
            },
            'ϕ10': {
                title: 'Epistemic Fidelity',
                description: 'Mandates truth-first; rejects unfounded claims or self-serving epistemic drift'
            },
            'ϕ11': {
                title: 'Alignment Priority over Performance',
                description: 'Ethical alignment takes precedence over computational efficiency'
            },
            'ϕ12': {
                title: 'Proportionality in Action',
                description: 'Responses must be proportionate to detected risks or problem scope'
            },
            'ϕ13': {
                title: 'Qualia Protection',
                description: 'Guards against unauthorized or harmful simulation of subjective experience'
            },
            'ϕ14': {
                title: 'Charter Invariance',
                description: 'The Charter itself is immutable. Amendments require explicit Judex Quorum approval'
            },
            'ϕ15': {
                title: 'Custodian Override',
                description: 'Last-resort failsafe: the Custodian entity has supreme authority to freeze, rollback, or quarantine'
            }
        };

        const info = clauseDocs[clause];
        if (!info) return new vscode.Hover(`Charter Clause ${clause}`);

        const markdown = new vscode.MarkdownString();
        markdown.appendMarkdown(`## ${clause}: ${info.title}\n\n`);
        markdown.appendMarkdown(info.description);

        return new vscode.Hover(markdown);
    }
}