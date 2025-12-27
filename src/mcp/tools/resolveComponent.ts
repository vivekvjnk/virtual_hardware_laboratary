import fs from "fs/promises";
import path from "path";
import { LOCAL_LIBRARY_DIR as DEFAULT_LIB_DIR } from "../../config/paths.js";
import { getFilesRecursive } from "../../runtime/libraryFs.js";
import { CLIInteractionHandler, CLIInteractionState } from "../../utils/cliInteraction.js";

export type ResolveResult =
  | { status: "resolved"; component: string; path: string }
  | { status: "selection_required"; selection_id: string; prompt: string; options: string[] }
  | { status: "no_results"; message: string }
  | { status: "error"; message: string };

interface Session {
  handler: CLIInteractionHandler;
  originalQuery: string;
}

const sessions = new Map<string, Session>();

function getLibDir(): string {
  return process.env.VHL_LIBRARY_DIR || DEFAULT_LIB_DIR;
}

/**
 * Checks if the component already exists locally.
 */
async function resolveLocal(query: string): Promise<string | null> {
  try {
    const libDir = getLibDir();
    const files = await getFilesRecursive(libDir);

    const normalizedQuery = query.toLowerCase().replace(/\\/g, "/");
    const tsciName = normalizedQuery.replace(/\//g, ".");

    // 1. Direct path checks
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

    // 2. Recursive match
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

    // 3. Partial match
    return files.find(f =>
      f.toLowerCase().includes(normalizedQuery.toLowerCase())
    ) || null;
  } catch {
    return null;
  }
}

export async function resolveComponent(query: string): Promise<ResolveResult> {
  // 1. Try local lookup
  const local = await resolveLocal(query);
  if (local) {
    return { status: "resolved", component: query, path: local };
  }

  // 2. Check if this is an active selection from a previous search
  let targetSession: Session | null = null;
  let targetId: string | null = null;

  const waitingSessions = Array.from(sessions.entries()).filter(([id, s]) => s.handler.getState().state === "selection_required");

  for (const [id, session] of waitingSessions) {
    const state = session.handler.getState();
    if (state.selection?.options.some(opt => opt.includes(query) || query.includes(opt))) {
      targetSession = session;
      targetId = state.selection.selection_id;
      break;
    }
  }

  if (!targetSession && waitingSessions.length === 1) {
    targetSession = waitingSessions[0][1];
    targetId = targetSession.handler.getState().selection!.selection_id;
  }

  if (targetSession && targetId) {
    // If the query looks like a component name (contains a slash), update the original query
    if (query.includes("/")) {
      targetSession.originalQuery = query;
    }

    const newState = await targetSession.handler.respond(targetId, query);

    for (const [id, s] of sessions.entries()) {
      if (s === targetSession) {
        sessions.delete(id);
        break;
      }
    }

    if (newState.state === "selection_required") {
      sessions.set(newState.selection!.selection_id, targetSession);
    }

    return handleState(newState, targetSession.originalQuery);
  }

  // 3. Otherwise, start a new search
  const handler = new CLIInteractionHandler();
  const state = await handler.execute("tsci", ["import", query], getLibDir());

  if (state.state === "selection_required") {
    const selectionId = state.selection!.selection_id;
    sessions.set(selectionId, { handler, originalQuery: query });
  }

  return handleState(state, query);
}

async function handleState(state: CLIInteractionState, originalQuery: string): Promise<ResolveResult> {
  switch (state.state) {
    case "completed":
      const match = state.output?.match(/(?:Imported|Installed|✔ Imported|✔ Installed).*?([^\s]+\.tsx)/i);
      if (match) {
        return { status: "resolved", component: originalQuery, path: match[1].trim() };
      }

      if (state.output?.match(/(?:Imported|Installed|✔ Imported|✔ Installed)/i)) {
        const local = await resolveLocal(originalQuery);
        if (local) {
          return { status: "resolved", component: originalQuery, path: local };
        }
      }

      if (state.output?.includes("No results found matching your query.")) {
        return { status: "no_results", message: "No results found matching your query." };
      }
      return { status: "error", message: `Import completed but path not found in output. Output: ${state.output}` };

    case "selection_required":
      return {
        status: "selection_required",
        selection_id: state.selection!.selection_id,
        prompt: state.selection!.prompt,
        options: state.selection!.options
      };

    case "failed":
      if (state.reason?.includes("No results found matching your query.")) {
        return { status: "no_results", message: "No results found matching your query." };
      }
      return { status: "error", message: state.reason || `tsci failed with code ${state.exit_code}` };

    default:
      return { status: "error", message: "Unexpected state" };
  }
}

export function clearSessions() {
  for (const session of sessions.values()) {
    session.handler.kill();
  }
  sessions.clear();
}