import { motion } from 'framer-motion';
import { FileQuestion, Sparkles, Clock, Scale, Quote, FileText, ExternalLink, Search } from 'lucide-react';
import { useWorkspace } from './CaseWorkspaceLayout';
import { Claim, EmptyState, GridSkeleton, SectionCard, StatusDot } from '@/components/case/primitives';
import { UploadFlow } from '@/components/case/UploadFlow';
import { ConcordanceBadge } from '@/components/case/ConcordanceBadge';
import type { MetaField } from '@/types/case-workspace';

/** "Section 482 BNSS" → "Section 482 — BNSS" for display only */
function formatSectionsValue(raw: string): string {
  return raw
    .split(',')
    .map((part) => {
      const t = part.trim();
      const m = t.match(/^(Section\s+[\dA-Z()-]+)\s+(.+)$/i);
      return m ? `${m[1]} — ${m[2]}` : t;
    })
    .join(', ');
}

export default function OverviewPage() {
  const { caseId, data, isLoading, refresh, openChat, openPdfViewer } = useWorkspace();
  const a = data?.analysis ?? null;

  if (!isLoading && !a) {
    return (
      <div className="mx-auto max-w-3xl py-6">
        <UploadFlow
          caseId={caseId}
          hasStoredDocs={data?.caseInfo.status === 'documents_uploaded' || data?.caseInfo.status === 'analysis_complete'}
          onCompleted={refresh}
        />
      </div>
    );
  }

  if (!a) return null;

  const issues = a.issues;
  const hasTimeline = a.timeline.length > 0;

  return (
    <div className="space-y-6 pb-10">
      {/* Executive Advisory Summary */}
      <SectionCard>
        <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3.5">
          <h2 className="flex items-center gap-2.5 font-serif text-base font-semibold tracking-tight text-slate-900">
            <Sparkles className="h-[18px] w-[18px] text-indigo-600" strokeWidth={1.7} />
            Executive Advisory Summary
          </h2>
          <StatusDot status={a.summary.status} />
        </div>
        <p className="pt-4 text-[15px] leading-relaxed text-slate-700">
          {a.summary.status === 'not_found' ? (
            <span className="italic text-slate-400">{a.summary.value}</span>
          ) : (
            <Claim>{a.summary.value}</Claim>
          )}
        </p>
      </SectionCard>

      {/* Grounded Metadata Matrix — 12 tiles */}
      <SectionCard>
        <div className="flex items-center justify-between border-b border-slate-100 pb-3.5">
          <h2 className="flex items-center gap-2.5 font-serif text-base font-semibold tracking-tight text-slate-900">
            <Scale className="h-[18px] w-[18px] text-sky-600" strokeWidth={1.7} />
            Grounded Metadata Matrix
          </h2>
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-emerald-700">
            {a.metadataTiles.filter((t) => t.field.status === 'extracted').length}/12 verified
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3 pt-4 sm:grid-cols-2 xl:grid-cols-3">
          {a.metadataTiles.map((tile, idx) => (
            <motion.div
              key={tile.key}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.04 }}
              className="space-y-1.5 rounded-xl border border-slate-200/70 bg-slate-50/60 p-3.5 transition hover:border-slate-300 hover:bg-white hover:shadow-sm"
            >
              <div className="flex items-center justify-between gap-1.5">
                <span className="truncate font-mono text-[9px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  {tile.label}
                </span>
                <StatusDot status={tile.field.status} compact />
              </div>
              <MetaValue field={tile.field} />
              {tile.key === 'sections' && (
                <ConcordanceBadge
                  actName={a.acts[0] || ''}
                  sectionNumber={tile.field.value}
                  className="mt-1"
                />
              )}
            </motion.div>
          ))}
        </div>
      </SectionCard>

      {/* Chronological timeline */}
      <SectionCard>
        <div className="flex items-center justify-between border-b border-slate-100 pb-3.5">
          <h2 className="flex items-center gap-2.5 font-serif text-base font-semibold tracking-tight text-slate-900">
            <Clock className="h-[18px] w-[18px] text-violet-600" strokeWidth={1.7} />
            Chronological Case-Facts Timeline
          </h2>
          {hasTimeline && (
            <span className="font-mono text-[11px] text-slate-500">{a.timeline.length} events</span>
          )}
        </div>

        <div className="pt-4">
          {!hasTimeline ? (
            <EmptyState
              icon={FileQuestion}
              title="No timeline entries recorded"
              description="Chronological events will appear here once the document pipeline extracts dated facts from the record."
            />
          ) : (
            <ol className="relative space-y-4 border-l border-slate-200 pl-6">
              {a.timeline.map((event, idx) => {
                const isTail = idx === a.timeline.length - 1 && a.dateChip.status !== 'not_found';
                return (
                  <motion.li
                    key={`${event.date}-${idx}`}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: Math.min(idx * 0.04, 0.3) }}
                    className="relative group cursor-pointer"
                    onClick={() =>
                      openPdfViewer({
                        quote: event.fact,
                        page: event.page || '1',
                        label: `Timeline Entry (${event.date})`,
                      })
                    }
                  >
                    <span
                      className={`absolute -left-[27px] top-1 flex h-3 w-3 items-center justify-center rounded-full ring-4 ring-white transition group-hover:scale-125 ${
                        isTail ? 'bg-gradient-to-tr from-sky-600 to-indigo-600' : 'bg-slate-300 group-hover:bg-indigo-500'
                      }`}
                    />
                    <div className="flex flex-wrap items-baseline gap-x-2.5">
                      <span className={`rounded border px-1.5 py-0.5 font-mono text-[10px] font-medium ${isTail ? 'border-indigo-200 bg-indigo-50 text-indigo-700' : 'border-slate-200 bg-slate-50 text-slate-600'}`}>
                        {event.date}
                      </span>
                      {isTail && (
                        <span className="rounded-full bg-violet-50 px-2 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider text-violet-700">
                          Outcome
                        </span>
                      )}
                      {event.page && (
                        <span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-1.5 py-0.5 font-mono text-[9px] text-slate-500 group-hover:border-indigo-300 group-hover:text-indigo-600">
                          <FileText className="h-2.5 w-2.5" /> p.{event.page}
                          <span className="text-[8px] text-indigo-500 underline ml-0.5">view PDF</span>
                        </span>
                      )}
                    </div>
                    <p className="mt-1 max-w-3xl text-[13.5px] leading-relaxed text-slate-700 group-hover:text-slate-900">{event.fact}</p>
                  </motion.li>
                );
              })}
            </ol>
          )}
        </div>
      </SectionCard>

      {/* Formulated legal issues */}
      <section className="space-y-3.5">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2.5 font-serif text-lg font-semibold tracking-tight text-slate-900">
            <Quote className="h-[18px] w-[18px] text-indigo-600" strokeWidth={1.7} />
            Formulated Legal Issues &amp; Determinations
          </h2>
          <span className="font-mono text-[11px] text-slate-500">
            Click any card to inspect verbatim source PDF
          </span>
        </div>

        {issues.length === 0 ? (
          <GridSkeleton count={2} height="h-28" />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {issues.map((issue, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(idx * 0.04, 0.25) }}
                whileHover={{ y: -2 }}
                onClick={() =>
                  openPdfViewer({
                    quote: issue.evidence || issue.text,
                    page: issue.page || '1',
                    label: `Issue #${idx + 1} Grounding`,
                  })
                }
                className="group cursor-pointer space-y-3 rounded-2xl border border-slate-200/80 bg-white/80 p-5 shadow-sm backdrop-blur-md transition hover:border-indigo-300 hover:shadow-md"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="rounded-md border border-indigo-200 bg-indigo-50 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-indigo-700">
                    Issue #{idx + 1}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {issue.source === 'document' ? (
                      <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wide text-emerald-700">
                        Document Fact
                      </span>
                    ) : (
                      <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wide text-violet-700">
                        AI Legal Analysis
                      </span>
                    )}
                    <span className="inline-flex items-center gap-0.5 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[9px] text-slate-500 opacity-0 group-hover:opacity-100 transition">
                      <Search className="h-2.5 w-2.5 text-indigo-600" /> View in PDF
                    </span>
                  </div>
                </div>
                <p className="font-serif text-[15px] font-semibold leading-snug tracking-tight text-slate-900 group-hover:text-indigo-950">
                  <Claim>{issue.text}</Claim>
                </p>
                {issue.evidence && (
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 transition group-hover:bg-indigo-50/30 group-hover:border-indigo-100">
                    <p className="text-xs leading-relaxed text-slate-600">
                      <Quote className="mr-1 inline h-3 w-3 text-slate-400" />
                      "{issue.evidence}"
                    </p>
                    {issue.page && (
                      <span className="mt-1.5 inline-block rounded border border-slate-200 bg-white px-1.5 py-0.5 font-mono text-[9px] text-slate-500 font-semibold">
                        Page {issue.page} • Verified Grounding
                      </span>
                    )}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </section>

      {/* Quiet CTA to continue */}
      <div className="flex justify-end pt-2 print:hidden">
        <button onClick={openChat} className="cursor-pointer text-[13px] font-medium text-indigo-700 transition hover:text-indigo-900">
          Ask LexOS AI about this dossier →
        </button>
      </div>
    </div>
  );
}

function MetaValue({ field }: { field: MetaField }) {
  if (field.status === 'not_found') {
    return <p className="truncate font-mono text-[11px] italic text-slate-400">Unstated in record</p>;
  }
  const display =
    field.value.startsWith('Section') && field.value.includes(',')
      ? formatSectionsValue(field.value)
      : field.value;
  return (
    <p className="truncate font-mono text-xs font-semibold text-slate-800" title={display}>
      {display}
    </p>
  );
}
