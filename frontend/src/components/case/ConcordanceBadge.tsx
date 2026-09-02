import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, BookOpen, Info, ShieldCheck, X } from 'lucide-react';
import { findConcordance, type ConcordanceItem } from '@/lib/concordance';

interface ConcordanceBadgeProps {
  actName?: string | null;
  sectionNumber?: string | null;
  className?: string;
}

export function ConcordanceBadge({ actName, sectionNumber, className = '' }: ConcordanceBadgeProps) {
  const item: ConcordanceItem | null = findConcordance(actName, sectionNumber);
  const [open, setOpen] = useState(false);

  if (!item) return null;

  return (
    <div className={`relative inline-flex items-center ${className}`}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
        className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-amber-50 px-2 py-0.5 font-mono text-[10px] font-semibold text-amber-900 shadow-sm transition hover:bg-amber-100 hover:border-amber-400 cursor-pointer"
        title="Click to view New Criminal Law concordance (BNS/BNSS/BSA)"
      >
        <BookOpen className="h-2.5 w-2.5 text-amber-700" />
        <span>→ Sec {item.new_section} {item.new_act.split(' ')[0]}</span>
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 6 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 6 }}
              transition={{ duration: 0.15 }}
              onClick={(e) => e.stopPropagation()}
              className="absolute left-0 top-full z-50 mt-1.5 w-80 rounded-xl border border-amber-200 bg-white p-4 shadow-xl text-left"
            >
              <div className="flex items-start justify-between gap-2 border-b border-amber-100 pb-2">
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-amber-600" />
                  <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-amber-800">
                    2023 Law Concordance
                  </span>
                </div>
                <button
                  onClick={() => setOpen(false)}
                  className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>

              <div className="mt-3 space-y-2.5 text-xs text-slate-700">
                <div className="flex items-center justify-between rounded-lg bg-amber-50/80 p-2 font-mono">
                  <div>
                    <span className="text-[10px] uppercase text-slate-400">Old Statute</span>
                    <p className="font-bold text-slate-800">Sec {item.old_section}</p>
                    <p className="text-[10px] text-slate-500">{item.old_act.split(',')[0]}</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-amber-600 shrink-0" />
                  <div className="text-right">
                    <span className="text-[10px] uppercase text-amber-600 font-semibold">New 2023 Code</span>
                    <p className="font-bold text-amber-900">Sec {item.new_section}</p>
                    <p className="text-[10px] text-amber-700 font-medium">{item.new_act.split('(')[0]}</p>
                  </div>
                </div>

                <div>
                  <h4 className="font-serif font-semibold text-slate-900">{item.title}</h4>
                  <p className="mt-1 text-[11.5px] leading-relaxed text-slate-600">
                    {item.key_change}
                  </p>
                </div>

                {(item.bailable || item.cognizable || item.forum) && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {item.bailable && (
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-700">
                        {item.bailable}
                      </span>
                    )}
                    {item.cognizable && (
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-700">
                        {item.cognizable}
                      </span>
                    )}
                    {item.forum && (
                      <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-[10px] text-indigo-700">
                        {item.forum}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
