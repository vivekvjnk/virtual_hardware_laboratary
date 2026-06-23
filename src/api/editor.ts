// src/api/editor.ts
import { FileType } from '../types/editor'; // I will create this

const API_BASE = 'http://localhost:3022/api/vhl-editor';

export async function readDirectory(targetPath: string): Promise<[string, FileType][]> {
    const response = await fetch(`${API_BASE}/rpc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'fs.readDirectory', params: { targetPath } })
    });
    const { data } = await response.json();
    return data;
}

export async function readFile(targetPath: string): Promise<string> {
    const response = await fetch(`${API_BASE}/rpc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'fs.readFile', params: { targetPath } })
    });
    const { data } = await response.json();
    return data.content;
}

export async function writeFile(targetPath: string, content: string): Promise<void> {
    await fetch(`${API_BASE}/rpc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'fs.writeFile', params: { targetPath, content } })
    });
}
