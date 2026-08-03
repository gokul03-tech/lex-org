import { useState, useMemo } from 'react';
import ReactFlow, { MiniMap, Controls, Background, Node, Edge } from 'react-flow-renderer';
import { Search, Info } from 'lucide-react';

interface CaseGraphProps {
  data: {
    nodes: Array<{ id: string; type: string; label: string }>;
    edges: Array<{ source: string; target: string; type: string }>;
  };
}

export default function CaseGraph({ data }: CaseGraphProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'case':
        return { bg: 'bg-blue-600/20 border-blue-500 text-blue-300', dot: '#3b82f6' };
      case 'judge':
        return { bg: 'bg-purple-600/20 border-purple-500 text-purple-300', dot: '#a855f7' };
      case 'court':
        return { bg: 'bg-emerald-600/20 border-emerald-500 text-emerald-300', dot: '#10b981' };
      case 'act':
        return { bg: 'bg-amber-600/20 border-amber-500 text-amber-300', dot: '#f59e0b' };
      case 'section':
      case 'article':
        return { bg: 'bg-cyan-600/20 border-cyan-500 text-cyan-300', dot: '#06b6d4' };
      case 'petitioner':
      case 'respondent':
        return { bg: 'bg-slate-600/20 border-slate-400 text-slate-200', dot: '#94a3b8' };
      case 'evidence':
        return { bg: 'bg-rose-600/20 border-rose-500 text-rose-300', dot: '#f43f5e' };
      default:
        return { bg: 'bg-slate-800 border-white/10 text-slate-300', dot: '#ffffff' };
    }
  };

  const graphData = useMemo(() => {
    if (!data || !data.nodes) return { nodes: [], edges: [] };

    const totalNodes = data.nodes.length;
    const centerX = 350;
    const centerY = 200;
    const radius = 180;

    const rfNodes: Node[] = data.nodes
      .filter((n) => {
        const matchesSearch = n.label.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesType = selectedType === 'all' || n.type.toLowerCase() === selectedType.toLowerCase();
        return matchesSearch && matchesType;
      })
      .map((n, index) => {
        const angle = (index / (totalNodes || 1)) * 2 * Math.PI;
        const x = n.type.toLowerCase() === 'case' ? centerX : centerX + radius * Math.cos(angle);
        const y = n.type.toLowerCase() === 'case' ? centerY : centerY + radius * Math.sin(angle);

        const colors = getTypeColor(n.type);
        const isHovered = hoveredNode === n.id;

        return {
          id: n.id,
          type: 'default',
          position: { x, y },
          data: {
            label: (
              <div className="flex flex-col items-center">
                <span className="text-[9px] uppercase font-bold tracking-wider opacity-60 font-mono">
                  {n.type}
                </span>
                <span className="font-semibold text-xs text-center leading-tight mt-0.5">
                  {n.label}
                </span>
              </div>
            ),
          },
          style: {
            background: colors.bg.split(' ')[0],
            border: `1.5px solid ${isHovered ? '#60a5fa' : colors.bg.split(' ')[1].replace('border-', '')}`,
            borderRadius: '8px',
            padding: '8px 12px',
            boxShadow: isHovered 
              ? '0 0 15px rgba(59, 130, 246, 0.4)' 
              : '0 4px 6px -1px rgba(0,0,0,0.1)',
            minWidth: '120px',
            transition: 'all 0.2s ease',
          },
        };
      });

    const rfEdges: Edge[] = data.edges
      .filter((e) => {
        const sourceExists = rfNodes.some((n) => n.id === e.source);
        const targetExists = rfNodes.some((n) => n.id === e.target);
        return sourceExists && targetExists;
      })
      .map((e, idx) => ({
        id: `e-${idx}`,
        source: e.source,
        target: e.target,
        label: e.type,
        labelStyle: { fill: '#94a3b8', fontSize: 8, fontWeight: 700, fontFamily: 'monospace' },
        labelBgStyle: { fill: '#0b1329', fillOpacity: 0.8 },
        animated: e.type === 'cites' || e.type === 'uses' || e.type === 'supports',
        style: {
          stroke: e.type === 'supports' ? '#f43f5e' : '#3b82f6',
          strokeWidth: 1.5,
          opacity: 0.6,
        },
      }));

    return { nodes: rfNodes, edges: rfEdges };
  }, [data, searchQuery, selectedType, hoveredNode]);

  const uniqueTypes = useMemo(() => {
    if (!data || !data.nodes) return [];
    return Array.from(new Set(data.nodes.map((n) => n.type)));
  }, [data]);

  return (
    <div className="flex flex-col h-full bg-card/10 border border-white/5 rounded-xl overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 border-b border-white/5 bg-card/30 backdrop-blur-md">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search graph nodes..."
              className="w-48 rounded-lg border border-white/5 bg-background/50 py-1.5 pl-8 pr-3 text-xs text-white placeholder-muted-foreground focus:outline-none"
            />
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
          </div>

          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="rounded-lg border border-white/5 bg-background/50 px-2 py-1.5 text-xs text-white focus:outline-none"
          >
            <option value="all">All Entity Types</option>
            {uniqueTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-[10px] text-muted-foreground font-mono">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-blue-500" /> Case
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-purple-500" /> Judge
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Court
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-500" /> Act
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-cyan-500" /> Sec/Art
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-rose-500" /> Evidence
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-[360px] relative bg-[#0b1329]">
        <ReactFlow
          nodes={graphData.nodes}
          edges={graphData.edges}
          onNodeMouseEnter={(_, node) => setHoveredNode(node.id)}
          onNodeMouseLeave={() => setHoveredNode(null)}
          fitView
          fitViewOptions={{ padding: 0.2 }}
        >
          <Background color="#1e293b" gap={16} size={1} />
          <Controls className="react-flow__controls-override bg-card/60 border border-white/5 rounded-lg text-white" />
          <MiniMap
            nodeStrokeColor={(n) => {
              const nodeData = data.nodes.find((originalNode) => originalNode.id === n.id);
              return nodeData ? getTypeColor(nodeData.type).dot : '#ffffff';
            }}
            nodeColor={(n) => {
              const nodeData = data.nodes.find((originalNode) => originalNode.id === n.id);
              return nodeData ? getTypeColor(nodeData.type).dot + '33' : '#ffffff33';
            }}
            maskColor="rgba(11, 19, 41, 0.6)"
            className="border border-white/5 rounded-lg overflow-hidden bg-card/40"
          />
        </ReactFlow>

        <div className="absolute bottom-4 left-4 z-10 flex items-center gap-2 rounded-lg bg-card/80 border border-white/5 px-3 py-2 text-[10px] text-slate-300 max-w-xs pointer-events-none">
          <Info className="h-3.5 w-3.5 text-primary shrink-0" />
          <span>Interactive Relational Map. Use scroll to zoom, click and drag to pan, and hover over nodes to highlight citations.</span>
        </div>
      </div>
    </div>
  );
}
