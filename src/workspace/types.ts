import { VAPStatus } from "../vap/runtime.js";

export interface VapContext {
    circuit_name: string;
    results_dir: string;
    datetime: string;
}

export interface WorkspaceSender {
    send(msg: any): void;
    sendError(type: string, message: string): void;
    onStableCircuitUpdated(circuitName: string): Promise<void>;
    startSync(projectId: string, resourceType: string, iterationId?: string | null, intent?: string | null, data?: Record<string, any>): Promise<void>;
}
