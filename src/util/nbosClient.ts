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

    private requireAcknowledgement(data: unknown, operation: string): void {
        if (!data || typeof data !== 'object' || (data as { ok?: unknown }).ok !== true) {
            throw new Error(`NBOS did not positively acknowledge ${operation}`);
        }
    }

    private requireRecord(data: unknown, operation: string): Record<string, any> {
        if (!data || typeof data !== 'object' || Array.isArray(data)) {
            throw new Error(`Malformed NBOS ${operation} response: expected an object`);
        }
        const record = data as Record<string, any>;
        if (record.ok === false) {
            throw new Error(record.error?.message || `NBOS rejected ${operation}`);
        }
        return record;
    }

    // Never send source code, commands or credentials to an implicitly
    // selected port. Port 8080 in this repository belongs to unrelated
    // development services, and the Python gateway is NOT an NBOS server.
    private requireEndpoint(): string {
        const raw = vscode.workspace.getConfiguration('neuralblitz')
            .get<string>('nbosEndpoint', '');
        if (typeof raw !== 'string' || !raw.trim()) {
            throw new Error(
                'NBOS endpoint is not configured. Set neuralblitz.nbosEndpoint ' +
                'to a verified, compatible NBOS server before executing commands.'
            );
        }

        let url: URL;
        try {
            url = new URL(raw.trim());
        } catch {
            throw new Error('Invalid neuralblitz.nbosEndpoint URL');
        }
        const localHost = ['localhost', '127.0.0.1', '::1']
            .includes(url.hostname.replace(/^\\[|\\]$/g, ''));
        if ((url.protocol !== 'https:' && !(url.protocol === 'http:' && localHost)) ||
            url.username || url.password || url.search || url.hash ||
            url.pathname !== '/') {
            throw new Error(
                'Invalid NBOS endpoint: use HTTPS, or HTTP only on loopback, ' +
                'with no embedded credentials, path, query or fragment'
            );
        }
        return url.origin;
    }

    private post(path: string, data?: unknown) {
        return this.client.post(path, data, { baseURL: this.requireEndpoint() });
    }

    private get(path: string) {
        return this.client.get(path, { baseURL: this.requireEndpoint() });
    }

    constructor() {
        this.client = axios.create({
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
            const response = await this.post('/boot', {
                charter: options.charter || 'ϕ1..ϕ15',
                goldendag: 'enable',
                mode: options.mode,
                trace: options.trace || false,
                strict: vscode.workspace.getConfiguration('neuralblitz').get('strictMode', false)
            });
            if (response.data?.ok !== true) {
                throw new Error(response.data?.error?.message || 'NBOS rejected the boot request');
            }
            this.connected = true;
        } catch (error) {
            this.connected = false;
            throw error;
        }
    }

    async executeFile(filePath: string, options?: { breakpoints?: any[] }): Promise<ExecutionResult> {
        const response = await this.post('/execute', {
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
        const response = await this.post('/execute', { command });
        const data = response.data;
        if (!data || typeof data !== 'object' || Array.isArray(data) || typeof data.ok !== 'boolean') {
            throw new Error('Malformed NBOS command response: missing boolean ok');
        }
        // Preserve explicit ok:false so the command UI can display its backend error.
        return data;
    }

    async getStackTrace(): Promise<StackFrame[]> {
        const response = await this.get('/debug/stack');
        const data = this.requireRecord(response.data, 'stack trace');
        if (!Array.isArray(data.frames)) {
            throw new Error('Malformed NBOS stack trace response: expected frames array');
        }
        return data.frames;
    }

    async getVariables(scope: string): Promise<Record<string, any>> {
        const response = await this.get(`/debug/variables/${encodeURIComponent(scope)}`);
        const data = this.requireRecord(response.data, 'variables');
        if (!data.variables || typeof data.variables !== 'object' || Array.isArray(data.variables)) {
            throw new Error('Malformed NBOS variables response: expected variables object');
        }
        return data.variables;
    }

    private async debugAction(path: string): Promise<void> {
        const response = await this.post(path);
        this.requireAcknowledgement(response.data, path);
    }

    async continue(): Promise<void> { await this.debugAction('/debug/continue'); }
    async stepOver(): Promise<void> { await this.debugAction('/debug/stepOver'); }
    async stepInto(): Promise<void> { await this.debugAction('/debug/stepInto'); }
    async stepOut(): Promise<void> { await this.debugAction('/debug/stepOut'); }
    async pause(): Promise<void> { await this.debugAction('/debug/pause'); }

    async evaluate(expression: string): Promise<any> {
        const response = await this.post('/debug/evaluate', { expression });
        const data = this.requireRecord(response.data, 'evaluation');
        if (!Object.prototype.hasOwnProperty.call(data, 'result')) {
            throw new Error('Malformed NBOS evaluation response: missing result');
        }
        return data.result;
    }

    disconnect(): void { this.connected = false; }
    isConnected(): boolean { return this.connected; }

    async getStatus(): Promise<any> {
        const response = await this.get('/status');
        return this.requireRecord(response.data, 'status');
    }

    async introspect(scope: string): Promise<any> {
        const response = await this.post('/introspect', { scope });
        return this.requireRecord(response.data, 'introspection');
    }
}
