import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Search,
  BookOpen,
  Scale,
  Network,
  Database,
  ArrowRight,
  PlusCircle,
  FileText,
  MessageSquare,
  Server,
  Cpu,
  RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [searchVal, setSearchVal] = useState('');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchVal.trim()) {
      navigate(`/chat?query=${encodeURIComponent(searchVal)}`);
    }
  };

  const statCards = [
    { label: 'Total Acts', val: '67', desc: 'Central Statutes', icon: BookOpen, color: 'text-blue-400' },
    { label: 'Judgments', val: '46,069', desc: 'SC & HC Case Laws', icon: Scale, color: 'text-cyan-400' },
    { label: 'KG Nodes', val: '124,510', desc: 'Entities & Edges', icon: Network, color: 'text-purple-400' },
    { label: 'Qdrant Vectors', val: '522,854', desc: '1024-Dim Chunks', icon: Database, color: 'text-primary' },
  ];

  const recentDocs = [
    { id: '1', name: 'Constitution of India.pdf', type: 'Constitution', date: '2 hours ago', size: '2.5 MB' },
    { id: '2', name: 'Aadhaar Act, 2016.pdf', type: 'Statute', date: '1 day ago', size: '1.1 MB' },
    { id: '3', name: 'Arbitration and Conciliation Act, 1996.pdf', type: 'Statute', date: '3 days ago', size: '1.8 MB' },
  ];

  const recentChats = [
    { id: '1', title: 'Admissibility of electronic records under BSA 2023', date: '10 minutes ago' },
    { id: '2', title: 'Landmark precedents on Article 21 personal liberty', date: '4 hours ago' },
    { id: '3', title: 'Bail conditions for economic offences under PMLA', date: 'Yesterday' },
  ];

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-8">
      {/* Glow Backdrop */}
      <div className="absolute left-[30%] top-[20%] h-96 w-96 rounded-full bg-primary/5 blur-[120px] pointer-events-none"></div>

      {/* WELCOME BANNER */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-2xl border border-white/5 bg-card/40 backdrop-blur-md p-8 lg:p-10 shadow-lg"
      >
        <div className="max-w-2xl space-y-4">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            <Cpu className="h-3.5 w-3.5" />
            LexOrch-KG Legal RAG Platform v1.0.0
          </span>
          <h1 className="text-3xl font-extrabold tracking-tight text-white lg:text-4xl">
            Welcome to the Future of <span className="text-gradient-cyan">Legal Intelligence</span>
          </h1>
          <p className="text-muted-foreground text-sm leading-relaxed">
            Query across 522k vector chunks of Indian laws and visualize connections instantly. 
            Select Qwen-3 or DeepSeek-R1 to begin analyzing.
          </p>

          {/* Quick Search */}
          <form onSubmit={handleSearchSubmit} className="relative mt-6 max-w-lg">
            <input
              type="text"
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value)}
              placeholder="Ask LexOrch-KG anything (e.g. bail rules in BNS Section 438)..."
              className="w-full rounded-xl border border-white/5 bg-muted/40 py-3 pl-11 pr-24 text-sm text-white placeholder-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/20 transition-all shadow-inner"
            />
            <Search className="absolute left-4 top-3.5 h-4.5 w-4.5 text-muted-foreground" />
            <Button
              type="submit"
              className="absolute right-1.5 top-1.5 h-8.5 bg-primary px-4 py-1.5 text-xs text-primary-foreground hover:bg-primary/95"
            >
              Analyze
            </Button>
          </form>
        </div>
      </motion.div>

      {/* STATS COUNT */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <motion.div
              key={card.label}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="glass-card rounded-xl p-5 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{card.label}</span>
                <Icon className={`h-5 w-5 ${card.color}`} />
              </div>
              <div className="mt-4">
                <span className="text-3xl font-extrabold text-white tracking-tight">{card.val}</span>
                <p className="text-xs text-muted-foreground mt-0.5">{card.desc}</p>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* TWO COLUMN SUMMARY SECTION */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Left Col: Uploads & Chats */}
        <div className="lg:col-span-2 space-y-8">
          {/* Recent Uploaded Documents */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-xl border border-white/5 bg-card/20 backdrop-blur-md p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold tracking-tight text-white">Recent Uploaded Documents</h2>
              <Button variant="ghost" size="sm" onClick={() => navigate('/document-analysis')} className="text-primary gap-1">
                Upload New <PlusCircle className="h-4 w-4" />
              </Button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-white/5 text-muted-foreground text-xs uppercase tracking-wider">
                    <th className="pb-3">Name</th>
                    <th className="pb-3">Type</th>
                    <th className="pb-3">Uploaded</th>
                    <th className="pb-3 text-right">Size</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {recentDocs.map((doc) => (
                    <tr key={doc.id} className="hover:bg-white/5 transition-colors group cursor-pointer" onClick={() => navigate('/document-analysis')}>
                      <td className="py-3 flex items-center gap-2 font-medium text-white group-hover:text-primary transition-colors">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        {doc.name}
                      </td>
                      <td className="py-3 text-muted-foreground text-xs">{doc.type}</td>
                      <td className="py-3 text-muted-foreground text-xs">{doc.date}</td>
                      <td className="py-3 text-right text-muted-foreground text-xs">{doc.size}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>

          {/* Recent Chats */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-xl border border-white/5 bg-card/20 backdrop-blur-md p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold tracking-tight text-white">Recent AI Conversations</h2>
              <Button variant="ghost" size="sm" onClick={() => navigate('/chat')} className="text-primary gap-1">
                Open Chat <ArrowRight className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid gap-3">
              {recentChats.map((chat) => (
                <div
                  key={chat.id}
                  onClick={() => navigate('/chat')}
                  className="flex items-center justify-between rounded-lg border border-white/5 bg-white/5 px-4 py-3 cursor-pointer hover:border-primary/20 hover:bg-white/10 transition-all"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <MessageSquare className="h-4 w-4 text-primary shrink-0" />
                    <span className="truncate text-sm font-medium text-white">{chat.title}</span>
                  </div>
                  <span className="text-xs text-muted-foreground shrink-0">{chat.date}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Right Col: System Status */}
        <div className="space-y-8">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-xl border border-white/5 bg-card/20 backdrop-blur-md p-6 space-y-6"
          >
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h2 className="text-lg font-bold tracking-tight text-white">System Status</h2>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-white">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-4 text-sm">
              <div className="flex items-center justify-between rounded-lg bg-white/5 p-3">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-emerald-400" />
                  <span className="font-medium">Qdrant DB</span>
                </div>
                <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                  Online
                </span>
              </div>

              <div className="flex items-center justify-between rounded-lg bg-white/5 p-3">
                <div className="flex items-center gap-2">
                  <Network className="h-4 w-4 text-emerald-400" />
                  <span className="font-medium">FalkorDB Graph</span>
                </div>
                <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                  Online
                </span>
              </div>

              <div className="flex items-center justify-between rounded-lg bg-white/5 p-3">
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-emerald-400" />
                  <span className="font-medium">Celery Workers</span>
                </div>
                <span className="text-xs font-bold text-white">2 Active</span>
              </div>

              <div className="flex items-center justify-between rounded-lg bg-white/5 p-3">
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-primary" />
                  <span className="font-medium">Model Backend</span>
                </div>
                <span className="text-xs font-semibold text-primary-foreground bg-primary px-2.5 py-0.5 rounded-md">
                  Local GPU
                </span>
              </div>
            </div>

            <div className="rounded-lg bg-primary/5 p-4 border border-primary/10 text-xs text-muted-foreground leading-relaxed">
              <strong>Info:</strong> Local model caching is enabled. Model paths are mapped to <code className="bg-white/5 px-1 py-0.5 rounded text-white">/models/</code> to minimize external API dependencies.
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
