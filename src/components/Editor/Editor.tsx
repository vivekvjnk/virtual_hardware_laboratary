// src/components/Editor/Editor.tsx
import React, { useState, useEffect } from 'react';
import { readFile, writeFile } from '../../api/editor';

interface Props {
    filePath: string | null;
}

export const Editor: React.FC<Props> = ({ filePath }) => {
    const [content, setContent] = useState('');

    useEffect(() => {
        if (filePath) {
            readFile(filePath).then(setContent);
        }
    }, [filePath]);

    const handleSave = () => {
        if (filePath) {
            writeFile(filePath, content);
        }
    };

    if (!filePath) return <div className="p-4">Select a file to edit.</div>;

    return (
        <div className="p-4">
            <h3 className="font-bold mb-2">{filePath}</h3>
            <textarea
                className="w-full h-96 p-2 border border-gray-300"
                value={content}
                onChange={(e) => setContent(e.target.value)}
            />
            <button className="bg-blue-500 text-white p-2 mt-2" onClick={handleSave}>Save</button>
        </div>
    );
};
