import * as vscode from 'vscode';
import axios, { AxiosInstance } from 'axios';

export interface BootOptions {
    mode: 'Sentio' | 'Dynamo' | 'Hybrid';
    trace?: boolean;
    charter?: string;
}
export interface ExecutionResult {
    completed: boolean;
    stopped?: boolean;
    line?: number;
    error?: string;
}
export interface StackFrame {
    index: number;
    name: string;
    file: string;
    line: number;
    column?: number;
}

export class NBOSClient {
    private client: AxiosInstance;
    private connected = false;

    constructor() {
        const config = vscode.workspace.getConfiguration('neuralblitz');
        const endpoint = config.get<string>('nbosEndpoint', 'http://localhost:8080');
        this.client = axios.create({
            baseURL: endpoint,
            timeout: 30000,
            headers: { 'Content-Type': 'application/json' }
        });
        this.client.interceptors.request.use(
            (requestConfig) => {
                const token = vscode.workspace.getConfiguration('neuralblitz').get<string>('authToken');
                if (token) requestConfig.headers.Authorization = `Bearer ${token}`;
                return requestConfig;
            },
            (error) => Promise.reject(error)
        );
    }

    async boot(options: BootOptions): Promise<void> {
        this.connected = false;
        try {
            const response = await this.client.post('/boot', {
                charter: options.charter || 'ϕ1..ϕ15',
                goldendag: 'enable',
                mode: options.mode,
                trace: options.trace || false,
                strict: vscode.workspace.getConfiguration('neuralblitz').get('strictMode', false)
            });
            if (!response.data?.ok) {
                throw new Error(response.data?.error?.message || 'NBOS rejected the boot request');
            }
            this.connected = true;
        } catch (error) {
            this.connected = false;
            throw error;
        }
    }

    async executeFile(filePath: string, options?: { breakpoints?: any[] }): Promise<ExecutionResult> {
        const response = await this.client.post('/execute', {
            program: filePath,
            breakpoints: options?.breakpoints || []
        });
        const data = response.data;
        if (!data || typeof data !== 'object' || typeof data.ok !== 'boolean') {
            throw new Error('Malformed NBOS execution response: missing boolean ok');
        }
        if (data.ok === false) {
            return {
                completed: false,
                error: data.error?.message || 'NBOS rejected execution'
            };
        }
        if (data.completed === true && data.stopped === true) {
            throw new Error('Contradictory NBOS execution response: completed and stopped');
        }
        if (data.stopped === true) {
            return { completed: false, stopped: true, line: data.line };
        }
        if (data.completed === true) {
            return { completed: true, stopped: false };
        }
        // HTTP success and ok:true only confirm acceptance, not completed work.
        throw new Error('NBOS did not confirm execution completion or a stopped state');
    }

    async executeCommand(command: string): Promise<any> {
        const response = await this.client.post('/execute', { command });
        return response.data;
    }

    async getStackTrace(): Promise<StackFrame[]> {
        const response = await this.client.get('/debug/stack');
        return response.data?.frames || [];
    }

    async getVariables(scope: string): Promise<Record<string, any>> {
        const response = await this.client.get(`/debug/variables/${encodeURIComponent(scope)}`);
        return response.data?.variables || {};
    }

    async continue(): Promise<void> { await this.client.post('/debug/continue'); }
    async stepOver(): Promise<void> { await this.client.post('/debug/stepOver'); }
    async stepInto(): Promise<void> { await this.client.post('/debug/stepInto'); }
    async stepOut(): Promise<void> { await this.client.post('/debug/stepOut'); }
    async pause(): Promise<void> { await this.client.post('/debug/pause'); }

    async evaluate(expression: string): Promise<any> {
        const response = await this.client.post('/debug/evaluate', { expression });
        return response.data?.result;
    }

    disconnect(): void { this.connected = false; }
    isConnected(): boolean { return this.connected; }

    async getStatus(): Promise<any> {
        const response = await this.client.get('/status');
        return response.data;
    }

    async introspect(scope: string): Promise<any> {
        const response = await this.client.post('/introspect', { scope });
        return response.data;
    }
}
