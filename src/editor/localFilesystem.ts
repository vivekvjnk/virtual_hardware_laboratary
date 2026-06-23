// src/editor/localFilesystem.ts
import { promises as fs } from 'fs';
import path from 'path';
import { IFileSystemProvider, FileType } from './filesystem.interface.js';

export class LocalFileSystemProvider implements IFileSystemProvider {
    private workspaceRoot: string;

    constructor(workspaceRoot: string) {
        this.workspaceRoot = path.resolve(workspaceRoot);
    }

    private resolvePath(safeUri: string): string {
        const resolved = path.resolve(this.workspaceRoot, safeUri);
        if (!resolved.startsWith(this.workspaceRoot)) {
            throw new Error("Access Denied: Path traversal detected.");
        }
        return resolved;
    }

    async readDirectory(safeUri: string): Promise<[string, FileType][]> {
        const fullPath = this.resolvePath(safeUri);
        const entries = await fs.readdir(fullPath, { withFileTypes: true });
        return entries.map(entry => [
            entry.name,
            entry.isDirectory() ? FileType.Directory : FileType.File
        ]);
    }

    async readFile(safeUri: string): Promise<string> {
        const fullPath = this.resolvePath(safeUri);
        return fs.readFile(fullPath, 'utf-8');
    }

    async writeFile(safeUri: string, content: string): Promise<void> {
        const fullPath = this.resolvePath(safeUri);
        await fs.writeFile(fullPath, content, 'utf-8');
    }
}
