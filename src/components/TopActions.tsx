import { useState, useRef } from 'react';
import type { HeroAction } from '../types/dashboard';
import CreateModuleModal from './CreateModuleModal';
import { Plus } from 'lucide-react';

interface TopActionsProps {
  actions: HeroAction[];
  isIdentified: boolean;
  onUpload: (projectName: string, file: File) => void;
  projectId?: string | null;
  onModuleCreated?: () => void;
}

const variantStyles = {
  primary: 'bg-violet-500 text-white',
  secondary: 'border border-slate-800 bg-slate-900 text-slate-100',
};

export default function TopActions({ actions, isIdentified, onUpload, projectId, onModuleCreated }: TopActionsProps) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && projectName) {
      onUpload(projectName, file);
      setShowCreateForm(false);
      setProjectName('');
    }
  };

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="col-span-2 mb-4 flex items-center gap-2 text-sm text-slate-400">
        <span className={`h-3 w-3 rounded-full ${isIdentified ? 'bg-green-500' : 'bg-red-500'}`}></span>
        {isIdentified ? 'Connected' : 'Disconnected'}
      </div>
      
      {projectId && (
        <div className="rounded-3xl border border-blue-800/50 bg-blue-900/20 p-6 shadow-xl shadow-slate-950/30">
          <div className="flex items-center justify-between gap-4 text-sm text-slate-400">
            <span className="uppercase tracking-[0.24em] text-blue-500">Active Project</span>
            <span className="rounded-full bg-blue-900/40 px-3 py-1 text-xs uppercase tracking-[0.2em] text-blue-400 border border-blue-800/50">
              In Progress
            </span>
          </div>
          <h2 className="mt-4 text-2xl font-semibold text-white">Add New Module</h2>
          <p className="mt-2 text-slate-400">Expand your design by adding a new functional module to the current project.</p>
          
          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="mt-8 inline-flex items-center justify-center gap-2 rounded-2xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 active:scale-95"
          >
            <Plus size={18} />
            <span>Create Module</span>
          </button>
        </div>
      )}

      {actions.map((action) => (
        <div
          key={action.id}
          className="rounded-3xl border border-slate-800 bg-slate-950/95 p-6 shadow-xl shadow-slate-950/30"
        >
          <div className="flex items-center justify-between gap-4 text-sm text-slate-400">
            <span className="uppercase tracking-[0.24em] text-slate-500">Project</span>
            <span className="rounded-full bg-slate-900 px-3 py-1 text-xs uppercase tracking-[0.2em]">
              {action.variant === 'primary' ? 'New' : 'Restore'}
            </span>
          </div>
          <h2 className="mt-4 text-2xl font-semibold text-white">{action.title}</h2>
          <p className="mt-2 text-slate-400">{action.description}</p>
          
          {action.id === 'create-project' && showCreateForm ? (
            <div className="mt-4">
              <input 
                type="text" 
                placeholder="Project Name" 
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                className="w-full p-2 mb-2 bg-slate-900 border border-slate-700 rounded"
              />
              <button onClick={handleUploadClick} className="bg-green-600 text-white p-2 rounded w-full">Upload Zip</button>
              <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept=".zip" />
            </div>
          ) : (
            <button
              type="button"
              disabled={action.id === 'create-project' && !isIdentified}
              onClick={() => action.id === 'create-project' && setShowCreateForm(true)}
              className={`mt-8 inline-flex items-center justify-center rounded-2xl px-5 py-3 text-sm font-semibold transition ${variantStyles[action.variant]} ${action.id === 'create-project' && !isIdentified ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {action.cta}
            </button>
          )}
        </div>
      ))}

      {projectId && (
        <CreateModuleModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          projectId={projectId}
          onSuccess={() => onModuleCreated?.()}
        />
      )}
    </div>
  );
}
