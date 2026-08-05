import React from 'react';
import { ChevronRight, Home } from 'lucide-react';
import type { ArchitectureGraphData } from '../../types/architecture';
import { getAncestors, getNode } from '../../data/backendArchitectureData';

interface ArchitectureBreadcrumbsProps {
  graph: ArchitectureGraphData;
  selectedId: string;
  onSelectNode: (id: string) => void;
}

export const ArchitectureBreadcrumbs: React.FC<ArchitectureBreadcrumbsProps> = ({
  graph,
  selectedId,
  onSelectNode,
}) => {
  const isRoot = selectedId === graph.rootId;
  const ancestorIds = isRoot ? [] : getAncestors(graph, selectedId);
  // For root selection: path = [rootId]. For others: ancestors + selected (root already in ancestors)
  const pathIds = isRoot ? [graph.rootId] : [...ancestorIds, selectedId];

  return (
    <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-400 bg-slate-900/60 border border-slate-800/80 px-4 py-2.5 rounded-2xl backdrop-blur-sm">
      <button
        onClick={() => onSelectNode(graph.rootId)}
        className="flex items-center gap-1.5 hover:text-white transition-colors"
        title="Go to root"
      >
        <Home className="w-3.5 h-3.5 text-violet-400" />
        <span className="text-slate-500 font-mono">vhl-agent-backend</span>
      </button>

      {!isRoot && pathIds.map((id, index) => {
        const node = getNode(graph, id);
        if (!node) return null;
        const isLast = index === pathIds.length - 1;
        // Skip root node if it's already shown via the Home button
        if (id === graph.rootId) return null;

        return (
          <React.Fragment key={id}>
            <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />
            <button
              onClick={() => onSelectNode(id)}
              className={`font-mono truncate max-w-[200px] transition-colors rounded px-1.5 py-0.5 ${
                isLast
                  ? 'bg-violet-500/20 text-violet-300 font-medium border border-violet-500/30'
                  : 'hover:text-white hover:bg-slate-800/60 text-slate-300'
              }`}
            >
              {node.title}
            </button>
          </React.Fragment>
        );
      })}

      {isRoot && (
        <>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />
          <span className="font-mono px-1.5 py-0.5 bg-violet-500/20 text-violet-300 font-medium border border-violet-500/30 rounded">
            {getNode(graph, graph.rootId)?.title ?? 'Root'}
          </span>
        </>
      )}
    </nav>
  );
};
