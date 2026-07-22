import { useState } from 'react';
import EditorView from './EditorView';
import CircuitCanvas from './CircuitCanvas';
import AgentChat from './AgentChat';

interface ModuleDetailViewProps {
  projectId: string;
  moduleName: string;
  setView: (view: 'dashboard' | 'editor' | 'mission' | 'module_detail') => void;
  showSidebar: boolean;
  setShowSidebar: (show: boolean) => void;
  showMissionFeed: boolean;
  setShowMissionFeed: (show: boolean) => void;
}

export default function ModuleDetailView({
  projectId,
  moduleName,
  setView,
  showSidebar,
  setShowSidebar,
  showMissionFeed,
  setShowMissionFeed
}: ModuleDetailViewProps) {
  const [showEditor, setShowEditor] = useState(true);
  const [showChat, setShowChat] = useState(true);
  const [activeAgent, setActiveAgent] = useState('archy');
  const [triggering, setTriggering] = useState(false);

  const triggerWorkflow = async () => {
    setTriggering(true);
    try {
      await fetch('http://localhost:3022/api/trigger-workflow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ module_name: moduleName })
      });
      alert(`Workflow triggered for ${moduleName}`);
    } catch (err) {
      console.error('Error triggering workflow:', err);
      alert('Failed to trigger workflow');
    } finally {
      setTriggering(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: 'white', gap: '1rem', padding: '0.5rem', backgroundColor: '#020617' }}>
      {/* Navigation Header Box */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1.5rem', borderRadius: '1rem', border: '1px solid #334155', backgroundColor: '#0f172a' }}>
        {/* Back Button */}
        <button 
        onClick={() => setView('mission')}
        style={{ 
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.375rem',
          padding: '0.5rem 1rem', 
          borderRadius: '0.75rem', 
          backgroundColor: 'rgba(14, 165, 233, 0.1)', 
          border: '1px solid rgba(56, 189, 248, 0.4)', 
          color: '#38bdf8',
          fontSize: '0.75rem', 
          fontWeight: 600, 
          textTransform: 'uppercase', 
          letterSpacing: '0.05em',
          cursor: 'pointer',
          boxShadow: '0 0 2px rgba(56, 189, 248, 0.15)',
          transition: 'all 0.2s ease'
        }}
      >
        <span>←</span> Back to Mission
      </button>

        {/* Module Title Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.625rem',
          backgroundColor: '#020617',
          border: '2px solid #1e293b',
          padding: '0.375rem 0.875rem',
          borderRadius: '9999px',
          boxShadow: 'inset 0 0 5px #38bdf8'
        }}>
          {/* <span style={{
            width: '0.5rem',
            height: '0.5rem',
            borderRadius: '50%',
            backgroundColor: '#38bdf8',
            boxShadow: '0 0 5px #38bdf8',
            display: 'inline-block'
          }} /> */}
          {/* <span style={{ color: '#64748b', fontSize: '0.7rem', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            MODULE
          </span> */}
          <span style={{ color: '#f8fafc', fontSize: '1rem', fontWeight: 700, fontFamily: 'monospace', textTransform: 'uppercase'  }}>
            {moduleName}
          </span>
        </div>

        {/* Action Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
  {/* Editor Toggle */}
  <button 
    onClick={() => setShowEditor(!showEditor)}
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
      backgroundColor: showEditor ? 'rgba(124, 58, 237, 0.15)' : '#020617',
      border: showEditor ? '1px solid rgba(139, 92, 246, 0.5)' : '1px solid #1e293b',
      color: showEditor ? '#c084fc' : '#64748b',
      boxShadow: showEditor ? '0 0 5px rgba(139, 92, 246, 0.2)' : 'none',
      transition: 'all 0.2s ease'
    }}
  >
            {showEditor ? 'Hide Editor' : 'Show Editor'}
          </button>

          <button 
    onClick={() => setShowChat(!showChat)}
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
      backgroundColor: showChat ? 'rgba(37, 99, 235, 0.15)' : '#020617',
      border: showChat ? '1px solid rgba(59, 130, 246, 0.5)' : '1px solid #1e293b',
      color: showChat ? '#60a5fa' : '#64748b',
      boxShadow: showChat ? '0 0 5px rgba(59, 130, 246, 0.2)' : 'none',
      transition: 'all 0.2s ease'
    }}
  >
            {showChat ? 'Hide Chat' : 'Show Chat'}
          </button>
        </div>
      </div>

      {/* Main Grid Layout */}
      <div style={{ display: 'flex', flexGrow: 1, gap: '1rem', overflow: 'hidden', minHeight: 0 }}>
        {/* Editor Panel */}
        {showEditor && (
          <div style={{ width: '25%', minWidth: '300px', height: '100%', borderRadius: '1rem', border: '1px solid #1e293b', backgroundColor: '#0f172a', overflow: 'hidden' }}>
            <EditorView 
              setView={setView}
              showSidebar={showSidebar}
              setShowSidebar={setShowSidebar}
              showMissionFeed={showMissionFeed}
              setShowMissionFeed={setShowMissionFeed}
              isEmbedded={true}
            />
          </div>
        )}
        
        {/* Canvas Panel */}
        <div style={{ flexGrow: 1, height: '100%', backgroundColor: '#0f172a', borderRadius: '1rem', border: '1px solid #1e293b', overflow: 'hidden', position: 'relative' }}>
          <CircuitCanvas 
            projectId={projectId}
            moduleName={moduleName}
            onClose={() => {}}
            isEmbedded={true}
          />
        </div>

        {/* Agent Chat Panel */}
        {showChat && (
          <div style={{ width: '25%', minWidth: '350px', height: '100%', display: 'flex', flexDirection: 'column', gap: '0.5rem', borderRadius: '1rem', border: '1px solid #1e293b', backgroundColor: '#0f172a', padding: '0.5rem' }}>
  {/* Agent Selection Pill Bar */}
  <div style={{ display: 'flex', gap: '0.375rem', width: '100%' }}>
    {[
      { 
        id: 'archy', 
        label: 'ARCHY', 
        activeBg: 'rgba(37, 99, 235, 0.15)', 
        activeBorder: '1px solid rgba(59, 130, 246, 0.5)', 
        activeColor: '#60a5fa', 
        activeGlow: '0 0 12px rgba(59, 130, 246, 0.2)' 
      },
      { 
        id: 'librarian', 
        label: 'LIBRARIAN', 
        activeBg: 'rgba(124, 58, 237, 0.15)', 
        activeBorder: '1px solid rgba(139, 92, 246, 0.5)', 
        activeColor: '#c084fc', 
        activeGlow: '0 0 12px rgba(139, 92, 246, 0.2)' 
      },
      { 
        id: 'ana', 
        label: 'ANA', 
        activeBg: 'rgba(13, 148, 136, 0.15)', 
        activeBorder: '1px solid rgba(45, 212, 191, 0.5)', 
        activeColor: '#2dd4bf', 
        activeGlow: '0 0 12px rgba(45, 212, 191, 0.2)' 
      }
    ].map((agent) => {
      const isActive = activeAgent === agent.id;
      return (
        <button
          key={agent.id}
          onClick={() => setActiveAgent(agent.id)}
          style={{
            flex: 1,
            padding: '0.5rem 0.25rem',
            borderRadius: '0.75rem',
            fontSize: '0.75rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            cursor: 'pointer',
            backgroundColor: isActive ? agent.activeBg : '#020617',
            border: isActive ? agent.activeBorder : '1px solid #1e293b',
            color: isActive ? agent.activeColor : '#64748b',
            boxShadow: isActive ? agent.activeGlow : 'none',
            transition: 'all 0.2s ease',
            textAlign: 'center'
          }}
        >
          {agent.label}
        </button>
      );
    })}
  </div>
            <div style={{ flexGrow: 1, minHeight: 0, overflow: 'hidden' }}>
              <AgentChat 
                moduleName={moduleName}
                agentType={activeAgent}
                onClose={() => {}}
                isEmbedded={true}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}