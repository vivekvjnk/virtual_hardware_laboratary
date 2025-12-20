import fs from "fs/promises";
import path from "path";

import { validateComponent } from "../../src/library/validator.js";
import { TEMP_DIR } from "../../src/config/paths.js";

describe("validator.ts", () => {
  const makeTempFile = async (
    filename: string,
    content: string
  ): Promise<string> => {
    const filePath = path.join(TEMP_DIR, filename);
    await fs.writeFile(filePath, content, "utf-8");
    return filePath;
  };

  afterEach(async () => {
    try {
      const files = await fs.readdir(TEMP_DIR);
      await Promise.all(
        files.map((f: string) =>
          fs.unlink(path.join(TEMP_DIR, f))
        )
      );
    } catch {
      // ignore
    }
  });

  test("fails if file does not exist", async () => {
    const result = await validateComponent(
      path.join(TEMP_DIR, "nope.tsx")
    );

    expect(result.success).toBe(false);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  test("fails if extension is not .tsx", async () => {
    const filePath = await makeTempFile(
      "invalid.txt",
      "export const X = 1;"
    );

    const result = await validateComponent(filePath);

    expect(result.success).toBe(false);
    expect(result.errors).toContain(
      "Component file must have .tsx or .kicad_mod extension"
    );
  });

  test("fails on syntax error", async () => {
    const filePath = await makeTempFile(
      "broken.tsx",
      "export const X = ;"
    );

    const result = await validateComponent(filePath);

    expect(result.success).toBe(false);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  test("fails if module has no exports", async () => {
    const filePath = await makeTempFile(
      "empty.tsx",
      "const x = 42;"
    );

    const result = await validateComponent(filePath);

    expect(result.success).toBe(false);
    expect(
      result.errors.some(e =>
        e.toLowerCase().includes("export")
      )
    ).toBe(true);
  });

  test("passes for valid TSX component with named export", async () => {
    const filePath = await makeTempFile(
      "valid.tsx",
      `
      export const MyComponent = () => {
        return null;
      };
      `
    );

    const result = await validateComponent(filePath);

    expect(result.success).toBe(true);
    expect(result.errors.length).toBe(0);
  });

  test("passes for valid TSX component with default export", async () => {
    const filePath = await makeTempFile(
      "default.tsx",
      `
      export default function DefaultComponent() {
        return null;
      }
      `
    );

    const result = await validateComponent(filePath);

    expect(result.success).toBe(true);
    expect(result.errors.length).toBe(0);
  });

  test("validator never throws", async () => {
    await expect(
      validateComponent("totally-invalid-path")
    ).resolves.toBeDefined();
  });
});
