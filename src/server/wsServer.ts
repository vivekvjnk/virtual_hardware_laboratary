import { ensureAgentWebSocketServer } from "./agent-websocket-server.js"
import { RelayAgentHandler } from "./relay-agent-handler.js"
import express from "express";

export const runWsServer = async () => {
    console.log("-----------------------------------------")
    console.log("INITIALIZING VHL AGENT WEBSOCKET SERVER...")
    console.log("-----------------------------------------")
    try {
        ensureAgentWebSocketServer(() => new RelayAgentHandler())

        // Setup Unified Container Health Check on $PORT (default 8080)
        const app = express();
        app.get("/health", (req, res) => {
            res.status(200).json({ status: "healthy", service: "vhl_runtime" });
        });
        const port = parseInt(process.env.PORT || "8080", 10);
        app.listen(port, "0.0.0.0", () => {
             console.log(`✅ Unified Health Check server LISTENING on 0.0.0.0:${port}`);
        });
    } catch (err) {
        console.error("Failed to start Agent WebSocket server:", err)
        throw err
    }
}
