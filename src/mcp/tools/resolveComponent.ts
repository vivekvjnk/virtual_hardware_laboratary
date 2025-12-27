import fs from "fs/promises";
import path from "path";
import crypto from "crypto";
import { LOCAL_LIBRARY_DIR as DEFAULT_LIB_DIR } from "../../config/paths.js";
import { getFilesRecursive } from "../../runtime/libraryFs.js";
import { CLIInteractionHandler, CLIInteractionState } from "../../utils/cliInteraction.js";

export type ResolveState =
  | "idle"
  | "checking_local"
  | "checking_global"
  | "selection_required"
  | "trying_import"
  | "finished"
  | "failed";

export interface ResolveStatus {
  task_id: string;
  state: ResolveState;
  location?: string;
  source?: "local" | "global";
  selection?: {
    selection_id: string;
    prompt: string;
    options: string[];
  };
  exit_code?: number;
  reason?: string;
}

class ResolveTask {
  public readonly taskId: string;
  public state: ResolveState = "idle";
  private handler: CLIInteractionHandler | null = null;
  private componentName: string;
  private location?: string;
  private source?: "local" | "global";
  private exitCode?: number;
  private reason?: string;

  constructor(componentName: string) {
    this.taskId = `rc-${crypto.randomBytes(4).toString("hex")}`;
    this.componentName = componentName;
  }

  public async start() {
    this.state = "checking_local";

    // Run the resolution logic in the background
    this.runResolution().catch(err => {
      this.state = "failed";
      this.reason = err.message;
    });
  }

  private async runResolution() {
    const local = await resolveLocal(this.componentName);
    if (local) {
      this.location = local;
      this.source = "local";
      this.state = "finished";
      return;
    }

    this.state = "checking_global";
    this.handler = new CLIInteractionHandler();

    // In the new model, we go straight to import which handles search/selection
    this.state = "trying_import";
    const state = await this.handler.execute("tsci", ["import", this.componentName], getLibDir());
    await this.handleHandlerState(state);
  }

  private async handleHandlerState(state: CLIInteractionState) {
    switch (state.state) {
      case "completed":
        const match = state.output?.match(/(?:Imported|Installed|✔ Imported|✔ Installed).*?([^\s]+\.tsx)/i);
        if (match) {
          this.location = match[1].trim();
          this.source = "global";
          this.state = "finished";
        } else {
          const local = await resolveLocal(this.componentName);
          if (local) {
            this.location = local;
            this.source = "global";
            this.state = "finished";
            this.reason = "Component found in local library";
          } else {
            this.state = "failed";
            this.reason = state.output || "Unknown error during import";
          }
        }
        break;
      case "selection_required":
        this.state = "selection_required";
        break;
      case "failed":
        this.state = "failed";
        this.exitCode = state.exit_code;
        this.reason = state.reason;
        break;
    }
  }

  public async select(selectionId: string, selectedOption: string) {
    if (this.state !== "selection_required" || !this.handler) {
      throw new Error("No active selection required");
    }

    this.state = "trying_import";

    // Process the response in the background
    this.handler.respond(selectionId, selectedOption).then(async (newState) => {
      await this.handleHandlerState(newState);
    }).catch(err => {
      this.state = "failed";
      this.reason = err.message;
    });
  }

  public getStatus(): ResolveStatus {
    const status: ResolveStatus = {
      task_id: this.taskId,
      state: this.state,
      location: this.location,
      source: this.source,
      exit_code: this.exitCode,
      reason: this.reason,
    };

    if (this.state === "selection_required" && this.handler) {
      const hState = this.handler.getState();
      if (hState.selection) {
        status.selection = {
          selection_id: hState.selection.selection_id,
          prompt: hState.selection.prompt,
          options: hState.selection.options,
        };
      }
    }

    return status;
  }

  public close() {
    if (this.handler) {
      this.handler.kill();
    }
  }
}

let currentTask: ResolveTask | null = null;

function getLibDir(): string {
  return process.env.VHL_LIBRARY_DIR || DEFAULT_LIB_DIR;
}

async function resolveLocal(query: string): Promise<string | null> {
  try {
    const libDir = getLibDir();
    const files = await getFilesRecursive(libDir);

    const normalizedQuery = query.toLowerCase().replace(/\\/g, "/");
    const tsciName = normalizedQuery.replace(/\//g, ".");

    const possiblePaths = [
      path.join(libDir, query),
      path.join(libDir, query + ".tsx"),
      path.join(libDir, "node_modules", "@tsci", tsciName, "index.js"),
      path.join(libDir, "node_modules", "@tsci", tsciName, "index.tsx"),
      path.join(libDir, "node_modules", "@tsci", tsciName, "index.cjs"),
      path.join(libDir, tsciName, "index.tsx"),
      path.join(libDir, tsciName + ".tsx"),
    ];

    for (const p of possiblePaths) {
      try {
        await fs.access(p);
        return p;
      } catch { }
    }

    const match = files.find(f => {
      const relativePath = path.relative(libDir, f).toLowerCase().replace(/\\/g, "/");
      const baseName = path.basename(f, ".tsx").toLowerCase();

      return (relativePath === normalizedQuery ||
        relativePath === normalizedQuery + ".tsx" ||
        baseName === normalizedQuery ||
        relativePath.endsWith("/" + normalizedQuery + ".tsx") ||
        relativePath.endsWith("/" + normalizedQuery) ||
        relativePath.includes(`@tsci/${tsciName}`) ||
        relativePath.includes(`@tsci/${normalizedQuery.replace(/\//g, ".")}`));
    });

    if (match) return match;

    return files.find(f =>
      f.toLowerCase().includes(normalizedQuery.toLowerCase())
    ) || null;
    } catch (err) {
    console.log("Error accessing library directory: ", err);
    return null;
  }
}

export async function resolveComponentStart(componentName: string): Promise<ResolveStatus> {
  if (currentTask && currentTask.getStatus().state !== "finished" && currentTask.getStatus().state !== "failed") {
    throw new Error("A resolution task is already running");
  }

  currentTask = new ResolveTask(componentName);
  await currentTask.start();
  return currentTask.getStatus();
}

export async function resolveComponentStatus(taskId: string): Promise<ResolveStatus> {
  if (!currentTask || currentTask.taskId !== taskId) {
    throw new Error(`Task ${taskId} not found`);
  }
  return currentTask.getStatus();
}

export async function resolveComponentSelect(taskId: string, selectionId: string, selectedOption: string): Promise<ResolveStatus> {
  if (!currentTask || currentTask.taskId !== taskId) {
    throw new Error(`Task ${taskId} not found`);
  }
  await currentTask.select(selectionId, selectedOption);
  return currentTask.getStatus();
}

export async function resolveComponentClose(taskId: string): Promise<{ success: boolean }> {
  if (currentTask && currentTask.taskId === taskId) {
    currentTask.close();
    currentTask = null;
    return { success: true };
  }
  return { success: false };
}

export function clearSessions() {
  if (currentTask) {
    currentTask.close();
    currentTask = null;
  }
}