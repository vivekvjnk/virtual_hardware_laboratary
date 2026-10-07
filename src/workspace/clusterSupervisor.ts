import { spawn, ChildProcess } from "node:child_process";
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import os from "node:os";
import net from "node:net";

export interface ClusterInstance {
    clusterId: string;
    port: number;
    url: string;
    worktreePath: string;
    type: "assembly" | "module";
    lead: string;
    process?: ChildProcess | null;
    pid?: number | null;
    status: "stopped" | "starting" | "running" | "error";
    startedAt?: string;
    error?: string;
}

export interface ClusterInfo {
    clusterId: string;
    port: number;
    url: string;
    worktreePath: string;
    type: "assembly" | "module";
    lead: string;
    status: "stopped" | "starting" | "running" | "error";
    pid?: number | null;
    startedAt?: string;
    error?: string;
}

export interface ClusterRoster {
    project_id: string;
    project_root: string;
    clusters: Record<string, {
        name: string;
        url: string;
        worktree: string;
        type: "assembly" | "module";
        lead: string;
        port: number;
    }>;
}

export class ClusterSupervisor {
    private clusters: Map<string, ClusterInstance> = new Map();
    private portAllocations: Map<string, number> = new Map();

    private readonly ROOT_PORT = 8000;
    private readonly MODULE_PORT_START = 8001;
    private readonly MODULE_PORT_END = 8050;

    constructor() {}

    /**
     * Resolves the path to the MOSAIC CLI binary
     */
    private findMosaicBinary(): string {
        if (process.env.MOSAIC_BIN && existsSync(process.env.MOSAIC_BIN)) {
            return process.env.MOSAIC_BIN;
        }

        const candidatePaths = [
            "/Library/Frameworks/Python.framework/Versions/3.14/bin/mosaic",
            "/Library/Frameworks/Python.framework/Versions/3.13/bin/mosaic",
            "/Library/Frameworks/Python.framework/Versions/3.12/bin/mosaic",
            path.join(os.homedir(), ".local/bin/mosaic"),
            path.join(os.homedir(), ".cargo/bin/mosaic"),
            "/opt/homebrew/bin/mosaic",
            "/usr/local/bin/mosaic"
        ];

        for (const candidate of candidatePaths) {
            if (existsSync(candidate)) {
                return candidate;
            }
        }

        return "mosaic";
    }

    /**
     * Dynamically allocates an available port for a cluster
     */
    public allocatePort(clusterId: string): number {
        if (clusterId === "root") {
            this.portAllocations.set("root", this.ROOT_PORT);
            return this.ROOT_PORT;
        }

        if (this.portAllocations.has(clusterId)) {
            return this.portAllocations.get(clusterId)!;
        }

        const allocatedPorts = new Set(this.portAllocations.values());
        for (let port = this.MODULE_PORT_START; port <= this.MODULE_PORT_END; port++) {
            if (!allocatedPorts.has(port)) {
                this.portAllocations.set(clusterId, port);
                return port;
            }
        }

        throw new Error(`Exceeded maximum cluster port allocation range (${this.MODULE_PORT_START}..${this.MODULE_PORT_END})`);
    }

    /**
     * Probes if a port is actively accepting connections
     */
    private probePort(port: number, timeoutMs = 250): Promise<boolean> {
        return new Promise((resolve) => {
            const socket = new net.Socket();
            let hasResponded = false;

            socket.setTimeout(timeoutMs);
            socket.on("connect", () => {
                hasResponded = true;
                socket.destroy();
                resolve(true);
            });

            socket.on("timeout", () => {
                if (!hasResponded) {
                    hasResponded = true;
                    socket.destroy();
                    resolve(false);
                }
            });

            socket.on("error", () => {
                if (!hasResponded) {
                    hasResponded = true;
                    socket.destroy();
                    resolve(false);
                }
            });

            socket.connect(port, "127.0.0.1");
        });
    }

    /**
     * Generates and writes cluster_roster.json across all active worktrees
     */
    public async generateClusterRoster(
        projectId: string,
        projectRoot: string,
        worktrees: Record<string, string>
    ): Promise<ClusterRoster> {
        const roster: ClusterRoster = {
            project_id: projectId,
            project_root: projectRoot,
            clusters: {}
        };

        // 1. Build roster map
        for (const [clusterId, wtPath] of Object.entries(worktrees)) {
            const isRoot = clusterId === "root";
            const port = this.allocatePort(clusterId);
            const url = `http://127.0.0.1:${port}`;

            roster.clusters[clusterId] = {
                name: isRoot ? "Assembly Root" : clusterId,
                url,
                worktree: wtPath,
                type: isRoot ? "assembly" : "module",
                lead: "archy",
                port
            };

            // Register or update cluster instance state
            if (!this.clusters.has(clusterId)) {
                this.clusters.set(clusterId, {
                    clusterId,
                    port,
                    url,
                    worktreePath: wtPath,
                    type: isRoot ? "assembly" : "module",
                    lead: "archy",
                    status: "stopped"
                });
            } else {
                const existing = this.clusters.get(clusterId)!;
                existing.port = port;
                existing.url = url;
                existing.worktreePath = wtPath;
            }
        }

        // 2. Write cluster_roster.json into each worktree's .agents/ directory
        const rosterJson = JSON.stringify(roster, null, 2);

        for (const wtPath of Object.values(worktrees)) {
            if (existsSync(wtPath)) {
                try {
                    const agentsDir = path.join(wtPath, ".agents");
                    await fs.mkdir(agentsDir, { recursive: true });
                    await fs.writeFile(path.join(agentsDir, "cluster_roster.json"), rosterJson, "utf-8");
                } catch (err: any) {
                    console.warn(`[ClusterSupervisor] Warning writing roster to ${wtPath}:`, err.message);
                }
            }
        }

        return roster;
    }

    /**
     * Starts a MOSAIC instance for a specific cluster worktree
     */
    public async startCluster(
        clusterId: string,
        worktreePath: string,
        port?: number
    ): Promise<ClusterInstance> {
        const allocatedPort = port || this.allocatePort(clusterId);
        const url = `http://127.0.0.1:${allocatedPort}`;
        const isRoot = clusterId === "root";

        let instance = this.clusters.get(clusterId);
        if (!instance) {
            instance = {
                clusterId,
                port: allocatedPort,
                url,
                worktreePath,
                type: isRoot ? "assembly" : "module",
                lead: "archy",
                status: "stopped"
            };
            this.clusters.set(clusterId, instance);
        }

        // Check if already running and responsive
        if (instance.status === "running" && instance.process && instance.pid) {
            const isListening = await this.probePort(allocatedPort);
            if (isListening) {
                return instance;
            }
        }

        if (!existsSync(worktreePath)) {
            instance.status = "error";
            instance.error = `Worktree path not found: ${worktreePath}`;
            return instance;
        }

        instance.status = "starting";
        instance.error = undefined;

        const mosaicBin = this.findMosaicBinary();
        const args = [
            "host",
            "--workspace", worktreePath,
            "--port", String(allocatedPort),
            "--strict-port"
        ];

        console.log(`[ClusterSupervisor] Spawning cluster '${clusterId}' on port ${allocatedPort} via: ${mosaicBin} ${args.join(" ")}`);

        try {
            const proc = spawn(mosaicBin, args, {
                cwd: worktreePath,
                stdio: ["ignore", "pipe", "pipe"],
                detached: true,
                env: {
                    ...process.env,
                    PYTHONUNBUFFERED: "1"
                }
            });

            instance.process = proc;
            instance.pid = proc.pid ?? null;

            let stderrBuffer = "";
            proc.stderr?.on("data", (chunk) => {
                stderrBuffer += chunk.toString();
            });

            proc.on("exit", (code) => {
                if (instance?.status === "running" || instance?.status === "starting") {
                    console.warn(`[ClusterSupervisor] Cluster '${clusterId}' process exited with code ${code}`);
                    instance.status = "stopped";
                    instance.process = null;
                    instance.pid = null;
                    if (code !== 0 && code !== null) {
                        instance.error = `Exited with code ${code}: ${stderrBuffer.slice(-200)}`;
                    }
                }
            });

            // Readiness probe loop (15s timeout, poll every 250ms)
            const startTime = Date.now();
            const timeoutMs = 15000;
            let isReady = false;

            while (Date.now() - startTime < timeoutMs) {
                if (proc.exitCode !== null) {
                    throw new Error(`Process terminated prematurely: ${stderrBuffer.slice(-200)}`);
                }

                const listening = await this.probePort(allocatedPort, 200);
                if (listening) {
                    isReady = true;
                    break;
                }
                await new Promise((r) => setTimeout(r, 250));
            }

            if (isReady) {
                instance.status = "running";
                instance.startedAt = new Date().toISOString();
                console.log(`[ClusterSupervisor] Cluster '${clusterId}' is READY on ${url} (PID ${proc.pid})`);
            } else {
                instance.status = "error";
                instance.error = `Cluster did not become ready within 15s. ${stderrBuffer.slice(-200)}`;
                this.stopCluster(clusterId).catch(() => {});
            }

        } catch (err: any) {
            instance.status = "error";
            instance.error = err.message;
            console.error(`[ClusterSupervisor] Failed to spawn cluster '${clusterId}':`, err.message);
        }

        return instance;
    }

    /**
     * Gracefully stops a running cluster (SIGTERM with 1.5s grace period, then SIGKILL)
     */
    public async stopCluster(clusterId: string): Promise<void> {
        const instance = this.clusters.get(clusterId);
        if (!instance || !instance.process) {
            if (instance) instance.status = "stopped";
            return;
        }

        const proc = instance.process;
        console.log(`[ClusterSupervisor] Stopping cluster '${clusterId}' (PID ${instance.pid})...`);

        try {
            if (proc.pid) {
                try {
                    process.kill(-proc.pid, "SIGTERM");
                } catch {
                    proc.kill("SIGTERM");
                }

                // Wait up to 1.5s grace period
                const start = Date.now();
                while (Date.now() - start < 1500) {
                    if (proc.exitCode !== null) break;
                    await new Promise((r) => setTimeout(r, 100));
                }

                // If still alive, SIGKILL
                if (proc.exitCode === null) {
                    try {
                        process.kill(-proc.pid, "SIGKILL");
                    } catch {
                        proc.kill("SIGKILL");
                    }
                }
            }
        } catch (err: any) {
            console.warn(`[ClusterSupervisor] Error stopping cluster '${clusterId}':`, err.message);
        } finally {
            instance.process = null;
            instance.pid = null;
            instance.status = "stopped";
        }
    }

    /**
     * Concurrently stops all active cluster processes
     */
    public async stopAllClusters(): Promise<void> {
        console.log(`[ClusterSupervisor] Stopping all ${this.clusters.size} clusters...`);
        const stopPromises = Array.from(this.clusters.keys()).map((id) => this.stopCluster(id));
        await Promise.all(stopPromises);
    }

    /**
     * Returns a snapshot of all tracked clusters
     */
    public getClusters(): ClusterInfo[] {
        return Array.from(this.clusters.values()).map((c) => ({
            clusterId: c.clusterId,
            port: c.port,
            url: c.url,
            worktreePath: c.worktreePath,
            type: c.type,
            lead: c.lead,
            status: c.status,
            pid: c.pid,
            startedAt: c.startedAt,
            error: c.error
        }));
    }
}
