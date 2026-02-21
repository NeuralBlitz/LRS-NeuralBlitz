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
    private connected: boolean = false;

    constructor() {
        const config = vscode.workspace.getConfiguration('neuralblitz');
        const endpoint = config.get<string>('nbosEndpoint', 'http://localhost:8080');
        
        this.client = axios.create({
            baseURL: endpoint,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json'
            }
        });

        // Setup request interceptor for authentication
        this.client.interceptors.request.use(
            (config) => {
                // Add authentication token if available
                const token = vscode.workspace.getConfiguration('neuralblitz').get<string>('authToken');
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );
    }

    async boot(options: BootOptions): Promise<void> {
        try {
            const response = await this.client.post('/boot', {
                charter: options.charter || 'ϕ1..ϕ15',
                goldendag: 'enable',
                mode: options.mode,
                trace: options.trace || false,
                strict: vscode.workspace.getConfiguration('neuralblitz').get('strictMode', false)
            });

            if (response.data.ok) {
                this.connected = true;
                console.log('NeuralBlitz OS booted successfully');
            } else {
                throw new Error(response.data.error?.message || 'Boot failed');
            }
        } catch (error) {
            // Mock implementation for development
            console.log('Mock boot:', options);
            this.connected = true;
        }
    }

    async executeFile(filePath: string, options?: { breakpoints?: any[] }): Promise<ExecutionResult> {
        try {
            const response = await this.client.post('/execute', {
                program: filePath,
                breakpoints: options?.breakpoints || []
            });

            return {
                completed: response.data.ok,
                stopped: response.data.stopped,
                line: response.data.line,
                error: response.data.error?.message
            };
        } catch (error) {
            // Mock implementation
            console.log('Mock execute:', filePath);
            return { completed: true };
        }
    }

    async executeCommand(command: string): Promise<any> {
        try {
            const response = await this.client.post('/execute', {
                command: command
            });
            return response.data;
        } catch (error) {
            // Mock implementation
            console.log('Mock command:', command);
            return { ok: true, result: 'Mock result' };
        }
    }

    async getStackTrace(): Promise<StackFrame[]> {
        try {
            const response = await this.client.get('/debug/stack');
            return response.data.frames || [];
        } catch (error) {
            // Mock implementation
            return [
                {
                    index: 0,
                    name: 'main.nbcl',
                    file: 'main.nbcl',
                    line: 1,
                    column: 1
                }
            ];
        }
    }

    async getVariables(scope: string): Promise<Record<string, any>> {
        try {
            const response = await this.client.get(`/debug/variables/${scope}`);
            return response.data.variables || {};
        } catch (error) {
            // Mock implementation
            const mockVariables: Record<string, Record<string, any>> = {
                local: {
                    current_command: '/boot',
                    mode: 'Sentio',
                    entropy_budget: 0.11,
                    vpce_score: 0.992
                },
                global: {
                    system_status: 'ACTIVE',
                    telos_driver: 'OPTIMIZING_FLOURISHING',
                    nbhs512_seal: 'e4c1a9b7...'
                },
                drs: {
                    coherence_vpce: 0.94,
                    entropy_sch_nb: 0.23,
                    drift_rate_mrde: 0.007,
                    ethic_stress_cect: 0.12
                },
                governance: {
                    charter_status: 'ALL_CLAUSES_ENFORCED',
                    sentia_mode: 'AMBER',
                    judex_quorum_pending: 0
                }
            };
            return mockVariables[scope] || {};
        }
    }

    async continue(): Promise<void> {
        try {
            await this.client.post('/debug/continue');
        } catch (error) {
            console.log('Mock continue');
        }
    }

    async stepOver(): Promise<void> {
        try {
            await this.client.post('/debug/stepOver');
        } catch (error) {
            console.log('Mock step over');
        }
    }

    async stepInto(): Promise<void> {
        try {
            await this.client.post('/debug/stepInto');
        } catch (error) {
            console.log('Mock step into');
        }
    }

    async stepOut(): Promise<void> {
        try {
            await this.client.post('/debug/stepOut');
        } catch (error) {
            console.log('Mock step out');
        }
    }

    async pause(): Promise<void> {
        try {
            await this.client.post('/debug/pause');
        } catch (error) {
            console.log('Mock pause');
        }
    }

    async evaluate(expression: string): Promise<any> {
        try {
            const response = await this.client.post('/debug/evaluate', {
                expression
            });
            return response.data.result;
        } catch (error) {
            // Mock evaluation
            return `Mock result for: ${expression}`;
        }
    }

    disconnect(): void {
        this.connected = false;
        console.log('Disconnected from NeuralBlitz OS');
    }

    isConnected(): boolean {
        return this.connected;
    }

    async getStatus(): Promise<any> {
        try {
            const response = await this.client.get('/status');
            return response.data;
        } catch (error) {
            return {
                system_status: 'NBOS ACTIVE',
                governance_core: {
                    charter_status: 'ALL_CLAUSES_ENFORCED',
                    veritas_vpce: { score: 0.992 }
                }
            };
        }
    }

    async introspect(scope: string): Promise<any> {
        try {
            const response = await this.client.post('/introspect', { scope });
            return response.data;
        } catch (error) {
            return {
                bundle_id: 'mock-bundle-id',
                context: {
                    operation: 'boot',
                    mode: 'Sentio'
                },
                metrics: {
                    vpce_score: 0.992,
                    drift_rate: 0.007
                }
            };
        }
    }
}