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
import { ROLE_WEBUI, ROLE_AGENT_BACKEND, ROLE_RUNTIME, VHLRole } from "./roles.js"

/**
 * A handler that relays messages between UI clients and the Agent client.
 * This is the central logic for the Runframe WebSocket Server.
 */
export class RelayAgentHandler implements AgentHandler {
    private static uiClients: Set<(msg: WebSocketMessage) => void> = new Set()
    private static agentClient: ((msg: WebSocketMessage) => void) | null = null
    private static runtimeClient: ((msg: WebSocketMessage) => void) | null = null

    private currentSend: ((msg: WebSocketMessage) => void) | null = null
    private role: VHLRole | "vap_mcp_agent" | null = null

    onConnect(send: (msg: WebSocketMessage) => void) {
        this.currentSend = send
    }

    async onMessage(msg: WebSocketMessage, send: (msg: WebSocketMessage) => void) {
        if (msg.type === "IDENTIFY") {
            this.handleIdentify(msg.payload?.role, send)
            return
        }

        if (this.role === ROLE_WEBUI) {
            // UI (WebUI) -> Agent (Backend)
            if (RelayAgentHandler.agentClient) {
                console.debug("[Websocket Relay] WebUI -> Agent backend", msg.type)
                RelayAgentHandler.agentClient(msg)
            }

            // Route specific messages to Runtime Client
            if (msg.type === "GET_SYSTEM_STATE") {
                if (RelayAgentHandler.runtimeClient) {
                    console.debug("[Websocket Relay] WebUI -> VHL Runtime", msg.type)
                    RelayAgentHandler.runtimeClient(msg)
                } else {
                    send({ type: "ERROR", payload: { message: "No runtime client connected", scope: ROLE_WEBUI, severity: "error" } } as any)
                }
            }
            else if (!RelayAgentHandler.agentClient) {
                send({ type: "ERROR", payload: { message: "No agent client connected", scope: ROLE_WEBUI, severity: "error" } } as any)
            }
        } else if (this.role === ROLE_RUNTIME) {
            // Runtime -> Agent (Backend)
            // Some events also go to UI (WebUI)
            if (msg.type === "DEV_SERVER_READY" || msg.type === "SYSTEM_STATE" || msg.type === "PROJECT_STATE") {
                console.debug("[Websocket Relay] VHL Runtime -> WebUI", msg.type)
                RelayAgentHandler.uiClients.forEach(uiSend => uiSend(msg));
            }

            if (RelayAgentHandler.agentClient) {
                console.debug("[Websocket Relay] VHL Runtime -> Agent backend", msg.type)
                RelayAgentHandler.agentClient(msg)
            } else {
                send({ type: "ERROR", payload: { message: "No agent client connected", scope: ROLE_RUNTIME, severity: "error" } } as any)
            }
        } else if ((this.role === ROLE_AGENT_BACKEND) || (this.role === "vap_mcp_agent")) {
            // Intercept Heartbeat directly
            if (msg.type === "AGENT_HEALTH") {
                return 
            }

            // Agent (Backend) -> UI (WebUI) or Runtime Client
            if (msg.type == "PROJECT_CREATED" || msg.type == "PROJECT_LOADED") {
                console.debug("[Websocket Relay] Agent backend -> WebUI and VHL Runtime", msg.type)
                RelayAgentHandler.uiClients.forEach(uiSend => uiSend(msg))
                if (RelayAgentHandler.runtimeClient) {
                    RelayAgentHandler.runtimeClient(msg)
                }
            } else if (msg.type === "WORKSPACE_DOWNLOAD" || msg.type === "WORKSPACE_UPLOAD" ||
                msg.type === "VAP_EXECUTE" || msg.type === "VAP_DECISION" ||
                msg.type === "DOWNLOAD_REQUEST" || msg.type === "UPLOAD_REQUEST") {
                console.debug("[Websocket Relay] Agent backend -> VHL Runtime", msg.type)
                if (RelayAgentHandler.runtimeClient) {
                    RelayAgentHandler.runtimeClient(msg)
                } else {
                    send({ type: "ERROR", payload: { message: "No runtime client connected", scope: ROLE_AGENT_BACKEND, severity: "error" } } as any)
                }
            }
            else {
                console.debug("[Websocket Relay] Agent backend -> WebUI", msg.type)
                RelayAgentHandler.uiClients.forEach(uiSend => uiSend(msg))
            }
        } else {
            send({ type: "ERROR", payload: { message: "Please IDENTIFY yourself first", scope: "system", severity: "fatal" } } as any)
        }
    }

    private handleIdentify(role: string, send: (msg: WebSocketMessage) => void) {
        if (role === "ui" || role === ROLE_WEBUI) {
            this.role = ROLE_WEBUI
            RelayAgentHandler.uiClients.add(send)
            console.log(`RelayAgentHandler: WebUI client identified (${role})`)

            if (RelayAgentHandler.agentClient) {
                send({ type: "AGENT_CONNECTED" })
            } else {
                send({ type: "AGENT_DISCONNECTED" })
            }

            if (RelayAgentHandler.runtimeClient) {
                send({ type: "WORKSPACE_CONNECTED" })
            } else {
                send({ type: "WORKSPACE_DISCONNECTED" })
            }

        } else if (role === "agent" || role === ROLE_AGENT_BACKEND) {
            this.role = ROLE_AGENT_BACKEND
            RelayAgentHandler.agentClient = send
            console.log(`RelayAgentHandler: Agent client identified (${role})`)
            RelayAgentHandler.uiClients.forEach(uiSend => uiSend({ type: "AGENT_CONNECTED" }))

            if (RelayAgentHandler.runtimeClient) {
                send({ id: randomUUID(), type: "WORKSPACE_CONNECTED", source: ROLE_AGENT_BACKEND, timestamp: new Date().toISOString() })
            } else {
                send({ id: randomUUID(), type: "WORKSPACE_DISCONNECTED", source: ROLE_AGENT_BACKEND, timestamp: new Date().toISOString() })
            }

        } else if (role === "vhl_workspace" || role === "vhl_runtime" || role === ROLE_RUNTIME) {
            this.role = ROLE_RUNTIME
            RelayAgentHandler.runtimeClient = send
            console.log(`RelayAgentHandler: Runtime client identified (${role})`)

            if (RelayAgentHandler.agentClient) {
                RelayAgentHandler.agentClient({ type: "WORKSPACE_CONNECTED" })
            }
            RelayAgentHandler.uiClients.forEach(uiSend => uiSend({ type: "WORKSPACE_CONNECTED" }))
        }
    }

    onDisconnect() {
        if (this.role === ROLE_WEBUI && this.currentSend) {
            RelayAgentHandler.uiClients.delete(this.currentSend)
        } else if (this.role === ROLE_AGENT_BACKEND) {
            RelayAgentHandler.agentClient = null
            console.log("RelayAgentHandler: Agent client disconnected")
            RelayAgentHandler.uiClients.forEach(uiSend => uiSend({ type: "AGENT_DISCONNECTED" }))
        } else if (this.role === ROLE_RUNTIME) {
            RelayAgentHandler.runtimeClient = null
            console.log("RelayAgentHandler: Runtime client disconnected")
            RelayAgentHandler.uiClients.forEach(uiSend => uiSend({ type: "WORKSPACE_DISCONNECTED" }))
        }
    }
}
