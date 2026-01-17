import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
    ListToolsRequestSchema,
    CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { HttpServerTransport } from "../mcp/transport/HttpServerTransport.js";
import { vapInit } from "./tools/vapInit.js";
import { vapStatus } from "./tools/vapStatus.js";

/**
 * Helper: always return structured JSON
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

export function createVapServer(): Server {
    const server = new Server(
        {
            name: "vhl-vap",
            version: "0.1.0",
        },
        {
            capabilities: {
                tools: {},
            },
        }
    );

    server.setRequestHandler(ListToolsRequestSchema, async () => {
        return {
            tools: [
                {
                    name: "VAP_init",
                    description: "Initialize a VHL ANA Process(VAP) for evaluating a circuit.",
                    inputSchema: {
                        type: "object",
                        properties: {
                            circuit_name: {
                                type: "string",
                                description: "Name of the circuit (without extension)",
                            },
                            blob_id: {
                                type: "string",
                                description: "MinIO object name (Blob ID) of the circuit file",
                            },
                        },
                        required: ["circuit_name", "blob_id"],
                    },
                },
                {
                    name: "VAP_status",
                    description: "Poll the status of a VAP evaluation process.",
                    inputSchema: {
                        type: "object",
                        properties: {
                            task_id: {
                                type: "string",
                                description: "Task ID returned by VAP_init",
                            },
                        },
                        required: ["task_id"],
                    },
                },
            ],
        };
    });

    server.setRequestHandler(CallToolRequestSchema, async (request) => {
        const { name, arguments: args } = request.params;
        console.log(`[VAP] Tool request: ${name}`);

        switch (name) {
            case "VAP_init": {
                const { circuit_name, blob_id } = args as {
                    circuit_name: string;
                    blob_id: string;
                };
                const result = await vapInit(circuit_name, blob_id);
                return jsonResult(result);
            }

            case "VAP_status": {
                const { task_id } = args as { task_id: string };
                const result = await vapStatus(task_id);
                return jsonResult(result);
            }

            default:
                throw new Error(`Unknown tool: ${name}`);
        }
    });

    return server;
}

export async function runVapServer() {
    const transportType = process.env.VHL_TRANSPORT || "http"; // Default to HTTP for VAP
    const serverInstance = createVapServer();

    if (transportType === "http") {
        const port = parseInt(process.env.VAP_PORT || "8081", 10);
        const transport = new HttpServerTransport(port);
        await serverInstance.connect(transport);
        console.error(`VHL VAP Server running on HTTP port ${port}`);
    } else {
        const transport = new StdioServerTransport();
        await serverInstance.connect(transport);
    }
}
