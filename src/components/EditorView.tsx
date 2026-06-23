import React, { useState, useEffect, useCallback, useRef } from 'react';
// Trigger rebuild for Vite cache fix.

interface EditorViewProps {
  projectPath: string;
  setView: (view: 'dashboard' | 'editor') => void;
  showSidebar: boolean;
  setShowSidebar: (show: boolean) => void;
  showMissionFeed: boolean;
  setShowMissionFeed: (show: boolean) => void;
  navItems: any[]; // Adjust type as needed
  missionFeed: any[]; // Adjust type as needed
}

export default function EditorView({ 
  projectPath, 
  setView, 
  showSidebar, 
  setShowSidebar, 
  showMissionFeed, 
  setShowMissionFeed,
  navItems, 
  missionFeed 
}: EditorViewProps) {
  const [tree, setTree] = useState<[string, number][]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [content, setContent] = useState('');
  const contentRef = useRef(content);
  
  useEffect(() => {
    contentRef.current = content;
  }, [content]);
  const [currentPath, setCurrentPath] = useState('.');
  const [sidebarWidth, setSidebarWidth] = useState(300);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeStartX, setResizeStartX] = useState(0);
  const [resizeStartWidth, setResizeStartWidth] = useState(0);
  const [showFileExplorer, setShowFileExplorer] = useState(true);
  const [notification, setNotification] = useState<string | null>(null);
  const writeFileRef = useRef<(() => Promise<void>) | null>(null);

  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [notification]);
  
  const writeFile = useCallback(async () => {
    if (!activeFile) return;
    await fetch('http://localhost:3022/api/vhl-editor/rpc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'fs.writeFile',
        params: { targetPath: activeFile, content: contentRef.current }
      })
    });
    setNotification('Saved successfully');
  }, [activeFile]);

  useEffect(() => {
    writeFileRef.current = writeFile;
  }, [writeFile]);
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'e') {
        e.preventDefault();
        setShowFileExplorer((prev) => !prev);
      }
      if (e.ctrlKey && e.key === 'b') {
        e.preventDefault();
        const shouldShow = !(showSidebar || showMissionFeed);
        setShowSidebar(shouldShow);
        setShowMissionFeed(shouldShow);
      }
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        if (writeFileRef.current) writeFileRef.current();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showFileExplorer, showSidebar, showMissionFeed]);


  useEffect(() => {
    fetchDirectory('.');
  }, []);
  
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const delta = e.clientX - resizeStartX;
      setSidebarWidth(Math.max(150, Math.min(600, resizeStartWidth + delta)));
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = 'default';
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const fetchDirectory = async (targetPath: string) => {
    const response = await fetch('http://localhost:3022/api/vhl-editor/rpc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'fs.readDirectory',
        params: { targetPath }
      })
    });
    const result = await response.json();
    if (result.success) {
      setTree(result.data);
      setCurrentPath(targetPath);
    }
  };

  const goBack = () => {
    if (currentPath === '.') return;
    const parentPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || '.';
    fetchDirectory(parentPath);
  };

  const readFile = async (targetPath: string) => {
    const response = await fetch('http://localhost:3022/api/vhl-editor/rpc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'fs.readFile',
        params: { targetPath }
      })
    });
    const result = await response.json();
    if (result.success) {
      setActiveFile(targetPath);
      setContent(result.data.content);
    }
  };

  return (
    <div className="flex h-[calc(100vh-3rem)] text-white bg-slate-900 border border-slate-700 rounded-lg flex-col">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            className="text-sm text-slate-400 hover:text-white"
            onClick={() => setView('dashboard')}
          >
            ← Back
          </button>
          <h2 className="text-xl font-bold">VHL Editor</h2>
        </div>
        <div className="flex gap-2">
          <button 
            className="bg-slate-800 text-white px-3 py-1 rounded text-sm hover:bg-slate-700"
            onClick={() => setShowFileExplorer(!showFileExplorer)}
          >
            {showFileExplorer ? 'Hide Explorer' : 'Show Explorer'}
          </button>
          <button 
            className="text-xs bg-slate-800 px-3 py-1 rounded hover:bg-slate-700"
            onClick={() => setShowSidebar(!showSidebar)}
          >
            {showSidebar ? 'Hide Sidebar' : 'Show Sidebar'}
          </button>
          <button 
            className="text-xs bg-slate-800 px-3 py-1 rounded hover:bg-slate-700"
            onClick={() => setShowMissionFeed(!showMissionFeed)}
          >
            {showMissionFeed ? 'Hide MissionFeed' : 'Show MissionFeed'}
          </button>
        </div>
      </div>
      <div className="flex h-full overflow-hidden">
        {showFileExplorer && (
          <>
            <div className="p-4 border-r border-slate-700 overflow-y-auto flex-shrink-0" style={{ width: `${sidebarWidth}px` }}>
              <h3 className="text-lg font-semibold mb-4">Files</h3>
              <p className="text-xs text-slate-400 mb-2">Current: {currentPath}</p>
              {currentPath !== '.' && (
                <button className="text-violet-400 mb-2" onClick={goBack}>.. (Back)</button>
              )}
              {tree.map(([name, type]) => {
                const path = currentPath === '.' ? name : `${currentPath}/${name}`;
                const isActive = activeFile === path;
                return (
                  <div 
                    key={name} 
                    className={`cursor-pointer px-2 py-2 border-b border-slate-800 last:border-b-0 transition-colors 
                      ${isActive ? 'bg-slate-800 text-violet-400' : 'hover:bg-slate-800 hover:text-white text-slate-300'}`}
                    onClick={() => {
                      if (type === 2) fetchDirectory(path);
                      else if (type === 1) readFile(path);
                    }}
                  >
                    {type === 2 ? `📁 ${name}` : `📄 ${name}`}
                  </div>
                );
              })}
            </div>
            <div 
              className="w-1 cursor-col-resize bg-slate-700 hover:bg-violet-500 transition-colors"
              onMouseDown={(e) => {
                setIsResizing(true);
                setResizeStartX(e.clientX);
                setResizeStartWidth(sidebarWidth);
              }}
            />
          </>
        )}
        <div className="flex-grow p-4 flex flex-col overflow-hidden relative">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">{activeFile || 'No file selected'}</h3>
          </div>
          <textarea
            className="flex-grow bg-slate-950 p-2 font-mono w-full"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            disabled={!activeFile}
          />
          {notification && (
            <div className="absolute bottom-6 left-6 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
              {notification}
            </div>
          )}
          {activeFile && (
            <button 
              className="absolute bottom-6 right-6 bg-violet-600 px-4 py-2 rounded-lg shadow-lg text-sm hover:bg-violet-700" 
              onClick={writeFile}
            >
              Save
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
