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
    <div className="flex flex-col h-full text-white gap-4">
      <div className="flex justify-between items-center p-4 rounded-3xl border border-slate-800 bg-slate-900">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setView('mission')}
            className="text-slate-400 hover:text-white transition-colors"
          >
            ← Back to Mission
          </button>
          <h1 className="text-xl font-bold text-white">Module: {moduleName}</h1>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => setShowEditor(!showEditor)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${showEditor ? 'bg-violet-600 hover:bg-violet-700 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
          >
            {showEditor ? 'Hide Editor' : 'Show Editor'}
          </button>
          <button 
            onClick={() => setShowChat(!showChat)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${showChat ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'bg-slate-800 text-slate-400'}`}
          >
            {showChat ? 'Hide Chat' : 'Show Chat'}
          </button>
        </div>
      </div>
      {/* Module action summary (mirrors tile design) */}
      <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6 mt-4"> 
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="inline-flex rounded-full bg-slate-800 text-slate-400 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]">
              Module
            </div>
            <h2 className="mt-3 text-lg font-semibold text-white">{moduleName}</h2>
          </div>

          <div className="flex-1">
            <div className="flex gap-3 mb-3">
              <button onClick={triggerWorkflow} disabled={triggering} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-xl text-sm transition-colors">
                {triggering ? 'Triggering...' : 'Trigger Workflow 1'}
              </button>
              <button onClick={renderCircuit} className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-xl text-sm transition-colors">
                Render Circuit
              </button>
            </div>
            <div className="flex gap-2">
              <button className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 py-1.5 px-3 rounded-lg transition-colors">Archy</button>
              <button className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 py-1.5 px-3 rounded-lg transition-colors">Librarian</button>
              <button className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 py-1.5 px-3 rounded-lg transition-colors">Ana</button>
            </div>
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
