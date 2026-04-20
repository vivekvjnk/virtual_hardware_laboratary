import { VAPStatus } from "../vap/runtime.js";

export interface VapContext {
    circuit_name: string;
    results_dir: string;
    datetime: string;
}

export interface RuntimeSender {
    send(msg: any): void;
    sendError(type: string, message: string): void;
    onStableCircuitUpdated(circuitName: string): Promise<void>;

}
