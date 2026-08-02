import { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Cpu, Globe, Database, Trash2, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/stores/appStore';

export default function SettingsPage() {
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
          <h1 className="text-2xl font-bold text-white">System Settings</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Configure model providers, local database connections, and API endpoints.</p>
        </div>
      </div>

      <div className="max-w-2xl space-y-6 text-xs text-left">
        {/* Model Provider Config */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Cpu className="h-4 w-4 text-primary" /> Active Model Provider
          </h3>
          <div className="space-y-3">
            <p className="text-muted-foreground">Select the local LLM executor to use for synthesis and debate validation loops.</p>
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
                <p className="text-[10px] text-muted-foreground mt-1">Highly performant general-purpose statutory parser (Local GPU).</p>
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
                <p className="text-[10px] text-muted-foreground mt-1">Deep reasoning model for verifications and contradiction logs (Local GPU).</p>
              </button>
            </div>
          </div>
        </div>

        {/* API Connection settings */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Globe className="h-4 w-4 text-cyan-400" /> API Gateway Connection
          </h3>
          <div className="space-y-3">
            <p className="text-muted-foreground">Configure the base URL of the FastAPI backend router gateway.</p>
            <div className="flex gap-3">
              <input
                type="text"
                value={apiEndpoint}
                onChange={(e) => setApiEndpoint(e.target.value)}
                className="flex-1 rounded-lg border border-white/5 bg-muted/50 p-2.5 text-xs text-white focus:outline-none"
              />
              <Button className="bg-secondary text-white hover:bg-secondary/95">Save Config</Button>
            </div>
          </div>
        </div>

        {/* Database Cache operations */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Database className="h-4 w-4 text-purple-400" /> Database & Client Cache
          </h3>
          <div className="space-y-3">
            <p className="text-muted-foreground">Force-clear the local client-side caches. This triggers full fresh query evaluations against Qdrant.</p>
            <Button
              onClick={handleClearCache}
              variant="outline"
              className="border-red-500/20 bg-red-500/5 hover:bg-red-500/10 text-red-400 gap-2"
            >
              {cacheCleared ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  Cache Reset Complete
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4" />
                  Reset Client Cache
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
