import { WorkspaceClient } from "./workspaceClient.js";
import { WORKSPACE_DIR } from "../config/paths.js";
import { COWWorkspaceManager } from "../utils/cowWorkspace.js";

const SERVER_URL = process.env.VHL_WS_SERVER || "ws://localhost:1080";
const WORKSPACE_PATH = process.env.VHL_WORKSPACE_DIR || WORKSPACE_DIR;

console.log("[Workspace] Starting workspace client...");
console.log(`[Workspace] Server URL: ${SERVER_URL}`);
console.log(`[Workspace] Workspace Path: ${WORKSPACE_PATH}`);

// Cleanup any stale evaluation workspaces on startup
await COWWorkspaceManager.cleanupAll();

const client = new WorkspaceClient(SERVER_URL, WORKSPACE_PATH);

client.connect().catch((err) => {
    console.error("[Workspace] Failed to start workspace client:", err);
    process.exit(1);
});
