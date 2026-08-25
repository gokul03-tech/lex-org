import { motion } from 'framer-motion';
import { BookOpen, Landmark, ScrollText } from 'lucide-react';
import { useWorkspace } from './CaseWorkspaceLayout';
import { EmptyState, SectionCard, StatusDot } from '@/components/case/primitives';

export default function StatutesPage() {
  const { data, isLoading } = useWorkspace();
  const a = data?.analysis ?? null;

  if (isLoading || !a) return null;

  const headerActs = a.acts.length
    ? a.acts.join(' • ')
    : 'Statutory Provisions Detected in Record';

  return (
    <div className="space-y-6 pb-10">
      {/* Dynamic acts header */}
      <SectionCard className="border-l-4 !border-l-emerald-500">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <p className="eyebrow">Applicable Statutory Framework</p>
            <h2 className="font-serif text-xl font-semibold leading-snug tracking-tight text-slate-900" title={headerActs}>
              {headerActs}
            </h2>
          </div>
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1 font-mono text-[11px] font-medium text-slate-600">
            {a.statutes.length} sections · {a.articles.length} articles · {a.precedents.length} precedents
          </span>
        </div>
      </SectionCard>

      {/* Statute cards */}
      <section className="space-y-3.5">
        <h3 className="flex items-center gap-2.5 font-serif text-lg font-semibold tracking-tight text-slate-900">
          <ScrollText className="h-[18px] w-[18px] text-emerald-600" strokeWidth={1.7} />
          Sections Invoked
        </h3>

        {a.statutes.length === 0 && a.articles.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="No statutory provisions extracted yet"
            description="When the pipeline detects acts and sections in the record, each appears here with its section chip and one-line statutory context."
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {a.statutes.map((s, idx) => (
              <motion.div
                key={`${s.num}-${idx}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(idx * 0.04, 0.25) }}
                whileHover={{ y: -2 }}
                className="space-y-2 rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-sm backdrop-blur-md transition hover:border-emerald-300 hover:shadow-md"
              >
                <span className="inline-block rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 font-mono text-[11px] font-semibold text-emerald-800">
                  {s.display}
                </span>
                <p className="text-xs leading-relaxed text-slate-600">
                  {s.context || 'Statutory provision invoked in the active proceedings.'}
                </p>
              </motion.div>
            ))}

            {a.articles.map((art, idx) => (
              <motion.div
                key={`art-${art.num}-${idx}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min((a.statutes.length + idx) * 0.04, 0.3) }}
                whileHover={{ y: -2 }}
                className="space-y-2 rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-sm backdrop-blur-md transition hover:border-amber-300 hover:shadow-md"
              >
                <span className="inline-block rounded-md border border-amber-200 bg-amber-50 px-2 py-1 font-mono text-[11px] font-semibold text-amber-800">
                  {art.display}
                </span>
                <p className="text-xs leading-relaxed text-slate-600">
                  {art.context || `Constitutional article referenced in the record (${art.act}).`}
                </p>
              </motion.div>
            ))}
          </div>
        )}
      </section>

      {/* Precedents — each name bound to its own citation+year */}
      <section className="space-y-3.5">
        <h3 className="flex items-center gap-2.5 font-serif text-lg font-semibold tracking-tight text-slate-900">
          <Landmark className="h-[18px] w-[18px] text-violet-600" strokeWidth={1.7} />
          Supreme Court Precedent Citations
        </h3>

        {a.precedents.length === 0 ? (
          <EmptyState
            icon={Landmark}
            title="No binding precedents retrieved"
            description="Precedent cases cited by or relevant to this record will be listed here, each bound to its own citation and year."
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {a.precedents.map((prec, idx) => (
              <motion.article
                key={`${prec.name}-${idx}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(idx * 0.04, 0.25) }}
                whileHover={{ y: -2 }}
                className="space-y-2.5 rounded-2xl border border-slate-200/80 bg-white/80 p-5 shadow-sm backdrop-blur-md transition hover:border-violet-300 hover:shadow-md"
              >
                <header className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h4 className="font-serif text-[15px] font-semibold leading-snug tracking-tight text-slate-900">
                      {prec.name}
                      {prec.year && (
                        <span className="ml-1.5 font-normal text-slate-400">({prec.year})</span>
                      )}
                    </h4>
                    {prec.citation && (
                      <p className="mt-0.5 font-mono text-[11px] font-medium text-violet-700">{prec.citation}</p>
                    )}
                  </div>
                  {prec.similarity != null && (
                    <span className="shrink-0 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-700" title="Vector similarity to the instant matter">
                      {prec.similarity}% match
                    </span>
                  )}
                </header>
                <p className="text-[13px] leading-relaxed text-slate-600">{prec.summary}</p>
                <footer className="flex items-center justify-between pt-1">
                  <StatusDot status={prec.summary ? 'extracted' : 'inferred'} compact />
                  <span className="font-mono text-[9px] uppercase tracking-wider text-slate-400">
                    CITES relation · knowledge graph
                  </span>
                </footer>
              </motion.article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
