import { ensureAgentWebSocketServer } from "./agent-websocket-server.js"
import { RelayAgentHandler } from "./relay-agent-handler.js"

export const runWsServer = async () => {
    console.log("-----------------------------------------")
    console.log("INITIALIZING VHL AGENT WEBSOCKET SERVER...")
    console.log("-----------------------------------------")
    try {
        ensureAgentWebSocketServer(() => new RelayAgentHandler())
    } catch (err) {
        console.error("Failed to start Agent WebSocket server:", err)
        throw err
    }
}
