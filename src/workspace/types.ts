import { VAPStatus } from "../vap/runtime.js";

export interface VapContext {
    circuit_name: string;
    results_dir: string;
    datetime: string;
}

export interface WorkspaceSender {
    send(msg: any): void;
    sendError(type: string, message: string): void;
}
