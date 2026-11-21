import * as vscode from 'vscode';
import {
    DebugSession,
    InitializedEvent,
    TerminatedEvent,
    StoppedEvent,
    BreakpointEvent,
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
    private _mode: LaunchRequestArguments['mode'] = 'Sentio';

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
        response.body.supportsConfigurationDoneRequest = false;
        response.body.supportsHitConditionalBreakpoints = false;
        response.body.supportsConditionalBreakpoints = false;
        response.body.supportsEvaluateForHovers = true;
        response.body.supportsStepBack = false;
        response.body.supportsDataBreakpoints = false;
        response.body.supportsCompletionsRequest = false;
        response.body.completionTriggerCharacters = ['.', '/', '-'];
        response.body.supportsCancelRequest = false;
        response.body.supportsBreakpointLocationsRequest = false;
        response.body.supportsRestartRequest = false;
        response.body.supportsExceptionOptions = false;
        response.body.supportsExceptionFilterOptions = false;

        this.sendResponse(response);
        this.sendEvent(new InitializedEvent());
    }

    protected async launchRequest(
        response: DebugProtocol.LaunchResponse,
        args: LaunchRequestArguments
    ): Promise<void> {
        this._mode = args.mode || 'Sentio';
        this._currentFile = args.program;
        this._isRunning = false;

        try {
            await this._nbosClient.boot({
                mode: this._mode,
                trace: args.trace || false
            });
            const result = await this._nbosClient.executeFile(args.program, {
                breakpoints: Array.from(this._breakpoints.values()).flat()
            });

            // A successful boot is not evidence that the program executed.
            // A launch can be acknowledged only after the backend confirms
            // completion or a real debugging stop.
            if (result.completed && result.stopped) {
                throw new Error('NBOS returned contradictory execution states');
            }
            if (result.completed) {
                this.sendResponse(response);
                this.sendEvent(new TerminatedEvent());
                return;
            }
            if (result.stopped) {
                this._currentLine = result.line ?? 0;
                this.sendResponse(response);
                this.sendEvent(
                    new StoppedEvent('breakpoint', NeuralBlitzDebugSession.threadId)
                );
                return;
            }

            throw new Error(result.error || 'NBOS did not confirm program execution');
        } catch (error) {
            this._nbosClient.disconnect();
            this.sendErrorResponse(response, 1001, `Failed to launch: ${error}`);
        }
    }

    protected async setBreakPointsRequest(
        response: DebugProtocol.SetBreakpointsResponse,
        args: DebugProtocol.SetBreakpointsArguments
    ): Promise<void> {
        const path = args.source?.path;
        if (!path) {
            this.sendErrorResponse(response, 1003, 'Breakpoint source path is required');
            return;
        }
        const clientBreakpoints = args.breakpoints || [];

        const breakpoints: DebugProtocol.Breakpoint[] = [];
        const runtimeBreakpoints: IRuntimeBreakpoint[] = [];

        for (let i = 0; i < clientBreakpoints.length; i++) {
            const b = clientBreakpoints[i];
            const runtimeBreakpoint: IRuntimeBreakpoint = {
                id: i + 1,
                line: this.convertClientLineToDebugger(b.line),
                // The backend has not acknowledged or bound this breakpoint.
                verified: false
            };

            runtimeBreakpoints.push(runtimeBreakpoint);

            breakpoints.push({
                verified: false,
                message: 'Unverified: NBOS has not confirmed breakpoint installation',
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
        try {
            const frames: IRuntimeStackFrame[] = await this._nbosClient.getStackTrace();
            response.body = {
                stackFrames: frames.map(f => new StackFrame(
                    f.index,
                    f.name,
                    new Source(f.file, f.file),
                    this.convertDebuggerLineToClient(f.line),
                    f.column ? this.convertDebuggerColumnToClient(f.column) : 0
                )),
                totalFrames: frames.length
            };
            this.sendResponse(response);
        } catch (error) {
            this.sendErrorResponse(response, 1002, `Stack trace unavailable: ${error}`);
        }
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
        const variables: DebugProtocol.Variable[] = [];
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
            this.sendErrorResponse(response, 1002, `Variables unavailable: ${error}`);
            return;
        }

        response.body = {
            variables: variables
        };

        this.sendResponse(response);
    }

    private async respondToBackendAction(
        response: DebugProtocol.Response,
        action: () => Promise<void>
    ): Promise<void> {
        try {
            await action();
            // An HTTP acknowledgement is not proof that a step completed.
            this.sendResponse(response);
        } catch (error) {
            this.sendErrorResponse(response, 1002, `NBOS debugger operation failed: ${error}`);
        }
    }

    protected async continueRequest(
        response: DebugProtocol.ContinueResponse,
        args: DebugProtocol.ContinueArguments
    ): Promise<void> {
        await this.respondToBackendAction(response, () => this._nbosClient.continue());
    }

    protected async nextRequest(
        response: DebugProtocol.NextResponse,
        args: DebugProtocol.NextArguments
    ): Promise<void> {
        await this.respondToBackendAction(response, () => this._nbosClient.stepOver());
    }

    protected async stepInRequest(
        response: DebugProtocol.StepInResponse,
        args: DebugProtocol.StepInArguments
    ): Promise<void> {
        await this.respondToBackendAction(response, () => this._nbosClient.stepInto());
    }

    protected async stepOutRequest(
        response: DebugProtocol.StepOutResponse,
        args: DebugProtocol.StepOutArguments
    ): Promise<void> {
        await this.respondToBackendAction(response, () => this._nbosClient.stepOut());
    }

    protected async pauseRequest(
        response: DebugProtocol.PauseResponse,
        args: DebugProtocol.PauseArguments
    ): Promise<void> {
        await this.respondToBackendAction(response, () => this._nbosClient.pause());
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
            this.sendResponse(response);
        } catch (error) {
            this.sendErrorResponse(response, 1002, `Evaluation failed: ${error}`);
        }
    }

    protected completionsRequest(
        response: DebugProtocol.CompletionsResponse,
        args: DebugProtocol.CompletionsArguments
    ): void {
        const completions: DebugProtocol.CompletionItem[] = [
            { label: '/boot', type: 'function' },
            { label: '/apply', type: 'function' },
            { label: '/status', type: 'function' },
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