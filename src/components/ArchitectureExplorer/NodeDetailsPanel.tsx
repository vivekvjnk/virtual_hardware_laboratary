import React, { useState } from 'react';
import {
  FolderGit2,
  FileText,
  ArrowUpRight,
  Copy,
  Check,
  ChevronRight,
  Layers,
  Cpu,
  ShieldCheck,
  Radio,
  Database,
  Activity,
  GitBranch,
  Terminal,
  Info
} from 'lucide-react';
import type { ArchitectureGraphData, NodeCategory } from '../../types/architecture';
import { getNode, getChildrenNodes } from '../../data/backendArchitectureData';

interface NodeDetailsPanelProps {
  graph: ArchitectureGraphData;
  selectedId: string;
  onSelectNode: (id: string) => void;
}

const CATEGORY_STYLES: Record<NodeCategory, { label: string; bg: string; text: string; border: string; icon: any }> = {
  root: { label: 'Root Subsystem', bg: 'bg-violet-500/15', text: 'text-violet-300', border: 'border-violet-500/30', icon: Layers },
  subsystem: { label: 'Subsystem', bg: 'bg-indigo-500/15', text: 'text-indigo-300', border: 'border-indigo-500/30', icon: Cpu },
  infrastructure: { label: 'Infrastructure', bg: 'bg-cyan-500/15', text: 'text-cyan-300', border: 'border-cyan-500/30', icon: Terminal },
  agent: { label: 'Specialized Agent', bg: 'bg-emerald-500/15', text: 'text-emerald-300', border: 'border-emerald-500/30', icon: Radio },
  feature: { label: 'Feature / Engine', bg: 'bg-amber-500/15', text: 'text-amber-300', border: 'border-amber-500/30', icon: Activity },
  storage: { label: 'Persistence / Storage', bg: 'bg-rose-500/15', text: 'text-rose-300', border: 'border-rose-500/30', icon: Database },
  protocol: { label: 'Protocol / Transport', bg: 'bg-sky-500/15', text: 'text-sky-300', border: 'border-sky-500/30', icon: GitBranch },
  controller: { label: 'Workflow Controller', bg: 'bg-purple-500/15', text: 'text-purple-300', border: 'border-purple-500/30', icon: ShieldCheck },
  gate: { label: 'Gate / Transport Engine', bg: 'bg-teal-500/15', text: 'text-teal-300', border: 'border-teal-500/30', icon: Radio }
};

export const NodeDetailsPanel: React.FC<NodeDetailsPanelProps> = ({
  graph,
  selectedId,
  onSelectNode,
}) => {
  const [copiedPath, setCopiedPath] = useState(false);
  const node = getNode(graph, selectedId);

  if (!node) {
    return (
      <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6 text-center text-slate-500">
        Select a node to inspect its architectural details.
      </div>
    );
  }

  const categoryInfo = CATEGORY_STYLES[node.category] || CATEGORY_STYLES.subsystem;
  const CategoryIcon = categoryInfo.icon;
  const parentNode = node.parentId ? getNode(graph, node.parentId) : null;
  const childrenNodes = getChildrenNodes(graph, node.id);

  const handleCopyPath = () => {
    if (node.repositoryPath) {
      navigator.clipboard.writeText(node.repositoryPath);
      setCopiedPath(true);
      setTimeout(() => setCopiedPath(false), 2000);
    }
  };

  return (
    <aside className="flex flex-col h-full rounded-3xl border border-slate-800 bg-slate-950/90 p-6 shadow-xl shadow-slate-950/40 overflow-y-auto space-y-6">
      {/* Node Header */}
      <div className="space-y-3 pb-4 border-b border-slate-800/80">
        <div className="flex items-center justify-between gap-2">
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-mono font-medium ${categoryInfo.bg} ${categoryInfo.text} ${categoryInfo.border}`}
          >
            <CategoryIcon className="w-3.5 h-3.5" />
            {categoryInfo.label}
          </span>
          <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
            ID: {node.id}
          </span>
        </div>

        <h2 className="text-2xl font-bold text-white tracking-tight">{node.title}</h2>

        {node.tags && node.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {node.tags.map((tag) => (
              <span
                key={tag}
                className="px-2.5 py-0.5 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-400"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Short Description & Purpose */}
      <div className="space-y-4">
        <div>
          <h3 className="text-xs uppercase tracking-wider font-mono font-bold text-slate-400 mb-1.5 flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-violet-400" />
            Summary
          </h3>
          <p className="text-sm text-slate-300 leading-relaxed bg-slate-900/50 p-3.5 rounded-2xl border border-slate-800/60">
            {node.shortDescription}
          </p>
        </div>

        <div>
          <h3 className="text-xs uppercase tracking-wider font-mono font-bold text-slate-400 mb-1.5">
            Architectural Purpose
          </h3>
          <p className="text-sm text-slate-400 leading-relaxed bg-slate-900/30 p-3.5 rounded-2xl border border-slate-800/40">
            {node.purpose}
          </p>
        </div>
      </div>

      {/* Repository Location */}
      {node.repositoryPath && (
        <div className="space-y-1.5">
          <h3 className="text-xs uppercase tracking-wider font-mono font-bold text-slate-400 flex items-center gap-1.5">
            <FolderGit2 className="w-3.5 h-3.5 text-violet-400" />
            Repository Location
          </h3>
          <div className="flex items-center justify-between gap-2 p-3 rounded-2xl bg-slate-900 border border-slate-800 font-mono text-xs text-slate-300">
            <span className="truncate">{node.repositoryPath}</span>
            <button
              onClick={handleCopyPath}
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              title="Copy repository path"
            >
              {copiedPath ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      )}

      {/* Documentation References */}
      {node.documentation && node.documentation.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs uppercase tracking-wider font-mono font-bold text-slate-400 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-violet-400" />
            Related Documentation ({node.documentation.length})
          </h3>
          <div className="space-y-2">
            {node.documentation.map((doc, idx) => (
              <div
                key={idx}
                className="group p-3 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-violet-500/40 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-xs text-white group-hover:text-violet-300 transition-colors">
                    {doc.title}
                  </span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-violet-400" />
                </div>
                <div className="text-[11px] font-mono text-slate-500 truncate mt-1">
                  {doc.path}
                </div>
                {doc.description && (
                  <p className="text-xs text-slate-400 mt-1.5 leading-snug">{doc.description}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Parent & Children Hierarchy Connections */}
      <div className="space-y-3 pt-2 border-t border-slate-800/80">
        {parentNode && (
          <div>
            <h3 className="text-xs uppercase tracking-wider font-mono font-bold text-slate-400 mb-1.5">
              Parent Component
            </h3>
            <button
              onClick={() => onSelectNode(parentNode.id)}
              className="flex items-center justify-between w-full p-3 rounded-2xl bg-slate-900 border border-slate-800 hover:border-violet-500/50 text-left transition-colors group"
            >
              <div>
                <div className="text-xs font-semibold text-white group-hover:text-violet-300">
                  {parentNode.title}
                </div>
                <div className="text-[11px] font-mono text-slate-500">{parentNode.id}</div>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-violet-400 group-hover:translate-x-0.5 transition-transform" />
            </button>
          </div>
        )}

        {childrenNodes.length > 0 && (
          <div>
            <h3 className="text-xs uppercase tracking-wider font-mono font-bold text-slate-400 mb-1.5 flex items-center justify-between">
              <span>Direct Children</span>
              <span className="px-2 py-0.5 rounded-full bg-slate-800 text-[10px] text-slate-400">
                {childrenNodes.length}
              </span>
            </h3>
            <div className="space-y-1.5">
              {childrenNodes.map((child) => (
                <button
                  key={child.id}
                  onClick={() => onSelectNode(child.id)}
                  className="flex items-center justify-between w-full px-3 py-2 rounded-xl bg-slate-900/60 border border-slate-800/70 hover:bg-slate-900 hover:border-violet-500/40 text-left transition-colors group"
                >
                  <span className="text-xs font-mono text-slate-300 group-hover:text-white truncate">
                    {child.title}
                  </span>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-violet-400 shrink-0" />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Metadata & Extension Slots */}
      {node.metadata && (
        <div className="space-y-2 pt-2 border-t border-slate-800/80">
          <h3 className="text-xs uppercase tracking-wider font-mono font-bold text-slate-400">
            System Metadata
          </h3>
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            {node.metadata.status && (
              <div className="bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                <span className="text-slate-500 block text-[10px] uppercase">Status</span>
                <span className="text-emerald-400 capitalize">{node.metadata.status}</span>
              </div>
            )}
            {node.metadata.authoritativeHost && (
              <div className="bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                <span className="text-slate-500 block text-[10px] uppercase">Authority Host</span>
                <span className="text-slate-300 truncate block">{node.metadata.authoritativeHost}</span>
              </div>
            )}
          </div>

          {node.metadata.techStack && (
            <div className="bg-slate-900 p-2.5 rounded-xl border border-slate-800 text-xs">
              <span className="text-slate-500 block text-[10px] font-mono uppercase mb-1">Tech Stack</span>
              <div className="flex flex-wrap gap-1">
                {node.metadata.techStack.map((tech) => (
                  <span key={tech} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px]">
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          )}

          {node.metadata.runtimeEvents && node.metadata.runtimeEvents.length > 0 && (
            <div className="bg-slate-900 p-2.5 rounded-xl border border-slate-800 text-xs">
              <span className="text-slate-500 block text-[10px] font-mono uppercase mb-1">Handled Events</span>
              <div className="flex flex-wrap gap-1">
                {node.metadata.runtimeEvents.map((evt) => (
                  <span key={evt} className="px-2 py-0.5 rounded bg-violet-500/10 text-violet-300 font-mono text-[10px] border border-violet-500/20">
                    {evt}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Future Capabilities Extension Placeholder */}
      <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/60 text-xs space-y-2">
        <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
          <span className="uppercase tracking-wider">Future Graph Layer</span>
          <span className="px-2 py-0.5 rounded bg-violet-500/10 text-violet-400 text-[10px]">Planned</span>
        </div>
        <p className="text-slate-500 text-[11px] leading-relaxed">
          Runtime health telemetry, Git history overlays, dependency graphs, and event diffs can be dynamically integrated directly into this node model.
        </p>
      </div>
    </aside>
  );
};
