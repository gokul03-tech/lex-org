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

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference;

  const getColor = (val: number) => {
    if (val >= 80) return { stroke: 'hsl(152 24% 34%)', text: 'text-sage' };
    if (val >= 60) return { stroke: 'hsl(35 45% 45%)', text: 'text-brass' };
    return { stroke: '#B4433A', text: 'text-destructive' };
  };

  const theme = getColor(clampedScore);

  return (
    <div
      className={cn('relative flex flex-col items-center justify-center rounded-xl border border-border bg-card p-3 shadow-sm transition-colors', className)}
      onMouseEnter={() => setShowPopover(true)}
      onMouseLeave={() => setShowPopover(false)}
    >
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="rotate-[-90deg]">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="hsl(40 20% 90%)"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
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

        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className={cn('font-serif text-3xl font-semibold tracking-tight', theme.text)}>
            {clampedScore}%
          </span>
          <span className="eyebrow !text-[9px]">{label}</span>
        </div>
      </div>

      <div className="mt-1.5 flex items-center gap-1.5 text-muted-foreground">
        <ShieldCheck className="h-3.5 w-3.5 text-sage" strokeWidth={1.8} />
        <span className="text-[11px] font-medium">
          {clampedScore >= 80 ? 'High Confidence (Grounded)' : clampedScore >= 60 ? 'Moderate Grounding' : 'Caution Required'}
        </span>
        <Info className="h-3 w-3 text-muted-foreground/60" />
      </div>

      {showPopover && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 4, scale: 0.95 }}
          className="absolute -top-44 left-1/2 z-50 w-64 -translate-x-1/2 rounded-xl border border-border bg-card p-4 shadow-xl"
        >
          <div className="flex items-center justify-between border-b border-border pb-2">
            <span className="font-mono text-xs font-semibold">Trust Matrix Breakdown</span>
            <span className={cn('font-mono text-xs font-bold', theme.text)}>{clampedScore}%</span>
          </div>

          <div className="mt-3 space-y-2.5">
            {[
              { name: 'RAG Retrieval', value: breakdown.retrieval, bar: 'bg-primary' },
              { name: 'Evidence Integrity', value: breakdown.evidence, bar: 'bg-sage' },
              { name: 'IRAC Reasoning', value: breakdown.reasoning, bar: 'bg-brass' },
              { name: 'Procedural Compliance', value: breakdown.compliance, bar: 'bg-primary/70' },
            ].map((row) => (
              <div key={row.name}>
                <div className="flex justify-between text-[11px] text-muted-foreground">
                  <span>{row.name}</span>
                  <span className="font-mono font-semibold text-foreground">{row.value}%</span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                  <div className={`h-full rounded-full ${row.bar}`} style={{ width: `${row.value}%` }} />
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}

export default RadialGauge;
