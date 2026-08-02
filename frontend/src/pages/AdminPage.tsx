import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Settings,
  Database,
  Network,
  Cpu,
  RefreshCw,
  CheckCircle2,
  Trash2,
  Server,
  Activity,
  Layers
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/stores/appStore';

export default function AdminPage() {
  const { activeModel, setActiveModel } = useAppStore();
  const [apiEndpoint, setApiEndpoint] = useState('/api/v1');
  const [cacheCleared, setCacheCleared] = useState(false);

  const handleClearCache = () => {
    localStorage.removeItem('qdrant_cache');
    setCacheCleared(true);
    setTimeout(() => setCacheCleared(false), 2000);
  };

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6">
      {/* Title Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-4 text-left">
        <div>
          <h1 className="text-2xl font-bold text-white">System Administration</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Monitor local docker containers, celery task runners, and active AI model parameters.</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* DB Status checks */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4 text-left md:col-span-2">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5 border-b border-white/5 pb-2">
            <Activity className="h-4.5 w-4.5 text-primary" /> Core Service Containers
          </h3>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg bg-white/5 border border-white/5 p-4 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-white flex items-center gap-1.5">
                  <Database className="h-4 w-4 text-emerald-400" />
                  Qdrant v1.10.0
                </span>
                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold text-emerald-400 border border-emerald-500/10">
                  Online
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Houses the local BGE-M3 embedded vectors. Total staged points: <code className="text-white bg-white/5 px-1 rounded">522,854</code>.
              </p>
            </div>

            <div className="rounded-lg bg-white/5 border border-white/5 p-4 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-white flex items-center gap-1.5">
                  <Network className="h-4 w-4 text-emerald-400" />
                  FalkorDB v2.0
                </span>
                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold text-emerald-400 border border-emerald-500/10">
                  Online
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Visualizes node graphs relationships. Active structured nodes count: <code className="text-white bg-white/5 px-1 rounded">124,510</code>.
              </p>
            </div>
          </div>
        </div>

        {/* Workers Status */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4 text-left md:col-span-1">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5 border-b border-white/5 pb-2">
            <Server className="h-4.5 w-4.5 text-cyan-400" /> Async Task Queues
          </h3>
          <div className="space-y-3 text-xs text-muted-foreground">
            <div className="flex items-center justify-between">
              <span>Celery Worker Nodes:</span>
              <span className="font-bold text-white">2 Running</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Active Redis Broker:</span>
              <span className="font-semibold text-emerald-400">Connected</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 text-xs text-left">
        {/* Model Configurations */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5 border-b border-white/5 pb-2">
            <Cpu className="h-4.5 w-4.5 text-primary" /> Active Model Provider
          </h3>
          <div className="space-y-3">
            <p className="text-muted-foreground">Modify the default neural reasoning provider. This changes the generation quality and response latencies.</p>
            <div className="flex gap-4">
              <button
                onClick={() => setActiveModel('qwen')}
                className={`flex-1 rounded-lg border p-4 transition-all text-left ${
                  activeModel === 'qwen'
                    ? 'border-primary bg-primary/5'
                    : 'border-white/5 bg-white/5 hover:border-white/10'
                }`}
              >
                <p className="font-bold text-white text-sm">Qwen3-8B-AWQ</p>
                <p className="text-[10px] text-muted-foreground mt-1">Slightly faster responses on standard GPU hardware.</p>
              </button>

              <button
                onClick={() => setActiveModel('deepseek')}
                className={`flex-1 rounded-lg border p-4 transition-all text-left ${
                  activeModel === 'deepseek'
                    ? 'border-primary bg-primary/5'
                    : 'border-white/5 bg-white/5 hover:border-white/10'
                }`}
              >
                <p className="font-bold text-white text-sm">DeepSeek-R1 Distill</p>
                <p className="text-[10px] text-muted-foreground mt-1">Deep thought reasoning models for legal evaluations.</p>
              </button>
            </div>
          </div>
        </div>

        {/* Maintenance Controls */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5 border-b border-white/5 pb-2">
            <Settings className="h-4.5 w-4.5 text-purple-400" /> Maintenance & Cache Ops
          </h3>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <span className="font-semibold text-white">Gateway Path</span>
              <div className="flex gap-3 mt-1">
                <input
                  type="text"
                  value={apiEndpoint}
                  onChange={(e) => setApiEndpoint(e.target.value)}
                  className="flex-1 rounded-lg border border-white/5 bg-muted/50 p-2.5 text-xs text-white focus:outline-none"
                />
                <Button className="bg-secondary text-white hover:bg-secondary/95">Save</Button>
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-white/5 pt-4">
              <div className="space-y-0.5">
                <span className="font-semibold text-white">Clear Local Cache</span>
                <p className="text-[10px] text-muted-foreground leading-relaxed mt-0.5">Forces the client to re-evaluate active RAG streams.</p>
              </div>
              <Button
                onClick={handleClearCache}
                variant="outline"
                className="border-red-500/20 bg-red-500/5 hover:bg-red-500/10 text-red-400 gap-1.5 h-9"
              >
                {cacheCleared ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    Cleared
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4" />
                    Reset
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
