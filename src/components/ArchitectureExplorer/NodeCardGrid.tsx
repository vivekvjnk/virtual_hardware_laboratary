import React from 'react';
import { ChevronRight, FolderGit2, FileText, Layers, Cpu, Terminal, Radio, Activity, Database, GitBranch, ShieldCheck } from 'lucide-react';
import type { ArchitectureGraphData, NodeCategory } from '../../types/architecture';
import { getChildrenNodes, getNode } from '../../data/backendArchitectureData';

interface NodeCardGridProps {
  graph: ArchitectureGraphData;
  selectedId: string;
  onSelectNode: (id: string) => void;
}

const CATEGORY_STYLES: Record<NodeCategory, { label: string; bg: string; text: string; border: string; icon: any }> = {
  root: { label: 'Root', bg: 'bg-violet-500/15', text: 'text-violet-300', border: 'border-violet-500/30', icon: Layers },
  subsystem: { label: 'Subsystem', bg: 'bg-indigo-500/15', text: 'text-indigo-300', border: 'border-indigo-500/30', icon: Cpu },
  infrastructure: { label: 'Infrastructure', bg: 'bg-cyan-500/15', text: 'text-cyan-300', border: 'border-cyan-500/30', icon: Terminal },
  agent: { label: 'Agent', bg: 'bg-emerald-500/15', text: 'text-emerald-300', border: 'border-emerald-500/30', icon: Radio },
  feature: { label: 'Feature', bg: 'bg-amber-500/15', text: 'text-amber-300', border: 'border-amber-500/30', icon: Activity },
  storage: { label: 'Storage', bg: 'bg-rose-500/15', text: 'text-rose-300', border: 'border-rose-500/30', icon: Database },
  protocol: { label: 'Protocol', bg: 'bg-sky-500/15', text: 'text-sky-300', border: 'border-sky-500/30', icon: GitBranch },
  controller: { label: 'Controller', bg: 'bg-purple-500/15', text: 'text-purple-300', border: 'border-purple-500/30', icon: ShieldCheck },
  gate: { label: 'Gate', bg: 'bg-teal-500/15', text: 'text-teal-300', border: 'border-teal-500/30', icon: Radio }
};

export const NodeCardGrid: React.FC<NodeCardGridProps> = ({
  graph,
  selectedId,
  onSelectNode,
}) => {
  const rootNode = getNode(graph, graph.rootId);
  if (!rootNode) return null;

  const subsystems = getChildrenNodes(graph, graph.rootId);

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        {subsystems.map((subsystem) => {
          const categoryInfo = CATEGORY_STYLES[subsystem.category] || CATEGORY_STYLES.subsystem;
          const Icon = categoryInfo.icon;
          const isSelected = selectedId === subsystem.id;
          const children = getChildrenNodes(graph, subsystem.id);

          return (
            <div
              key={subsystem.id}
              onClick={() => onSelectNode(subsystem.id)}
              className={`flex flex-col justify-between p-6 rounded-3xl border transition-all duration-200 cursor-pointer space-y-4 ${
                isSelected
                  ? 'bg-violet-500/15 border-violet-500 shadow-xl shadow-violet-500/10 ring-1 ring-violet-500/30'
                  : 'bg-slate-950/80 border-slate-800 hover:bg-slate-900/90 hover:border-slate-700'
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-mono ${categoryInfo.bg} ${categoryInfo.text} ${categoryInfo.border}`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {categoryInfo.label}
                  </span>
                  <span className="text-xs font-mono text-slate-500">
                    {children.length} Components
                  </span>
                </div>

                <h3 className="text-xl font-bold text-white tracking-tight">{subsystem.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{subsystem.shortDescription}</p>
              </div>

              {/* Children Nodes preview */}
              {children.length > 0 && (
                <div className="pt-3 border-t border-slate-800/80 space-y-2">
                  <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
                    Architectural Ownership:
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {children.map((child) => {
                      const childCategory = CATEGORY_STYLES[child.category] || CATEGORY_STYLES.subsystem;
                      const ChildIcon = childCategory.icon;
                      const isChildSelected = selectedId === child.id;

                      return (
                        <button
                          key={child.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectNode(child.id);
                          }}
                          className={`flex items-center justify-between p-2.5 rounded-xl border text-left text-xs transition-colors ${
                            isChildSelected
                              ? 'bg-violet-500/20 border-violet-400 text-white font-medium'
                              : 'bg-slate-900/70 border-slate-800 hover:bg-slate-900 hover:border-slate-700 text-slate-300'
                          }`}
                        >
                          <span className="flex items-center gap-2 truncate">
                            <ChildIcon className={`w-3.5 h-3.5 shrink-0 ${childCategory.text}`} />
                            <span className="truncate">{child.title}</span>
                          </span>
                          <ChevronRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Card Footer */}
              <div className="pt-2 flex items-center justify-between text-xs text-slate-500 font-mono">
                {subsystem.repositoryPath && (
                  <span className="flex items-center gap-1.5 truncate max-w-[200px]">
                    <FolderGit2 className="w-3.5 h-3.5 text-slate-600" />
                    {subsystem.repositoryPath}
                  </span>
                )}
                {subsystem.documentation && subsystem.documentation.length > 0 && (
                  <span className="flex items-center gap-1 text-violet-400">
                    <FileText className="w-3.5 h-3.5" />
                    {subsystem.documentation.length} Docs
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
