import {
  ensureLibraryDirs,
  writeTempComponent,
  commitComponent,
  cleanupTempFile,
} from "../../runtime/libraryFs.js";

import { validateComponent } from "../../library/validator.js";

export interface AddComponentResult {
  success: boolean;
  errors?: string[];
  componentPath?: string;
}

/**
 * Add or update a component in the local library.
 * This is the ONLY mutation entrypoint into the library.
 */
export async function addComponent(
  componentName: string,
  fileContent: string
): Promise<AddComponentResult> {
  await ensureLibraryDirs();

  let filename = componentName;
  if (!filename.endsWith(".kicad_mod") && !filename.endsWith(".tsx")) {
    filename = `${componentName}.tsx`;
  }
  let tempPath: string | null = null;

  try {
    // ---- Stage ----
    tempPath = await writeTempComponent(filename, fileContent);

    // ---- Validate ----
    const validation = await validateComponent(tempPath);
    if (!validation.success) {
      await cleanupTempFile(tempPath);
      return {
        success: false,
        errors: validation.errors,
      };
    }

    // ---- Commit (overwrite allowed) ----
    const finalPath = await commitComponent(tempPath, filename);

    return {
      success: true,
      componentPath: finalPath,
    };
  } catch (err) {
    // Defensive: should never happen, but never throw outward
    if (tempPath) {
      await cleanupTempFile(tempPath);
    }

    return {
      success: false,
      errors: [
        err instanceof Error
          ? err.message
          : "Unknown error while adding component",
      ],
    };
  }
}
