import { motion } from 'framer-motion';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { BarChart3, Database, Network, Clock, Sparkles } from 'lucide-react';

const indexedDocsData = [
  { month: 'Mar', docs: 12 },
  { month: 'Apr', docs: 28 },
  { month: 'May', docs: 45 },
  { month: 'Jun', docs: 78 },
  { month: 'Jul', docs: 112 },
];

const topActsData = [
  { name: 'BNSS', citations: 12992 },
  { name: 'BNS', citations: 12389 },
  { name: 'IPC', citations: 3135 },
  { name: 'BSA', citations: 3089 },
  { name: 'Constitution', citations: 2594 },
];

const confidenceData = [
  { name: 'High (85%+)', value: 72 },
  { name: 'Medium (60%-85%)', value: 21 },
  { name: 'Low (<60%)', value: 7 },
];

const modelLatencyData = [
  { name: 'Embed BGE-M3', qwen: 590, deepseek: 590 },
  { name: 'Vector Search', qwen: 12, deepseek: 12 },
  { name: 'FalkorDB query', qwen: 85, deepseek: 85 },
  { name: 'LLM Generation', qwen: 2500, deepseek: 4800 },
];

const COLORS = ['#0ea5e9', '#38bdf8', '#7dd3fc'];

export default function AnalyticsPage() {
  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6">
      {/* Title Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-4 text-left">
        <div>
          <h1 className="text-2xl font-bold text-white">Database & LLM Analytics</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Audit search latency, confidence levels, and legal corpus distributions.</p>
        </div>
      </div>

      {/* Grid count cards */}
      <div className="grid gap-6 sm:grid-cols-3">
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 flex items-center gap-4 text-left">
          <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
            <Database className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Vector Chunks</span>
            <p className="text-xl font-extrabold text-white mt-0.5">522,854</p>
          </div>
        </div>

        <div className="rounded-xl border border-white/5 bg-card/20 p-5 flex items-center gap-4 text-left">
          <div className="rounded-lg bg-cyan-500/10 p-2.5 text-cyan-400">
            <Network className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">FalkorDB Nodes</span>
            <p className="text-xl font-extrabold text-white mt-0.5">124,510</p>
          </div>
        </div>

        <div className="rounded-xl border border-white/5 bg-card/20 p-5 flex items-center gap-4 text-left">
          <div className="rounded-lg bg-purple-500/10 p-2.5 text-purple-400">
            <Clock className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Avg Latency</span>
            <p className="text-xl font-extrabold text-white mt-0.5">3.2 sec</p>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Line Chart: Documents Indexed */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4 text-left">
          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Total Documents Ingested</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={indexedDocsData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorDocs" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="month" stroke="#64748b" fontSize={10} />
                <YAxis stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#030a21', border: '1px solid #1e293b', borderRadius: '8px' }} />
                <Area type="monotone" dataKey="docs" stroke="#0ea5e9" fillOpacity={1} fill="url(#colorDocs)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bar Chart: Citations by Act */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4 text-left">
          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Indexed Chunks by Act</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topActsData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                <YAxis stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#030a21', border: '1px solid #1e293b', borderRadius: '8px' }} />
                <Bar dataKey="citations" fill="#38bdf8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pie Chart: Confidence level */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4 text-left">
          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Advisory Confidence Level</h3>
          <div className="h-64 flex flex-col justify-between items-center sm:flex-row">
            <div className="h-full flex-1 w-full max-w-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={confidenceData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={70}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {confidenceData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#030a21', border: '1px solid #1e293b', borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-2 text-xs">
              {confidenceData.map((entry, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></span>
                  <span className="text-muted-foreground">{entry.name}:</span>
                  <span className="font-bold text-white">{entry.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Multi Bar: Latency comparison */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4 text-left">
          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Latency Profile: Qwen3 vs DeepSeek-R1 (ms)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelLatencyData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={9} />
                <YAxis stroke="#64748b" fontSize={9} />
                <Tooltip contentStyle={{ backgroundColor: '#030a21', border: '1px solid #1e293b', borderRadius: '8px' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 10 }} />
                <Bar dataKey="qwen" name="Qwen3" fill="#0ea5e9" radius={[2, 2, 0, 0]} />
                <Bar dataKey="deepseek" name="DeepSeek-R1" fill="#a855f7" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
