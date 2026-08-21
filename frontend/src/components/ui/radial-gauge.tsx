import * as React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TrustBreakdown {
  retrieval: number;
  evidence: number;
  reasoning: number;
  compliance: number;
}

interface RadialGaugeProps {
  score: number; // 0 to 100
  size?: number;
  strokeWidth?: number;
  className?: string;
  breakdown?: TrustBreakdown;
  label?: string;
}

export function RadialGauge({
  score,
  size = 130,
  strokeWidth = 9,
  className,
  breakdown = {
    retrieval: 94,
    evidence: 90,
    reasoning: 92,
    compliance: 96,
  },
  label = 'Trust Index',
}: RadialGaugeProps) {
  const [showPopover, setShowPopover] = React.useState(false);
  const clampedScore = Math.max(0, Math.min(100, Math.round(score)));

  // Radius and circumference
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference;

  // Dynamic color selection for Daylight Chambers
  const getColor = (val: number) => {
    if (val >= 80) return { stroke: '#059669', text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200' };
    if (val >= 60) return { stroke: '#D97706', text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200' };
    return { stroke: '#E11D48', text: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-200' };
  };

  const theme = getColor(clampedScore);

  return (
    <div
      className={cn('relative flex flex-col items-center justify-center p-3 rounded-2xl bg-white/90 border border-slate-200 shadow-sm backdrop-blur-md', className)}
      onMouseEnter={() => setShowPopover(true)}
      onMouseLeave={() => setShowPopover(false)}
    >
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="rotate-[-90deg]">
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#E2E8F0"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Progress bar */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={theme.stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
            strokeLinecap="round"
            fill="transparent"
          />
        </svg>

        {/* Center score readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className={cn('font-mono text-3xl font-bold tracking-tight', theme.text)}>
            {clampedScore}%
          </span>
          <span className="font-mono text-[9px] uppercase tracking-widest text-slate-500 font-semibold">
            {label}
          </span>
        </div>
      </div>

      <div className="mt-1.5 flex items-center gap-1.5 text-xs text-slate-600">
        <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
        <span className="font-sans font-medium text-[11px]">
          {clampedScore >= 80 ? 'High Confidence (Grounded)' : clampedScore >= 60 ? 'Moderate Grounding' : 'Caution Required'}
        </span>
        <Info className="h-3 w-3 text-slate-400" />
      </div>

      {/* Hover breakdown popover */}
      {showPopover && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 4, scale: 0.95 }}
          className="absolute -top-40 left-1/2 -translate-x-1/2 z-50 w-64 rounded-xl border border-slate-200 bg-white p-3.5 shadow-xl"
        >
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="font-mono text-xs font-semibold text-slate-800">Trust Matrix Breakdown</span>
            <span className={cn('font-mono text-xs font-bold', theme.text)}>{clampedScore}%</span>
          </div>

          <div className="mt-2.5 space-y-2 text-xs">
            <div>
              <div className="flex justify-between text-[11px] text-slate-600">
                <span>RAG Retrieval</span>
                <span className="font-mono text-slate-900 font-semibold">{breakdown.retrieval}%</span>
              </div>
              <div className="mt-0.5 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full bg-sky-600 rounded-full" style={{ width: `${breakdown.retrieval}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[11px] text-slate-600">
                <span>Evidence Integrity</span>
                <span className="font-mono text-slate-900 font-semibold">{breakdown.evidence}%</span>
              </div>
              <div className="mt-0.5 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full bg-emerald-600 rounded-full" style={{ width: `${breakdown.evidence}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[11px] text-slate-600">
                <span>IRAC Reasoning</span>
                <span className="font-mono text-slate-900 font-semibold">{breakdown.reasoning}%</span>
              </div>
              <div className="mt-0.5 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full bg-indigo-600 rounded-full" style={{ width: `${breakdown.reasoning}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[11px] text-slate-600">
                <span>Procedural Compliance</span>
                <span className="font-mono text-slate-900 font-semibold">{breakdown.compliance}%</span>
              </div>
              <div className="mt-0.5 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full bg-amber-600 rounded-full" style={{ width: `${breakdown.compliance}%` }} />
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}

export default RadialGauge;
