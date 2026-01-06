
import fs from "fs/promises";
import path from "path";
import { LOCAL_LIBRARY_DIR } from "../../config/paths.js";
import { getFilesRecursive } from "../../runtime/libraryFs.js";

export async function getComponent(deviceName: string): Promise<string> {
    const libDir = process.env.VHL_LIBRARY_DIR || LOCAL_LIBRARY_DIR;

    // 1. Try exact path or simple variations
    const possiblePaths = [
        path.join(libDir, deviceName),
        path.join(libDir, deviceName + ".tsx"),
    ];

    let filePath: string | null = null;

    for (const p of possiblePaths) {
        try {
            await fs.access(p);
            filePath = p;
            break;
        } catch { }
    }

    // 2. If not found, search recursive
    if (!filePath) {
        const files = await getFilesRecursive(libDir);
        const normalizedQuery = deviceName.toLowerCase().replace(/\\/g, "/");

        // Exact match on basename
        filePath = files.find(f => {
            const baseName = path.basename(f, ".tsx").toLowerCase();
            return baseName === normalizedQuery;
        }) || null;
    }

    if (!filePath) {
        return "Device not found";
    }

    const content = await fs.readFile(filePath, "utf-8");

    // Extract pinLabels object
    const pinLabelsMatch = content.match(/const\s+pinLabels\s*=\s*(\{[\s\S]*?\})\s*(?:as\s*const)?/);

    if (!pinLabelsMatch) {
        return "No pin labels found";
    }

    const pinLabelsBlock = pinLabelsMatch[1];
    const mappings: string[] = [];

    // Regex to extract key and value from the block
    // Matches: pin1: ["BAT"] or "pin1": ["BAT"]
    // We assume the value is an array of strings ["VAL"]
    const entryRegex = /(?:["']?(\w+)["']?)\s*:\s*\[\s*"([^"]+)"/g;

    let match;
    while ((match = entryRegex.exec(pinLabelsBlock)) !== null) {
        mappings.push(`${match[1]}: ${match[2]}`);
    }

    if (mappings.length === 0) {
        return "No pin labels found";
    }

    return mappings.join("\n");
}
