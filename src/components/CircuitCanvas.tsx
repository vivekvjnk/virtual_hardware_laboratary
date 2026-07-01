import { useEffect, useState } from 'react';
import { RunFrame } from '@tscircuit/runframe/runner';

export default function CircuitCanvas({ projectId, moduleName, onClose, isEmbedded = false }: { projectId: string, moduleName: string, onClose: () => void, isEmbedded?: boolean }) {
  const [fsMap, setFsMap] = useState<Record<string, string> | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadCircuit = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`http://localhost:3022/api/projects/${projectId}/modules/${moduleName}/circuit`);
        if (!response.ok) {
          throw new Error(`Failed to fetch circuit: ${response.statusText}`);
        }
        const data = await response.json();
        setFsMap(data);
      } catch (err: any) {
        console.error('Error rendering circuit:', err);
        setError(err.message || 'Unknown error occurred while fetching circuit files.');
      } finally {
        setLoading(false);
      }
    };

    loadCircuit();
  }, [projectId, moduleName]);

  const containerClasses = isEmbedded 
    ? "flex flex-col h-full w-full bg-slate-950"
    : "fixed inset-0 bg-slate-950 p-6 flex flex-col z-50";

  return (
    <div className={containerClasses}>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-white">Circuit: {moduleName}</h2>
        {!isEmbedded && (
          <button 
            onClick={onClose}
            className="bg-slate-800 hover:bg-slate-700 text-white font-bold py-2 px-4 rounded-xl transition-colors cursor-pointer"
          >
            Close
          </button>
        )}
      </div>
      <div className="flex-grow bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden relative" id="circuit-container">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center text-white bg-slate-900 z-10">
            <div className="flex flex-col items-center">
              <div className="w-10 h-10 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mb-4"></div>
              <span className="text-slate-400 font-medium">Loading circuit preview...</span>
            </div>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center text-red-400 bg-slate-900 p-4">
            <div className="text-center max-w-md">
              <p className="font-semibold text-lg mb-2">Error Loading Circuit</p>
              <p className="text-sm opacity-80 mb-4">{error}</p>
              <button 
                onClick={onClose}
                className="bg-red-900/30 hover:bg-red-900/50 text-red-200 border border-red-800/50 font-medium py-2 px-4 rounded-lg transition-colors cursor-pointer"
              >
                Go Back
              </button>
            </div>
          </div>
        )}
        {!loading && !error && fsMap && (
          <RunFrame
            fsMap={fsMap}
            entrypoint={`${moduleName}.tsx`}
            availableTabs={["pcb", "schematic", "cad"]}
            defaultTab="pcb"
          />
        )}
      </div>
    </div>
  );
}

