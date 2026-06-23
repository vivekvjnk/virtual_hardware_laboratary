import { VHLRuntime } from "./vhlRuntime.js";
import { WORKSPACE_DIR } from "../config/paths.js";
import { COWWorkspaceManager } from "../utils/cowWorkspace.js";
import { setProjectDir } from "./projectContext.js";
import { VHLWebUI } from "./vhlWebUI.js";

const SERVER_URL = process.env.VHL_WS_SERVER || "ws://0.0.0.0:1080";
const WORKSPACE_PATH = process.env.VHL_WORKSPACE_DIR || WORKSPACE_DIR;

console.log("[VHLRuntime] Starting...");
console.log(`[VHLRuntime] Server URL: ${SERVER_URL}`);
console.log(`[VHLRuntime] Workspace Path: ${WORKSPACE_PATH}`);

// Cleanup any stale evaluation workspaces on startup
await COWWorkspaceManager.cleanupAll();
setProjectDir(null);

const client = new VHLRuntime(SERVER_URL, WORKSPACE_PATH);

const webui = new VHLWebUI(WORKSPACE_PATH)

client.connect().catch((err) => {
    console.error("[VHLRuntime] Failed to start:", err);
    process.exit(1);
});
