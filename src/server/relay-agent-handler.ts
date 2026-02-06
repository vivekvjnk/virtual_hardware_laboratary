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

    private currentSend: ((msg: WebSocketMessage) => void) | null = null
    private role: "ui" | "agent" | null = null

    onConnect(send: (msg: WebSocketMessage) => void) {
        this.currentSend = send
        // Notify new UI connection about agent status (Transport-only)
        if (RelayAgentHandler.agentClient) {
            send({ type: "AGENT_CONNECTED" })
        } else {
            send({ type: "AGENT_DISCONNECTED" })
        }
    }

    async onMessage(msg: WebSocketMessage, send: (msg: WebSocketMessage) => void) {
        if (msg.type === "IDENTIFY") {
            this.handleIdentify(msg.payload?.role, send)
            return
        }

        if (this.role === "ui") {
            // UI (Runtime) -> Agent (Backend)
            // Rule: Runtime emits HUMAN_INPUT, REFERENCE_UPLOADED, INTERRUPT_REQUEST
            if (RelayAgentHandler.agentClient) {
                RelayAgentHandler.agentClient(msg)
            } else {
                send({ type: "ERROR", payload: { message: "No agent client connected", scope: "runtime", severity: "error" } } as any)
            }
        } else if (this.role === "agent") {
            // Agent (Backend) -> all UIs (Runtime)
            // Rule: Backend emits STATE_TRANSITION, EVALUATION_UPDATE, ARTIFACT_UPDATED, etc.
            RelayAgentHandler.uiClients.forEach(uiSend => uiSend(msg))
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
        } else if (role === "agent") {
            this.role = "agent"
            RelayAgentHandler.agentClient = send
            console.log("RelayAgentHandler: Agent client identified")
            // Notify all UIs that agent is connected
            RelayAgentHandler.uiClients.forEach(uiSend => uiSend({ type: "AGENT_CONNECTED" }))
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
        }
    }
}
