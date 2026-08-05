import React, { useMemo, useState, useRef, useEffect, useCallback } from 'react';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import type { ArchitectureGraphData, NodeCategory } from '../../types/architecture';

const NW = 152, NH = 50, HG = 24, VG = 72, PAD = 60;

const CAT: Record<NodeCategory, { bg: string; border: string; text: string; dot: string }> = {
  root:           { bg: '#1e1b4b', border: '#7c3aed', text: '#c4b5fd', dot: '#7c3aed' },
  subsystem:      { bg: '#1a1e4a', border: '#4338ca', text: '#a5b4fc', dot: '#4f46e5' },
  infrastructure: { bg: '#0c2340', border: '#0369a1', text: '#7dd3fc', dot: '#0284c7' },
  agent:          { bg: '#0d2d1a', border: '#15803d', text: '#86efac', dot: '#16a34a' },
  feature:        { bg: '#2d1f0a', border: '#b45309', text: '#fcd34d', dot: '#d97706' },
  storage:        { bg: '#2d0d0d', border: '#b91c1c', text: '#fca5a5', dot: '#dc2626' },
  protocol:       { bg: '#0c2240', border: '#0891b2', text: '#67e8f9', dot: '#06b6d4' },
  controller:     { bg: '#1f1040', border: '#7e22ce', text: '#d8b4fe', dot: '#9333ea' },
  gate:           { bg: '#0d2828', border: '#0d9488', text: '#5eead4', dot: '#14b8a6' },
};

function initialExpanded(graph: ArchitectureGraphData): Set<string> {
  const s = new Set([graph.rootId]);
  (graph.nodes[graph.rootId]?.children ?? []).forEach(c => { if (graph.nodes[c]) s.add(c); });
  return s;
}

function visibleSet(graph: ArchitectureGraphData, expanded: Set<string>): Set<string> {
  const vis = new Set<string>();
  const q = [graph.rootId];
  while (q.length) {
    const id = q.shift()!;
    vis.add(id);
    if (expanded.has(id)) (graph.nodes[id]?.children ?? []).forEach(c => { if (graph.nodes[c]) q.push(c); });
  }
  return vis;
}

interface Pos { id: string; x: number; y: number }

function layout(graph: ArchitectureGraphData, vis: Set<string>): { positions: Pos[]; cw: number; ch: number } {
  const lvl: Record<string, number> = { [graph.rootId]: 0 };
  const ordered: string[] = [];
  const q = [graph.rootId];
  while (q.length) {
    const id = q.shift()!;
    if (!vis.has(id)) continue;
    ordered.push(id);
    (graph.nodes[id]?.children ?? []).forEach(c => {
      if (vis.has(c) && !(c in lvl)) { lvl[c] = lvl[id] + 1; q.push(c); }
    });
  }
  const lc: Record<string, number> = {};
  for (const id of [...ordered].reverse()) {
    const kids = (graph.nodes[id]?.children ?? []).filter(c => c in lvl);
    lc[id] = kids.length ? kids.reduce((s, c) => s + (lc[c] || 1), 0) : 1;
  }
  let leaf = 0;
  const px: Record<string, number> = {};
  function ax(id: string) {
    const kids = (graph.nodes[id]?.children ?? []).filter(c => c in lvl);
    if (!kids.length) { px[id] = leaf++ * (NW + HG); return; }
    kids.forEach(ax);
    px[id] = (px[kids[0]] + px[kids[kids.length - 1]]) / 2;
  }
  ax(graph.rootId);

  // Center layout around the root node at a fixed CENTER_X coordinate so root node never shifts position
  const CENTER_X = 3000;
  const rootX = px[graph.rootId] ?? 0;
  ordered.forEach(id => {
    px[id] = (px[id] ?? 0) - rootX + CENTER_X;
  });

  const maxLvl = Math.max(0, ...Object.values(lvl));

  return {
    positions: ordered.map(id => ({ id, x: px[id] + PAD, y: lvl[id] * (NH + VG) })),
    cw: CENTER_X * 2 + NW + PAD * 2,
    ch: (maxLvl + 1) * (NH + VG) + PAD * 2,
  };
}

const trunc = (s: string, n = 19) => s.length > n ? s.slice(0, n - 1) + '…' : s;

interface Props { graph: ArchitectureGraphData; selectedId: string; onSelectNode: (id: string) => void; height?: string }

export const GraphView: React.FC<Props> = ({ graph, selectedId, onSelectNode, height = 'calc(100vh - 125px)' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(0.7);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [expanded, setExpanded] = useState<Set<string>>(() => initialExpanded(graph));

  // refs to avoid stale closures in native event handlers
  const zoomRef = useRef(zoom);
  const panRef = useRef(pan);
  useEffect(() => { zoomRef.current = zoom; }, [zoom]);
  useEffect(() => { panRef.current = pan; }, [pan]);

  const drag = useRef({ on: false, sx: 0, sy: 0, spx: 0, spy: 0 });

  const vis = useMemo(() => visibleSet(graph, expanded), [graph, expanded]);
  const { positions, cw, ch } = useMemo(() => layout(graph, vis), [graph, vis]);
  const posMap = useMemo(() => { const m: Record<string, Pos> = {}; positions.forEach(p => { m[p.id] = p; }); return m; }, [positions]);
  const edges = useMemo(() => {
    const out: Array<{ fp: Pos; tp: Pos; fid: string; tid: string }> = [];
    Object.values(graph.nodes).forEach(n => {
      if (!vis.has(n.id)) return;
      n.children?.forEach(cid => {
        const fp = posMap[n.id], tp = posMap[cid];
        if (fp && tp && vis.has(cid)) out.push({ fp, tp, fid: n.id, tid: cid });
      });
    });
    return out;
  }, [graph, posMap, vis]);

  // Centre / fit on mount (once)
  const centre = useCallback(() => {
    const el = containerRef.current; if (!el) return;
    const { width } = el.getBoundingClientRect();
    const rootCenterX = 3000 + PAD + NW / 2;
    const z = 0.7;
    setZoom(z);
    setPan({ x: width / 2 - rootCenterX * z, y: 24 });
  }, []);

  useEffect(() => { const t = setTimeout(centre, 60); return () => clearTimeout(t); }, [centre]);

  // Non-passive wheel → prevents page scroll while inside canvas
  useEffect(() => {
    const el = containerRef.current; if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault(); e.stopPropagation();
      const rect = el.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      const factor = e.deltaY < 0 ? 1.12 : 0.88;
      const pz = zoomRef.current, pp = panRef.current;
      const nz = Math.min(Math.max(pz * factor, 0.12), 3);
      setZoom(nz);
      setPan({ x: mx - (mx - pp.x) * (nz / pz), y: my - (my - pp.y) * (nz / pz) });
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  const onMD = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    drag.current = { on: true, sx: e.clientX, sy: e.clientY, spx: panRef.current.x, spy: panRef.current.y };
  };
  const onMM = (e: React.MouseEvent) => {
    if (!drag.current.on) return;
    setPan({ x: drag.current.spx + (e.clientX - drag.current.sx), y: drag.current.spy + (e.clientY - drag.current.sy) });
  };
  const onMU = () => { drag.current.on = false; };

  const handleClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    onSelectNode(id);
    const node = graph.nodes[id];
    if (!node || !node.children.length) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-950 overflow-hidden" style={{ position: 'relative' }}>
      {/* Controls overlay */}
      <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
        <button onClick={() => { const z = Math.min(zoomRef.current * 1.2, 3); setZoom(z); }} title="Zoom in"
          className="flex items-center justify-center w-8 h-8 rounded-xl bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors">
          <ZoomIn className="w-4 h-4" />
        </button>
        <button onClick={() => { const z = Math.max(zoomRef.current * 0.8, 0.12); setZoom(z); }} title="Zoom out"
          className="flex items-center justify-center w-8 h-8 rounded-xl bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors">
          <ZoomOut className="w-4 h-4" />
        </button>
        <button onClick={centre} title="Reset view"
          className="flex items-center justify-center w-8 h-8 rounded-xl bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors">
          <Maximize2 className="w-4 h-4 text-violet-400" />
        </button>
        <div className="px-1.5 py-1 rounded-xl bg-slate-900/90 border border-slate-800 text-[10px] font-mono text-slate-400 text-center">
          {Math.round(zoom * 100)}%
        </div>
      </div>

      {/* Legend */}
      <div style={{ position: 'absolute', bottom: 10, left: 14, zIndex: 10 }}
        className="flex items-center gap-3 text-[10px] font-mono text-slate-600">
        <span>⟳ Scroll = zoom</span>
        <span>✥ Drag = pan</span>
        <span className="text-violet-500/60">+ / − = expand / collapse</span>
      </div>

      {/* Canvas */}
      <div
        ref={containerRef}
        style={{ width: '100%', height, overflow: 'hidden', cursor: 'grab', userSelect: 'none', position: 'relative' }}
        onMouseDown={onMD}
        onMouseMove={onMM}
        onMouseUp={onMU}
        onMouseLeave={onMU}
      >
        {/* Dot grid (static) */}
        <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
          <defs>
            <pattern id="gdots" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r="0.9" fill="#1e293b" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#gdots)" />
        </svg>

        {/* Zoomable graph SVG */}
        <svg
          width={cw} height={ch}
          style={{ position: 'absolute', transformOrigin: '0 0', transform: `translate(${pan.x}px,${pan.y}px) scale(${zoom})`, transition: 'none', pointerEvents: 'all' }}
        >
          {edges.map(({ fp, tp, fid, tid }) => {
            const key = `${fid}->${tid}`;
            const active = selectedId === fid || selectedId === tid;
            const x1 = fp.x + NW / 2 + PAD, y1 = fp.y + NH + PAD;
            const x2 = tp.x + NW / 2 + PAD, y2 = tp.y + PAD, my = (y1 + y2) / 2;
            const dStr = `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`;
            return (
              <path
                key={key}
                d={dStr}
                fill="none"
                stroke={active ? '#8b5cf6' : '#1e293b'}
                strokeWidth={active ? 2 : 1.5}
                opacity={active ? 1 : 0.8}
                style={{ transition: 'd 300ms cubic-bezier(0.4, 0, 0.2, 1), stroke 300ms ease, opacity 300ms ease' }}
              />
            );
          })}

          {positions.map(pos => {
            const node = graph.nodes[pos.id]; if (!node) return null;
            const sel = pos.id === selectedId;
            const isExp = expanded.has(pos.id);
            const hasKids = node.children.length > 0;
            const c = CAT[node.category] || CAT.subsystem;
            const x = pos.x + PAD, y = pos.y + PAD;
            return (
              <g
                key={pos.id}
                onClick={e => handleClick(e, pos.id)}
                style={{
                  transform: `translate(${x}px, ${y}px)`,
                  cursor: hasKids ? 'pointer' : 'default',
                  transition: 'transform 300ms cubic-bezier(0.4, 0, 0.2, 1), opacity 300ms ease-in-out',
                }}
              >
                {sel && <rect width={NW} height={NH} rx={10} fill="#7c3aed" opacity={0.22} className="transition-opacity duration-300" />}
                <rect width={NW} height={NH} rx={10} fill={sel ? '#2d1264' : c.bg} stroke={sel ? '#a855f7' : c.border} strokeWidth={sel ? 2 : 1} className="transition-colors duration-300" />
                <circle cx={14} cy={NH / 2} r={4} fill={c.dot} />
                <text x={27} y={NH / 2 - 4} fill={sel ? '#ede9fe' : c.text} fontSize={10} fontWeight={sel ? '700' : '600'} fontFamily="ui-monospace,monospace" className="transition-colors duration-300">
                  {trunc(node.title)}
                </text>
                <text x={27} y={NH / 2 + 10} fill="#475569" fontSize={8} fontFamily="ui-monospace,monospace">
                  {node.category.toUpperCase()}{hasKids ? (isExp ? ' · −' : ` · +${node.children.length}`) : ''}
                </text>
                {hasKids && (
                  <>
                    <rect x={NW - 22} y={NH / 2 - 8} width={16} height={16} rx={4}
                      fill={isExp ? '#1e293b' : '#1e1b4b'} stroke={isExp ? '#334155' : '#4c1d95'} strokeWidth={1} className="transition-colors duration-300" />
                    <text x={NW - 14} y={NH / 2 + 4} fill={isExp ? '#64748b' : '#a78bfa'}
                      fontSize={12} fontWeight="700" fontFamily="ui-monospace,monospace" textAnchor="middle" className="transition-colors duration-300">
                      {isExp ? '−' : '+'}
                    </text>
                  </>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};
