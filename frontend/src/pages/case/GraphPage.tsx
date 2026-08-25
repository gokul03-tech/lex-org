import { useMemo, useState } from 'react';
import ReactFlow, { Background, Controls, MarkerType } from 'react-flow-renderer';
import { Network, Search, X } from 'lucide-react';
import { useWorkspace } from './CaseWorkspaceLayout';
import { EmptyState, SectionCard } from '@/components/case/primitives';
import type { KgNode } from '@/types/case-workspace';
import 'react-flow-renderer/dist/style.css';

/* Legend colors per node kind */
const KIND_STYLE: Record<KgNode['kind'], { color: string; bg: string; label: string }> = {
  case: { color: '#0284C7', bg: '#E0F2FE', label: 'Case' },
  judge: { color: '#7C3AED', bg: '#EDE9FE', label: 'Judge' },
  court: { color: '#4F46E5', bg: '#E0E7FF', label: 'Court' },
  act: { color: '#059669', bg: '#D1FAE5', label: 'Act' },
  section: { color: '#D97706', bg: '#FEF3C7', label: 'Sec / Art' },
  evidence: { color: '#E11D48', bg: '#FFE4E6', label: 'Evidence' },
  citation: { color: '#9333EA', bg: '#F3E8FF', label: 'Citation' },
  party: { color: '#0F766E', bg: '#CCFBF1', label: 'Party' },
  other: { color: '#64748B', bg: '#F1F5F9', label: 'Other' },
};

const KIND_ANGLE: Record<KgNode['kind'], number> = {
  case: 0,
  court: -90,
  citation: -35,
  judge: 25,
  party: 90,
  evidence: 145,
  section: 200,
  act: 255,
  other: 320,
};

export default function GraphPage() {
  const { data, isLoading } = useWorkspace();
  const a = data?.analysis ?? null;
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<KgNode | null>(null);

  const kg = a?.kg;

  const { nodes, edges } = useMemo(() => {
    if (!kg || kg.nodes.length === 0) return { nodes: [], edges: [] };

    // Group indices for deterministic radial spread within each kind
    const kindCount: Partial<Record<KgNode['kind'], number>> = {};
    const positioned = new Map<string, { x: number; y: number }>();
    for (const n of kg.nodes) {
      if (n.kind === 'case') {
        positioned.set(n.id, { x: 0, y: 0 });
        continue;
      }
      const i = kindCount[n.kind] ?? 0;
      kindCount[n.kind] = i + 1;
      const baseAngle = ((KIND_ANGLE[n.kind] ?? 0) * Math.PI) / 180;
      const spread = (i - 1) * 0.38; // radians between siblings in same spoke
      const radius = n.kind === 'evidence' ? 340 : n.kind === 'section' ? 300 : 260;
      positioned.set(n.id, {
        x: Math.cos(baseAngle + spread) * radius,
        y: Math.sin(baseAngle + spread) * radius,
      });
    }

    const q = query.trim().toLowerCase();

    const rfNodes = kg.nodes.map((n) => {
      const s = KIND_STYLE[n.kind] ?? KIND_STYLE.other;
      const pos = positioned.get(n.id) ?? { x: 0, y: 0 };
      const isMatch = q.length > 0 && n.label.toLowerCase().includes(q);
      const dimmed = q.length > 0 && !isMatch && !(selected?.id === n.id);
      return {
        id: n.id,
        position: pos,
        data: { label: n.label.length > 42 ? `${n.label.slice(0, 40)}…` : n.label },
        style: {
          background: s.bg,
          border: `2px solid ${isMatch ? '#4338CA' : s.color}`,
          borderWidth: isMatch ? 3 : 2,
          borderRadius: 12,
          color: '#0F172A',
          fontSize: 11,
          fontFamily: 'IBM Plex Mono, monospace',
          padding: '8px 10px',
          boxShadow: isMatch ? '0 0 0 5px rgba(67,56,202,0.18)' : undefined,
          opacity: dimmed ? 0.22 : 1,
          transition: 'opacity .2s',
        },
      };
    });

    const rfEdges = kg.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.relation,
      animated: e.relation === 'CITES',
      style: { stroke: '#CBD5E1', strokeWidth: 1.4, opacity: q ? 0.35 : 1 },
      labelStyle: { fontSize: 8.5, fontFamily: 'IBM Plex Mono, monospace', fill: '#64748B' },
      labelBgStyle: { fill: '#FFFFFFEE' },
      marker: { type: MarkerType.ArrowClosed, color: '#CBD5E1', width: 14, height: 14 },
    }));

    return { nodes: rfNodes, edges: rfEdges };
  }, [kg, query, selected]);

  if (isLoading || !a) return null;

  return (
    <div className="space-y-4 pb-6">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2.5 font-serif text-lg font-semibold tracking-tight text-slate-900">
          <Network className="h-5 w-5 text-sky-600" strokeWidth={1.7} />
          Knowledge Graph Explorer
        </h2>

        <div className="flex flex-wrap items-center gap-2">
          {/* Legend */}
          <div className="hidden items-center gap-1.5 md:flex">
            {(Object.keys(KIND_STYLE) as KgNode['kind'][])
              .filter((k) => !['other'].includes(k))
              .map((k) => (
                <span
                  key={k}
                  className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white/80 px-2 py-0.5 font-mono text-[10px] text-slate-600"
                  title={`Nodes of kind "${KIND_STYLE[k].label}"`}
                >
                  <span className="h-2 w-2 rounded-full" style={{ background: KIND_STYLE[k].color }} />
                  {KIND_STYLE[k].label}
                </span>
              ))}
          </div>

          {/* Search-to-highlight */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Highlight nodes…"
              className="w-52 rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-8 font-mono text-xs text-slate-800 shadow-sm placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
            {query && (
              <button onClick={() => setQuery('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700" aria-label="Clear search">
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {!kg || kg.nodes.length === 0 ? (
        <SectionCard>
          <EmptyState
            icon={Network}
            title="No knowledge graph available"
            description="Once the ingestion pipeline builds the FalkorDB graph, its cases, judges, statutes, and evidence nodes are rendered here as an explorable canvas."
          />
        </SectionCard>
      ) : (
        <div className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm" style={{ height: 'calc(100vh - 220px)', minHeight: 480 }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            minZoom={0.25}
            maxZoom={1.75}
            onNodeClick={(_, node) => {
              const found = kg.nodes.find((n) => n.id === node.id) ?? null;
              setSelected(found);
            }}
            onPaneClick={() => setSelected(null)}
          >
            <Background color="#E2E8F0" gap={22} size={1} />
            <Controls showInteractive={false} className="!shadow-sm" />
          </ReactFlow>

          {/* Provenance panel */}
          {selected && (
            <aside className="absolute right-4 top-4 z-10 w-72 space-y-2.5 rounded-xl border border-slate-200 bg-white/95 p-4 shadow-lg backdrop-blur-md">
              <button
                onClick={() => setSelected(null)}
                className="absolute right-3 top-3 text-slate-400 transition hover:text-slate-700"
                aria-label="Close provenance panel"
              >
                <X className="h-4 w-4" />
              </button>
              <div className="flex items-center gap-2 pr-5">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: (KIND_STYLE[selected.kind] ?? KIND_STYLE.other).color }} />
                <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  {(KIND_STYLE[selected.kind] ?? KIND_STYLE.other).label} node
                </span>
              </div>
              <h3 className="font-serif text-[15px] font-semibold leading-snug tracking-tight text-slate-900">{selected.label}</h3>
              <dl className="space-y-1.5 border-t border-slate-100 pt-2.5 text-[11px]">
                {selected.page && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-slate-500">Source page</dt>
                    <dd className="font-mono font-semibold text-slate-800">p.{selected.page}</dd>
                  </div>
                )}
                {selected.confidence != null && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-slate-500">Confidence</dt>
                    <dd className="font-mono font-semibold text-emerald-700">{selected.confidence}%</dd>
                  </div>
                )}
                {!selected.page && !selected.quote && selected.confidence == null && (
                  <p className="italic text-slate-400">No provenance recorded for this node.</p>
                )}
              </dl>
              {selected.quote && (
                <blockquote className="rounded-lg border border-slate-100 bg-slate-50 p-2.5 text-[11px] italic leading-relaxed text-slate-600">
                  "{selected.quote}"
                </blockquote>
              )}
            </aside>
          )}
        </div>
      )}
    </div>
  );
}
