import { useState } from 'react';
import {
  Settings, Database, Network, Cpu, CheckCircle2, Trash2, Server, Activity,
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

  const statusPill = (label: string) => (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-sage/30 bg-sage/10 px-2.5 py-0.5 text-[11px] font-medium text-sage">
      <span className="h-1.5 w-1.5 rounded-full bg-sage ring-2 ring-sage/20" />
      {label}
    </span>
  );

  return (
    <div className="mx-auto max-w-6xl space-y-7 px-6 py-8 lg:px-10 lg:py-12">
      {/* Header */}
      <div className="space-y-1.5 border-b border-border pb-6">
        <p className="eyebrow">Operations Console</p>
        <h1 className="font-serif text-3xl font-semibold tracking-tight">System Administration</h1>
        <p className="text-[15px] text-muted-foreground">
          Monitor service containers, task runners, and active AI model parameters.
        </p>
      </div>

      {/* Services */}
      <section className="grid gap-5 md:grid-cols-3">
        <div className="card-elevated rounded-xl p-6 md:col-span-2">
          <h3 className="eyebrow mb-4 flex items-center gap-2 border-b border-border pb-3">
            <Activity className="h-4 w-4 text-primary" strokeWidth={1.8} />
            Core Service Containers
          </h3>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-border bg-secondary/50 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 font-serif text-[15px] font-semibold tracking-tight">
                  <Database className="h-4 w-4 text-sage" strokeWidth={1.8} />
                  Qdrant
                  <span className="font-mono text-[10px] font-normal text-muted-foreground">v1.10.0</span>
                </span>
                {statusPill('Online')}
              </div>
              <p className="text-[13px] leading-relaxed text-muted-foreground">
                Houses local BGE-M3 embedded vectors. Staged points:{' '}
                <code className="rounded border border-border bg-card px-1 py-0.5 font-mono text-[11px] text-foreground">522,854</code>.
              </p>
            </div>

            <div className="rounded-lg border border-border bg-secondary/50 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 font-serif text-[15px] font-semibold tracking-tight">
                  <Network className="h-4 w-4 text-sage" strokeWidth={1.8} />
                  FalkorDB
                  <span className="font-mono text-[10px] font-normal text-muted-foreground">v2.0</span>
                </span>
                {statusPill('Online')}
              </div>
              <p className="text-[13px] leading-relaxed text-muted-foreground">
                Node-graph relationship store. Structured nodes:{' '}
                <code className="rounded border border-border bg-card px-1 py-0.5 font-mono text-[11px] text-foreground">124,510</code>.
              </p>
            </div>
          </div>
        </div>

        <div className="card-elevated rounded-xl p-6">
          <h3 className="eyebrow mb-4 flex items-center gap-2 border-b border-border pb-3">
            <Server className="h-4 w-4 text-primary" strokeWidth={1.8} />
            Async Task Queues
          </h3>
          <div className="space-y-3.5 text-[13px] text-muted-foreground">
            <div className="flex items-center justify-between">
              <span>Celery Workers</span>
              <span className="font-semibold text-foreground">2 Running</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Redis Broker</span>
              {statusPill('Connected')}
            </div>
          </div>
        </div>
      </section>

      {/* Config + maintenance */}
      <section className="grid gap-5 md:grid-cols-2">
        <div className="card-elevated rounded-xl p-6 space-y-4">
          <h3 className="eyebrow flex items-center gap-2 border-b border-border pb-3">
            <Cpu className="h-4 w-4 text-primary" strokeWidth={1.8} />
            Active Model Provider
          </h3>
          <p className="text-[13px] leading-relaxed text-muted-foreground">
            Switch the default neural reasoning provider. This changes generation quality and response latency.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setActiveModel('qwen')}
              className={`cursor-pointer rounded-lg border p-4 text-left transition-all ${
                activeModel === 'qwen'
                  ? 'border-primary/60 bg-card shadow-sm ring-1 ring-primary/15'
                  : 'border-border bg-secondary/40 hover:border-brass/40'
              }`}
            >
              <p className="font-serif text-sm font-semibold tracking-tight">Qwen3-8B-AWQ</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">Faster responses on standard GPU hardware.</p>
            </button>

            <button
              onClick={() => setActiveModel('deepseek')}
              className={`cursor-pointer rounded-lg border p-4 text-left transition-all ${
                activeModel === 'deepseek'
                  ? 'border-primary/60 bg-card shadow-sm ring-1 ring-primary/15'
                  : 'border-border bg-secondary/40 hover:border-brass/40'
              }`}
            >
              <p className="font-serif text-sm font-semibold tracking-tight">DeepSeek-R1 Distill</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">Deep-reasoning mode for complex legal evaluation.</p>
            </button>
          </div>
        </div>

        <div className="card-elevated rounded-xl p-6 space-y-5">
          <h3 className="eyebrow flex items-center gap-2 border-b border-border pb-3">
            <Settings className="h-4 w-4 text-primary" strokeWidth={1.8} />
            Maintenance & Cache Ops
          </h3>

          <div className="space-y-1.5">
            <label className="eyebrow block">Gateway Path</label>
            <div className="flex gap-2.5 pt-0.5">
              <input
                type="text"
                value={apiEndpoint}
                onChange={(e) => setApiEndpoint(e.target.value)}
                className="w-full rounded-lg border border-input bg-card px-3.5 py-2.5 font-mono text-[13px] transition focus:border-brass/60 focus:outline-none focus:ring-2 focus:ring-brass/20"
              />
              <Button variant="secondary" className="rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/80">Save</Button>
            </div>
          </div>

          <div className="flex items-center justify-between gap-4 border-t border-border pt-4">
            <div className="space-y-0.5">
              <p className="text-[14px] font-semibold">Clear Local Cache</p>
              <p className="text-xs leading-relaxed text-muted-foreground">Forces the client to re-evaluate active RAG streams.</p>
            </div>
            <Button
              onClick={handleClearCache}
              variant="outline"
              className="shrink-0 gap-1.5 rounded-lg border-destructive/25 bg-destructive/5 text-destructive hover:bg-destructive/10 hover:text-destructive"
            >
              {cacheCleared ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-sage" /> Cleared
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4" /> Reset
                </>
              )}
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
