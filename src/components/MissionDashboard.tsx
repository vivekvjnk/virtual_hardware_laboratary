import { useState, useEffect } from 'react';

export default function MissionDashboard({ projectId }: { projectId: string }) {
  const [modules, setModules] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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
  }, [projectId]);

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
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {modules.map(moduleName => (
          <div key={moduleName} className="border border-slate-800 bg-slate-900 p-6 rounded-3xl">
            <h2 className="text-lg font-semibold text-white mb-4">{moduleName}</h2>
            <button 
              onClick={() => triggerWorkflow(moduleName)}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-xl"
            >
              Trigger Workflow 1
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
