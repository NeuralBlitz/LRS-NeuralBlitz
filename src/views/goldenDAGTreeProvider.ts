import * as vscode from 'vscode';

/** Displays the currently configured GoldenDAG status without inventing attestation data. */
export class GoldenDAGTreeProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(): vscode.TreeItem[] {
        const item = new vscode.TreeItem('No attestation loaded', vscode.TreeItemCollapsibleState.None);
        item.description = 'Connect to a backend to inspect GoldenDAG';
        item.tooltip = 'No GoldenDAG attestation has been retrieved or verified.';
        return [item];
    }
}
