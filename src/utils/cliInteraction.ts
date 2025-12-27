import { spawn, ChildProcessWithoutNullStreams } from "child_process";
import crypto from "crypto";
import { EventEmitter } from "events";
import fs from "fs";
import path from "path";

export interface Selection {
    selection_id: string;
    prompt: string;
    options: string[];
    cursor_index: number;
}

export interface CLIInteractionState {
    state: "idle" | "running" | "selection_required" | "completed" | "failed";
    selection?: Selection;
    error?: string;
    reason?: string;
    exit_code?: number;
    output?: string;
}

const DEBUG_LOG = path.join(process.cwd(), "handler_debug.log");
function debug(msg: string) {
    fs.appendFileSync(DEBUG_LOG, `[${new Date().toISOString()}] ${msg}\n`);
}

export class CLIInteractionHandler extends EventEmitter {
    private proc: ChildProcessWithoutNullStreams | null = null;
    private buffer: string = "";
    private currentState: CLIInteractionState = { state: "idle" };
    private selectionId: string | null = null;
    private interactionTimeout: NodeJS.Timeout | null = null;
    private lastBufferLength: number = 0;
    private readonly WAIT_TIMEOUT = 5000;
    private currentResolve: ((state: CLIInteractionState) => void) | null = null;

    constructor() {
        super();
        if (fs.existsSync(DEBUG_LOG)) fs.unlinkSync(DEBUG_LOG);
    }

    private resolveState(state: CLIInteractionState) {
        if (this.currentResolve) {
            debug(`Resolving with state: ${state.state}`);
            const resolve = this.currentResolve;
            this.currentResolve = null;
            if (this.interactionTimeout) {
                clearTimeout(this.interactionTimeout);
                this.interactionTimeout = null;
            }
            resolve(state);
        }
    }

    public async execute(command: string, args: string[], cwd: string, env?: NodeJS.ProcessEnv): Promise<CLIInteractionState> {
        if (this.proc) {
            throw new Error("Process already running");
        }

        debug(`Executing: ${command} ${args.join(" ")} in ${cwd}`);
        this.proc = spawn(command, args, {
            cwd,
            stdio: "pipe",
            env: { ...process.env, ...env }
        });
        this.currentState = { state: "running" };
        this.buffer = "";
        this.lastBufferLength = 0;

        const onData = (chunk: Buffer) => {
            const raw = chunk.toString();
            const text = raw.replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, "");
            this.buffer += text;
            debug(`Data received. Buffer length: ${this.buffer.length}`);
            this.resetInteractionTimeout();
        };

        this.proc.stdout.on("data", onData);
        this.proc.stderr.on("data", onData);

        this.proc.on("exit", (code) => {
            debug(`Process exited with code: ${code}`);
            setTimeout(() => {
                this.cleanup();
                if (code === 0) {
                    this.currentState = { state: "completed", output: this.buffer };
                } else {
                    this.currentState = { state: "failed", reason: this.buffer, exit_code: code ?? -1 };
                }
                this.resolveState(this.currentState);
            }, 1000);
        });

        this.proc.on("error", (err) => {
            debug(`Process error: ${err.message}`);
            this.cleanup();
            this.currentState = { state: "failed", reason: err.message };
            this.resolveState(this.currentState);
        });

        return new Promise((resolve) => {
            this.currentResolve = resolve;
            this.resetInteractionTimeout();
        });
    }

    private resetInteractionTimeout() {
        if (this.interactionTimeout) {
            clearTimeout(this.interactionTimeout);
        }

        this.interactionTimeout = setTimeout(() => {
            if (this.currentState.state === "running" && this.proc) {
                this.handlePotentialInteraction();
            }
        }, this.WAIT_TIMEOUT);
    }


    private stripMarkers(line: string): string {
        return line.replace(/^[❯*»]\s*/, "").replace(/^\[[ x]\]\s*/, "").replace(/^\([ x]\)\s*/, "").trim();
    }

    private handlePotentialInteraction() {
        debug("Handling potential interaction...");
        if (this.buffer.length === this.lastBufferLength && this.buffer.length > 0) {
            debug("Buffer stopped growing.");
            let allLines = this.buffer.split("\n").map(l => l.trim()).filter(l => l.length > 0);

            if (allLines.length > 0) {
                const prompt = allLines[0];
                const options = allLines.slice(1).map(l => this.stripMarkers(l)).filter(l => l.length > 0);
                debug(`Prompt detected: ${prompt}`);

                this.selectionId = crypto.randomUUID();
                this.currentState = {
                    state: "selection_required",
                    selection: {
                        selection_id: this.selectionId,
                        prompt,
                        options,
                        cursor_index: 0
                    }
                };
                this.resolveState(this.currentState);
                return;
            }
        }

        this.lastBufferLength = this.buffer.length;
        this.resetInteractionTimeout();
    }

    public async respond(selectionId: string, selectedOption: string): Promise<CLIInteractionState> {
        if (this.currentState.state !== "selection_required" || this.selectionId !== selectionId || !this.proc) {
            throw new Error("No active selection or invalid selection ID");
        }

        debug(`Responding with: ${selectedOption}`);
        const selection = this.currentState.selection!;
        const targetIndex = selection.options.findIndex(opt => opt.includes(selectedOption) || selectedOption.includes(opt));

        const delta = targetIndex !== -1 ? targetIndex - selection.cursor_index : 0;
        const DOWN_ARROW = "\u001b[B";
        const UP_ARROW = "\u001b[A";
        const ENTER = "\n";

        if (delta > 0) {
            for (let i = 0; i < delta; i++) {
                this.proc.stdin.write(DOWN_ARROW);
            }
        } else if (delta < 0) {
            for (let i = 0; i < Math.abs(delta); i++) {
                this.proc.stdin.write(UP_ARROW);
            }
        }

        if (targetIndex === -1) {
            this.proc.stdin.write(selectedOption + ENTER);
        } else {
            this.proc.stdin.write(ENTER);
        }

        this.currentState = { state: "running" };
        this.buffer = "";
        this.lastBufferLength = 0;

        return new Promise((resolve) => {
            this.currentResolve = resolve;
            this.resetInteractionTimeout();
        });
    }

    private cleanup() {
        if (this.interactionTimeout) {
            clearTimeout(this.interactionTimeout);
            this.interactionTimeout = null;
        }
    }

    public kill() {
        if (this.proc) {
            this.proc.kill();
            this.proc = null;
        }
        this.cleanup();
        this.currentState = { state: "idle" };
        this.currentResolve = null;
    }

    public getState(): CLIInteractionState {
        return this.currentState;
    }
}
