import { useState, useEffect, useCallback, useRef } from 'react';

interface EditorViewProps {
  setView: (view: 'dashboard' | 'editor' | 'mission' | 'module_detail') => void;
  showSidebar: boolean;
  setShowSidebar: (show: boolean) => void;
  showMissionFeed: boolean;
  setShowMissionFeed: (show: boolean) => void;
  isEmbedded?: boolean;
}

export default function EditorView({ 
  setView, 
  showSidebar, 
  setShowSidebar, 
  showMissionFeed, 
  setShowMissionFeed,
  isEmbedded = false
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
  }, [showFileExplorer, showSidebar, showMissionFeed, setShowSidebar, setShowMissionFeed]);

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
  }, [isResizing, resizeStartX, resizeStartWidth]);

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
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: isEmbedded ? '100%' : 'calc(100vh - 3rem)',
      width: '100%',
      color: '#ffffff',
      backgroundColor: '#0f172a',
      border: '1px solid #334155',
      borderRadius: '0.75rem',
      overflow: 'hidden'
    }}>
      {/* Top Bar */}
      <div style={{
        padding: '0.75rem 1rem',
        borderBottom: '1px solid #1e293b',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: '#0f172a'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {!isEmbedded && (
            <button 
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                fontSize: '0.875rem',
                cursor: 'pointer'
              }}
              onClick={() => setView('dashboard')}
            >
              ← Back
            </button>
          )}
          <h2 style={{ fontSize: '0.825rem', fontWeight: 'bold', margin: 0, color: '#ffffff' }}>
            EDITOR
          </h2>
        </div>
        
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            style={{ 
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem', 
            borderRadius: '0.75rem', 
            fontSize: '0.75rem', 
            fontWeight: 600, 
            textTransform: 'uppercase', 
            letterSpacing: '0.05em',
            cursor: 'pointer',
            backgroundColor: 'rgba(37, 99, 235, 0.15)' ,
            border: '1px solid rgba(59, 130, 246, 0.5)' ,
            color: '#60a5fa',
            boxShadow: '0 0 2px rgba(59, 130, 246, 0.2)' ,
            transition: 'all 0.2s ease'
          }}
            onClick={() => setShowFileExplorer(!showFileExplorer)}
          >
            {showFileExplorer ? 'Hide Explorer' : 'Show Explorer'}
          </button>

          {!isEmbedded && (
            <>
              <button 
                style={{
                  backgroundColor: '#1e293b',
                  color: '#ffffff',
                  padding: '0.375rem 0.75rem',
                  borderRadius: '0.375rem',
                  border: '1px solid #334155',
                  fontSize: '0.75rem',
                  cursor: 'pointer'
                }}
                onClick={() => setShowSidebar(!showSidebar)}
              >
                {showSidebar ? 'Hide Sidebar' : 'Show Sidebar'}
              </button>
              <button 
                style={{
                  backgroundColor: '#1e293b',
                  color: '#ffffff',
                  padding: '0.375rem 0.75rem',
                  borderRadius: '0.375rem',
                  border: '1px solid #334155',
                  fontSize: '0.75rem',
                  cursor: 'pointer'
                }}
                onClick={() => setShowMissionFeed(!showMissionFeed)}
              >
                {showMissionFeed ? 'Hide MissionFeed' : 'Show MissionFeed'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Main Workspace Area */}
      <div style={{ display: 'flex', flexGrow: 1, minHeight: 0, overflow: 'hidden' }}>
        {showFileExplorer && (
          <>
            {/* File Explorer Tree Panel */}
            <div style={{
              width: `${sidebarWidth}px`,
              padding: '1rem',
              borderRight: '1px solid #334155',
              overflowY: 'auto',
              flexShrink: 0,
              backgroundColor: '#0f172a'
            }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem', marginTop: 0 }}>Files</h3>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.5rem', wordBreak: 'break-all' }}>
                Current: {currentPath}
              </p>
              
              {currentPath !== '.' && (
                <button 
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#c084fc',
                    fontSize: '0.875rem',
                    cursor: 'pointer',
                    padding: 0,
                    marginBottom: '0.5rem',
                    fontWeight: 600
                  }} 
                  onClick={goBack}
                >
                  .. (Back)
                </button>
              )}

              {tree.map(([name, type]) => {
                const path = currentPath === '.' ? name : `${currentPath}/${name}`;
                const isActive = activeFile === path;
                return (
                  <div 
                    key={name} 
                    style={{
                      cursor: 'pointer',
                      padding: '0.5rem',
                      borderBottom: '1px solid #1e293b',
                      backgroundColor: isActive ? '#1e293b' : 'transparent',
                      color: isActive ? '#c084fc' : '#cbd5e1',
                      fontSize: '0.875rem',
                      borderRadius: '0.25rem',
                      transition: 'background-color 0.15s'
                    }}
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

            {/* Resize Splitter Handle */}
            <div 
              style={{
                width: '4px',
                cursor: 'col-resize',
                backgroundColor: isResizing ? '#8b5cf6' : '#334155',
                flexShrink: 0,
                transition: 'background-color 0.15s'
              }}
              onMouseDown={(e) => {
                setIsResizing(true);
                setResizeStartX(e.clientX);
                setResizeStartWidth(sidebarWidth);
              }}
            />
          </>
        )}

        {/* Code Editor Panel */}
        <div style={{
          flexGrow: 1,
          padding: '1rem',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'relative',
          backgroundColor: '#020617'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e2e8f0', margin: 0, fontFamily: 'monospace' }}>
              {activeFile || 'No file selected'}
            </h3>
          </div>

          <textarea
            style={{
              flexGrow: 1,
              backgroundColor: '#0f172a',
              color: '#f8fafc',
              padding: '0.75rem',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              width: '100%',
              border: '1px solid #1e293b',
              borderRadius: '0.5rem',
              resize: 'none',
              outline: 'none',
              boxSizing: 'border-box'
            }}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            disabled={!activeFile}
          />

          {notification && (
            <div style={{
              position: 'absolute',
              bottom: '1.5rem',
              left: '1.5rem',
              backgroundColor: '#16a34a',
              color: '#ffffff',
              padding: '0.5rem 1rem',
              borderRadius: '0.5rem',
              boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
              fontSize: '0.875rem',
              border: '1px solid #22c55e',
              zIndex: 20
            }}>
              {notification}
            </div>
          )}

          {activeFile && (
            <button 
              style={{
                position: 'absolute',
                bottom: '1.5rem',
                right: '1.5rem',
                backgroundColor: 'rgba(12, 31, 73, 0.83)' ,
                border: '1px solid rgba(59, 130, 246, 0.5)' ,
                color: '#60a5fa',
                padding: '0.5rem 1.25rem',
                borderRadius: '0.5rem',
                boxShadow: '0 0 5px rgba(59, 130, 246, 0.2)' ,
                fontSize: '0.875rem',
                fontWeight: 600,
                cursor: 'pointer',
                zIndex: 20
              }} 
          //     style={{ 
          //   display: 'inline-flex',
          //   alignItems: 'center',
          //   gap: '0.5rem',
          //   padding: '0.5rem 1rem', 
          //   borderRadius: '0.75rem', 
          //   fontSize: '0.75rem', 
          //   fontWeight: 600, 
          //   textTransform: 'uppercase', 
          //   letterSpacing: '0.05em',
          //   cursor: 'pointer',
          //   backgroundColor: 'rgba(37, 99, 235, 0.15)' ,
          //   border: '1px solid rgba(59, 130, 246, 0.5)' ,
          //   color: '#60a5fa',
          //   boxShadow: '0 0 2px rgba(59, 130, 246, 0.2)' ,
          //   transition: 'all 0.2s ease'
          // }}
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