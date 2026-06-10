export type ResourceType = "Library" | "Circuit" | "Evaluation" | "StableCircuit" | "CompiledCircuit";
export type SyncIntent = "EVALUATION" | "ALIGNMENT" | "RESULT";

export interface SyncPayload {
    sync_id: string;
    project_id: string;
    iteration_id?: string | null;
    resource_type: ResourceType;
    intent?: SyncIntent | null;
    hash?: string | null;
    blob_id?: string | null;
    reason?: string | null;
    data?: Record<string, any>;
    source: "vhl_webui" | "vhl_agent_backend" | "vhl_runtime";
}

export enum SyncState {
    IDLE = "IDLE",
    REQUEST_HASH = "REQUEST_HASH",
    COMPARE = "COMPARE",
    REQUEST_UPLOAD = "REQUEST_UPLOAD",
    REQUEST_DOWNLOAD = "REQUEST_DOWNLOAD",
    VERIFY_OBJECT = "VERIFY_OBJECT",
    APPLY_ATOMIC = "APPLY_ATOMIC",
    COMPLETE = "COMPLETE",
    ERROR = "ERROR"
}
