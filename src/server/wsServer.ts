import express from 'express';
import multer from 'multer';
import cors from 'cors';
import { createServer } from "http";
import path from 'path';
import fs from 'fs/promises';
import * as os from 'os';
import { randomUUID } from 'crypto';
import { TEMP_DIR, WORKSPACE_DIR } from "../config/paths.js";
import { decompressZip } from "../workspace/fileOperations.js";
import { ensureAgentWebSocketServer } from "./agent-websocket-server.js"
import { RelayAgentHandler } from "./relay-agent-handler.js"

const upload = multer({ dest: path.join(os.tmpdir(), 'vhl-uploads/') });

export const runWsServer = async () => {
    console.log("-----------------------------------------")
    console.log("INITIALIZING VHL AGENT WEBSOCKET SERVER...")
    console.log("-----------------------------------------")
    try {
        const app = express();
        app.use(cors());
        const httpServer = createServer(app);
        
        app.post('/api/upload-project-zip', upload.single('file'), async (req, res) => {
            const file = (req as any).file;
            if (!file) {
                return res.status(400).send('No file uploaded.');
            }
            
            const zipPath = file.path;
            // Extract directly into the workspace folder's .zip_temp, as AOSM expects
            const zipTempDir = path.join(WORKSPACE_DIR, '.zip_temp');
            await fs.mkdir(zipTempDir, { recursive: true });
            
            try {
                // Clear existing temp dir
                await fs.rm(zipTempDir, { recursive: true, force: true });
                await fs.mkdir(zipTempDir, { recursive: true });
                
                await decompressZip(zipPath, zipTempDir);
                await fs.unlink(zipPath); // Clean up zip
                res.status(200).json({ status: 'success', path: zipTempDir });
            } catch (err: any) {
                console.error("Error extracting zip:", err);
                res.status(500).send("Extraction failed");
            }
        });

        ensureAgentWebSocketServer(() => new RelayAgentHandler(), { server: httpServer });
        
        httpServer.listen(1080, '0.0.0.0', () => {
             console.log("HTTP/WS Server listening on port 1080");
        });

    } catch (err) {
        console.error("Failed to start Agent WebSocket server:", err)
        throw err
    }
}
