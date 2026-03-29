import { WebSocketServer, WebSocket } from "ws"
import type { AgentHandler, WebSocketMessage } from "./types.js"
import type { Server } from "http"

export interface AgentWebSocketServerOptions {
    port?: number
    server?: Server
    path?: string
    host?: string
}

/**
 * A modular WebSocket server for the Agentic Chatbox.
 * It uses a handler factory to create a new handler for each connection,
 * allowing for dependency injection and decoupled state management.
 */
export class AgentWebSocketServer {
    private wss: WebSocketServer | null = null
    private createHandler: () => AgentHandler

    constructor(createHandler: () => AgentHandler) {
        this.createHandler = createHandler
    }

    start(options: AgentWebSocketServerOptions = { port: 1080 }) {
        if (options.port && !options.host) {
            (options as any).host = "0.0.0.0"
        }
        this.wss = new WebSocketServer(options)

        this.wss.on("listening", () => {
            const addr = this.wss?.address()
            if (typeof addr === "object" && addr) {
                console.log(`✅ Agent WebSocket Server is LISTENING on ${addr.address}:${addr.port}`)
            }
        })

        this.wss.on("connection", (ws: WebSocket) => {
            console.log("[Websocket Relay]: New client connected")

            const handler = this.createHandler()

            const send = (msg: WebSocketMessage) => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify(msg))
                }
            }

            if (handler.onConnect) {
                handler.onConnect(send)
            }

            ws.on("message", async (data: any) => {
                const dataString = data.toString()
                console.debug(`[Websocket Relay] Received raw message: ${dataString}`)
                try {
                    const msg = JSON.parse(dataString) as WebSocketMessage
                    console.log(`[Websocket Relay] Handling message of type: ${msg.type}`)
                    await handler.onMessage(msg, send)
                } catch (err) {
                    console.error("[Websocket Relay] Error handling message:", err, dataString)
                    ws.send(JSON.stringify({
                        type: "ERROR",
                        payload: { message: "Internal server error handling message", scope: "runtime", severity: "error" }
                    }))
                }
            })

            ws.on("close", (code, reason) => {
                console.log(`[Websocket Relay] Client disconnected. Code: ${code}, Reason: ${reason}`)
                if (handler.onDisconnect) {
                    handler.onDisconnect()
                }
            })

            ws.onerror = (err: any) => {
                console.error("[Websocket Relay]: WebSocket error", err)
            }
        })

        if (options.port) {
            console.log(`Agent WebSocket Server starting on ws://${options.host || "0.0.0.0"}:${options.port}${options.path || ""}`)
        } else if (options.server) {
            console.log(`Agent WebSocket Server attached to HTTP server at path: ${options.path || "/"}`)
        }
    }

    stop() {
        if (this.wss) {
            this.wss.close()
            this.wss = null
        }
    }
}

let globalServer: AgentWebSocketServer | null = null

/**
 * Ensures that an Agent WebSocket server is running.
 * If a server is already running, it returns the existing instance.
 */
export const ensureAgentWebSocketServer = (
    createHandler: () => AgentHandler,
    options: AgentWebSocketServerOptions = { port: 1080 }
) => {
    if (globalServer) return globalServer

    globalServer = new AgentWebSocketServer(createHandler)
    globalServer.start(options)
    return globalServer
}

/**
 * Helper function to create and start an Agent WebSocket server.
 */
export const startAgentWebSocketServer = (
    createHandler: () => AgentHandler,
    options: AgentWebSocketServerOptions = { port: 1080 }
) => {
    return ensureAgentWebSocketServer(createHandler, options)
}
