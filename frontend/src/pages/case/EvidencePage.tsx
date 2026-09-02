import { motion } from 'framer-motion';
import { Gavel, ShieldCheck, ShieldAlert, Users, Search, FileText } from 'lucide-react';
import { useWorkspace } from './CaseWorkspaceLayout';
import { Claim, EmptyState, SectionCard, StatusDot } from '@/components/case/primitives';

export default function EvidencePage() {
  const { data, isLoading, openPdfViewer } = useWorkspace();
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
                onClick={() =>
                  openPdfViewer({
                    quote: ev.detail,
                    page: '1',
                    label: `Evidence Exhibit: ${ev.label}`,
                  })
                }
                className={`group cursor-pointer space-y-2 rounded-2xl border bg-white/80 p-4 shadow-sm backdrop-blur-md transition hover:shadow-md ${
                  disputed ? 'border-rose-200/80 hover:border-rose-300' : 'border-slate-200/80 hover:border-emerald-300'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-serif text-sm font-semibold tracking-tight text-slate-900 group-hover:text-indigo-950">{ev.label}</h3>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold ${
                        disputed
                          ? 'border border-rose-200 bg-rose-50 text-rose-700'
                          : 'border border-emerald-200 bg-emerald-50 text-emerald-700'
                      }`}
                    >
                      {ev.reliability}
                    </span>
                    <span className="inline-flex items-center gap-0.5 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[9px] text-slate-500 opacity-0 group-hover:opacity-100 transition">
                      <Search className="h-2.5 w-2.5 text-indigo-600" /> View in PDF
                    </span>
                  </div>
                </div>
                <p className="text-[13px] leading-relaxed text-slate-600">
                  <Claim>{ev.detail}</Claim>
                </p>
                <footer className="pt-1 flex items-center justify-between">
                  <StatusDot status={disputed ? 'not_found' : 'extracted'} compact />
                  <span className="font-mono text-[9px] text-slate-400">Click to inspect in PDF record</span>
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
                <p className="pt-4 text-xs italic text-slate-400">
                  No submissions extracted under this heading.
                </p>
              ) : (
                <ul className="space-y-3 pt-3">
                  {col.items.map((sub, idx) => (
                    <li
                      key={idx}
                      onClick={() =>
                        openPdfViewer({
                          quote: sub,
                          page: '1',
                          label: `${col.heading} (Point #${idx + 1})`,
                        })
                      }
                      className="group cursor-pointer rounded-xl border border-slate-100 bg-slate-50/60 p-3 transition hover:border-indigo-200 hover:bg-indigo-50/30"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-[13px] leading-relaxed text-slate-700 group-hover:text-slate-900">
                          <Claim>{sub}</Claim>
                        </p>
                        <span className="shrink-0 inline-flex items-center gap-0.5 rounded border border-slate-200 bg-white px-1.5 py-0.5 font-mono text-[9px] text-slate-400 group-hover:text-indigo-600 group-hover:border-indigo-200">
                          <FileText className="h-2.5 w-2.5" /> p.1
                        </span>
                      </div>
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
