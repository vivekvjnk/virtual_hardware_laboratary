export interface RuntimeSender {
    send(msg: any): void;
    sendError(type: string, message: string): void;
    onStableCircuitUpdated(circuitName: string): Promise<void>;
}
