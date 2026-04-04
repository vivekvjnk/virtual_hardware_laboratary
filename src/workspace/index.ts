import { WorkspaceClient } from "./workspaceClient.js";
import { WORKSPACE_DIR } from "../config/paths.js";
import { COWWorkspaceManager } from "../utils/cowWorkspace.js";
import { setProjectDir } from "./projectContext.js";

const SERVER_URL = process.env.VHL_WS_SERVER || "ws://0.0.0.0:1080";
const WORKSPACE_PATH = process.env.VHL_WORKSPACE_DIR || WORKSPACE_DIR;

console.log("[Runtime Workspace] Starting workspace client...");
console.log(`[Runtime Workspace] Server URL: ${SERVER_URL}`);
console.log(`[Runtime Workspace] Workspace Path: ${WORKSPACE_PATH}`);

// Cleanup any stale evaluation workspaces on startup
await COWWorkspaceManager.cleanupAll();
setProjectDir(null);

const client = new WorkspaceClient(SERVER_URL, WORKSPACE_PATH);

client.connect().catch((err) => {
    console.error("[Runtime Workspace] Failed to start workspace client:", err);
    process.exit(1);
});
