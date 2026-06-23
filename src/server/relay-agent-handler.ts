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
import { ROLE_WEBUI, ROLE_AGENT_BACKEND, ROLE_RUNTIME, ROLE_TEST_OBSERVER, VHLRole } from "./roles.js"

/**
 * A handler that relays messages between UI clients and the Agent client.
 * This is the central logic for the Runframe WebSocket Server.
 */
export class RelayAgentHandler implements AgentHandler {
    private static uiClients: Set<(msg: WebSocketMessage) => void> = new Set()
    private static agentClient: ((msg: WebSocketMessage) => void) | null = null
    private static runtimeClient: ((msg: WebSocketMessage) => void) | null = null
    private static observerClients: Set<(msg: WebSocketMessage) => void> = new Set()

    private currentSend: ((msg: WebSocketMessage) => void) | null = null
    private role: VHLRole | "vap_mcp_agent" | null = null

    onConnect(send: (msg: WebSocketMessage) => void) {
        this.currentSend = send
    }

    async onMessage(msg: WebSocketMessage, send: (msg: WebSocketMessage) => void) {
        // Broadcast all incoming messages to observers for testing/debugging
        if (RelayAgentHandler.observerClients.size > 0) {
            const observation = {
                ...msg,
                _direction: "incoming",
                _observed_at: new Date().toISOString(),
                _observed_role: this.role
            };
            RelayAgentHandler.observerClients.forEach(obsSend => obsSend(observation as any));
        }

        if (msg.type === "IDENTIFY") {
            this.handleIdentify(msg.payload?.role, send)
            return
        }
        // Superset case. If role is any one of the identified ones, check if the message has `target`. If target is specified, route based on that. Otherwise use the legacy routing based on role and message type.
        if ("target" in msg && msg.target) {
            const target = msg.target
            if (target === ROLE_AGENT_BACKEND) {
                if (RelayAgentHandler.agentClient) {
                    console.debug(`[Websocket Relay] Routing message to Agent backend based on target: ${msg.type}`)
                    RelayAgentHandler.agentClient(msg)
                } else {
                    send({ type: "ERROR", payload: { message: "No agent client connected", scope: "target_routing", severity: "error" } } as any)
                }
            }
            else if (target === ROLE_RUNTIME) {
                if (RelayAgentHandler.runtimeClient) {
                    console.debug(`[Websocket Relay] Routing message to VHL Runtime based on target: ${msg.type}`)
                    RelayAgentHandler.runtimeClient(msg)
                } else {
                    send({ type: "ERROR", payload: { message: "No runtime client connected", scope: "target_routing", severity: "error" } } as any)
                }
            }
            else if (target === ROLE_WEBUI) {
                console.debug(`[Websocket Relay] Routing message to WebUI clients based on target: ${msg.type}`)
                RelayAgentHandler.uiClients.forEach(uiSend => uiSend(msg));
            }
            else {
                send({ type: "ERROR", payload: { message: `Invalid target specified: ${target}`, scope: "target_routing", severity: "error" } } as any)
            }
            return
        }    
        if (this.role === ROLE_WEBUI || this.role == ROLE_TEST_OBSERVER) {
            // Heartbeat check
            if (msg.type === "HEARTBEAT") {
                send({ type: "HEARTBEAT_ACK" })
                return
            }

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

            // Send feedback that identification was successful
            send({ type: "IDENTIFIED" })

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
        } else if (role === ROLE_TEST_OBSERVER) {
            this.role = ROLE_TEST_OBSERVER
            RelayAgentHandler.observerClients.add(send)
            console.log("RelayAgentHandler: Test Observer client identified")

            // Notify observer of existing connections
            if (RelayAgentHandler.agentClient) {
                send({ type: "AGENT_CONNECTED", source: ROLE_AGENT_BACKEND } as any)
            }
            if (RelayAgentHandler.runtimeClient) {
                send({ type: "WORKSPACE_CONNECTED", source: ROLE_RUNTIME } as any)
            }
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
        } else if (this.role === ROLE_TEST_OBSERVER && this.currentSend) {
            RelayAgentHandler.observerClients.delete(this.currentSend)
            console.log("RelayAgentHandler: Test Observer client disconnected")
        }
    }
}
