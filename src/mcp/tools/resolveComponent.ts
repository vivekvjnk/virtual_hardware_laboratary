import fs from "fs/promises";
import path from "path";
import { spawn, ChildProcessWithoutNullStreams } from "child_process";
import crypto from "crypto";
import { IMPORTS_DIR } from "../../config/paths.js";

export type ResolveResult =
  | {
    status: "resolved";
    component: string;
    path: string;
  }
  | {
    status: "selection_required";
    options: string[];
  }
  | {
    status: "error";
    message: string;
  };

interface ImportSession {
  proc: ChildProcessWithoutNullStreams;
  options: string[];
}

const sessions = new Map<string, ImportSession>();

async function resolveLocal(query: string): Promise<string | null> {
  try {
    const files = await fs.readdir(IMPORTS_DIR);

    const match = files.find(f =>
      f.toLowerCase().includes(query.toLowerCase()) &&
      f.endsWith(".tsx")
    );

    return match ? path.join(IMPORTS_DIR, match) : null;
  } catch {
    return null;
  }
}

function startImport(query: string): Promise<{ sessionId: string; options: string[] }> {
  return new Promise((resolve, reject) => {
    const proc = spawn("tsci", ["import", query], {
      cwd: process.cwd(),
      stdio: "pipe",
    });

    let buffer = "";
    const options = new Set<string>();

    proc.stdout.on("data", (chunk) => {
      buffer += chunk.toString();

      // crude but stable extraction
      buffer.split("\n").forEach(line => {
        const m = line.match(/^\s*[-*↓]?\s*([A-Za-z0-9_:@\/\.-]+)(?:\s+-.*)?$/);
        if (m) options.add(m[1]);
      });

      if (options.size > 0) {
        const sessionId = crypto.randomUUID();
        sessions.set(sessionId, { proc, options: [...options] });
        resolve({ sessionId, options: [...options] });
      }
    });

    proc.stderr.on("data", (chunk) => {
      console.error(`tsci stderr: ${chunk}`);
    });

    proc.on("exit", (code) => {
      if (options.size === 0) {
        reject(new Error(`tsci exited with code ${code} and no options found`));
      }
    });

    proc.on("error", (err) => {
      reject(err);
    });
  });
}

export function clearSessions() {
  for (const session of sessions.values()) {
    session.proc.kill();
  }
  sessions.clear();
}

async function completeImport(selection: string): Promise<string> {
  const sessionEntry = [...sessions.entries()].find(([_, s]) =>
    s.options.includes(selection)
  );

  if (!sessionEntry) {
    throw new Error("Invalid or expired selection");
  }

  const [sessionId, session] = sessionEntry;

  session.proc.stdin.write(selection + "\n");

  return new Promise((resolve, reject) => {
    const onData = (chunk: Buffer) => {
      const text = chunk.toString();
      const match = text.match(/Imported.*?\s+to\s+(\/.*\.tsx)/);

      if (match) {
        session.proc.stdout.off("data", onData);
        session.proc.kill();
        sessions.delete(sessionId);
        resolve(match[1]);
      }
    };

    session.proc.stdout.on("data", onData);

    session.proc.on("exit", (code) => {
      sessions.delete(sessionId);
      reject(new Error(`tsci exited with code ${code} without confirming import`));
    });

    session.proc.on("error", (err) => {
      sessions.delete(sessionId);
      reject(err);
    });
  });
}

export async function resolveComponent(
  query: string,
  depth: "surface" | "deep"
): Promise<ResolveResult> {

  const local = await resolveLocal(query);
  if (local) {
    return {
      status: "resolved",
      component: path.basename(local, ".tsx"),
      path: local,
    };
  }

  // is this a selection?
  for (const [sessionId, s] of sessions.entries()) {
    if (s.options.includes(query)) {
      try {
        const importedPath = await completeImport(query);
        return {
          status: "resolved",
          component: query,
          path: importedPath,
        };
      } catch (err) {
        return {
          status: "error",
          message: err instanceof Error ? err.message : "Import failed",
        };
      }
    }
  }

  // otherwise start new import
  try {
    const { options } = await startImport(query);
    return {
      status: "selection_required",
      options,
    };
  } catch (err) {
    return {
      status: "error",
      message: "No components found or tsci error",
    };
  }
}
