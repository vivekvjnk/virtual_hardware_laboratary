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
 * Imports directory.
 * This is where resolved components are stored.
 */
export const IMPORTS_DIR = process.env.VHL_IMPORTS_DIR || path.join(PROJECT_ROOT, "imports");

/**
 * Local component library directory.
 *
 * This is the ONLY place where librarian-added components live.
 * Anything here is guaranteed to be validated.
 */
export const LOCAL_LIBRARY_DIR = process.env.VHL_LIBRARY_DIR || IMPORTS_DIR;

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
