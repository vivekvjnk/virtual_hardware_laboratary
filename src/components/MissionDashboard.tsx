import { useState, useEffect } from 'react';
import CircuitCanvas from './CircuitCanvas';
import ProjectStateView from './ProjectStateView';
import AgentChat from './AgentChat';

export default function MissionDashboard({ projectId }: { projectId: string }) {
  const [modules, setModules] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCircuit, setActiveCircuit] = useState<string | null>(null);
  const [projectState, setProjectState] = useState<any>(null);
  const [activeChat, setActiveChat] = useState<{ moduleName: string, agentType: string } | null>(null);

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
      <h1 className="text-2xl font-bold text-white mb-6">Mission Dashboard</h1>
      {projectState && <ProjectStateView state={projectState} />}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {modules.map(moduleName => (
          <div key={moduleName} className="border border-slate-800 bg-slate-900 p-6 rounded-3xl">
            <h2 className="text-lg font-semibold text-white mb-4">{moduleName}</h2>
            <div className="flex flex-col gap-2">
              <div className="flex gap-2">
                <button 
                  onClick={() => triggerWorkflow(moduleName)}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-xl flex-grow"
                >
                  Trigger Workflow 1
                </button>
                <button 
                  onClick={() => setActiveCircuit(moduleName)}
                  className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-xl"
                >
                  Render Circuit
                </button>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <button 
                  onClick={() => openChat(moduleName, 'archy')}
                  className="bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold py-2 px-1 rounded-lg"
                >
                  Archy
                </button>
                <button 
                  onClick={() => openChat(moduleName, 'librarian')}
                  className="bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold py-2 px-1 rounded-lg"
                >
                  Librarian
                </button>
                <button 
                  onClick={() => openChat(moduleName, 'ana')}
                  className="bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold py-2 px-1 rounded-lg"
                >
                  Ana
                </button>
              </div>
            </div>
          </div>
        ))}
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
          onClose={() => setActiveChat(null)} 
        />
      )}
    </div>
  );
}
