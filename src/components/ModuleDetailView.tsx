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

  const renderCircuit = () => {
    // In the embedded view the circuit canvas is already visible; this is a placeholder
    // to allow parity with the dashboard action. We can optionally scroll to the canvas.
    const el = document.querySelector('.module-canvas') as HTMLElement | null;
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };



  return (
    <div className="flex flex-col h-full text-white gap-4 ">
      <div className="flex justify-between items-center p-4 rounded-3xl border border-slate-800 bg-slate-900">
        <div className="inline-flex rounded-full bg-slate-800 text-slate-400 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]">
          <button 
            onClick={() => setView('mission')}
            className="text-slate-400 hover:text-white transition-colors"
          >
            ← Back to Mission
          </button>
        </div>
        <div className="inline-flex rounded-full bg-slate-800 text-slate-400 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]">
          <h1 className="text-xl font-bold text-white">Module: {moduleName}</h1>
        </div>
        <div className="inline-flex rounded-full bg-slate-800 text-slate-400 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]">
        
          <div className="inline-flex rounded-full bg-slate-800 text-slate-400 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]">
            <button 
              onClick={() => setShowEditor(!showEditor)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${showEditor ? 'bg-violet-600 hover:bg-violet-700 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
            >
          
              {showEditor ? 'Hide Editor' : 'Show Editor'}
            </button>
          </div>
          <div className="inline-flex rounded-full bg-slate-800 text-slate-400 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]">
          
            <button 
              onClick={() => setShowChat(!showChat)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${showChat ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'bg-slate-800 text-slate-400'}`}
            >
              {showChat ? 'Hide Chat' : 'Show Chat'}
            </button>
          </div>
        </div>
      </div>

      <div className="flex-grow flex gap-4 overflow-hidden">
        {showEditor && (
          <div className="w-1/4 min-w-[300px] h-full">
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
        
        <div className="flex-grow h-full bg-slate-900 rounded-3xl border border-slate-800 overflow-hidden relative">
          <CircuitCanvas 
            projectId={projectId}
            moduleName={moduleName}
            onClose={() => {}}
            isEmbedded={true}
          />
        </div>

        {showChat && (
          <div className="w-1/4 min-w-[350px] h-full flex flex-col gap-2">
            <div className="flex-none flex gap-1 bg-slate-800 p-1 rounded-xl">
               {['archy', 'librarian', 'ana'].map(agent => (
                 <button
                    key={agent}
                    onClick={() => setActiveAgent(agent)}
                    className={`flex-grow py-1 px-2 rounded-lg text-xs capitalize transition-colors ${activeAgent === agent ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
                 >
                   {agent}
                 </button>
               ))}
            </div>
            <div className="flex-grow min-h-0">
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
