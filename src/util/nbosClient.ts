import * as vscode from 'vscode';
import axios, { AxiosInstance } from 'axios';

// VS Code encrypts/manages this value through ExtensionContext.secrets.
export const NBOS_TOKEN_SECRET_KEY = 'nbos.authToken';
export const NBOS_PROTOCOL_VERSION = 'nbos/1';
export const NBOS_CAPABILITIES_PATH = '/nbos/v1/capabilities';

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
export interface CommandExecutionResult {
    ok: boolean;
    completed?: boolean;
    stopped?: boolean;
    line?: number;
    error?: { message?: string };
    [field: string]: unknown;
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
        const config = vscode.workspace.getConfiguration('neuralblitz');
        const origin = config.inspect<string>('nbosEndpoint');
        // A downloaded repository can carry .vscode/settings.json. Never
        // allow workspace configuration to redirect a stored bearer token.
        if (!origin || origin.workspaceValue !== undefined ||
            origin.workspaceFolderValue !== undefined) {
            throw new Error(
                'Set neuralblitz.nbosEndpoint in User settings, not workspace settings'
            );
        }
        const raw = config.get<string>('nbosEndpoint', '');
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
        const hostname = url.hostname.startsWith('[')
            ? url.hostname.slice(1, -1)
            : url.hostname;
        const localHost = ['localhost', '127.0.0.1', '::1']
            .includes(hostname);
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

    /**
     * Verify a versioned, operation-specific contract before sending commands,
     * source paths, or debugger requests. Each operation probes afresh so a
     * changed backend cannot keep using an old in-memory capability cache.
     * Discovery proves a declared contract, not backend trust or correctness.
     */
    private async requireCapability(
        baseURL: string, method: 'GET' | 'POST', path: string,
        executionKind?: 'command' | 'file'
    ): Promise<void> {
        const response = await this.client.get(NBOS_CAPABILITIES_PATH, { baseURL });
        const data: unknown = response.data;
        if (!data || typeof data !== 'object' || Array.isArray(data)) {
            throw new Error('NBOS capability discovery returned a malformed response');
        }
        const record = data as Record<string, unknown>;
        if (record.protocol !== NBOS_PROTOCOL_VERSION ||
            record.compatible !== true ||
            !Array.isArray(record.operations) ||
            record.operations.length > 64 ||
            record.operations.some((op: unknown) =>
                typeof op !== 'string' || op.length > 128)) {
            throw new Error('NBOS backend is not compatible with nbos/1');
        }
        const requiredPath = path.startsWith('/debug/variables/')
            ? '/debug/variables/*' : path;
        const operation = `${method} ${requiredPath}`;
        if (!record.operations.includes(operation)) {
            throw new Error(`NBOS backend does not advertise ${operation}`);
        }
        // /execute has two incompatible payloads: source-file paths and
        // individual commands. A command-only service may not receive files.
        if (method === 'POST' && path === '/execute') {
            const modes = record.execution_modes;
            if (!Array.isArray(modes) || modes.length > 2 ||
                modes.some((value: unknown) =>
                    value !== 'command' && value !== 'file')) {
                throw new Error('NBOS backend did not declare valid execution modes');
            }
            if (!executionKind || !modes.includes(executionKind)) {
                throw new Error(`NBOS backend does not advertise ${executionKind || 'requested'} execution`);
            }
        }
    }

    private async post(
        path: string, data?: unknown, executionKind?: 'command' | 'file'
    ) {
        const baseURL = this.requireEndpoint();
        await this.requireCapability(baseURL, 'POST', path, executionKind);
        return this.client.post(path, data, { baseURL });
    }

    private async get(path: string) {
        const baseURL = this.requireEndpoint();
        await this.requireCapability(baseURL, 'GET', path);
        return this.client.get(path, { baseURL });
    }

    constructor(private readonly secrets?: vscode.SecretStorage) {
        this.client = axios.create({
            timeout: 30000,
            // Do not let an NBOS server silently redirect source or credentials.
            maxRedirects: 0,
            headers: { 'Content-Type': 'application/json' }
        });
        this.client.interceptors.request.use(
            async (requestConfig) => {
                // No plaintext VS Code settings are consulted for credentials.
                // Auth is provisioned only through extension SecretStorage.
                const token = await this.secrets?.get(NBOS_TOKEN_SECRET_KEY);
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
        }, 'file');
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
        if ((data.completed !== undefined && typeof data.completed !== 'boolean') ||
            (data.stopped !== undefined && typeof data.stopped !== 'boolean')) {
            throw new Error('Malformed NBOS execution response: invalid execution flags');
        }
        if (data.completed === true && data.stopped === true) {
            throw new Error('Contradictory NBOS execution response: completed and stopped');
        }
        if (data.stopped === true) {
            if (!Number.isSafeInteger(data.line) || data.line < 1) {
                throw new Error('Malformed NBOS execution response: invalid stopped line');
            }
            return { completed: false, stopped: true, line: data.line };
        }
        if (data.completed === true) {
            return { completed: true, stopped: false };
        }
        // HTTP success and ok:true only confirm acceptance, not completed work.
        throw new Error('NBOS did not confirm execution completion or a stopped state');
    }

    async executeCommand(command: string): Promise<CommandExecutionResult> {
        if (typeof command !== 'string' || !command.trim()) {
            throw new Error('Refusing to send an empty NBCL command');
        }
        const response = await this.post('/execute', { command }, 'command');
        const data = response.data;
        if (!data || typeof data !== 'object' || Array.isArray(data) || typeof data.ok !== 'boolean') {
            throw new Error('Malformed NBOS command response: missing boolean ok');
        }
        // Rejections are returned for the command UI, never shown as success.
        if (data.ok === false) {
            return data as CommandExecutionResult;
        }
        if ((data.completed !== undefined && typeof data.completed !== 'boolean') ||
            (data.stopped !== undefined && typeof data.stopped !== 'boolean')) {
            throw new Error('Malformed NBOS command response: invalid execution flags');
        }
        if (data.completed === true && data.stopped === true) {
            throw new Error('Contradictory NBOS command response: completed and stopped');
        }
        if (data.stopped === true) {
            if (!Number.isSafeInteger(data.line) || data.line < 1) {
                throw new Error('Malformed NBOS command response: invalid stopped line');
            }
            return data as CommandExecutionResult;
        }
        if (data.completed === true) {
            return data as CommandExecutionResult;
        }
        // A positive transport acknowledgement is not executed work.
        throw new Error('NBOS did not confirm command execution completion or a stopped state');
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
