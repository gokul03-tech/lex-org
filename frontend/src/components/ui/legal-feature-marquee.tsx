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
  },
  {
    title: 'Adaptive Hybrid RAG',
    description:
      'Combines BGE-M3 1024-d dense vector search, BM25 exact keyword matching, and cross-encoder neural reranking over complete Indian law.',
    icon: Icons.shine,
    tag: 'BGE-M3 + BM25',
  },
  {
    title: 'Knowledge Graph Reasoning',
    description:
      'Graph-augmented intelligence powered by FalkorDB, connecting cases, sections, judges, precedents, and procedural compliance rules in Cypher.',
    icon: Icons.unBlur,
    tag: 'FalkorDB Cypher',
  },
  {
    title: 'Explainable IRAC Advisory',
    description:
      'Synthesizes Issue-Rule-Application-Conclusion advisory reports with explicit confidence fusion and evidence reliability matrices.',
    icon: Icons.shaders,
    tag: 'DeepSeek-R1 + Qwen3',
  },
];

export function LegalFeatureMarquee() {
  const m1 = legalMarqueeData.slice(0, 4);
  const m2 = legalMarqueeData.slice(4, 8);
  const m3 = legalMarqueeData.slice(8, 12);

  return (
    <section className="card-elevated relative overflow-hidden rounded-xl p-6 md:p-10">
      <div className="relative z-10 mx-auto max-w-6xl">
        <div className="mx-auto flex max-w-3xl flex-col items-center justify-center space-y-3 text-center">
          <p className="eyebrow-brass flex items-center gap-2">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brass" />
            LexOrch-KG Architecture
          </p>
          <h2 className="font-serif text-2xl font-semibold tracking-tight sm:text-3xl">
            Courtroom-grade legal intelligence, grounded in evidence
          </h2>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            Eliminating AI hallucinations in judicial research through multi-agent orchestration
            over statutory codes, precedent networks, and procedural compliance rules.
          </p>

          <div className="relative mt-5 w-full max-w-4xl overflow-hidden py-4">
            <div className="pointer-events-none absolute left-0 top-0 z-10 h-full w-20 bg-gradient-to-r from-card to-transparent" />
            <div className="pointer-events-none absolute right-0 top-0 z-10 h-full w-20 bg-gradient-to-l from-card to-transparent" />

            <div className="flex flex-col gap-2.5">
              <Marquee className="[--duration:45s] [--gap:0.75rem]" repeat={3}>
                {m1.map((q) => (
                  <Badge key={q} variant="statute" size="lg" className="cursor-default font-mono text-xs shadow-sm transition hover:border-brass/40">
                    § {q}
                  </Badge>
                ))}
              </Marquee>

              <Marquee className="[--duration:50s] [--gap:0.75rem]" repeat={3} reverse>
                {m2.map((q) => (
                  <Badge key={q} variant="precedent" size="lg" className="cursor-default font-mono text-xs shadow-sm transition hover:border-brass/40">
                    ⚖ {q}
                  </Badge>
                ))}
              </Marquee>

              <Marquee className="[--duration:42s] [--gap:0.75rem]" repeat={3}>
                {m3.map((q) => (
                  <Badge key={q} variant="arbitration" size="lg" className="cursor-default font-mono text-xs shadow-sm transition hover:border-brass/40">
                    ⚖ {q}
                  </Badge>
                ))}
              </Marquee>
            </div>
          </div>
        </div>

        <div className="mt-9 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="group flex flex-col justify-between rounded-lg border border-border bg-card p-5 transition-all duration-300 hover:-translate-y-1 hover:border-brass/40 hover:shadow-md"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-brass/30 bg-brass/10 transition group-hover:scale-105">
                      <Icon className="h-[18px] w-[18px] text-brass" />
                    </div>
                    <span className="eyebrow !text-[9px]">{feature.tag}</span>
                  </div>

                  <h3 className="font-serif text-base font-semibold tracking-tight transition-colors group-hover:text-primary">
                    {feature.title}
                  </h3>
                  <p className="text-xs leading-relaxed text-muted-foreground">{feature.description}</p>
                </div>

                <div className="mt-4 flex items-center gap-1.5 border-t border-border pt-3 font-mono text-[11px] font-medium text-muted-foreground">
                  <span className="h-1.5 w-1.5 rounded-full bg-sage" />
                  Grounded &amp; Verified
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
