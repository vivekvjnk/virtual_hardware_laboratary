import { spawn, ChildProcess } from "node:child_process";
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import os from "node:os";
import net from "node:net";
import { formatUrl } from "../config/network.js";

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
            path.join(os.homedir(), ".local/bin/mosaic"),
            path.join(os.homedir(), ".local/bin/mesh"),
            "/Library/Frameworks/Python.framework/Versions/3.14/bin/mosaic",
            "/Library/Frameworks/Python.framework/Versions/3.13/bin/mosaic",
            "/Library/Frameworks/Python.framework/Versions/3.12/bin/mosaic",
            path.join(os.homedir(), ".cargo/bin/mosaic"),
            "/opt/homebrew/bin/mosaic",
            "/opt/homebrew/bin/mesh",
            "/usr/local/bin/mosaic",
            "/usr/local/bin/mesh"
        ];

        for (const candidate of candidatePaths) {
            if (existsSync(candidate)) {
                return candidate;
            }
        }

        return "mosaic";
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
     * Checks if a port is available to be bound
     */
    public async isPortAvailable(port: number): Promise<boolean> {
        // 1. Probe if any server responds on TCP
        const inUse = await this.probePort(port, 150);
        if (inUse) return false;

        // 2. Check if we can bind a server to the port
        return new Promise<boolean>((resolve) => {
            const server = net.createServer();
            server.once("error", () => {
                resolve(false);
            });
            server.once("listening", () => {
                server.close(() => resolve(true));
            });
            server.listen(port, "127.0.0.1");
        });
    }

    /**
     * Searches for a base port such that `requiredCount` consecutive ports
     * [base, base + requiredCount - 1] are available.
     * If base port is not available, checks the next 100 set (8000, 8100, 8200, ...).
     */
    public async findAvailableBasePort(
        requiredCount: number = 1,
        startBase: number = this.ROOT_PORT
    ): Promise<number> {
        const maxPort = 65000;
        for (let candidateBase = startBase; candidateBase <= maxPort - requiredCount; candidateBase += 100) {
            let blockAvailable = true;
            for (let i = 0; i < requiredCount; i++) {
                const port = candidateBase + i;
                if (!(await this.isPortAvailable(port))) {
                    blockAvailable = false;
                    break;
                }
            }
            if (blockAvailable) {
                return candidateBase;
            }
        }

        throw new Error(
            `Exceeded maximum cluster port allocation range searching for ${requiredCount} consecutive ports starting from ${startBase}`
        );
    }

    /**
     * Dynamically allocates an available port for a cluster, avoiding host port conflicts.
     * Guarantees that there are enough consecutive ports available from base port for all
     * MESH instances (number of MESH instances = Number of modules + 1(main worktree)).
     */
    public async allocatePort(clusterId: string, totalInstances?: number): Promise<number> {
        const count = totalInstances ?? Math.max(this.clusters.size, 1);

        // 1. Root / Assembly cluster (base port holder)
        if (clusterId === "root") {
            const existingRootPort = this.portAllocations.get("root");
            if (existingRootPort !== undefined) {
                let canKeep = true;
                for (let i = 0; i < count; i++) {
                    const port = existingRootPort + i;
                    const isRunning = Array.from(this.clusters.values()).some(
                        (c) => c.port === port && c.status === "running"
                    );
                    if (!isRunning && !(await this.isPortAvailable(port))) {
                        canKeep = false;
                        break;
                    }
                }
                if (canKeep) {
                    return existingRootPort;
                }

                // Existing base block is invalid/broken, clear stale non-running allocations
                for (const [id] of this.portAllocations.entries()) {
                    const inst = this.clusters.get(id);
                    if (!inst || inst.status !== "running") {
                        this.portAllocations.delete(id);
                    }
                }
            }

            const basePort = await this.findAvailableBasePort(count, this.ROOT_PORT);
            this.portAllocations.set("root", basePort);
            return basePort;
        }

        // 2. Module clusters
        let basePort = this.portAllocations.get("root");
        if (basePort === undefined) {
            basePort = await this.findAvailableBasePort(count, this.ROOT_PORT);
            this.portAllocations.set("root", basePort);
        }

        // Check if this module already has a valid allocation in the current base block
        if (this.portAllocations.has(clusterId)) {
            const existingPort = this.portAllocations.get(clusterId)!;
            const instance = this.clusters.get(clusterId);
            if (existingPort > basePort && existingPort < basePort + 100) {
                if (instance && instance.status === "running") {
                    return existingPort;
                }
                if (await this.isPortAvailable(existingPort)) {
                    return existingPort;
                }
            }
        }

        const currentlyAllocated = new Set(this.portAllocations.values());

        // Allocate the lowest available consecutive port in the base block (basePort + 1 .. basePort + 99)
        for (let port = basePort + 1; port < basePort + 100; port++) {
            if (!currentlyAllocated.has(port) && (await this.isPortAvailable(port))) {
                this.portAllocations.set(clusterId, port);
                return port;
            }
        }

        // Fallback search if 100-block range is exhausted
        for (let port = basePort + 100; port <= 65000; port++) {
            if (!currentlyAllocated.has(port) && (await this.isPortAvailable(port))) {
                this.portAllocations.set(clusterId, port);
                return port;
            }
        }

        throw new Error(`Exceeded maximum cluster port allocation range for cluster '${clusterId}'`);
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

        // Ensure 'root' is processed first so it gets the base root port
        const entries = Object.entries(worktrees);
        entries.sort(([a], [b]) => (a === "root" ? -1 : b === "root" ? 1 : a.localeCompare(b)));
        const totalInstances = entries.length;

        // 1. Build roster map with dynamically allocated non-conflicting ports
        for (const [clusterId, wtPath] of entries) {
            const isRoot = clusterId === "root";
            const port = await this.allocatePort(clusterId, totalInstances);
            const url = formatUrl(port);

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
        const allocatedPort = port || (await this.allocatePort(clusterId));
        const url = formatUrl(allocatedPort);
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

        const ecpRepoUrl = process.env.MOSAIC_ECP_REPO_URL || "git@github.com:vivekvjnk/ECP_VHL.git";
        const ecpRef = process.env.MOSAIC_ECP_REF || "main";
        const ecpProvider = process.env.MOSAIC_ECP_PROVIDER || "git";

        const mosaicBin = this.findMosaicBinary();
        const args = [
            "host",
            "--workspace", worktreePath,
            "--port", String(allocatedPort),
            "--strict-port",
            "--no-reload",
            "--ecp-repo-url", ecpRepoUrl,
            "--ecp-provider", ecpProvider,
            "--ecp-ref", ecpRef
        ];

        console.log(`[ClusterSupervisor] Spawning cluster '${clusterId}' on port ${allocatedPort} via: ${mosaicBin} ${args.join(" ")}`);

        try {
            const proc = spawn(mosaicBin, args, {
                cwd: worktreePath,
                stdio: ["ignore", "pipe", "pipe"],
                detached: true,
                env: {
                    ...process.env,
                    PYTHONUNBUFFERED: "1",
                    MOSAIC_ECP_REPO_URL: ecpRepoUrl,
                    MOSAIC_ECP_REF: ecpRef,
                    MOSAIC_ECP_PROVIDER: ecpProvider
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

                const listening = await this.probePort(allocatedPort, 150);
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
     * Starts all registered clusters concurrently
     */
    public async startAllClusters(): Promise<ClusterInstance[]> {
        console.log(`[ClusterSupervisor] Starting all ${this.clusters.size} clusters...`);
        const clusterIds = Array.from(this.clusters.keys());

        const promises = clusterIds.map(async (id) => {
            const instance = this.clusters.get(id)!;
            try {
                return await this.startCluster(id, instance.worktreePath, instance.port);
            } catch (err: any) {
                console.error(`[ClusterSupervisor] Error starting cluster '${id}':`, err.message);
                instance.status = "error";
                instance.error = err.message;
                return instance;
            }
        });

        const results = await Promise.all(promises);
        return results;
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
