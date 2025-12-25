import fs from "fs/promises";
import path from "path";
import { spawn, ChildProcessWithoutNullStreams } from "child_process";
import crypto from "crypto";
import { IMPORTS_DIR } from "../../config/paths.js";

export type ResolveResult =
  | { status: "resolved"; component: string; path: string }
  | { status: "selection_required"; options: string[] }
  | { status: "no_results"; message: string }
  | { status: "error"; message: string };

interface ImportSession {
  proc: ChildProcessWithoutNullStreams;
  options: string[];
}

const sessions = new Map<string, ImportSession>();

/**
 * Checks if the component already exists locally.
 */
async function resolveLocal(query: string): Promise<string | null> {
  try {
    const files = await fs.readdir(IMPORTS_DIR);
    const match = files.find(f =>
      f.toLowerCase().includes(query.toLowerCase()) && f.endsWith(".tsx")
    );
    return match ? path.join(IMPORTS_DIR, match) : null;
  } catch {
    return null;
  }
}

/**
 * Phase 1: Search for components and identify if a selection is needed.
 */
function startImport(query: string): Promise<{ sessionId: string; options: string[] }> {
  return new Promise((resolve, reject) => {
    const proc = spawn("tsci", ["import", query], {
      cwd: process.cwd(),
      stdio: "pipe",
    });

    console.log("Searching for: ", query, "...");
    let buffer = "";
    const options = new Set<string>();
    let isListingActive = false;

    // Define listeners as named functions so they can be removed
    const onStdout = (chunk: Buffer) => {
      const text = chunk.toString();
      buffer += text;

      if (buffer.includes("No results found matching your query.")) {
        cleanup();
        return resolve({ sessionId: "no_results", options: [] });
      }

      if (buffer.includes("Select a part to import")) {
        isListingActive = true;
      }

      if (isListingActive) {
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        lines.forEach(line => {
          if (line.includes("Select a part to import")) return;
          // Capture the name between [source] and the trailing dash
          const cleanMatch = line.match(/\]\s*(.*?)\s*-/);
          if (cleanMatch && cleanMatch[1]) {
            options.add(cleanMatch[1].trim());
          }
        });

        if (options.size > 0) {
          cleanup(); // CRITICAL: Stop listening before resolving
          const sessionId = crypto.randomUUID();
          const finalOptions = [...options];
          sessions.set(sessionId, { proc, options: finalOptions });
          resolve({ sessionId, options: finalOptions });
        }
      }
    };

    const onExit = (code: number | null) => {
      cleanup();
      if (options.size === 0) {
        if (buffer.includes("No results found")) {
          resolve({ sessionId: "no_results", options: [] });
        } else {
          reject(new Error(`tsci exited with code ${code}`));
        }
      }
    };

    const cleanup = () => {
      proc.stdout.off("data", onStdout);
      proc.off("exit", onExit);
    };

    proc.stdout.on("data", onStdout);
    proc.on("exit", onExit);
    proc.on("error", (err) => { cleanup(); reject(err); });
  });
}

/**
 * Phase 2: Use arrow keys to select the item and wait for the import path.
 */
async function completeImport(selection: string): Promise<string> {
  const sessionEntry = [...sessions.entries()].find(([_, s]) =>
    s.options.includes(selection)
  );

  if (!sessionEntry) throw new Error("Invalid or expired selection");

  const [sessionId, session] = sessionEntry;
  const targetIndex = session.options.indexOf(selection);

  // ANSI escape sequences
  const DOWN_ARROW = "\u001b[B";
  const ENTER = "\n";

  // Simulate keyboard navigation
  if (targetIndex > 0) {
    for (let i = 0; i < targetIndex; i++) {
      session.proc.stdin.write(DOWN_ARROW);
    }
  }
  session.proc.stdin.write(ENTER);

  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      cleanup();
      session.proc.kill();
      sessions.delete(sessionId);
      reject(new Error("Import timed out after 30 seconds"));
    }, 30000);

    const onOutput = (chunk: Buffer) => {
      const text = chunk.toString();
      // Matches both "Imported /path" and "✔ Imported /path"
      const match = text.match(/(?:Imported|✔ Imported)\s+([^\s]+\.tsx)/i);

      if (match) {
        const filePath = match[1].trim();
        cleanup();
        session.proc.kill();
        sessions.delete(sessionId);
        resolve(filePath);
      }
    };

    const cleanup = () => {
      clearTimeout(timeout);
      session.proc.stdout.off("data", onOutput);
      session.proc.stderr.off("data", onOutput);
    };

    // Listen to both because success messages often go to stderr
    session.proc.stdout.on("data", onOutput);
    session.proc.stderr.on("data", onOutput);

    session.proc.on("exit", (code) => {
      cleanup();
      sessions.delete(sessionId);
      if (code !== 0 && code !== null) reject(new Error(`tsci exited with code ${code}`));
    });
  });
}

export async function resolveComponent(query: string): Promise<ResolveResult> {
  // 1. Try local lookup
  const local = await resolveLocal(query);
  if (local) {
    return { status: "resolved", component: path.basename(local, ".tsx"), path: local };
  }

  // 2. Check if this is an active selection from a previous search
  for (const [_, s] of sessions.entries()) {
    if (s.options.includes(query)) {
      try {
        const importedPath = await completeImport(query);
        return { status: "resolved", component: query, path: importedPath };
      } catch (err) {
        return { status: "error", message: err instanceof Error ? err.message : "Import failed" };
      }
    }
  }

  // 3. Otherwise, start a new search
  try {
    const { sessionId, options } = await startImport(query);
    if (sessionId === "no_results") {
      return { status: "no_results", message: "No results found matching your query." };
    }
    return { status: "selection_required", options };
  } catch (err) {
    return { status: "error", message: "Search failed or tsci error" };
  }
}

export function clearSessions() {
  for (const session of sessions.values()) {
    session.proc.kill();
  }
  sessions.clear();
}