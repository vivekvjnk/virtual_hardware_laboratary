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
    | "VAP_EXECUTE"
    | "VAP_COMPLETE"
    | "VAP_DECISION"
    // Human In Loop Mangement
    | "HIL_REQUEST"
    // Project Initialization
    | "CREATE_PROJECT"
    | "PROJECT_CREATED"
    | "LOAD_PROJECT"
    | "PROJECT_LOADED"
    | "LIST_PROJECTS"
    | "PROJECTS_LIST"
    | "SYNTHESIZE_CIRCUIT"
    | "CLOSE_PROJECT"
    | "PROJECT_CLOSED"
    // Dev Server Management
    | "DEV_SERVER_READY"
    // System State
    | "GET_SYSTEM_STATE"
    | "SYSTEM_STATE"
    | "PROJECT_STATE"
    | "AGENT_STATE"
    // Sync Protocol
    | "UPLOAD_REQUEST"
    | "DOWNLOAD_REQUEST"
    | "SYNC_COMPLETE"
    | "SYNC_ERROR"
    | "AGENT_HEALTH"
    | "MESSAGE_TO_AGENT"
    | "MESSAGE_FROM_AGENT"

import { ROLE_WEBUI, ROLE_AGENT_BACKEND, ROLE_RUNTIME } from "./roles.js";

export interface AgentMessage {
    id: string
    type: EventType
    artifact_id: string | null
    timestamp: string // ISO-8601
    source: typeof ROLE_WEBUI | typeof ROLE_AGENT_BACKEND | typeof ROLE_RUNTIME
    target?: typeof ROLE_WEBUI | typeof ROLE_AGENT_BACKEND | typeof ROLE_RUNTIME
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

export type ProjectStatus = "initialized" | "uninitialized" | "initializing"
export type AgentStatus = "Running" | "Idle"

export interface ProjectStatePayload {
    backend_status: ProjectStatus
    runtime_status: ProjectStatus
}

export interface AgentStatePayload {
    archy: AgentStatus
    librarian: AgentStatus
    ana: AgentStatus
    aosm: AgentStatus
}
