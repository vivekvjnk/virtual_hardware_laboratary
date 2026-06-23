// src/components/Editor/FileExplorer.tsx
import React, { useState, useEffect } from 'react';
import { readDirectory } from '../../api/editor';
import { FileType } from '../../types/editor';

interface Props {
    onFileSelect: (path: string) => void;
}

export const FileExplorer: React.FC<Props> = ({ onFileSelect }) => {
    const [files, setFiles] = useState<[string, FileType][]>([]);

    useEffect(() => {
        readDirectory('.').then(setFiles);
    }, []);

    return (
        <div className="p-4 border-r border-gray-200">
            <h3 className="font-bold mb-2">Workspace</h3>
            <ul>
                {files.map(([name, type]) => (
                    <li key={name} className="cursor-pointer hover:bg-gray-100" onClick={() => type === FileType.File && onFileSelect(name)}>
                        {type === FileType.Directory ? '📁' : '📄'} {name}
                    </li>
                ))}
            </ul>
        </div>
    );
};
