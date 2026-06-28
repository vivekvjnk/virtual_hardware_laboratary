import React, { useState } from 'react';

interface ProjectState {
    project_id: string | null;
    workspace_root: string | null;
    project_root: string | null;
    worktrees: Record<string, string>;
    artifacts: any[];
    backend_status: string;
    runtime_status: string;
    is_synthesizable?: boolean;
    is_synthesis_completed?: boolean;
}

const CollapsibleSection = ({ title, children, initialExpanded = false }: { title: string, children: React.ReactNode, initialExpanded?: boolean }) => {
    const [expanded, setExpanded] = useState(initialExpanded);
    return (
        <div className="mb-4">
            <button 
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-2 text-sm font-semibold text-slate-400 uppercase tracking-wider hover:text-white transition-colors w-full text-left"
            >
                <span className={`inline-block transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`} style={{ fontSize: '10px' }}>▶</span>
                {title}
            </button>
            {expanded && <div className="mt-3 ml-4 space-y-3">{children}</div>}
        </div>
    );
};

const ScrollablePath = ({ label, path }: { label: string, path: string | null }) => (
    <div className="mb-3">
        {label && <span className="text-slate-500 block text-[10px] uppercase tracking-tight mb-1">{label}</span>}
        <div className="max-w-[280px] sm:max-w-sm md:max-w-md overflow-x-auto whitespace-nowrap bg-slate-800/80 px-3 py-1.5 rounded-lg scrollbar-hide border border-slate-700/50">
            <code className="text-xs text-blue-300 font-mono">{path || 'N/A'}</code>
        </div>
    </div>
);

export default function ProjectStateView({ state }: { state: ProjectState }) {
    if (!state.project_id) return null;

    return (
        <div className="mt-8 p-6 border border-slate-800/60 bg-slate-900/50 backdrop-blur-sm rounded-3xl text-white">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-3">
                <div className="w-1.5 h-6 bg-blue-500 rounded-full shadow-[0_0_10px_rgba(59,130,246,0.5)]"></div>
                Project Context
            </h2>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                <div className="space-y-6">
                    <CollapsibleSection title="System Paths">
                        <ScrollablePath label="Workspace" path={state.workspace_root} />
                        <ScrollablePath label="Project Root" path={state.project_root} />
                    </CollapsibleSection>

                    <div className="flex gap-4">
                        <div className="flex-1 bg-slate-800/30 p-3 rounded-2xl border border-slate-700/20">
                            <span className="text-[10px] text-slate-500 uppercase block mb-1">Backend</span>
                            <div className="flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${state.backend_status === 'initialized' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 'bg-yellow-500'}`}></span>
                                <span className="text-xs font-mono">{state.backend_status || 'Offline'}</span>
                            </div>
                        </div>
                        <div className="flex-1 bg-slate-800/30 p-3 rounded-2xl border border-slate-700/20">
                            <span className="text-[10px] text-slate-500 uppercase block mb-1">Runtime</span>
                            <div className="flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${state.runtime_status === 'initialized' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 'bg-yellow-500'}`}></span>
                                <span className="text-xs font-mono">{state.runtime_status || 'Offline'}</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex gap-4">
                         <div className="flex-1 bg-slate-800/30 p-3 rounded-2xl border border-slate-700/20">
                            <span className="text-[10px] text-slate-500 uppercase block mb-1">Synthesizable</span>
                            <div className="text-xs font-mono">{state.is_synthesizable ? 'YES' : 'NO'}</div>
                        </div>
                        <div className="flex-1 bg-slate-800/30 p-3 rounded-2xl border border-slate-700/20">
                            <span className="text-[10px] text-slate-500 uppercase block mb-1">Synthesis Completed</span>
                            <div className="text-xs font-mono">{state.is_synthesis_completed ? 'YES' : 'NO'}</div>
                        </div>
                    </div>

                    <CollapsibleSection title="Active Worktrees">
                        <div className="space-y-1">
                            {Object.entries(state.worktrees).map(([name, path]) => (
                                <ScrollablePath key={name} label={name} path={path} />
                            ))}
                            {Object.keys(state.worktrees).length === 0 && (
                                <p className="text-slate-500 italic text-xs bg-slate-800/30 p-3 rounded-lg">No worktrees currently active</p>
                            )}
                        </div>
                    </CollapsibleSection>
                </div>

                <div>
                    <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center justify-between">
                        Recent Activity
                        <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded-full text-slate-500 font-mono">
                            {state.artifacts.length}
                        </span>
                    </h3>
                    <div className="max-h-[320px] overflow-y-auto space-y-3 pr-2 custom-scrollbar">
                        {state.artifacts.map((art, idx) => (
                            <div key={idx} className="bg-slate-800/30 p-3.5 rounded-2xl border border-slate-700/20 hover:border-slate-600/40 transition-all group">
                                <div className="flex justify-between items-start mb-2">
                                    <span className="font-mono text-[10px] text-blue-400 bg-blue-900/20 px-2 py-0.5 rounded-md group-hover:bg-blue-900/40 transition-colors">
                                        {art.git_commit_hash?.substring(0, 7) || 'PENDING'}
                                    </span>
                                    <span className="text-[10px] text-slate-500 font-medium">
                                        {art.snapshot_timestamp ? new Date(art.snapshot_timestamp).toLocaleTimeString() : 'now'}
                                    </span>
                                </div>
                                <div className="text-sm font-semibold text-slate-200 mb-1.5">{art.op_name || 'Manual Adjustment'}</div>
                                <div className="flex items-center gap-2 text-[11px] text-slate-400">
                                    <span className="bg-slate-700/50 px-2 py-0.5 rounded text-[10px] font-medium text-slate-300">{art.module_name}</span>
                                    <span className="text-slate-600">•</span>
                                    <span className="italic">{art.author}</span>
                                </div>
                                {art.status && (
                                    <div className={`mt-3 text-[9px] uppercase font-black tracking-[0.2em] flex items-center gap-1.5 ${art.status === 'SUCCESS' ? 'text-green-400' : 'text-red-400'}`}>
                                        <span className={`w-1.5 h-1.5 rounded-full ${art.status === 'SUCCESS' ? 'bg-green-400 shadow-[0_0_5px_rgba(74,222,128,0.5)]' : 'bg-red-400 shadow-[0_0_5px_rgba(248,113,113,0.5)]'}`}></span>
                                        {art.status}
                                    </div>
                                )}
                            </div>
                        ))}
                        {state.artifacts.length === 0 && (
                            <div className="flex flex-col items-center justify-center py-12 bg-slate-800/10 rounded-2xl border border-dashed border-slate-700/50">
                                <p className="text-slate-500 italic text-sm">No activity recorded</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
