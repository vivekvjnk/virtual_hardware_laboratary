// src/runtime/libraryFs.ts

import fs from "fs/promises";
import path from "path";
import {
  LOCAL_LIBRARY_DIR,
  TEMP_DIR
} from "../config/paths.js";

/**
 * Ensure that required directories exist.
 * Safe to call multiple times.
 */
export async function ensureLibraryDirs(): Promise<void> {
  await fs.mkdir(LOCAL_LIBRARY_DIR, { recursive: true });
  await fs.mkdir(TEMP_DIR, { recursive: true });
}

/**
 * Write a temporary TSX file for validation.
 * Returns the absolute path to the temp file.
 */
export async function writeTempComponent(
  filename: string,
  content: string
): Promise<string> {
  const tempPath = path.join(TEMP_DIR, filename);
  await fs.writeFile(tempPath, content, { encoding: "utf-8" });
  return tempPath;
}

/**
 * Atomically move a validated component into the local library.
 * This is the ONLY way files may enter LOCAL_LIBRARY_DIR.
 */
export async function commitComponent(
  tempPath: string,
  targetFilename: string
): Promise<string> {
  const finalPath = path.join(
    LOCAL_LIBRARY_DIR,
    targetFilename
  );

  await fs.rename(tempPath, finalPath);
  return finalPath;
}

/**
 * Best-effort cleanup of a temp file.
 * Never throws — cleanup failure must not mask validation errors.
 */
export async function cleanupTempFile(
  tempPath: string
): Promise<void> {
  try {
    await fs.unlink(tempPath);
  } catch {
    // Intentionally ignored
  }
}
