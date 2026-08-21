import * as React from 'react';
import { Icons } from './icons';
import { Badge } from './badge';
import { Marquee } from './marquee';

const legalMarqueeData = [
  'Is Section 63 BSA electronic certificate mandatory?',
  'When does Section 50 NDPS Act search safeguard apply?',
  'Test for patent illegality under Section 34(2A) Arbitration Act?',
  'What are the three essential ingredients of Section 111 BNS?',
  'How to establish lack of mens rea in financial cyber fraud?',
  'Can bail be granted when charge sheet is already filed?',
  'Doctrine of proportionality under Article 14 & 21 writ jurisdiction?',
  'Standard of proof for Section 65B IEA electronic call logs?',
  'Relevance threshold for Supreme Court Sanjay Chandra bail rule?',
  'Procedural non-compliance in Section 42 NDPS search without warrant?',
  'Validity of unilateral arbitrator appointment under Section 12(5)?',
  'Grounds for interim stay against executive notification under Article 226?',
];

const features = [
  {
    title: 'Grounded Fact Extraction',
    description:
      'Zero hallucinations. Every statement, party, judge, and section is verbatim verified and linked directly to original document page offsets.',
    icon: Icons.grass,
    tag: 'Deterministic Layer',
    accent: 'text-rose-600 bg-rose-50 border-rose-200',
  },
  {
    title: 'Adaptive Hybrid RAG',
    description:
      'Combines BGE-M3 1024-d dense vector search, BM25 exact keyword matching, and cross-encoder neural reranking over complete Indian law.',
    icon: Icons.shine,
    tag: 'BGE-M3 + BM25',
    accent: 'text-indigo-600 bg-indigo-50 border-indigo-200',
  },
  {
    title: 'Knowledge Graph Reasoning',
    description:
      'Graph-augmented intelligence powered by FalkorDB, connecting cases, sections, judges, precedents, and procedural compliance rules in Cypher.',
    icon: Icons.unBlur,
    tag: 'FalkorDB Cypher',
    accent: 'text-amber-600 bg-amber-50 border-amber-200',
  },
  {
    title: 'Explainable IRAC Advisory',
    description:
      'Synthesizes Issue-Rule-Application-Conclusion advisory reports with explicit confidence fusion and evidence reliability matrices.',
    icon: Icons.shaders,
    tag: 'DeepSeek-R1 + Qwen3',
    accent: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  },
];

export function LegalFeatureMarquee() {
  const m1 = legalMarqueeData.slice(0, 4);
  const m2 = legalMarqueeData.slice(4, 8);
  const m3 = legalMarqueeData.slice(8, 12);

  return (
    <section className="relative overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-b from-white/90 via-slate-50/80 to-white/90 p-6 md:p-10 shadow-sm backdrop-blur-xl">
      {/* Background Soft Warm Glows */}
      <div className="pointer-events-none absolute -top-24 left-1/4 h-72 w-96 rounded-full bg-sky-200/40 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 right-1/4 h-72 w-96 rounded-full bg-amber-200/30 blur-3xl" />

      <div className="relative z-10 mx-auto max-w-6xl">
        <div className="mx-auto flex max-w-3xl flex-col items-center justify-center space-y-3 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3.5 py-1 text-xs font-semibold text-sky-700 shadow-xs">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-600 animate-pulse" />
            LexOrch-KG Architecture
          </div>
          <h2 className="font-serif text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            Courtroom-Grade Legal Intelligence & Grounded AI
          </h2>
          <p className="text-sm md:text-base text-slate-600 leading-relaxed">
            Eliminating AI hallucinations in judicial research. Multi-agent orchestration grounded in statutory codes, precedent networks, and procedural compliance.
          </p>

          {/* Marquee Badge Stream in Daylight Chambers Styling */}
          <div className="relative mt-6 w-full max-w-4xl overflow-hidden py-4">
            <div className="pointer-events-none absolute left-0 top-0 z-10 h-full w-20 bg-gradient-to-r from-[#FAF9F6] to-transparent" />
            <div className="pointer-events-none absolute right-0 top-0 z-10 h-full w-20 bg-gradient-to-l from-[#FAF9F6] to-transparent" />

            <div className="flex flex-col gap-2.5">
              <Marquee className="[--duration:45s] [--gap:0.75rem]" repeat={3}>
                {m1.map((q) => (
                  <Badge
                    key={q}
                    variant="statute"
                    size="lg"
                    className="border-sky-200 bg-sky-50 text-sky-800 font-mono text-xs hover:border-sky-300 transition cursor-default shadow-2xs"
                  >
                    § {q}
                  </Badge>
                ))}
              </Marquee>

              <Marquee
                className="[--duration:50s] [--gap:0.75rem]"
                repeat={3}
                reverse
              >
                {m2.map((q) => (
                  <Badge
                    key={q}
                    variant="precedent"
                    size="lg"
                    className="border-purple-200 bg-purple-50 text-purple-800 font-mono text-xs hover:border-purple-300 transition cursor-default shadow-2xs"
                  >
                    ⚖ {q}
                  </Badge>
                ))}
              </Marquee>

              <Marquee className="[--duration:42s] [--gap:0.75rem]" repeat={3}>
                {m3.map((q) => (
                  <Badge
                    key={q}
                    variant="arbitration"
                    size="lg"
                    className="border-amber-200 bg-amber-50 text-amber-800 font-mono text-xs hover:border-amber-300 transition cursor-default shadow-2xs"
                  >
                    🏛 {q}
                  </Badge>
                ))}
              </Marquee>
            </div>
          </div>
        </div>

        {/* 4 Core Pillars Grid */}
        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="group relative flex flex-col justify-between rounded-2xl border border-slate-200 bg-white/90 p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:border-slate-300"
              >
                <div className="space-y-3.5">
                  <div className="flex items-center justify-between">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl border ${feature.accent} group-hover:scale-105 transition shadow-xs`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
                      {feature.tag}
                    </span>
                  </div>

                  <h3 className="font-serif text-lg font-bold text-slate-900 group-hover:text-sky-700 transition">
                    {feature.title}
                  </h3>
                  <p className="text-xs leading-relaxed text-slate-600">
                    {feature.description}
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-slate-100 flex items-center gap-1.5 text-[11px] font-mono text-slate-500 font-medium">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  Grounded & Verified
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export default LegalFeatureMarquee;
