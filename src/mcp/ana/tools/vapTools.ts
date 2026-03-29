
import { WebSocket } from 'ws';
import { randomUUID } from 'crypto';

const RELAY_URL = process.env.VHL_WS_SERVER || 'ws://0.0.0.0:1080';

export async function evaluateCircuit(args: { circuit_name: string, blob_id: string, iteration_id?: string }) {
    console.log(`[MCP VAP] Triggering VAP evaluation for ${args.circuit_name}`);

    return new Promise((resolve, reject) => {
        const ws = new WebSocket(RELAY_URL);

        const timeout = setTimeout(() => {
            ws.terminate();
            reject(new Error('VAP evaluation timed out after 5 minutes'));
        }, 300000); // 5 minutes

        ws.on('open', () => {
            ws.send(JSON.stringify({
                id: randomUUID(),
                type: 'IDENTIFY',
                payload: { role: 'vap_mcp_agent' },
                timestamp: new Date().toISOString(),
                source: 'vap_mcp_agent'
            }));

            ws.send(JSON.stringify({
                id: randomUUID(),
                type: 'VAP_EXECUTE',
                timestamp: new Date().toISOString(),
                source: 'vap_mcp_agent',
                payload: {
                    circuit_name: args.circuit_name,
                    blob_id: args.blob_id,
                    iteration_id: args.iteration_id
                }
            }));
        });

        ws.on('message', (data) => {
            try {
                const msg = JSON.parse(data.toString());
                if (msg.type === 'VAP_COMPLETE') {
                    // In current implementation, VAPRuntime enforces single task.
                    // So we can assume this is our task.
                    // We can also verify task_id if we had it, but VAP_EXECUTE doesn't return it yet.
                    clearTimeout(timeout);
                    ws.close();
                    resolve(msg.payload);
                }
            } catch (err) {
                console.error('[MCP VAP] Failed to parse message:', err);
            }
        });

        ws.on('error', (err) => {
            clearTimeout(timeout);
            reject(err);
        });

        ws.on('close', () => {
            console.log('[MCP VAP] WebSocket connection closed');
        });
    });
}

export async function applyVapDecision(args: { task_id: string, decision: 'ACCEPT' | 'REJECT' }) {
    console.log(`[MCP VAP] Applying VAP decision ${args.decision} for task ${args.task_id}`);

    return new Promise((resolve, reject) => {
        const ws = new WebSocket(RELAY_URL);

        ws.on('open', () => {
            ws.send(JSON.stringify({
                id: randomUUID(),
                type: 'IDENTIFY',
                payload: { role: 'vap_mcp_agent' },
                timestamp: new Date().toISOString(),
                source: 'vap_mcp_agent'
            }));

            ws.send(JSON.stringify({
                id: randomUUID(),
                type: 'VAP_DECISION',
                timestamp: new Date().toISOString(),
                source: 'vap_mcp_agent',
                payload: {
                    task_id: args.task_id,
                    decision: args.decision
                }
            }));

            // For VAP_DECISION, we don't necessarily get a response back over websocket 
            // in the current implementation (it just processes it).
            // However, we can close after sending.
            setTimeout(() => {
                ws.close();
                resolve({ status: 'OK', task_id: args.task_id, decision: args.decision });
            }, 500);
        });

        ws.on('error', (err) => {
            reject(err);
        });
    });
}
