import { useState, useEffect } from 'react';
import CircuitCanvas from './CircuitCanvas';
import ProjectStateView from './ProjectStateView';
import AgentChat from './AgentChat';

export default function MissionDashboard({ projectId, onOpenModuleDetail }: { projectId: string, onOpenModuleDetail: (moduleName: string) => void }) {
  const [modules, setModules] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCircuit, setActiveCircuit] = useState<string | null>(null);
  const [projectState, setProjectState] = useState<any>(null);
  const [activeChat, setActiveChat] = useState<{ moduleName: string, agentType: string, initialMessage?: string } | null>(null);

  useEffect(() => {
    // Fetch modules
    fetch('http://localhost:3022/api/get-modules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId })
    })
      .then(res => res.json())
      .then(data => {
        setModules(data.modules || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching modules:', err);
        setLoading(false);
      });

    // Fetch project state
    const fetchState = () => {
        fetch('http://localhost:3022/api/project-state')
          .then(res => res.json())
          .then(data => {
            setProjectState(data);
          })
          .catch(err => {
            console.error('Error fetching project state:', err);
          });
    };

    fetchState();
    const interval = setInterval(fetchState, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, [projectId]);

  const openChat = (moduleName: string, agentType: string) => {
    setActiveChat({ moduleName, agentType });
  };

  const triggerWorkflow = (moduleName: string) => {
    fetch('http://localhost:3022/api/trigger-workflow', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ module_name: moduleName })
    })
      .then(res => res.json())
      .then(data => {
        console.log('Workflow triggered:', data);
        alert(`Workflow 1 triggered for module: ${moduleName}`);
      })
      .catch(err => console.error('Error triggering workflow:', err));
  };


  if (loading) return <div className="text-white p-6">Loading modules...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-white mb-4">Mission Dashboard</h1>
      {projectState && <ProjectStateView state={projectState} />}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 mt-4">
        {modules.map(moduleName => {
          return (
            <div key={moduleName} className="border border-slate-800 bg-slate-900/60 p-5 rounded-3xl flex flex-col justify-between min-h-[200px]">
              {/* Header row: module name + open detail button */}
              <div className="flex justify-between items-start gap-3 mb-4">
                <h2 className="text-base font-bold text-white break-words leading-snug flex-1 min-w-[120px]">{moduleName}</h2>
                <button
                  onClick={() => onOpenModuleDetail(moduleName)}
                  className="flex-shrink-0 bg-violet-600 hover:bg-violet-700 text-white text-xs font-bold py-1 px-3 rounded-lg flex items-center gap-1.5 transition-colors"
                >
                  <span>Open Detail View</span>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </button>
              </div>

              <div className="flex flex-col gap-2.5">
                {/* Action buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={() => triggerWorkflow(moduleName)}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold py-2 px-4 rounded-xl flex-grow transition-colors"
                  >
                    Trigger Workflow 1
                  </button>
                  <button
                    onClick={() => setActiveCircuit(moduleName)}
                    className="bg-green-600 hover:bg-green-700 text-white text-xs font-bold py-2 px-4 rounded-xl transition-colors"
                  >
                    Render Circuit
                  </button>
                </div>

                {/* Agent buttons */}
                <div className="grid grid-cols-3 gap-2">
                  <button
                    onClick={() => openChat(moduleName, 'archy')}
                    className="bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold py-2 px-1 rounded-lg transition-colors"
                  >
                    Archy
                  </button>
                  <button
                    onClick={() => openChat(moduleName, 'librarian')}
                    className="bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold py-2 px-1 rounded-lg transition-colors"
                  >
                    Librarian
                  </button>
                  <button
                    onClick={() => openChat(moduleName, 'ana')}
                    className="bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold py-2 px-1 rounded-lg transition-colors"
                  >
                    Ana
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {activeCircuit && (
        <CircuitCanvas
          projectId={projectId}
          moduleName={activeCircuit}
          onClose={() => setActiveCircuit(null)}
        />
      )}
      {activeChat && (
        <AgentChat
          moduleName={activeChat.moduleName}
          agentType={activeChat.agentType}
          initialMessage={activeChat.initialMessage}
          onClose={() => setActiveChat(null)}
        />
      )}
    </div>
  );
}
