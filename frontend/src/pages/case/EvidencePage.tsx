import { motion } from 'framer-motion';
import { Gavel, ShieldCheck, ShieldAlert, Users } from 'lucide-react';
import { useWorkspace } from './CaseWorkspaceLayout';
import { Claim, EmptyState, SectionCard, StatusDot } from '@/components/case/primitives';

export default function EvidencePage() {
  const { data, isLoading } = useWorkspace();
  const a = data?.analysis ?? null;

  if (isLoading || !a) return null;

  const highCount = a.evidence.filter((e) => e.reliability === 'HIGH').length;
  const disputedCount = a.evidence.length - highCount;

  return (
    <div className="space-y-6 pb-10">
      {/* Heading — generic, per spec */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2.5 font-serif text-lg font-semibold tracking-tight text-slate-900">
          <ShieldCheck className="h-5 w-5 text-emerald-600" strokeWidth={1.7} />
          Evidence Integrity &amp; Reliability Matrix
        </h2>
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 font-semibold text-emerald-700">
            {highCount} HIGH
          </span>
          <span className="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-0.5 font-semibold text-rose-700">
            {disputedCount} DISPUTED
          </span>
        </div>
      </div>

      {/* Evidence cards */}
      {a.evidence.length === 0 ? (
        <EmptyState
          icon={ShieldAlert}
          title="No evidentiary records extracted"
          description="Documents, logs, and exhibits detected in the record will be graded here for integrity — with statutory reliability caveats where certification is missing."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {a.evidence.map((ev, idx) => {
            const disputed = ev.reliability === 'DISPUTED';
            return (
              <motion.div
                key={`${ev.label}-${idx}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(idx * 0.04, 0.25) }}
                whileHover={{ y: -2 }}
                className={`space-y-2 rounded-2xl border bg-white/80 p-4 shadow-sm backdrop-blur-md transition hover:shadow-md ${
                  disputed ? 'border-rose-200/80 hover:border-rose-300' : 'border-slate-200/80 hover:border-emerald-300'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-serif text-sm font-semibold tracking-tight text-slate-900">{ev.label}</h3>
                  <span
                    className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold ${
                      disputed
                        ? 'border border-rose-200 bg-rose-50 text-rose-700'
                        : 'border border-emerald-200 bg-emerald-50 text-emerald-700'
                    }`}
                  >
                    {ev.reliability}
                  </span>
                </div>
                <p className="text-[13px] leading-relaxed text-slate-600">
                  <Claim>{ev.detail}</Claim>
                </p>
                <footer className="pt-1">
                  <StatusDot status={disputed ? 'not_found' : 'extracted'} compact />
                </footer>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Submissions — category-aware columns */}
      <section className="space-y-3.5 pt-2">
        <h2 className="flex items-center gap-2.5 font-serif text-lg font-semibold tracking-tight text-slate-900">
          <Users className="h-[18px] w-[18px] text-indigo-600" strokeWidth={1.7} />
          Counsel Submissions on Record
        </h2>

        <div className="grid gap-5 lg:grid-cols-2">
          {[a.submissionsA, a.submissionsB].map((col, colIdx) => (
            <SectionCard
              key={col.heading}
              className={colIdx === 0 ? 'border-t-4 !border-t-rose-400' : 'border-t-4 !border-t-indigo-400'}
            >
              <h3 className="flex items-center justify-between gap-2 border-b border-slate-100 pb-3 font-serif text-[15px] font-semibold tracking-tight text-slate-900">
                {col.heading}
                <Gavel
                  className={`h-4 w-4 ${colIdx === 0 ? 'text-rose-500' : 'text-indigo-500'}`}
                  strokeWidth={1.7}
                />
              </h3>

              {col.items.length === 0 ? (
                <p className="pt-3 text-[13px] italic leading-relaxed text-slate-400">
                  No extracted submissions available in the record.
                </p>
              ) : (
                <ul className="space-y-2.5 pt-3.5">
                  {col.items.map((item, i) => (
                    <li key={i} className="flex gap-2.5 text-[13.5px] leading-relaxed text-slate-700">
                      <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${colIdx === 0 ? 'bg-rose-400' : 'bg-indigo-400'}`} />
                      <Claim>{item}</Claim>
                    </li>
                  ))}
                </ul>
              )}
            </SectionCard>
          ))}
        </div>
      </section>
    </div>
  );
}
