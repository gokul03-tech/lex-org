import * as React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, Clock, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface StepItem {
  id: string;
  name: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  durationMs?: number;
  confidence?: number;
}

interface AgentStepperProps {
  steps: StepItem[];
  currentStepId?: string;
  className?: string;
}

export function AgentStepper({ steps, currentStepId, className }: AgentStepperProps) {
  return (
    <div className={cn('space-y-3 text-left', className)}>
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-slate-500">
          Multi-Agent Pipeline Orchestration
        </h4>
        <span className="font-mono text-[11px] font-semibold text-sky-700 bg-sky-50 px-2 py-0.5 rounded-full border border-sky-100">
          {steps.filter((s) => s.status === 'completed').length}/{steps.length} Agents
        </span>
      </div>

      <div className="space-y-2">
        {steps.map((step, idx) => {
          const isActive = step.id === currentStepId || step.status === 'in_progress';
          const isCompleted = step.status === 'completed';
          const isFailed = step.status === 'failed';

          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.03 }}
              className={cn(
                'flex items-center justify-between rounded-xl px-3.5 py-2.5 border transition-all text-xs shadow-2xs',
                isActive
                  ? 'border-sky-300 bg-sky-50/90 text-sky-900 shadow-xs ring-2 ring-sky-100'
                  : isCompleted
                  ? 'border-slate-200/80 bg-white/90 text-slate-800'
                  : isFailed
                  ? 'border-rose-200 bg-rose-50 text-rose-800'
                  : 'border-slate-100 bg-slate-50/50 text-slate-400'
              )}
            >
              <div className="flex items-center gap-2.5">
                <div className="flex h-5 w-5 items-center justify-center">
                  {isCompleted && <CheckCircle2 className="h-4 w-4 text-emerald-600" />}
                  {isActive && <Loader2 className="h-4 w-4 animate-spin text-sky-600" />}
                  {isFailed && <AlertCircle className="h-4 w-4 text-rose-600" />}
                  {!isCompleted && !isActive && !isFailed && (
                    <div className="h-1.5 w-1.5 rounded-full bg-slate-300" />
                  )}
                </div>
                <div>
                  <span className="font-sans font-semibold text-slate-800">{step.name}</span>
                  {step.description && (
                    <span className="ml-2 text-[10px] text-slate-500 font-mono">
                      {step.description}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 font-mono text-[10px] text-slate-500">
                {step.confidence !== undefined && (
                  <span className="text-emerald-700 font-bold bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-100">
                    {Math.round(step.confidence * 100)}%
                  </span>
                )}
                {step.durationMs !== undefined && (
                  <span className="flex items-center gap-0.5 text-slate-500 font-medium">
                    <Clock className="h-2.5 w-2.5" />
                    {step.durationMs}ms
                  </span>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

export default AgentStepper;
