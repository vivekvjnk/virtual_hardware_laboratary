// src/editor/filesystem.interface.ts
export enum FileType {
    Unknown = 0,
    File = 1,
    Directory = 2
}

export interface IFileStat {
    type: FileType;
    ctime: number; // Creation time
    mtime: number; // Modification time
    size: number;
}

export interface IFileSystemProvider {
    readDirectory(workspaceUri: string): Promise<[string, FileType][]>;
    readFile(fileUri: string): Promise<string>;
    writeFile(fileUri: string, content: string): Promise<void>;
}
