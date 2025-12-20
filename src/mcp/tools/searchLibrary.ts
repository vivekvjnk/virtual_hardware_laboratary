import fs from "fs/promises";
import path from "path";
import {
  LOCAL_LIBRARY_DIR,
} from "../../config/paths.js";

export type SearchMode = "fuzzy" | "regex";
export type SearchDepth = "surface" | "deep";

export interface SurfaceSearchResult {
  name: string;
  source: "local" | "global";
  description?: string;
}

export interface DeepSearchResult extends SurfaceSearchResult {
  exports?: string[];
  pins?: string[];
}

import { exec } from "child_process";
import util from "util";

const execPromise = util.promisify(exec);

async function searchGlobalLibrary(
  query: string,
  mode: SearchMode,
  depth: SearchDepth
): Promise<(SurfaceSearchResult | DeepSearchResult)[]> {
  try {
    // We use the local tscircuit CLI clone
    const { stdout } = await execPromise(
      `bun ./tscircuit/cli.mjs search "${query}"`,
      {
        cwd: process.cwd(), // Assuming running from project root
      }
    );

    const REGEX = /^\d+\.\s+(?<name>\S+)\s+-\s+Stars:\s+\d+(?:\s+-\s+(?<description>.*))?$/;

    const parsedItems = stdout
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line)
      .map((line) => {
        const match = line.match(REGEX);
        if (!match || !match.groups) return null;
        return {
          name: match.groups.name,
          description: match.groups.description,
        };
      })
      .filter((item): item is { name: string; description?: string } => item !== null);

    return parsedItems.map((item) => {
      if (depth === "deep") {
        return {
          name: item.name,
          source: "global",
          description: item.description,
          exports: ["default"],
        } as DeepSearchResult;
      } else {
        return {
          name: item.name,
          source: "global",
          description: item.description,
        } as SurfaceSearchResult;
      }
    });
  } catch (error) {
    console.error("Error searching global library:", error);
    return [];
  }
}

/**
 * Search local and global libraries.
 */
export async function searchLibrary(
  query: string,
  mode: SearchMode,
  depth: SearchDepth
): Promise<(SurfaceSearchResult | DeepSearchResult)[]> {
  let localResults: (SurfaceSearchResult | DeepSearchResult)[] = [];

  try {
    const files = await fs.readdir(LOCAL_LIBRARY_DIR);

    const matcher =
      mode === "regex"
        ? new RegExp(query, "i")
        : null;

    localResults = files
      .filter(f => f.endsWith(".tsx"))
      .map(f => path.basename(f, ".tsx"))
      .filter(name =>
        mode === "regex"
          ? matcher!.test(name)
          : name.toLowerCase().includes(query.toLowerCase())
      )
      .map(name =>
        depth === "deep"
          ? {
            name,
            source: "local",
            exports: ["default"], // best-effort stub
          }
          : {
            name,
            source: "local",
          }
      );
  } catch {
    // ignore missing local library
  }

  const globalResults = await searchGlobalLibrary(
    query,
    mode,
    depth
  );

  return [
    ...localResults.sort((a, b) =>
      a.name.localeCompare(b.name)
    ),
    ...globalResults.sort((a, b) =>
      a.name.localeCompare(b.name)
    ),
  ];
}
