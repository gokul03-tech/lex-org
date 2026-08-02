import { useState } from 'react';
import { motion } from 'framer-motion';
import { User, Shield, BookOpen, ToggleLeft, ToggleRight, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/authStore';

export default function ProfilePage() {
  const user = useAuthStore((state) => state.user);
  
  // Custom preferences states
  const [enableDebate, setEnableDebate] = useState(true);
  const [autoSummarize, setAutoSummarize] = useState(true);

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6">
      {/* Title Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-4 text-left">
        <div>
          <h1 className="text-2xl font-bold text-white">Researcher Profile</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Manage your professional credentials, legal role preferences, and UI toggles.</p>
        </div>
      </div>

      <div className="max-w-2xl space-y-6 text-xs text-left">
        {/* User Card */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-6 flex flex-col sm:flex-row items-center gap-6">
          <div className="h-16 w-16 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center text-primary text-xl font-bold">
            {user?.full_name?.charAt(0) || 'L'}
          </div>
          <div className="space-y-1 text-center sm:text-left flex-1">
            <h2 className="text-lg font-bold text-white">{user?.full_name || 'Legal Advocate'}</h2>
            <p className="text-muted-foreground text-xs">{user?.email || 'advocate@court.in'}</p>
            <div className="flex flex-wrap gap-2 pt-2 justify-center sm:justify-start">
              <span className="rounded-full bg-primary/10 border border-primary/25 px-2.5 py-0.5 font-bold text-primary">
                Role: {user?.role || 'Advocate'}
              </span>
              <span className="rounded-full bg-white/5 border border-white/10 px-2.5 py-0.5 font-bold text-muted-foreground">
                Affiliation: Bar Council of India
              </span>
            </div>
          </div>
        </div>

        {/* User Preferences */}
        <div className="rounded-xl border border-white/5 bg-card/20 p-5 space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="h-4 w-4 text-primary" /> RAG & Reasoning Preferences
          </h3>
          <div className="space-y-4">
            {/* Toggle 1: Multi Agent Debate */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5 pr-4">
                <span className="font-semibold text-white">Enable Multi-Agent Consensus Debate</span>
                <p className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">
                  Forces Qwen-3 and DeepSeek-R1 to cross-examine arguments before rendering legal council abstracts.
                </p>
              </div>
              <button onClick={() => setEnableDebate(!enableDebate)} className="text-muted-foreground hover:text-white">
                {enableDebate ? (
                  <ToggleRight className="h-7 w-7 text-primary" />
                ) : (
                  <ToggleLeft className="h-7 w-7" />
                )}
              </button>
            </div>

            {/* Toggle 2: Auto Summarization */}
            <div className="flex items-center justify-between border-t border-white/5 pt-4">
              <div className="space-y-0.5 pr-4">
                <span className="font-semibold text-white">Auto-summarize Uploads</span>
                <p className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">
                  Automatically invoke LLMs to construct statutory summaries upon drag-and-drop file ingestion completions.
                </p>
              </div>
              <button onClick={() => setAutoSummarize(!autoSummarize)} className="text-muted-foreground hover:text-white">
                {autoSummarize ? (
                  <ToggleRight className="h-7 w-7 text-primary" />
                ) : (
                  <ToggleLeft className="h-7 w-7" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
