import { runSnapshotServer } from "./server.js";

runSnapshotServer().catch((err: any) => {
    console.error("UI Snapshot MCP Server failed:", err);
    process.exit(1);
});
