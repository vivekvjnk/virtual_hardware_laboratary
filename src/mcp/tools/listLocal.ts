import path from "path";
import { resolveLibDir } from "../../workspace/projectContext.js";


import { getFilesRecursive } from "../../runtime/libraryFs.js";

export interface LocalComponentSummary {
  name: string;
  file: string;
}

/**
 * List components explicitly added to the local library.
 * Read-only. Deterministic.
 */
export async function listLocalComponents(): Promise<
  LocalComponentSummary[]
> {
  try {
    const libDir = resolveLibDir();

    const allFiles = await getFilesRecursive(libDir);

    return allFiles
      .filter(f => f.endsWith(".tsx"))
      .map(f => {
        const relativePath = path.relative(libDir, f);
        return {
          name: relativePath.replace(/\.tsx$/, ""),
          file: relativePath,
        };
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  } catch {
    // Library directory may not exist yet
    return [];
  }
}
