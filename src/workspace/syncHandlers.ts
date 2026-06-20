import { randomUUID } from "crypto";
import * as path from "path";
import * as fs from "fs/promises";
import { TEMP_DIR } from "../config/paths.js";
import { pushObject, pullObject, ensureBucket } from "../utils/minio.js";
import { compressDirectory, decompressZip, runPredefinedOperations } from "./fileOperations.js";
import { AgentMessage } from "../server/types.js";
import { RuntimeSender } from "./types.js";
import { ROLE_RUNTIME } from "../server/roles.js";

export async function handleWorkspaceUpload(
    msg: AgentMessage,
    
    sender: RuntimeSender
) {
    try {
        console.log("[Runtime Workspace] Processing WORKSPACE_UPLOAD");
        const requestId = msg.id;

        await ensureBucket();

        const zipName = `workspace_${randomUUID()}.zip`;
        const zipPath = path.join(TEMP_DIR, zipName);
        await fs.mkdir(TEMP_DIR, { recursive: true });

        console.log(`[Runtime Workspace] Compressing ${workspaceDir} to ${zipPath}`);
        await compressDirectory(workspaceDir, zipPath);

        console.log(`[Runtime Workspace] Uploading ${zipName} to object store`);
        await pushObject(zipPath, zipName);

        sender.send({
            id: randomUUID(),
            artifact_id: zipName,
            type: "WORKSPACE_SYNC_COMPLETE",
            timestamp: new Date().toISOString(),
            source: ROLE_RUNTIME,
            payload: {
                original_request_id: requestId,
                status: "success"
            }
        });
        console.log(`[Runtime Workspace] Sync complete. Artifact ID: ${zipName}`);

        await fs.unlink(zipPath).catch(() => { });

    } catch (err: any) {
        console.error("[Runtime Workspace] Upload failed:", err);
        sender.sendError("WORKSPACE_UPLOAD_FAILED", err.message);
    }
}

export async function handleWorkspaceDownload(
    msg: AgentMessage,
    workspaceDir: string,
    sender: RuntimeSender
) {
    try {
        console.log("[Runtime Workspace] Processing WORKSPACE_DOWNLOAD");
        const artifactId = msg.artifact_id;
        if (!artifactId) {
            throw new Error("No artifact_id provided in WORKSPACE_UPLOAD message");
        }

        const tempDir = path.join(TEMP_DIR, `download_${randomUUID()}`);
        console.log(`[Runtime Workspace] Pulling artifact ${artifactId} to ${tempDir}`);
        const localZipPath = await pullObject(artifactId, tempDir);

        console.log(`[Runtime Workspace] Decompressing to ${workspaceDir}`);
        await decompressZip(localZipPath, workspaceDir);

        console.log("[Runtime Workspace] Running predefined file operations");
        await runPredefinedOperations(workspaceDir);

        sender.send({
            id: randomUUID(),
            type: "WORKSPACE_SYNC_COMPLETE",
            artifact_id: artifactId,
            timestamp: new Date().toISOString(),
            source: ROLE_RUNTIME,
            payload: {
                status: "success",
                operation: "download"
            }
        });
        console.log("[Runtime Workspace] Download and sync complete");

        await fs.rm(tempDir, { recursive: true, force: true }).catch(() => { });

    } catch (err: any) {
        console.error("[Runtime Workspace] Download failed:", err);
        sender.sendError("WORKSPACE_DOWNLOAD_FAILED", err.message);
    }
}
