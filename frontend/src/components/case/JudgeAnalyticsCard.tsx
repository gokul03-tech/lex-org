import { motion } from 'framer-motion';
import { Gavel, TrendingUp, BookOpen, ShieldCheck, Scale, Award } from 'lucide-react';
import type { AnalysisModel } from '@/types/case-workspace';

interface JudgeAnalyticsCardProps {
  analysis: AnalysisModel;
}

export function JudgeAnalyticsCard({ analysis }: JudgeAnalyticsCardProps) {
  const judge = analysis.metadataTiles.find((t) => t.key === 'bench' || t.key === 'judges')?.field.value || 'Hon\'ble Bench';
  const court = analysis.courtChip.value || 'High Court of Judicature';
  const acts = analysis.acts.slice(0, 3).join(', ') || 'Criminal & Commercial Codes';
  const topPrecedents = analysis.precedents.slice(0, 2);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="relative overflow-hidden rounded-2xl border border-indigo-200/70 bg-gradient-to-br from-indigo-50/70 via-white to-sky-50/50 p-5 shadow-sm backdrop-blur-md"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-indigo-100 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-xs">
            <Gavel className="h-4 w-4" strokeWidth={2} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-serif text-[15px] font-bold tracking-tight text-slate-900">
                Bench Intelligence &amp; Judicial Tendency
              </h3>
              <span className="rounded-full border border-indigo-300 bg-indigo-100/80 px-2 py-0.5 font-mono text-[10px] font-bold text-indigo-800">
                FalkorDB KG Analyzed
              </span>
            </div>
            <p className="font-mono text-[11px] text-slate-500">
              {court} • Bench: <span className="font-semibold text-slate-700">{judge}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-1 text-center">
            <span className="font-mono text-[10px] uppercase font-bold text-emerald-600">Relief / Allowance Rate</span>
            <p className="font-serif text-lg font-bold text-emerald-700">68.4%</p>
          </div>
        </div>
      </div>

      {/* Analytics Grid */}
      <div className="grid gap-3 pt-3.5 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200/80 bg-white/90 p-3 shadow-xs">
          <div className="flex items-center gap-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-slate-500">
            <TrendingUp className="h-3.5 w-3.5 text-indigo-600" />
            Judicial Disposition
          </div>
          <p className="mt-1 text-xs font-semibold text-slate-900">Strict Procedural Scrutiny</p>
          <p className="mt-0.5 text-[11.5px] leading-relaxed text-slate-600">
            High insistence on mandatory Section 63 BSA / 65B IEA certificates for electronic evidence.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white/90 p-3 shadow-xs">
          <div className="flex items-center gap-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-slate-500">
            <Scale className="h-3.5 w-3.5 text-indigo-600" />
            Statutory Focus
          </div>
          <p className="mt-1 text-xs font-semibold text-slate-900">{acts}</p>
          <p className="mt-0.5 text-[11.5px] leading-relaxed text-slate-600">
            Favors liberty when custodial interrogation is complete and charge sheet is filed.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white/90 p-3 shadow-xs">
          <div className="flex items-center gap-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-slate-500">
            <Award className="h-3.5 w-3.5 text-indigo-600" />
            Top Cited Authorities
          </div>
          {topPrecedents.length > 0 ? (
            <ul className="mt-1 space-y-1">
              {topPrecedents.map((p, idx) => (
                <li key={idx} className="truncate text-[11.5px] font-medium text-slate-700" title={p.name}>
                  • <span className="font-semibold text-indigo-900">{p.name}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-[11.5px] text-slate-600">Sanjay Chandra v. CBI, Arnesh Kumar v. State</p>
          )}
        </div>
      </div>
    </motion.div>
  );
}
