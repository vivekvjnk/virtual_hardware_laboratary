import { randomUUID } from "crypto"
import type { AgentHandler, WebSocketMessage } from "./types.js"

/**
 * A handler that relays messages between UI clients and the Agent client.
 * This is the central logic for the Runframe WebSocket Server.
 * 
 * According to Canonical v0.1:
 * - Runtime -> Backend (Observation Events): HUMAN_INPUT, REFERENCE_UPLOADED, INTERRUPT_REQUEST
 * - Backend -> Runtime (System Events): STATE_TRANSITION, EVALUATION_UPDATE, ARTIFACT_UPDATED, AUTHORITY_REQUIRED, ERROR
 */
export class RelayAgentHandler implements AgentHandler {
    private static uiClients: Set<(msg: WebSocketMessage) => void> = new Set()
    private static agentClient: ((msg: WebSocketMessage) => void) | null = null
    private static workspaceClient: ((msg: WebSocketMessage) => void) | null = null

    private currentSend: ((msg: WebSocketMessage) => void) | null = null
    private role: "ui" | "agent" | "vhl_workspace" | null = null

    onConnect(send: (msg: WebSocketMessage) => void) {
        this.currentSend = send
    }

    async onMessage(msg: WebSocketMessage, send: (msg: WebSocketMessage) => void) {
        if (msg.type === "IDENTIFY") {
            this.handleIdentify(msg.payload?.role, send)
            return
        }

        if (this.role === "ui") {
            // UI (Runtime) -> Agent (Backend)
            // 1. Always relay to Agent if connected
            if (RelayAgentHandler.agentClient) {
                console.debug("[Websocket Relay] Relaying message from UI to VHL_Agent_Backend:", msg)
                RelayAgentHandler.agentClient(msg)
            }

            // 2. Route specific messages to Workspace Client (Irrespective of Agent connectivity)
            if (msg.type === "START_DEV_SERVER" || msg.type === "GET_SYSTEM_STATE") {
                if (RelayAgentHandler.workspaceClient) {
                    console.debug("[Websocket Relay] Relaying message from UI to VHL_Runtime:", msg)
                    RelayAgentHandler.workspaceClient(msg)
                } else {
                    send({ type: "ERROR", payload: { message: "No workspace client connected", scope: "runtime", severity: "error" } } as any)
                }
            }
            // 3. Fallback: If no agent connected and message wasn't one of the special types
            else if (!RelayAgentHandler.agentClient) {
                send({ type: "ERROR", payload: { message: "No agent client connected", scope: "runtime", severity: "error" } } as any)
            }
        } else if (this.role === "vhl_workspace") {
            // Workspace Client -> Agent (Backend)
            // Some events also go to UI (Runtime)
            if (msg.type === "VHL_WORKSPACE_READY" || msg.type === "DEV_SERVER_READY" || msg.type === "SYSTEM_STATE") {
                RelayAgentHandler.uiClients.forEach(uiSend => uiSend(msg));
            }

            if (RelayAgentHandler.agentClient) {
                RelayAgentHandler.agentClient(msg)
            } else {
                send({ type: "ERROR", payload: { message: "No agent client connected", scope: "vhl_workspace", severity: "error" } } as any)
            }
        } else if (this.role === "agent") {
            // Agent (Backend) -> UI (Runtime) or Workspace Client
            if (msg.type == "PROJECT_CREATED" || msg.type == "PROJECT_LOADED") {
                // Send message to uiclient and workspace client
                RelayAgentHandler.uiClients.forEach(uiSend => uiSend(msg))
                if (RelayAgentHandler.workspaceClient) {
                    RelayAgentHandler.workspaceClient(msg)
                }
            } // To workspace client
            else if (msg.type === "WORKSPACE_DOWNLOAD" || msg.type === "WORKSPACE_UPLOAD" ||
                msg.type === "VAP_INIT" || msg.type === "VAP_DECISION" || msg.type === "START_DEV_SERVER" ||
                msg.type === "SYNC_TRIGGER" || msg.type === "UPLOAD_PROPOSAL" || msg.type === "HASH_REQUEST" || 
                msg.type === "HASH_RESPONSE") {
                if (RelayAgentHandler.workspaceClient) {
                    RelayAgentHandler.workspaceClient(msg)
                } else {
                    send({ type: "ERROR", payload: { message: "No workspace client connected", scope: "backend", severity: "error" } } as any)
                }
            }
            else {
                RelayAgentHandler.uiClients.forEach(uiSend => uiSend(msg))
            }
        } else {
            // Unidentified client
            send({ type: "ERROR", payload: { message: "Please IDENTIFY yourself first", scope: "runtime", severity: "fatal" } } as any)
        }
    }

    private handleIdentify(role: string, send: (msg: WebSocketMessage) => void) {
        if (role === "ui") {
            this.role = "ui"
            RelayAgentHandler.uiClients.add(send)
            console.log("RelayAgentHandler: UI client identified")

            // Notify new UI connection about agent status (Transport-only)
            if (RelayAgentHandler.agentClient) {
                send({ type: "AGENT_CONNECTED" })
            } else {
                send({ type: "AGENT_DISCONNECTED" })
            }

            if (RelayAgentHandler.workspaceClient) {
                send({ type: "WORKSPACE_CONNECTED" })
            } else {
                send({ type: "WORKSPACE_DISCONNECTED" })
            }

        } else if (role === "agent") {
            this.role = "agent"
            RelayAgentHandler.agentClient = send
            console.log("RelayAgentHandler: Agent client identified")
            // Notify all UIs that agent is connected
            RelayAgentHandler.uiClients.forEach(uiSend => uiSend({ type: "AGENT_CONNECTED" }))

            // Notify agent about workspace status
            if (RelayAgentHandler.workspaceClient) {
                send({ id: randomUUID(), type: "WORKSPACE_CONNECTED", source: "backend", timestamp: new Date().toISOString() })
            } else {
                send({ id: randomUUID(), type: "WORKSPACE_DISCONNECTED", source: "backend", timestamp: new Date().toISOString() })
            }

        } else if (role === "vhl_workspace") {
            this.role = "vhl_workspace"
            RelayAgentHandler.workspaceClient = send
            console.log("RelayAgentHandler: Workspace client identified")

            // Notify agent and all UIs that workspace client is connected
            if (RelayAgentHandler.agentClient) {
                RelayAgentHandler.agentClient({ type: "WORKSPACE_CONNECTED" })
            }
            RelayAgentHandler.uiClients.forEach(uiSend => uiSend({ type: "WORKSPACE_CONNECTED" }))
        }
    }

    onDisconnect() {
        if (this.role === "ui" && this.currentSend) {
            RelayAgentHandler.uiClients.delete(this.currentSend)
        } else if (this.role === "agent") {
            RelayAgentHandler.agentClient = null
            console.log("RelayAgentHandler: Agent client disconnected")
            // Notify all UIs that agent is gone
            RelayAgentHandler.uiClients.forEach(uiSend => uiSend({ type: "AGENT_DISCONNECTED" }))
        } else if (this.role === "vhl_workspace") {
            RelayAgentHandler.workspaceClient = null
            console.log("RelayAgentHandler: Workspace client disconnected")
            // Notify agent and UIs that workspace is gone
            if (RelayAgentHandler.agentClient) {
                RelayAgentHandler.agentClient({ type: "WORKSPACE_DISCONNECTED" })
            }
            RelayAgentHandler.uiClients.forEach(uiSend => uiSend({ type: "WORKSPACE_DISCONNECTED" }))
        }
    }
}
