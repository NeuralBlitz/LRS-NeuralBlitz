import * as vscode from 'vscode';
import {
    DebugSession,
    InitializedEvent,
    TerminatedEvent,
    StoppedEvent,
    BreakpointEvent,
    OutputEvent,
    Thread,
    StackFrame,
    Scope,
    Variable,
    Source,
    Handles
} from 'vscode-debugadapter';
import { DebugProtocol } from 'vscode-debugprotocol';
import { NBOSClient } from '../util/nbosClient';

interface LaunchRequestArguments extends DebugProtocol.LaunchRequestArguments {
    program: string;
    args?: string[];
    mode: 'Sentio' | 'Dynamo' | 'Hybrid';
    trace?: boolean;
}

interface IRuntimeBreakpoint {
    id: number;
    line: number;
    verified: boolean;
}

interface IRuntimeStackFrame {
    index: number;
    name: string;
    file: string;
    line: number;
    column?: number;
}

export class NeuralBlitzDebugSession extends DebugSession {
    private static threadId = 1;
    private _variableHandles = new Handles<string>();
    private _breakpoints = new Map<string, IRuntimeBreakpoint[]>();
    private _nbosClient: NBOSClient;
    private _currentFile = '';
    private _currentLine = 0;
    private _isRunning = false;
    private _mode: string = 'Sentio';

    public constructor() {
        super();
        this._nbosClient = new NBOSClient();
        this.setDebuggerLinesStartAt1(true);
        this.setDebuggerColumnsStartAt1(true);
    }

    protected initializeRequest(
        response: DebugProtocol.InitializeResponse,
        args: DebugProtocol.InitializeRequestArguments
    ): void {
        response.body = response.body || {};
        response.body.supportsConfigurationDoneRequest = true;
        response.body.supportsHitConditionalBreakpoints = true;
        response.body.supportsConditionalBreakpoints = true;
        response.body.supportsEvaluateForHovers = true;
        response.body.supportsStepBack = false;
        response.body.supportsDataBreakpoints = false;
        response.body.supportsCompletionsRequest = true;
        response.body.completionTriggerCharacters = ['.', '/', '-'];
        response.body.supportsCancelRequest = true;
        response.body.supportsBreakpointLocationsRequest = true;
        response.body.supportsRestartRequest = true;
        response.body.supportsExceptionOptions = true;
        response.body.supportsExceptionFilterOptions = true;

        this.sendResponse(response);
        this.sendEvent(new InitializedEvent());
    }

    protected async launchRequest(
        response: DebugProtocol.LaunchResponse,
        args: LaunchRequestArguments
    ): Promise<void> {
        this._mode = args.mode || 'Sentio';
        this._currentFile = args.program;

        // Boot NeuralBlitz with specified mode
        try {
            await this._nbosClient.boot({
                mode: this._mode,
                trace: args.trace || false
            });

            this._isRunning = true;
            this.sendResponse(response);

            // Start executing the program
            await this.executeProgram(args.program);
        } catch (error) {
            this.sendErrorResponse(response, 1001, `Failed to launch: ${error}`);
        }
    }

    private async executeProgram(programPath: string): Promise<void> {
        try {
            // Load and parse the NBCL file
            const result = await this._nbosClient.executeFile(programPath, {
                breakpoints: Array.from(this._breakpoints.values()).flat()
            });

            if (result.completed) {
                this.sendEvent(new TerminatedEvent());
            } else if (result.stopped) {
                this._currentLine = result.line || 0;
                this.sendEvent(
                    new StoppedEvent('breakpoint', NeuralBlitzDebugSession.threadId)
                );
            }
        } catch (error) {
            this.sendEvent(
                new OutputEvent(`Error: ${error}\\n`, 'stderr')
            );
            this.sendEvent(new TerminatedEvent());
        }
    }

    protected async setBreakPointsRequest(
        response: DebugProtocol.SetBreakpointsResponse,
        args: DebugProtocol.SetBreakpointsArguments
    ): Promise<void> {
        const path = args.source.path as string;
        const clientBreakpoints = args.breakpoints || [];

        const breakpoints: DebugProtocol.Breakpoint[] = [];
        const runtimeBreakpoints: IRuntimeBreakpoint[] = [];

        for (let i = 0; i < clientBreakpoints.length; i++) {
            const b = clientBreakpoints[i];
            const runtimeBreakpoint: IRuntimeBreakpoint = {
                id: i + 1,
                line: this.convertClientLineToDebugger(b.line),
                verified: true
            };

            runtimeBreakpoints.push(runtimeBreakpoint);

            breakpoints.push({
                verified: true,
                line: b.line,
                column: b.column,
                id: runtimeBreakpoint.id
            });
        }

        this._breakpoints.set(path, runtimeBreakpoints);

        response.body = {
            breakpoints: breakpoints
        };

        this.sendResponse(response);
    }

    protected threadsRequest(response: DebugProtocol.ThreadsResponse): void {
        response.body = {
            threads: [
                new Thread(
                    NeuralBlitzDebugSession.threadId,
                    `NBCL Thread (${this._mode} Mode)`
                )
            ]
        };
        this.sendResponse(response);
    }

    protected async stackTraceRequest(
        response: DebugProtocol.StackTraceResponse,
        args: DebugProtocol.StackTraceArguments
    ): Promise<void> {
        const frames: IRuntimeStackFrame[] = await this._nbosClient.getStackTrace();

        response.body = {
            stackFrames: frames.map(f => {
                return new StackFrame(
                    f.index,
                    f.name,
                    new Source(f.file, f.file),
                    this.convertDebuggerLineToClient(f.line),
                    f.column ? this.convertDebuggerColumnToClient(f.column) : 0
                );
            }),
            totalFrames: frames.length
        };

        this.sendResponse(response);
    }

    protected scopesRequest(
        response: DebugProtocol.ScopesResponse,
        args: DebugProtocol.ScopesArguments
    ): void {
        response.body = {
            scopes: [
                new Scope('Local', this._variableHandles.create('local'), false),
                new Scope('Global', this._variableHandles.create('global'), false),
                new Scope('DRS State', this._variableHandles.create('drs'), false),
                new Scope('Governance', this._variableHandles.create('governance'), false)
            ]
        };
        this.sendResponse(response);
    }

    protected async variablesRequest(
        response: DebugProtocol.VariablesResponse,
        args: DebugProtocol.VariablesArguments,
        request?: DebugProtocol.Request
    ): Promise<void> {
        const variables: Variable[] = [];
        const scope = this._variableHandles.get(args.variablesReference);

        try {
            const scopeData = await this._nbosClient.getVariables(scope);

            for (const [name, value] of Object.entries(scopeData)) {
                let variableValue: string;
                let variableType = typeof value;

                if (typeof value === 'object') {
                    variableValue = JSON.stringify(value, null, 2);
                    variableType = value?.constructor?.name || 'Object';
                } else {
                    variableValue = String(value);
                }

                variables.push({
                    name,
                    value: variableValue,
                    type: variableType,
                    variablesReference: 0
                });
            }
        } catch (error) {
            variables.push({
                name: 'error',
                value: `Failed to load: ${error}`,
                type: 'error',
                variablesReference: 0
            });
        }

        response.body = {
            variables: variables
        };

        this.sendResponse(response);
    }

    protected async continueRequest(
        response: DebugProtocol.ContinueResponse,
        args: DebugProtocol.ContinueArguments
    ): Promise<void> {
        await this._nbosClient.continue();
        this.sendResponse(response);
    }

    protected async nextRequest(
        response: DebugProtocol.NextResponse,
        args: DebugProtocol.NextArguments
    ): Promise<void> {
        await this._nbosClient.stepOver();
        this.sendResponse(response);
        this.sendEvent(
            new StoppedEvent('step', NeuralBlitzDebugSession.threadId)
        );
    }

    protected async stepInRequest(
        response: DebugProtocol.StepInResponse,
        args: DebugProtocol.StepInArguments
    ): Promise<void> {
        await this._nbosClient.stepInto();
        this.sendResponse(response);
        this.sendEvent(
            new StoppedEvent('step', NeuralBlitzDebugSession.threadId)
        );
    }

    protected async stepOutRequest(
        response: DebugProtocol.StepOutResponse,
        args: DebugProtocol.StepOutArguments
    ): Promise<void> {
        await this._nbosClient.stepOut();
        this.sendResponse(response);
        this.sendEvent(
            new StoppedEvent('step', NeuralBlitzDebugSession.threadId)
        );
    }

    protected async pauseRequest(
        response: DebugProtocol.PauseResponse,
        args: DebugProtocol.PauseArguments
    ): Promise<void> {
        await this._nbosClient.pause();
        this.sendResponse(response);
    }

    protected disconnectRequest(
        response: DebugProtocol.DisconnectResponse,
        args: DebugProtocol.DisconnectArguments
    ): void {
        this._nbosClient.disconnect();
        this.sendResponse(response);
    }

    protected async evaluateRequest(
        response: DebugProtocol.EvaluateResponse,
        args: DebugProtocol.EvaluateArguments
    ): Promise<void> {
        try {
            const result = await this._nbosClient.evaluate(args.expression);
            
            response.body = {
                result: String(result),
                type: typeof result,
                variablesReference: 0
            };
        } catch (error) {
            response.body = {
                result: `Error: ${error}`,
                variablesReference: 0
            };
        }

        this.sendResponse(response);
    }

    protected completionsRequest(
        response: DebugProtocol.CompletionsResponse,
        args: DebugProtocol.CompletionsArguments
    ): void {
        const completions: DebugProtocol.CompletionItem[] = [
            { label: '/boot', type: 'command' },
            { label: '/apply', type: 'command' },
            { label: '/status', type: 'command' },
            { label: 'Causa', type: 'class' },
            { label: 'Ethics', type: 'class' },
            { label: 'Wisdom', type: 'class' }
        ];

        response.body = {
            targets: completions
        };

        this.sendResponse(response);
    }
}