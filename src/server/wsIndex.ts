import { runWsServer } from "./wsServer.js";

runWsServer().catch((err) => {
    console.error("Agent WebSocket server failed:", err);
    process.exit(1);
});
