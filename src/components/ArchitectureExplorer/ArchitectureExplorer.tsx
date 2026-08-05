import React, { useState, useMemo, useEffect } from 'react';
import {
  Layers,
  Search,
  X,
  Maximize2,
  Minimize2,
  RotateCcw,
  Grid,
  List,
  GitFork,
  Share2,
  PanelRightClose,
  PanelRightOpen,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import { backendArchitectureData, getAncestors, searchNodes } from '../../data/backendArchitectureData';
import { ArchitectureBreadcrumbs } from './ArchitectureBreadcrumbs';
import { NodeTreeRenderer } from './NodeTreeRenderer';
import { NodeCardGrid } from './NodeCardGrid';
import { NodeDetailsPanel } from './NodeDetailsPanel';
import { GraphView } from './GraphView';
import type { ArchitectureNode } from '../../types/architecture';

interface ArchitectureExplorerProps {
  onClose?: () => void;
}

export const ArchitectureExplorer: React.FC<ArchitectureExplorerProps> = ({ onClose }) => {
  const graph = backendArchitectureData;

  // Selected node state
  const [selectedId, setSelectedId] = useState<string>(graph.rootId);

  // View Projection mode: 'tree' | 'grid' | 'flat' | 'graph'
  const [viewMode, setViewMode] = useState<'tree' | 'grid' | 'flat' | 'graph'>('tree');

  // Search query state
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Right details panel toggle state (default open)
  const [showDetailsPanel, setShowDetailsPanel] = useState<boolean>(true);

  // Top toolbar visibility toggle state (default open)
  const [showTopBar, setShowTopBar] = useState<boolean>(true);

  // Expanded nodes state (Root + level 1 initially expanded for clean progressive disclosure)
  const initialExpanded = useMemo(() => {
    const set = new Set<string>([graph.rootId]);
    if (graph.nodes[graph.rootId]) {
      graph.nodes[graph.rootId].children.forEach((id) => set.add(id));
    }
    return set;
  }, [graph]);

  const [expandedIds, setExpandedIds] = useState<Set<string>>(initialExpanded);

  // Toggle node expand/collapse
  const handleToggleExpand = (id: string) => {
    setExpandedIds((prev: Set<string>) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Expand all nodes
  const handleExpandAll = () => {
    const allIds = new Set(Object.keys(graph.nodes));
    setExpandedIds(allIds);
  };

  // Collapse all nodes except root
  const handleCollapseAll = () => {
    setExpandedIds(new Set([graph.rootId]));
  };

  // Select node & auto-expand its ancestors so it is visible in the tree
  const handleSelectNode = (id: string) => {
    setSelectedId(id);
    const ancestors = getAncestors(graph, id);
    setExpandedIds((prev: Set<string>) => {
      const next = new Set(prev);
      ancestors.forEach((aId) => next.add(aId));
      next.add(id);
      return next;
    });
  };

  // Search filter matches
  const searchResults = useMemo(() => {
    return searchNodes(graph, searchQuery);
  }, [graph, searchQuery]);

  // When search query changes, expand ancestor nodes of search results automatically
  useEffect(() => {
    if (searchQuery.trim().length > 0 && searchResults.length > 0) {
      setExpandedIds((prev: Set<string>) => {
        const next = new Set(prev);
        searchResults.forEach((node: ArchitectureNode) => {
          const ancestors = getAncestors(graph, node.id);
          ancestors.forEach((aId) => next.add(aId));
          next.add(node.id);
        });
        return next;
      });
    }
  }, [searchQuery, searchResults, graph]);

  // Calculate dynamic canvas height
  const canvasHeight = showTopBar ? 'calc(100vh - 120px)' : 'calc(100vh - 25px)';

  return (
    <div className="flex flex-col w-full bg-slate-950 text-white space-y-2 relative" style={{ minHeight: 'calc(100vh - 1rem)' }}>
      {/* Floating Unhide Toolbar Button when Top Bar is hidden */}
      {!showTopBar && (
        <button
          onClick={() => setShowTopBar(true)}
          className="absolute top-3 left-3 z-30 flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-800 hover:bg-slate-800 text-xs text-violet-400 hover:text-white shadow-xl backdrop-blur-md transition-all font-medium"
          title="Show Top Bar"
        >
          <ChevronDown className="w-3.5 h-3.5" />
          <span>Show Toolbar</span>
        </button>
      )}

      {/* Collapsible Single Unified Header & Toolbar Panel */}
      {showTopBar && (
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 bg-slate-950/90 p-2.5 rounded-2xl border border-slate-800 shadow-md backdrop-blur-md">
          {/* Left Section: Back button, Title, View Mode Selectors, Breadcrumbs */}
          <div className="flex flex-wrap items-center gap-2.5 min-w-0">
            {onClose && (
              <button
                onClick={onClose}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-xs text-slate-300 hover:text-white transition-all font-medium shrink-0"
                title="Back to Dashboard"
              >
                <X className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Back</span>
              </button>
            )}

            {/* Title */}
            <div className="flex items-center gap-2 pr-2.5 border-r border-slate-800/80 shrink-0">
              <Layers className="w-4.5 h-4.5 text-violet-400" />
              <span className="font-bold text-sm text-white tracking-tight">Architecture Explorer</span>
            </div>

            {/* View Mode Buttons */}
            <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-xl border border-slate-800 shrink-0">
              <button
                onClick={() => setViewMode('tree')}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  viewMode === 'tree'
                    ? 'bg-violet-600 text-white shadow-sm shadow-violet-600/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <GitFork className="w-3.5 h-3.5" />
                Tree
              </button>

              <button
                onClick={() => setViewMode('graph')}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  viewMode === 'graph'
                    ? 'bg-violet-600 text-white shadow-sm shadow-violet-600/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <Share2 className="w-3.5 h-3.5" />
                Graph
              </button>

              <button
                onClick={() => setViewMode('grid')}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  viewMode === 'grid'
                    ? 'bg-violet-600 text-white shadow-sm shadow-violet-600/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <Grid className="w-3.5 h-3.5" />
                Grid
              </button>

              <button
                onClick={() => setViewMode('flat')}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  viewMode === 'flat'
                    ? 'bg-violet-600 text-white shadow-sm shadow-violet-600/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <List className="w-3.5 h-3.5" />
                Flat
              </button>
            </div>

            {/* Integrated Breadcrumbs Path */}
            <div className="min-w-0">
              <ArchitectureBreadcrumbs graph={graph} selectedId={selectedId} onSelectNode={handleSelectNode} />
            </div>
          </div>

          {/* Right Section: Search Input, Action Buttons, Details Panel Toggle & Hide Top Bar Button */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Search Bar */}
            <div className="relative w-40 sm:w-52">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search..."
                className="w-full pl-9 pr-8 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-500 transition-colors font-mono"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            <button
              onClick={handleExpandAll}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-xs text-slate-300 hover:text-white transition-colors"
              title="Expand all tree nodes"
            >
              <Maximize2 className="w-3 h-3 text-violet-400" />
              <span className="hidden sm:inline">Expand</span>
            </button>

            <button
              onClick={handleCollapseAll}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-xs text-slate-300 hover:text-white transition-colors"
              title="Collapse all child nodes"
            >
              <Minimize2 className="w-3 h-3 text-slate-400" />
              <span className="hidden sm:inline">Collapse</span>
            </button>

            <button
              onClick={() => handleSelectNode(graph.rootId)}
              className="p-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              title="Reset selection to root"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>

            {/* Toggle Details Panel Button */}
            <button
              onClick={() => setShowDetailsPanel(!showDetailsPanel)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all ${
                showDetailsPanel
                  ? 'bg-violet-600/20 border-violet-500/40 text-violet-300'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
              }`}
              title={showDetailsPanel ? 'Hide Node Details Panel' : 'Expand Details Panel'}
            >
              {showDetailsPanel ? <PanelRightClose className="w-3.5 h-3.5" /> : <PanelRightOpen className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">{showDetailsPanel ? 'Hide Panel' : 'Show Panel'}</span>
            </button>

            {/* Hide Top Bar Button */}
            <button
              onClick={() => setShowTopBar(false)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-xs text-slate-400 hover:text-white transition-colors"
              title="Hide Top Toolbar (Maximize Canvas Real Estate)"
            >
              <ChevronUp className="w-3.5 h-3.5" />
              <span className="hidden md:inline text-[11px]">Hide Bar</span>
            </button>
          </div>
        </div>
      )}

      {/* Search results banner if active */}
      {searchQuery.trim().length > 0 && (
        <div className="flex items-center justify-between px-3.5 py-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300">
          <span>
            Found <strong className="font-mono">{searchResults.length}</strong> architecture node match(es) for "{searchQuery}"
          </span>
          <button onClick={() => setSearchQuery('')} className="underline hover:text-white">
            Clear filter
          </button>
        </div>
      )}

      {/* Main Content Area: Responsive Grid (Full width when details panel is hidden) */}
      <div className={`grid gap-4 ${showDetailsPanel ? 'lg:grid-cols-[1fr_400px] xl:grid-cols-[1fr_440px]' : 'grid-cols-1'} items-start`}>
        {/* Visualization Canvas Column */}
        <main className={viewMode === 'graph' ? 'w-full relative' : 'rounded-2xl border border-slate-800 bg-slate-950/80 p-5 shadow-lg shadow-slate-950/30 min-h-[500px] relative'}>
          {viewMode === 'graph' ? (
            <GraphView graph={graph} selectedId={selectedId} onSelectNode={handleSelectNode} height={canvasHeight} />
          ) : viewMode === 'tree' ? (
            <div className="space-y-4" style={{ minHeight: canvasHeight }}>
              <NodeTreeRenderer
                graph={graph}
                nodeId={graph.rootId}
                selectedId={selectedId}
                expandedIds={expandedIds}
                onSelectNode={handleSelectNode}
                onToggleExpand={handleToggleExpand}
                searchQuery={searchQuery}
              />
            </div>
          ) : viewMode === 'grid' ? (
            <div style={{ minHeight: canvasHeight }}>
              <NodeCardGrid graph={graph} selectedId={selectedId} onSelectNode={handleSelectNode} />
            </div>
          ) : (
            /* Flat Directory List projection */
            <div className="space-y-2" style={{ minHeight: canvasHeight }}>
              {(searchQuery.trim().length > 0 ? searchResults : Object.values(graph.nodes)).map((node: ArchitectureNode) => {
                const isSelected = node.id === selectedId;
                return (
                  <button
                    key={node.id}
                    onClick={() => handleSelectNode(node.id)}
                    className={`flex items-center justify-between w-full p-3.5 rounded-xl border text-left transition-colors ${
                      isSelected
                        ? 'bg-violet-500/15 border-violet-500 text-white'
                        : 'bg-slate-950/80 border-slate-800 hover:bg-slate-900/90 text-slate-300'
                    }`}
                  >
                    <div className="min-w-0 pr-4">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-white">{node.title}</span>
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                          {node.category}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 truncate mt-1">{node.shortDescription}</p>
                    </div>
                    {node.repositoryPath && (
                      <span className="text-[11px] font-mono text-slate-500 truncate max-w-[160px] hidden sm:block">
                        {node.repositoryPath}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </main>

        {/* Right Details Panel Column (Collapsible) */}
        {showDetailsPanel && (
          <div className="h-full sticky top-4">
            <NodeDetailsPanel graph={graph} selectedId={selectedId} onSelectNode={handleSelectNode} />
          </div>
        )}
      </div>
    </div>
  );
};
