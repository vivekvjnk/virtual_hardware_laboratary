
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
    ListToolsRequestSchema,
    CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ObservationCommitSchema, VapEvaluationSchema, VapDecisionSchema } from "./tools/schemas.js";
import { commitObservation } from "./tools/commitObservation.js";
import { evaluateCircuit, applyVapDecision } from "./tools/vapTools.js";
import { commitManager } from "./commitManager.js";
import express from "express";

const OBSERVE_TOOLS = [
    {
        name: "commit_observation",
        description: "Commit an observation found during analysis. An observation can be about an issue or a confirmation of correctness.",
        inputSchema: ObservationCommitSchema,
    }
];

const VAP_TOOLS = [
    {
        name: "evaluate_circuit",
        description: "Trigger VAP evaluation for a circuit code artifact. Waits for completion and returns evaluation results.",
        inputSchema: VapEvaluationSchema,
    },
    {
        name: "apply_vap_decision",
        description: "Apply a decision (ACCEPT/REJECT) on a previously evaluated circuit task. ACCEPT commits the changes to the main workspace.",
        inputSchema: VapDecisionSchema,
    }
];

const ALL_TOOLS = [...OBSERVE_TOOLS, ...VAP_TOOLS];

/**
 * Helper: always return structured JSON for OpenHands
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

/**
 * Create and configure the ANA Commit MCP Server.
 */
export function createAnaServer(): Server {
    const server = new Server(
        {
            name: "ana-commit-server",
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
            tools: ALL_TOOLS,
        };
    });

    /**
     * Tool dispatcher
     */
    server.setRequestHandler(CallToolRequestSchema, async (request) => {
        const { name, arguments: args } = request.params;

        switch (name) {
            case "commit_observation": {
                const result = await commitObservation(args as any);
                return jsonResult(result);
            }

            case "evaluate_circuit": {
                const result = await evaluateCircuit(args as any);
                return jsonResult(result);
            }

            case "apply_vap_decision": {
                const result = await applyVapDecision(args as any);
                return jsonResult(result);
            }

            default:
                throw new Error(`Unknown tool: ${name}`);
        }
    });

    return server;
}

export async function runAnaServer() {
    const transportType = process.env.ANA_TRANSPORT || "stdio";
    const serverInstance = createAnaServer();

    if (transportType === "http") {
        const port = parseInt(process.env.ANA_PORT || "8081", 10);
        const app = express();
        app.use(express.json());

        // Health check
        app.get("/health", (req, res) => {
            res.status(200).send({ status: "ok" });
        });

        // Commits log query
        app.get("/mcp/commits", (req, res) => {
            const since = req.query.since ? parseInt(req.query.since as string, 10) : undefined;
            const endpoint = req.query.endpoint as string | undefined;
            res.json({ commits: commitManager.getCommits(since, endpoint) });
        });

        // Legacy tool listing via REST
        app.get("/mcp/:scope_endpoint/tools", (req, res) => {
            const scope = req.params.scope_endpoint;
            if (scope === "observe") {
                res.json(OBSERVE_TOOLS.map(t => ({ ...t, schema: t.inputSchema, target_channel: "OBSERVATION_MESSAGE", visibility_scope: "/mcp/observe" })));
            } else if (scope === "vap") {
                res.json(VAP_TOOLS.map(t => ({ ...t, schema: t.inputSchema, visibility_scope: "/mcp/vap" })));
            } else {
                res.json([]);
            }
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

        // Hybrid endpoint support (path-based scoping if needed)
        app.post("/mcp/:scope_endpoint", (req, res) => {
            const message = req.body;
            const scope = req.params.scope_endpoint;

            if (message.jsonrpc === "2.0") {
                // Scoping logic for standard MCP
                if (message.method === "tools/list") {
                    let tools = ALL_TOOLS;
                    if (scope === "observe") {
                        tools = OBSERVE_TOOLS;
                    } else if (scope === "vap") {
                        tools = VAP_TOOLS;
                    }
                    console.log(`[ANA MCP] Scoped tools/list for ${scope}: returning ${tools.length} tools`);
                    return res.json({
                        jsonrpc: "2.0",
                        id: message.id,
                        result: { tools }
                    });
                }

                if (message.method === "tools/call") {
                    const toolName = message.params.name;
                    if (scope === "observe" && toolName !== "commit_observation") {
                        return res.status(400).json({
                            jsonrpc: "2.0",
                            id: message.id,
                            error: { code: -32601, message: `Tool '${toolName}' is not visible in endpoint '/mcp/observe'.` }
                        });
                    }
                    if (scope === "vap" && (toolName !== "evaluate_circuit" && toolName !== "apply_vap_decision")) {
                        return res.status(400).json({
                            jsonrpc: "2.0",
                            id: message.id,
                            error: { code: -32601, message: `Tool '${toolName}' is not visible in endpoint '/mcp/vap'.` }
                        });
                    }
                }

                if (message.id !== undefined && message.id !== null) {
                    pendingRequests.set(message.id, res);
                } else {
                    res.status(202).send();
                }
                if (transport.onmessage) {
                    transport.onmessage(message);
                }
            } else if (message.tool_name) {
                // Legacy CommitRequest support
                const fullScope = `/mcp/${scope}`;
                if (message.tool_name === "commit_observation") {
                    if (fullScope !== "/mcp/observe") {
                        res.status(400).send({ error: `Tool '${message.tool_name}' is not visible in endpoint '${fullScope}'.` });
                        return;
                    }
                    const payload = message.payload || { ...message };
                    delete (payload as any).tool_name;

                    commitObservation(payload as any)
                        .then(result => res.json(result))
                        .catch(err => res.status(500).send({ error: err.message }));
                } else {
                    res.status(400).send({ error: `Tool '${message.tool_name}' not found.` });
                }
            } else {
                res.status(400).send({ error: "Invalid request format. Expected JSON-RPC 2.0 or legacy CommitRequest." });
            }
        });

        await serverInstance.connect(transport as any);
        app.listen(port, "0.0.0.0", () => {
            console.error(`ANA Commit MCP Server running on HTTP port ${port}`);
        });
    } else {
        if (process.stdin.isTTY) {
            throw new Error(
                "MCP stdio server cannot run in TTY mode.\n" +
                "Start this server from an MCP client or pipe stdin."
            );
        }

        const transport = new StdioServerTransport();
        await serverInstance.connect(transport);
        console.error("ANA Commit MCP Server running on stdio");
    }
}
