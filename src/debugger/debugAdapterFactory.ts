import * as vscode from 'vscode';
import { DebugAdapterDescriptor, DebugAdapterDescriptorFactory, DebugSession } from 'vscode';
import { NeuralBlitzDebugSession } from './debugSession';

export class NeuralBlitzDebugAdapterFactory implements DebugAdapterDescriptorFactory {
    createDebugAdapterDescriptor(
        session: DebugSession
    ): vscode.ProviderResult<DebugAdapterDescriptor> {
        // Return a debug adapter descriptor that creates a new debug session
        return new vscode.DebugAdapterInlineImplementation(
            new NeuralBlitzDebugSession()
        );
    }
}