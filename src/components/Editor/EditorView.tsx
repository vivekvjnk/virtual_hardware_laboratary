// src/components/Editor/EditorView.tsx
import React, { useState } from 'react';
import { FileExplorer } from './FileExplorer';
import { Editor } from './Editor';

export const EditorView: React.FC = () => {
    const [selectedFile, setSelectedFile] = useState<string | null>(null);

    return (
        <div className="flex h-screen">
            <FileExplorer onFileSelect={setSelectedFile} />
            <Editor filePath={selectedFile} />
        </div>
    );
};
