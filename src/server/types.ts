/**
 * Canonical Event Types (v0.1)
 */
export type EventType =
    // Runtime -> Backend (Observation Events)
    | "HUMAN_INPUT"
    | "REFERENCE_UPLOADED"
    | "INTERRUPT_REQUEST"
    // Backend -> Runtime (System Events)
    | "STATE_TRANSITION"
    | "EVALUATION_UPDATE"
    | "ARTIFACT_UPDATED"
    | "AUTHORITY_REQUIRED"
    | "ERROR"
    // Workspace Management
    | "WORKSPACE_DOWNLOAD"
    | "WORKSPACE_UPLOAD"
    | "WORKSPACE_SYNC_COMPLETE"
    // Transport-Only (Relay Layer)
    | "IDENTIFY"
    | "AGENT_CONNECTED"
    | "AGENT_DISCONNECTED"
    | "WORKSPACE_CONNECTED"
    | "WORKSPACE_DISCONNECTED"
    // VAP (VHL ANA Process)
    | "VAP_INIT"
    | "VAP_INIT_COMPLETE"
    | "VAP_STATUS"
    | "VAP_STATUS_REPORT"

export interface AgentMessage {
    id: string
    type: EventType
    artifact_id: string | null
    timestamp: string // ISO-8601
    source: "runtime" | "backend" | "vhl_workspace"
    payload: any
}

/**
 * Transport-only messages don't follow the mandatory event schema
 * but we can wrap them or handle them specifically.
 * For simplicity in this implementation, we'll allow them to have a partial schema.
 */
export interface TransportMessage {
    type: "IDENTIFY" | "AGENT_CONNECTED" | "AGENT_DISCONNECTED" | "WORKSPACE_CONNECTED" | "WORKSPACE_DISCONNECTED"
    payload?: any
}

export type WebSocketMessage = AgentMessage | TransportMessage

export interface AgentHandler {
    onConnect?: (send: (msg: WebSocketMessage) => void) => void
    onMessage: (msg: WebSocketMessage, send: (msg: WebSocketMessage) => void) => Promise<void>
    onDisconnect?: () => void
}
