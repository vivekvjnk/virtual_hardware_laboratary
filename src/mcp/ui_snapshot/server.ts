
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
    ListToolsRequestSchema,
    CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import express from "express";
import { getProjectState } from "../../workspace/projectContext.js";
import path from "path";
import fs from "fs/promises";

/**
 * Helper: always return structured JSON for MCP results
 */
function jsonResult(value: unknown) {
    let text: string;

    try {
        text = JSON.stringify(value, null, 2);
    } catch {
        text = String(value);
    }
    return {
        content: [
            {
                type: "text",
                text,
            },
        ],
    };
}

const SchematicSnapshotSchema = {
    type: "object",
    properties: {},
};

const LayoutSnapshotSchema = {
    type: "object",
    properties: {},
};

/**
 * Common logic to retrieve a snapshot file from the active project's __snapshots__ directory.
 */
async function getSnapshot(type: "schematic" | "pcb") {
    const { projectDir, currentCircuitName } = getProjectState();
    if (!projectDir) {
        throw new Error("No active project");
    }

    const snapshotsDir = path.join(projectDir, "__snapshots__");

    // 1. Try to use the current circuit name from persisted state
    let baseName = currentCircuitName;

    // 2. If no circuit name is tracked, try to infer it from the snapshots directory
    if (!baseName) {
        try {
            const files = await fs.readdir(snapshotsDir);
            const match = files.find(f => f.endsWith(`-${type}.snap.svg`));
            if (match) {
                baseName = match.replace(`-${type}.snap.svg`, "");
            }
        } catch (err) {
            // Directory might not exist yet
        }
    }

    if (!baseName) {
        throw new Error(`Could not determine circuit name for ${type} snapshot in ${snapshotsDir}. Ensure StableCircuit has been updated.`);
    }

    const snapPath = path.join(snapshotsDir, `${baseName}-${type}.snap.svg`);
    try {
        const content = await fs.readFile(snapPath, "utf-8");
        return {
            success: true,
            type,
            circuit_name: baseName,
            content,
            path: snapPath
        };
    } catch (err: any) {
        return {
            success: false,
            error: `Snapshot not found at ${snapPath}. Error: ${err.message}. Make sure 'tsci snapshot' has run.`
        };
    }
}

/**
 * Create and configure the UI Snapshot MCP Server.
 */
export function createSnapshotServer(): Server {
    const server = new Server(
        {
            name: "ui-snapshot-server",
            version: "1.0.0",
        },
        {
            capabilities: {
                tools: {},
            },
        }
    );

    /**
     * Tool inventory
     */
    server.setRequestHandler(ListToolsRequestSchema, async () => {
        return {
            tools: [
                {
                    name: "get_schematic_snapshot",
                    description: "Get the latest schematic snapshot (SVG) of the active circuit.",
                    inputSchema: SchematicSnapshotSchema,
                },
                {
                    name: "get_layout_snapshot",
                    description: "Get the latest layout (PCB) snapshot (SVG) of the active circuit.",
                    inputSchema: LayoutSnapshotSchema,
                },
            ],
        };
    });

    /**
     * Tool dispatcher
     */
    server.setRequestHandler(CallToolRequestSchema, async (request) => {
        const { name } = request.params;

        switch (name) {
            case "get_schematic_snapshot": {
                const result = await getSnapshot("schematic");
                return jsonResult(result);
            }

            case "get_layout_snapshot": {
                const result = await getSnapshot("pcb");
                return jsonResult(result);
            }

            default:
                throw new Error(`Unknown tool: ${name}`);
        }
    });

    return server;
}

/**
 * Run the server with HTTP transport as requested.
 */
export async function runSnapshotServer() {
    const port = parseInt(process.env.SNAPSHOT_PORT || "8083", 10);
    const serverInstance = createSnapshotServer();

    const app = express();
    app.use(express.json());

    // Health check
    app.get("/health", (req, res) => {
        res.status(200).send({ status: "ok" });
    });

    // Standard MCP endpoint for HTTP
    const pendingRequests = new Map<string | number, express.Response>();

    const transport = {
        onclose: undefined as (() => void) | undefined,
        onerror: undefined as ((error: Error) => void) | undefined,
        onmessage: undefined as ((message: any) => void) | undefined,
        async start() { },
        async close() { },
        async send(message: any) {
            if (message.id !== undefined && message.id !== null) {
                const res = pendingRequests.get(message.id);
                if (res) {
                    res.json(message);
                    pendingRequests.delete(message.id);
                }
            }
        }
    };

    app.post("/mcp", (req, res) => {
        const message = req.body;
        if (message.id !== undefined && message.id !== null) {
            pendingRequests.set(message.id, res);
        } else {
            res.status(202).send();
        }
        if (transport.onmessage) {
            transport.onmessage(message);
        }
    });

    await serverInstance.connect(transport as any);
    app.listen(port, "0.0.0.0", () => {
        console.error(`UI Snapshot MCP Server running on HTTP port ${port}`);
    });
}
