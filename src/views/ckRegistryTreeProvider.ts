import * as vscode from 'vscode';
import { CKRegistry } from '../util/ckRegistry';

class CKTreeItem extends vscode.TreeItem {
    constructor(
        label: string,
        public readonly family: string,
        public readonly isFamily: boolean,
        description?: string
    ) {
        super(label, isFamily ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None);
        this.description = description;
        this.contextValue = isFamily ? 'ckFamily' : 'ck';
    }
}

/** Shows the capability kernels registered in the local CKRegistry. */
export class CKRegistryTreeProvider implements vscode.TreeDataProvider<CKTreeItem> {
    constructor(private readonly registry: CKRegistry) {}

    getTreeItem(element: CKTreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: CKTreeItem): Promise<CKTreeItem[]> {
        if (!element) {
            const families = await this.registry.getFamilies();
            return families.map(family => new CKTreeItem(family, family, true));
        }
        if (!element.isFamily) {
            return [];
        }
        const kernels = await this.registry.getCKsInFamily(element.family);
        return kernels.map(ck => {
            const item = new CKTreeItem(ck.name, ck.family, false, `v${ck.version}`);
            item.tooltip = ck.intent;
            return item;
        });
    }
}
