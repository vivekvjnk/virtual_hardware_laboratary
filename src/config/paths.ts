// src/config/paths.ts

import path from "path";
import { fileURLToPath } from "url";

/**
 * Node.js ES modules do not provide __dirname / __filename.
 * This is the canonical, runtime-safe way to reconstruct them.
 */
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * PROJECT_ROOT
 *
 * This file lives at:
 *   src/config/paths.ts   (dev)
 *   dist/config/paths.js  (prod)
 *
 * Going two levels up always lands us at project root.
 */
export const PROJECT_ROOT = path.resolve(__dirname, "..", "..");

/**
 * Source directory (TypeScript)
 * Useful for tools that need to reason about original sources.
 */
export const SRC_DIR = path.join(PROJECT_ROOT, "src");

/**
 * Local component library directory.
 *
 * This is the ONLY place where librarian-added and imported components live.
 * Anything here is guaranteed to be validated.
 */
export const LOCAL_LIBRARY_DIR = process.env.VHL_LIBRARY_DIR || path.join(PROJECT_ROOT, "lib");

/**
 * Imports directory.
 * Historically separate, now unified with LOCAL_LIBRARY_DIR.
 */
export const IMPORTS_DIR = LOCAL_LIBRARY_DIR;

/**
 * Temporary working directory.
 *
 * Used for:
 * - staging new components
 * - validation harness execution
 * - transient files
 *
 * This directory may be created and deleted freely.
 */
export const TEMP_DIR = path.join(PROJECT_ROOT, ".tmp");

/**
 * Circuits directory.
 * 
 * Used by VAP (VHL ANA Process) to store circuit files.
 * This is separate from the component library.
 */
export const CIRCUITS_DIR = path.join(PROJECT_ROOT, "circuits");

/**
 * Temporary circuits directory.
 * 
 * Used by VAP for provisional circuit files during evaluation.
 * Files here are either promoted to CIRCUITS_DIR (ACCEPT) or deleted (REJECT).
 */
export const CIRCUITS_TEMP_DIR = path.join(CIRCUITS_DIR, ".tmp");

/**
 * Evaluation results directory.
 * 
 * Used by VAP to store evaluation logs and artifacts.
 */
export const EVAL_RESULTS_DIR = path.join(PROJECT_ROOT, "eval_results");

/**
 * Workspace directory.
 * 
 * Default location for the workspace folder.
 * This is easily configurable via environment variable.
 */
export const WORKSPACE_DIR = process.env.VHL_WORKSPACE_DIR || path.join(PROJECT_ROOT, "workspace");
