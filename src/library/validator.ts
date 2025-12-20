import fs from "fs/promises";
import path from "path";
import ts from "typescript";
import { LOCAL_LIBRARY_DIR } from "../config/paths.js";

export interface ValidationResult {
  success: boolean;
  errors: string[];
}

export async function validateComponent(
  tempFilePath: string
): Promise<ValidationResult> {
  const errors: string[] = [];

  // ---------- Layer 1: file existence ----------
  let sourceText: string;
  try {
    sourceText = await fs.readFile(tempFilePath, "utf-8");
  } catch {
    return {
      success: false,
      errors: ["Temp component file does not exist"],
    };
  }

  const ext = path.extname(tempFilePath);
  if (ext === ".kicad_mod") {
    return { success: true, errors: [] };
  }

  if (ext !== ".tsx") {
    return {
      success: false,
      errors: ["Component file must have .tsx or .kicad_mod extension"],
    };
  }

  // ---------- Layer 2: Create Program ----------
  const compilerOptions: ts.CompilerOptions = {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.ESNext,
    jsx: ts.JsxEmit.ReactJSX,
    strict: true,
    noEmit: true,
  };

  const host = ts.createCompilerHost(compilerOptions);

  // Override file reading to control inputs
  host.readFile = (fileName: string) =>
    fileName === tempFilePath ? sourceText : undefined;

  host.fileExists = (fileName: string) =>
    fileName === tempFilePath;

  const program = ts.createProgram(
    [tempFilePath],
    compilerOptions,
    host
  );

  const sourceFile = program.getSourceFile(tempFilePath);
  if (!sourceFile) {
    return {
      success: false,
      errors: ["Failed to load source file into program"],
    };
  }

  // ---------- Layer 3: Diagnostics ----------
  const diagnostics = [
    ...program.getSyntacticDiagnostics(sourceFile),
    ...program.getSemanticDiagnostics(sourceFile),
  ];

  if (diagnostics.length > 0) {
    diagnostics.forEach((d: ts.Diagnostic) => {
      errors.push(
        ts.flattenDiagnosticMessageText(
          d.messageText,
          "\n"
        )
      );
    });

    return { success: false, errors };
  }

  // ---------- Layer 3.5: Import Validation ----------
  const importedKicadFiles: string[] = [];

  function visit(node: ts.Node) {
    if (ts.isImportDeclaration(node)) {
      const moduleSpecifier = node.moduleSpecifier;
      if (ts.isStringLiteral(moduleSpecifier)) {
        const importPath = moduleSpecifier.text;
        if (importPath.endsWith(".kicad_mod")) {
          importedKicadFiles.push(importPath);
        }
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(sourceFile);

  for (const kicadFile of importedKicadFiles) {
    const basename = path.basename(kicadFile);
    const kicadPath = path.join(LOCAL_LIBRARY_DIR, basename);
    try {
      await fs.access(kicadPath);
    } catch {
      errors.push(
        `Imported footprint not found in library: ${basename}. Please upload it first.`
      );
    }
  }

  if (errors.length > 0) {
    return { success: false, errors };
  }

  // ---------- Layer 4: Export detection ----------
  let hasExport = false;

  sourceFile.forEachChild(node => {
    // export default ...
    if (ts.isExportAssignment(node)) {
      hasExport = true;
    }

    // export const / function / class / etc
    if (
      ts.canHaveModifiers(node) &&
      node.modifiers?.some(
        m => m.kind === ts.SyntaxKind.ExportKeyword
      )
    ) {
      hasExport = true;
    }
  });

  if (!hasExport) {
    return {
      success: false,
      errors: ["Component must export at least one symbol"],
    };
  }

  return {
    success: true,
    errors: [],
  };
}
