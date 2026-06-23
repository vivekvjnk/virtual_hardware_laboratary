// src/types/editor.ts
export const FileType = {
    Unknown: 0,
    File: 1,
    Directory: 2
} as const;

export type FileType = typeof FileType[keyof typeof FileType];
