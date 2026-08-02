import { useState } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  Node,
  Edge
} from 'react-flow-renderer';
import { motion } from 'framer-motion';
import { Network, Search, Info, HelpCircle, Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';

const initialNodes: Node[] = [
  { id: '1', type: 'input', data: { label: 'BNS, 2023' }, position: { x: 250, y: 0 }, style: { background: '#020617', border: '1px solid #0ea5e9', color: '#fff', borderRadius: '8px' } },
  { id: '2', data: { label: 'Section 103 (Murder)' }, position: { x: 100, y: 100 }, style: { background: '#020617', border: '1px solid #38bdf8', color: '#fff', borderRadius: '8px' } },
  { id: '3', data: { label: 'Section 111 (Organised Crime)' }, position: { x: 400, y: 100 }, style: { background: '#020617', border: '1px solid #38bdf8', color: '#fff', borderRadius: '8px' } },
  { id: '4', data: { label: 'Article 21 (Personal Liberty)' }, position: { x: 250, y: 200 }, style: { background: '#020617', border: '1px solid #a855f7', color: '#fff', borderRadius: '8px' } },
  { id: '5', type: 'output', data: { label: 'State of Maharashtra v. Roy (Precedent)' }, position: { x: 100, y: 300 }, style: { background: '#020617', border: '1px solid #f43f5e', color: '#fff', borderRadius: '8px' } },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#0ea5e9' } },
  { id: 'e1-3', source: '1', target: '3', animated: true, style: { stroke: '#0ea5e9' } },
  { id: 'e2-4', source: '2', target: '4', style: { stroke: '#a855f7' } },
  { id: 'e4-5', source: '4', target: '5', animated: true, style: { stroke: '#f43f5e' } },
];

export default function KnowledgeGraphPage() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [searchVal, setSearchVal] = useState('');
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  const onNodeClick = (_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchVal.trim()) {
      setNodes(initialNodes);
      return;
    }
    const filtered = initialNodes.map(node => {
      if (node.data.label.toLowerCase().includes(searchVal.toLowerCase())) {
        return { ...node, style: { ...node.style, border: '2px solid #22c55e', boxShadow: '0 0 10px #22c55e' } };
      }
      return node;
    });
    setNodes(filtered);
  };

  return (
    <div className="container mx-auto p-6 lg:p-8 flex flex-col h-[calc(100vh-4rem)] overflow-hidden">
      {/* Page Title & Search */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-4 mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Relational Knowledge Graph</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Visualize citation linkages between cases, statutes, sections, and courts.</p>
        </div>
        <form onSubmit={handleSearch} className="relative flex items-center w-full max-w-xs">
          <input
            type="text"
            value={searchVal}
            onChange={(e) => setSearchVal(e.target.value)}
            placeholder="Search node (e.g. Article 21)..."
            className="w-full rounded-xl border border-white/5 bg-card/40 py-2 pl-10 pr-4 text-xs text-white focus:outline-none"
          />
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        </form>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden relative">
        {/* Left Side: Graph Canvas */}
        <div className="flex-1 rounded-xl border border-white/5 bg-card/10 overflow-hidden relative h-full">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodeClick={onNodeClick}
            fitView
            attributionPosition="bottom-left"
          >
            <MiniMap nodeStrokeColor={() => '#0ea5e9'} nodeColor={() => '#030a21'} maskColor="rgba(2, 6, 23, 0.6)" />
            <Controls className="bg-card border-white/5 text-white" />
            <Background color="#1e293b" gap={16} />
          </ReactFlow>
        </div>

        {/* Right Side: Selected Node Inspector Panel */}
        <div className="w-80 shrink-0 flex flex-col gap-4 overflow-y-auto pr-1">
          {selectedNode ? (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="rounded-xl border border-white/5 bg-card/30 backdrop-blur-md p-5 space-y-4 text-left"
            >
              <div className="flex items-center gap-2 border-b border-white/5 pb-3">
                <Info className="h-4.5 w-4.5 text-primary" />
                <h3 className="font-bold text-white">Node Inspector</h3>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Node Name</span>
                  <p className="text-sm font-bold text-white mt-0.5">{selectedNode.data.label}</p>
                </div>

                <div>
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Node ID</span>
                  <p className="text-muted-foreground mt-0.5 font-mono">{selectedNode.id}</p>
                </div>

                <div>
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Classification</span>
                  <span className="mt-1 block w-max rounded-full bg-primary/10 border border-primary/25 px-2.5 py-0.5 font-bold text-primary">
                    {selectedNode.data.label.includes('Section') ? 'Section Clause' : selectedNode.data.label.includes('Article') ? 'Constitutional Article' : 'Precedent Judgment'}
                  </span>
                </div>

                <div className="border-t border-white/5 pt-3">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Context Relational Index</span>
                  <p className="text-muted-foreground leading-relaxed mt-1 text-[11px]">
                    This node is connected to {edges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id).length} other entities in the FalkorDB graph structure.
                  </p>
                </div>
              </div>

              <div className="pt-2">
                <Button size="sm" className="w-full bg-secondary text-white hover:bg-secondary/90">
                  Expand Child Nodes
                </Button>
              </div>
            </motion.div>
          ) : (
            <div className="rounded-xl border border-white/5 bg-card/25 p-5 text-center flex flex-col items-center justify-center h-full text-muted-foreground">
              <Layers className="h-8 w-8 mb-2" />
              <p className="text-xs">Click on any node in the canvas to inspect entity properties and relationship pathways.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
