import React from 'react';
import {
  ChevronRight,
  ChevronDown,
  Layers,
  Cpu,
  Terminal,
  Radio,
  Activity,
  Database,
  GitBranch,
  ShieldCheck,
  FolderGit2
} from 'lucide-react';
import type { ArchitectureGraphData, NodeCategory } from '../../types/architecture';
import { getNode, getChildrenNodes } from '../../data/backendArchitectureData';

interface NodeTreeRendererProps {
  graph: ArchitectureGraphData;
  nodeId: string;
  selectedId: string;
  expandedIds: Set<string>;
  onSelectNode: (id: string) => void;
  onToggleExpand: (id: string) => void;
  searchQuery?: string;
  level?: number;
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

export const NodeTreeRenderer: React.FC<NodeTreeRendererProps> = ({
  graph,
  nodeId,
  selectedId,
  expandedIds,
  onSelectNode,
  onToggleExpand,
  searchQuery = '',
  level = 0,
}) => {
  const node = getNode(graph, nodeId);
  if (!node) return null;

  const children = getChildrenNodes(graph, nodeId);
  const hasChildren = children.length > 0;
  const isExpanded = expandedIds.has(nodeId);
  const isSelected = selectedId === nodeId;

  const categoryInfo = CATEGORY_STYLES[node.category] || CATEGORY_STYLES.subsystem;
  const Icon = categoryInfo.icon;

  const isSearchMatch =
    searchQuery.trim().length > 0 &&
    (node.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      node.shortDescription.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (node.repositoryPath && node.repositoryPath.toLowerCase().includes(searchQuery.toLowerCase())));

  return (
    <div className="space-y-2">
      {/* Node Row / Card */}
      <div
        className={`group relative flex items-center justify-between p-3.5 rounded-2xl border transition-all duration-200 cursor-pointer ${
          isSelected
            ? 'bg-violet-500/15 border-violet-500 shadow-lg shadow-violet-500/10 ring-1 ring-violet-500/30'
            : isSearchMatch
            ? 'bg-amber-500/10 border-amber-500/50'
            : 'bg-slate-950/80 border-slate-800/80 hover:bg-slate-900/90 hover:border-slate-700'
        }`}
        onClick={() => onSelectNode(node.id)}
      >
        <div className="flex items-center gap-3 min-w-0 pr-2">
          {/* Expand / Collapse Button */}
          {hasChildren ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleExpand(node.id);
              }}
              className="p-1 rounded-lg bg-slate-900/80 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors shrink-0"
              title={isExpanded ? 'Collapse' : 'Expand'}
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-violet-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-slate-400" />
              )}
            </button>
          ) : (
            <div className="w-6 shrink-0" />
          )}

          {/* Node Icon */}
          <div
            className={`p-2 rounded-xl border ${categoryInfo.bg} ${categoryInfo.border} ${categoryInfo.text} shrink-0`}
          >
            <Icon className="w-4 h-4" />
          </div>

          {/* Node Details */}
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-sm text-white truncate">{node.title}</h3>
              <span
                className={`px-2 py-0.5 rounded-full border text-[10px] font-mono ${categoryInfo.bg} ${categoryInfo.text} ${categoryInfo.border}`}
              >
                {categoryInfo.label}
              </span>
              {isSearchMatch && (
                <span className="px-2 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-[10px] font-mono text-amber-300">
                  Match
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 truncate mt-0.5">{node.shortDescription}</p>
          </div>
        </div>

        {/* Right Info Badges */}
        <div className="flex items-center gap-2 shrink-0">
          {node.repositoryPath && (
            <span className="hidden md:flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-900/80 border border-slate-800 text-[11px] font-mono text-slate-400">
              <FolderGit2 className="w-3 h-3 text-slate-500" />
              <span className="truncate max-w-[140px]">{node.repositoryPath.split('/').pop()}</span>
            </span>
          )}

          {hasChildren && (
            <span className="px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-400">
              {children.length} {children.length === 1 ? 'child' : 'children'}
            </span>
          )}
        </div>
      </div>

      {/* Children Tree Indentation */}
      {hasChildren && isExpanded && (
        <div className="ml-6 pl-4 border-l border-slate-800/80 space-y-2 pt-1">
          {children.map((child) => (
            <NodeTreeRenderer
              key={child.id}
              graph={graph}
              nodeId={child.id}
              selectedId={selectedId}
              expandedIds={expandedIds}
              onSelectNode={onSelectNode}
              onToggleExpand={onToggleExpand}
              searchQuery={searchQuery}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};
