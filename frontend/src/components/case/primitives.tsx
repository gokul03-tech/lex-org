import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { FieldStatus } from '@/types/case-workspace';

/* ── Status dot: emerald=extracted · amber=inferred · rose=not_found ── */
export function StatusDot({ status, compact = false }: { status: FieldStatus; compact?: boolean }) {
  const map = {
    extracted: { dot: 'bg-emerald-500', text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Extracted', title: 'Extracted verbatim from the original document' },
    inferred: { dot: 'bg-amber-500', text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Inferred', title: 'Inferred via multi-agent reasoning' },
    not_found: { dot: 'bg-rose-500', text: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-200', label: 'Not Found', title: 'Not stated in the record' },
  } as const;
  const m = map[status];
  if (compact) {
    return <span className={cn('inline-block h-1.5 w-1.5 rounded-full', m.dot)} title={m.title} />;
  }
  return (
    <span
      className={cn('inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-px font-mono text-[9px] font-semibold uppercase tracking-wide', m.bg, m.text, m.border)}
      title={m.title}
    >
      <span className={cn('h-1 w-1 rounded-full', m.dot)} />
      {m.label}
    </span>
  );
}

/* ── Provenance claim: dotted underline + hover tooltip with quote/page/confidence ── */
export function Claim({
  children,
  page,
  quote,
  confidence,
  className,
}: {
  children: ReactNode;
  page?: string;
  quote?: string;
  confidence?: number;
  className?: string;
}) {
  const hasProvenance = page || quote || confidence != null;
  if (!hasProvenance) return <span className={className}>{children}</span>;
  const tip = [
    quote ? `"${quote.length > 160 ? quote.slice(0, 160) + '…' : quote}"` : null,
    page ? `Page ${page}` : null,
    confidence != null ? `Confidence ${confidence}%` : null,
  ].filter(Boolean).join(' · ');
  return (
    <span title={tip} className={cn('cursor-help underline decoration-dotted decoration-slate-300 underline-offset-4', className)}>
      {children}
    </span>
  );
}

/* ── Trust mini-ring for the persistent header ── */
export function MiniGauge({ score, size = 44 }: { score: number; size?: number }) {
  const stroke = 4;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (Math.max(0, Math.min(100, score)) / 100) * c;
  const color = score >= 80 ? '#059669' : score >= 60 ? '#D97706' : '#E11D48';
  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
      title={`Trust Index ${score}% — calibrated against extraction coverage`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#E2E8F0" strokeWidth={stroke} fill="transparent" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="transparent" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={offset} />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-mono text-[10px] font-bold" style={{ color }}>
        {score}
      </span>
    </div>
  );
}

/* ── Section card wrapper ── */
export function SectionCard({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn(
        'rounded-2xl border border-slate-200/80 bg-white/80 p-6 shadow-sm backdrop-blur-md',
        className
      )}
    >
      {children}
    </motion.section>
  );
}

/* ── Skeletons ── */
export function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-24 animate-pulse rounded-2xl bg-slate-200/60" />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="h-56 animate-pulse rounded-2xl bg-slate-200/60" />
        <div className="h-56 animate-pulse rounded-2xl bg-slate-200/60" />
      </div>
      <div className="h-64 animate-pulse rounded-2xl bg-slate-200/60" />
    </div>
  );
}

export function GridSkeleton({ count = 4, height = 'h-32' }: { count?: number; height?: string }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={cn('animate-pulse rounded-2xl bg-slate-200/60', height)} style={{ animationDelay: `${i * 60}ms` }} />
      ))}
    </div>
  );
}

/* ── Teaching empty state ── */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-slate-300 bg-white/70 px-8 py-14 text-center backdrop-blur-sm">
      <div className="flex h-13 w-13 items-center justify-center rounded-full border border-sky-100 bg-sky-50 p-3.5">
        <Icon className="h-6 w-6 text-sky-600" />
      </div>
      <div className="space-y-1.5">
        <h3 className="font-serif text-lg font-semibold tracking-tight text-slate-900">{title}</h3>
        <p className="mx-auto max-w-md text-[13px] leading-relaxed text-slate-500">{description}</p>
      </div>
      {action}
    </div>
  );
}
