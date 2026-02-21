import * as vscode from 'vscode';
import { CKRegistry, CKInfo } from '../util/ckRegistry';

export class CKCompletionProvider implements vscode.CompletionItemProvider {
    constructor(private ckRegistry: CKRegistry) {}

    async provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): Promise<vscode.CompletionItem[]> {
        const lineText = document.lineAt(position).text.substring(0, position.character);
        const items: vscode.CompletionItem[] = [];

        // Check if we're completing a CK reference (e.g., /apply Causa/...)
        const applyMatch = lineText.match(/\\/apply\\s+([A-Za-z]*)\\/?$/);
        if (applyMatch) {
            const partialFamily = applyMatch[1];
            return this.provideCKCompletions(partialFamily);
        }

        // Check for CK family completion after "/apply "
        if (lineText.match(/\\/apply\\s*$/)) {
            return this.provideCKFamilies();
        }

        // Check for specific CK completion after family/
        const familyMatch = lineText.match(/\\/apply\\s+([A-Za-z]+)\\/([A-Za-z0-9_]*)$/);
        if (familyMatch) {
            const family = familyMatch[1];
            const partialName = familyMatch[2];
            return this.provideCKInFamily(family, partialName);
        }

        return items;
    }

    private async provideCKCompletions(partialFamily: string): Promise<vscode.CompletionItem[]> {
        const items: vscode.CompletionItem[] = [];
        const families = await this.ckRegistry.getFamilies();

        for (const family of families) {
            if (family.toLowerCase().startsWith(partialFamily.toLowerCase())) {
                const item = new vscode.CompletionItem(
                    family,
                    vscode.CompletionItemKind.Module
                );
                item.detail = `CK Family: ${family}`;
                item.documentation = await this.ckRegistry.getFamilyDescription(family);
                item.insertText = family + '/';
                item.command = {
                    command: 'editor.action.triggerSuggest',
                    title: 'Trigger Suggest'
                };
                items.push(item);
            }
        }

        return items;
    }

    private async provideCKFamilies(): Promise<vscode.CompletionItem[]> {
        const items: vscode.CompletionItem[] = [];
        const families = await this.ckRegistry.getFamilies();

        for (const family of families) {
            const item = new vscode.CompletionItem(
                family,
                vscode.CompletionItemKind.Module
            );
            item.detail = `CK Family: ${family}`;
            item.documentation = await this.ckRegistry.getFamilyDescription(family);
            item.insertText = family + '/';
            item.command = {
                command: 'editor.action.triggerSuggest',
                title: 'Trigger Suggest'
            };
            items.push(item);
        }

        return items;
    }

    private async provideCKInFamily(family: string, partialName: string): Promise<vscode.CompletionItem[]> {
        const items: vscode.CompletionItem[] = [];
        const cks = await this.ckRegistry.getCKsInFamily(family);

        for (const ck of cks) {
            if (ck.name.toLowerCase().startsWith(partialName.toLowerCase())) {
                const item = new vscode.CompletionItem(
                    ck.name,
                    vscode.CompletionItemKind.Function
                );
                item.detail = `CK: ${family}/${ck.name} v${ck.version}`;
                item.documentation = new vscode.MarkdownString(
                    this.formatCKDocumentation(ck)
                );
                item.insertText = ck.name;
                items.push(item);
            }
        }

        return items;
    }

    private formatCKDocumentation(ck: CKInfo): string {
        let doc = `# ${ck.name}\n\n`;
        doc += `**Version:** ${ck.version}\n\n`;
        doc += `**Intent:** ${ck.intent}\n\n`;
        
        if (ck.inputs && Object.keys(ck.inputs).length > 0) {
            doc += `## Inputs\n`;
            for (const [key, value] of Object.entries(ck.inputs)) {
                doc += `- **${key}**: ${value}\n`;
            }
            doc += '\n';
        }

        if (ck.outputs && Object.keys(ck.outputs).length > 0) {
            doc += `## Outputs\n`;
            for (const [key, value] of Object.entries(ck.outputs)) {
                doc += `- **${key}**: ${value}\n`;
            }
            doc += '\n';
        }

        if (ck.riskFactors && ck.riskFactors.length > 0) {
            doc += `## Risk Factors\n`;
            for (const risk of ck.riskFactors) {
                doc += `- ⚠️ ${risk}\n`;
            }
            doc += '\n';
        }

        if (ck.veritasInvariants && ck.veritasInvariants.length > 0) {
            doc += `## Veritas Invariants\n`;
            for (const inv of ck.veritasInvariants) {
                doc += `- ✅ ${inv}\n`;
            }
        }

        return doc;
    }

    async resolveCompletionItem(
        item: vscode.CompletionItem,
        token: vscode.CancellationToken
    ): Promise<vscode.CompletionItem> {
        // Enhance completion item with additional details if needed
        return item;
    }
}