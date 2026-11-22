import * as vscode from 'vscode';
import { NBCLCompletionProvider } from './providers/nbclCompletionProvider';
import { CKCompletionProvider } from './providers/ckCompletionProvider';
import { NBCLHoverProvider } from './providers/nbclHoverProvider';
import { NBCLDocumentSymbolProvider } from './providers/nbclDocumentSymbolProvider';
import { NBCLDiagnosticProvider } from './providers/nbclDiagnosticProvider';
import { NBCLCommands } from './commands/nbclCommands';
import { NeuralBlitzDebugAdapterFactory } from './debugger/debugAdapterFactory';
import { GoldenDAGTreeProvider } from './views/goldenDAGTreeProvider';
import { CKRegistryTreeProvider } from './views/ckRegistryTreeProvider';
import { CKRegistry } from './util/ckRegistry';
import { NBOSClient } from './util/nbosClient';

export function activate(context: vscode.ExtensionContext) {
    console.log('NeuralBlitz extension is now active');

    // Initialize core utilities
    const ckRegistry = new CKRegistry();
    const nbosClient = new NBOSClient(context.secrets);

    // Register completion providers
    const nbclCompletionProvider = vscode.languages.registerCompletionItemProvider(
        { scheme: 'file', language: 'nbcl' },
        new NBCLCompletionProvider(),
        '/', '-', '"'
    );

    const ckCompletionProvider = vscode.languages.registerCompletionItemProvider(
        { scheme: 'file', language: 'nbcl' },
        new CKCompletionProvider(ckRegistry),
        '/', ' '
    );

    // Register hover provider
    const hoverProvider = vscode.languages.registerHoverProvider(
        { scheme: 'file', language: 'nbcl' },
        new NBCLHoverProvider(ckRegistry)
    );

    // Register document symbol provider
    const symbolProvider = vscode.languages.registerDocumentSymbolProvider(
        { scheme: 'file', language: 'nbcl' },
        new NBCLDocumentSymbolProvider()
    );

    // Register diagnostic provider
    const diagnosticProvider = new NBCLDiagnosticProvider();
    diagnosticProvider.activate(context);

    // Register commands
    const commands = new NBCLCommands(nbosClient, ckRegistry, context.secrets);
    const commandDisposables = commands.register(context);

    // Register debug adapter factory
    const debugAdapterFactory = vscode.debug.registerDebugAdapterDescriptorFactory(
        'neuralblitz',
        new NeuralBlitzDebugAdapterFactory(context.secrets)
    );

    // Register tree views
    const goldenDAGProvider = new GoldenDAGTreeProvider();
    const goldenDAGTree = vscode.window.registerTreeDataProvider(
        'neuralblitzGoldenDAG',
        goldenDAGProvider
    );

    const ckRegistryProvider = new CKRegistryTreeProvider(ckRegistry);
    const ckRegistryTree = vscode.window.registerTreeDataProvider(
        'neuralblitzCKRegistry',
        ckRegistryProvider
    );

    // Add all disposables to context
    context.subscriptions.push(
        nbclCompletionProvider,
        ckCompletionProvider,
        hoverProvider,
        symbolProvider,
        debugAdapterFactory,
        goldenDAGTree,
        ckRegistryTree,
        ...commandDisposables
    );

    // Register file system watchers for NBCL files
    const nbclWatcher = vscode.workspace.createFileSystemWatcher('**/*.nbcl');
    nbclWatcher.onDidChange((uri) => {
        diagnosticProvider.validateDocument(uri);
    });
    nbclWatcher.onDidCreate((uri) => {
        diagnosticProvider.validateDocument(uri);
    });
    context.subscriptions.push(nbclWatcher);

    // Show welcome message
    vscode.window.showInformationMessage(
        'NeuralBlitz IDE is ready',
        'Open Documentation'
    ).then(selection => {
        if (selection === 'Open Documentation') {
            vscode.env.openExternal(vscode.Uri.parse(
                'https://github.com/NeuralBlitz/LRS-NeuralBlitz/blob/main/docs/production-readiness.md'
            ));
        }
    });
}

export function deactivate() {
    console.log('NeuralBlitz extension is now deactivated');
}