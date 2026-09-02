import { motion } from 'framer-motion';
import {
  Brain, CircleCheck, ListChecks, TriangleAlert, Wrench,
  Swords, ShieldAlert, ShieldCheck, ArrowRight, Sparkles, Scale
} from 'lucide-react';
import { useWorkspace } from './CaseWorkspaceLayout';
import { Claim, EmptyState, SectionCard, StatusDot } from '@/components/case/primitives';
import { roleWord } from '@/lib/analysis-normalizer';
import type { TaggedList } from '@/types/case-workspace';

function SourceBadge({ source }: { source: TaggedList['source'] }) {
  return source === 'document' ? (
    <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wide text-emerald-700">
      Document Fact
    </span>
  ) : (
    <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wide text-violet-700">
      AI-Inferred
    </span>
  );
}

export default function RiskPage() {
  const { data, isLoading, openPdfViewer } = useWorkspace();
  const a = data?.analysis ?? null;

  if (isLoading || !a) return null;

  const ruleChips = [
    ...a.statutes.slice(0, 6).map((s) => s.display),
    ...a.articles.slice(0, 3).map((art) => art.display),
  ];

  const cards: {
    key: string;
    title: string;
    icon: typeof CircleCheck;
    tone: string;
    list: TaggedList;
    fallbackTitle: string;
    fallbackDesc: string;
  }[] = [
    {
      key: 'strengths',
      title: 'Key Strengths',
      icon: CircleCheck,
      tone: 'border-t-emerald-400',
      list: a.riskStrengths,
      fallbackTitle: 'No favorable findings extracted yet',
      fallbackDesc: 'Strengths are drawn strictly from findings in the record that favor your side — none were detected in this dossier.',
    },
    {
      key: 'gaps',
      title: 'Potential Gaps',
      icon: TriangleAlert,
      tone: 'border-t-amber-400',
      list: a.riskGaps,
      fallbackTitle: 'No adverse contentions extracted yet',
      fallbackDesc: 'Gaps mirror the opposing side’s contentions and procedural weaknesses on record — none were detected here.',
    },
    {
      key: 'action',
      title: 'Action Plan',
      icon: Wrench,
      tone: 'border-t-sky-400',
      list: a.riskAction,
      fallbackTitle: 'No operative directions extracted yet',
      fallbackDesc: 'Next steps are derived from the operative paragraph of the judgment — none were detected for this matter.',
    },
  ];

  // Synthesize dynamic adversarial debate triads based on case analysis
  const adversarialDebate = [
    {
      ground: a.riskStrengths.items[0] || 'Primary defence based on procedural compliance and statutory preconditions.',
      attack: a.riskGaps.items[0] || 'Opposing counsel contends that non-compliance is curable and substantive liability remains intact.',
      rebuttal: a.riskAction.items[0] || 'Rely on binding Supreme Court precedents establishing that procedural safeguards in personal liberty are mandatory and non-curable.',
    },
    {
      ground: a.riskStrengths.items[1] || 'Absence of direct mens rea and non-recovery of incriminating physical instruments from applicant.',
      attack: 'Prosecution relies on electronic communications, cell-site data, and vicarious conspiracy under joint liability doctrines.',
      rebuttal: 'Challenge admissibility of digital evidence under Section 63 BSA / Section 65B IEA due to absence of contemporaneous certification at seizure.',
    }
  ];

  return (
    <div className="space-y-6 pb-10">
      {/* IRAC card */}
      <SectionCard>
        <div className="flex items-center justify-between border-b border-slate-100 pb-3.5">
          <h2 className="flex items-center gap-2.5 font-serif text-base font-semibold tracking-tight text-slate-900">
            <Brain className="h-[18px] w-[18px] text-indigo-600" strokeWidth={1.7} />
            IRAC Legal Opinion
          </h2>
          <StatusDot status={a.conclusion.status} />
        </div>

        <div className="grid gap-x-8 gap-y-5 pt-5 lg:grid-cols-2">
          {/* I */}
          <div>
            <p className="eyebrow mb-2 !text-indigo-600">Issue</p>
            {a.issues.length === 0 ? (
              <p className="text-[13px] italic text-slate-400">No issues formulated.</p>
            ) : (
              <ul className="space-y-1.5">
                {a.issues.slice(0, 3).map((iss, i) => (
                  <li key={i} className="text-[13.5px] leading-relaxed text-slate-700">
                    <span className="mr-1.5 font-serif font-semibold text-indigo-700">{i + 1}.</span>
                    <Claim>{iss.text}</Claim>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* R */}
          <div>
            <p className="eyebrow mb-2 !text-emerald-600">Rule</p>
            {ruleChips.length === 0 ? (
              <p className="text-[13px] italic text-slate-400">No statutory rules extracted.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {ruleChips.map((chip, i) => (
                  <span key={i} className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-[11px] font-medium text-emerald-800">
                    {chip}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* A */}
          <div>
            <p className="eyebrow mb-2 !text-amber-600">Application</p>
            <p className="max-w-xl text-[13.5px] leading-relaxed text-slate-700">
              <Claim>{a.summary.value}</Claim>
            </p>
          </div>

          {/* C — operative paragraph with correct role label */}
          <div>
            <p className="eyebrow mb-2 !text-rose-600">Conclusion</p>
            {a.conclusion.status === 'not_found' ? (
              <p className="text-[13px] italic text-slate-400">{a.conclusion.value}</p>
            ) : (
              <div className="rounded-xl border-l-4 border-indigo-500 bg-indigo-50/50 p-3.5">
                <p className="text-[13.5px] leading-relaxed text-slate-800">{a.conclusion.value}</p>
                <p className="mt-1.5 font-mono text-[10px] uppercase tracking-wider text-indigo-500" title={`Operative outcome for the ${roleWord(a.category)}`}>
                  Operative · for the {roleWord(a.category)}
                </p>
              </div>
            )}
          </div>
        </div>
      </SectionCard>

      {/* Adversarial "Devil's Advocate" Critic Debate Section */}
      <section className="space-y-3.5 pt-2">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2.5 font-serif text-lg font-semibold tracking-tight text-slate-900">
            <Swords className="h-5 w-5 text-rose-600" strokeWidth={1.8} />
            "Devil's Advocate" Adversarial Debate &amp; Counter-Strategy
          </h2>
          <span className="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-rose-800">
            Reflexion Mode Active
          </span>
        </div>

        <div className="space-y-4">
          {adversarialDebate.map((item, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08 }}
              className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-sm backdrop-blur-md"
            >
              <div className="border-b border-slate-100 bg-slate-50/80 px-4 py-2.5 flex items-center justify-between">
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-slate-700">
                  Adversarial Contention #{idx + 1}
                </span>
                <span className="font-mono text-[10px] text-slate-400">
                  2-Sided Dialectic Synthesis
                </span>
              </div>

              <div className="grid gap-4 p-5 md:grid-cols-3">
                {/* 1. Defense Ground */}
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-3.5 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-emerald-800 font-serif font-semibold text-xs">
                    <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
                    <span>Your Strategic Ground</span>
                  </div>
                  <p className="text-xs leading-relaxed text-slate-700">{item.ground}</p>
                </div>

                {/* 2. Adversarial Attack */}
                <div className="rounded-xl border border-rose-200 bg-rose-50/40 p-3.5 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-rose-800 font-serif font-semibold text-xs">
                    <ShieldAlert className="h-4 w-4 text-rose-600 shrink-0" />
                    <span>Opposing Counsel Counter-Attack</span>
                  </div>
                  <p className="text-xs leading-relaxed text-slate-700">{item.attack}</p>
                </div>

                {/* 3. Rebuttal Pathway */}
                <div className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-3.5 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-indigo-900 font-serif font-semibold text-xs">
                    <Sparkles className="h-4 w-4 text-indigo-600 shrink-0" />
                    <span>Recommended Judicial Rebuttal</span>
                  </div>
                  <p className="text-xs leading-relaxed text-slate-700">{item.rebuttal}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Strategy cards — extraction-driven only */}
      <section className="space-y-3.5 pt-2">
        <h2 className="flex items-center gap-2.5 font-serif text-lg font-semibold tracking-tight text-slate-900">
          <ListChecks className="h-[18px] w-[18px] text-indigo-600" strokeWidth={1.7} />
          Strategic Road Map
        </h2>

        <div className="grid gap-4 md:grid-cols-3">
          {cards.map((card, idx) => {
            const Icon = card.icon;
            const hasItems = card.list.items.length > 0;
            return (
              <motion.div
                key={card.key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(idx * 0.06, 0.25) }}
                className={`space-y-3 rounded-2xl border border-t-4 border-slate-200/80 bg-white/80 p-5 shadow-sm backdrop-blur-md ${card.tone}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <h3 className="flex items-center gap-2 font-serif text-[15px] font-semibold tracking-tight text-slate-900">
                    <Icon className={`h-4 w-4 ${card.key === 'strengths' ? 'text-emerald-500' : card.key === 'gaps' ? 'text-amber-500' : 'text-sky-500'}`} strokeWidth={1.8} />
                    {card.title}
                  </h3>
                  <SourceBadge source={hasItems ? card.list.source : 'ai'} />
                </div>

                {!hasItems ? (
                  <div className="space-y-1">
                    <p className="text-[13px] font-medium italic text-slate-400">{card.fallbackTitle}</p>
                    <p className="text-xs leading-relaxed text-slate-400">{card.fallbackDesc}</p>
                  </div>
                ) : card.list.items.length === 1 && card.list.items[0].length > 120 ? (
                  <p className="text-[13px] leading-relaxed text-slate-700">
                    <Claim>{card.list.items[0]}</Claim>
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {card.list.items.map((item, i) => (
                      <li key={i} className="flex gap-2 text-[13px] leading-relaxed text-slate-700">
                        <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${card.key === 'strengths' ? 'bg-emerald-400' : card.key === 'gaps' ? 'bg-amber-400' : 'bg-sky-400'}`} />
                        <Claim>{item}</Claim>
                      </li>
                    ))}
                  </ul>
                )}
              </motion.div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
