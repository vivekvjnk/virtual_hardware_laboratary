import { WORKSPACE_DIR } from "../config/paths.js";
import { setProjectDir } from "./projectContext.js";
import { VHLWebUI } from "./vhlWebUI.js";

const WORKSPACE_PATH = process.env.VHL_WORKSPACE_DIR || WORKSPACE_DIR;

console.log("[VHLWebUI] Starting Native Substrate...");
console.log(`[VHLWebUI] Workspace Path: ${WORKSPACE_PATH}`);

setProjectDir(null);

const webui = new VHLWebUI(WORKSPACE_PATH);
await webui.isReady;
console.log(`[VHLWebUI] Native Substrate active on API port ${webui.getApiPort()}`);
