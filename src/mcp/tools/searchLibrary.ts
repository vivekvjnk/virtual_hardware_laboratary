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
    const TSCIRCUIT_CLI =
      process.env.TSCIRCUIT_CLI ??
      path.resolve(process.cwd(), "tscircuit", "cli.mjs");

    const { stdout } = await execPromise(
      `bun "${TSCIRCUIT_CLI}" search "${query}"`,
      {
        cwd: process.cwd(),
      }
    );

    // Regex for registry items (with stars)
    const REGISTRY_REGEX = /^\d+\.\s+(?<name>\S+)\s+-\s+Stars:\s+\d+(?:\s+-\s+(?<description>.*))?$/;
    // Regex for KiCad items
    const KICAD_REGEX = /^\s*\d+\.\s+(?<name>kicad:\S+)(?:\s+-\s+(?<description>.*))?$/;
    // Regex for JLC items
    const JLC_REGEX = /^\d+\.\s+(?<name>\S+)\s+\((?<jlc_id>C\d+)\)\s+-\s+(?<description>.*)\s+\(stock:\s+[\d,]+\)$/;

    const parsedItems = stdout
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        let match = line.match(REGISTRY_REGEX);
        if (match?.groups) {
          return {
            name: match.groups.name,
            description: match.groups.description,
          };
        }

        match = line.match(KICAD_REGEX);
        if (match?.groups) {
          return {
            name: match.groups.name,
            description: match.groups.description ?? "KiCad footprint",
          };
        }

        match = line.match(JLC_REGEX);
        if (match?.groups) {
          return {
            name: match.groups.name,
            description: match.groups.description,
          };
        }

        return null;
      })
      .filter(
        (item): item is { name: string; description: string | undefined } =>
          item !== null
      );

    return parsedItems.map((item) => {
      if (depth === "deep") {
        return {
          name: item.name,
          source: "global",
          description: item.description,
          exports: ["default"],
        } as DeepSearchResult;
      }

      return {
        name: item.name,
        source: "global",
        description: item.description,
      } as SurfaceSearchResult;
    });
  } catch (error) {
    console.error("Error searching global library:", error);
    throw new Error("Library CLI failed");
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
