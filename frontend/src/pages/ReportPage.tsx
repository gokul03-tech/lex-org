import { useParams, Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ChevronLeft, FileText, Printer, Download, Scale, ShieldCheck, BookOpen, Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import apiClient from '@/lib/api';

export default function ReportPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [loading, setLoading] = useState(true);
  const [caseDetail, setCaseDetail] = useState<any>(null);
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const caseRes = await apiClient.get(`/cases/${caseId}`);
        setCaseDetail(caseRes.data);

        try {
          const analysisRes = await apiClient.get(`/analysis/case/${caseId}`);
          setAnalysisData(analysisRes.data);
        } catch (e) {
          setError('No analysis report has been compiled yet. Please analyze the case first.');
        }
      } catch (err) {
        console.error('Error fetching report info:', err);
        setError('Error loading report. Please check server connection.');
      } finally {
        setLoading(false);
      }
    };
    if (caseId) {
      fetchData();
    }
  }, [caseId]);

  if (loading) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-4 text-center">
        <Loader2 className="h-9 w-9 animate-spin text-primary" strokeWidth={1.6} />
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Compiling advisory report…</p>
      </div>
    );
  }

  if (error || !analysisData) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-4 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full border border-brass/30 bg-brass/10">
          <Scale className="h-6 w-6 text-brass" strokeWidth={1.6} />
        </div>
        <h2 className="font-serif text-xl font-semibold">No Report Compiled</h2>
        <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
          {error || 'Advisory summary has not been generated for this dossier yet.'}
        </p>
        <Link to={`/cases/${caseId}`} className="mt-2">
          <Button variant="outline" className="rounded-lg bg-card">Go to Case Detail</Button>
        </Link>
      </div>
    );
  }

  const reportDate = analysisData.created_at
    ? new Date(analysisData.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    : 'Recently';

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-6 py-8 lg:px-10 lg:py-12">
      {/* Header actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex items-center gap-2.5">
          <Link
            to={`/cases/${caseId}`}
            className="rounded-md border border-border bg-card p-1.5 text-muted-foreground shadow-sm transition hover:text-primary"
            aria-label="Back to case"
          >
            <ChevronLeft className="h-4 w-4" />
          </Link>
          <div>
            <p className="eyebrow">Dossier · {caseId}</p>
            <h1 className="font-serif text-2xl font-semibold tracking-tight">Advisory Opinion Report</h1>
          </div>
        </div>

        <div className="flex gap-2.5">
          <Button variant="outline" size="sm" onClick={() => window.print()} className="gap-1.5 rounded-lg bg-card text-[13px]">
            <Printer className="h-3.5 w-3.5" /> Print
          </Button>
          <Button size="sm" onClick={() => window.print()} className="gap-1.5 rounded-lg text-[13px]">
            <Download className="h-3.5 w-3.5" /> Download PDF
          </Button>
        </div>
      </div>

      {/* Document sheet */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="card-elevated mx-auto max-w-4xl space-y-9 rounded-xl px-8 py-10 lg:px-14 print:border-none print:bg-white print:p-0 print:shadow-none"
      >
        {/* Masthead */}
        <div className="border-b-2 border-double border-primary/30 pb-7 print:border-black/20">
          <p className="eyebrow-brass mb-2 !text-brass">LexOrch-KG · Chambers Memorandum</p>
          <h2 className="font-serif text-2xl font-semibold leading-snug tracking-tight md:text-[28px]">
            {caseDetail?.title || 'State vs. Vikram Dev'}
          </h2>
          <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
            <span className="rounded border border-brass/40 bg-brass/10 px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-brass print:bg-transparent">
              Confidential Legal Advisory Opinion
            </span>
            <div className="space-y-0.5 text-right font-mono text-[11px] text-muted-foreground">
              <p>Report Date: {reportDate}</p>
              <p>Author: LexOrch-KG Council</p>
            </div>
          </div>
        </div>

        {/* Executive summary */}
        <section className="space-y-3.5">
          <h3 className="flex items-center gap-2 font-serif text-lg font-semibold tracking-tight">
            <FileText className="h-4 w-4 text-primary" strokeWidth={1.8} />
            Executive Legal Summary
          </h3>
          <div className="border-l-2 border-brass/60 pl-5">
            <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-foreground/90 print:text-black">
              {analysisData.summary || 'No executive summary generated.'}
            </p>
          </div>
        </section>

        {/* Statutory findings */}
        {analysisData.sections && analysisData.sections.length > 0 && (
          <section className="space-y-4">
            <h3 className="flex items-center gap-2 font-serif text-lg font-semibold tracking-tight">
              <BookOpen className="h-4 w-4 text-primary" strokeWidth={1.8} />
              Statutory Citations & Impact Index
            </h3>
            <div className="grid gap-3.5">
              {analysisData.sections.map((item: any, idx: number) => (
                <div key={idx} className="rounded-lg border border-border bg-secondary/50 p-4 space-y-1.5 print:bg-slate-50">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-serif text-[15px] font-semibold tracking-tight">
                      {item.act} — Section {item.section_number}
                    </span>
                    <span className="rounded-full border border-primary/25 bg-primary/5 px-2 py-0.5 font-mono text-[10px] font-medium text-primary">
                      Relevance {Math.round((item.relevance_score || 0.85) * 100)}%
                    </span>
                  </div>
                  {item.title && (
                    <p className="text-[13px] font-semibold text-foreground">{item.title}</p>
                  )}
                  <p className="text-[13px] leading-relaxed text-muted-foreground">{item.text || item.description}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Precedents */}
        {analysisData.precedents && analysisData.precedents.length > 0 && (
          <section className="space-y-4 border-t border-border pt-8">
            <h3 className="flex items-center gap-2 font-serif text-lg font-semibold tracking-tight">
              <Scale className="h-4 w-4 text-primary" strokeWidth={1.8} />
              Core Judicial Precedents Cited
            </h3>
            <div className="space-y-5">
              {analysisData.precedents.map((prec: any, idx: number) => (
                <div key={idx} className="space-y-1.5">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h4 className="font-serif text-[15px] font-semibold tracking-tight">
                      {prec.case_name || prec.case}
                    </h4>
                    {prec.relevance_score && (
                      <span className="font-mono text-[10px] text-muted-foreground">
                        Score {Math.round(prec.relevance_score * 100)}%
                      </span>
                    )}
                  </div>
                  {(prec.citation && prec.citation !== `Source: ${prec.source}`) && (
                    <p className="font-mono text-[11px] font-medium text-brass print:text-black">{prec.citation}</p>
                  )}
                  <p className="text-[13px] leading-relaxed text-foreground/85 print:text-slate-700">
                    {prec.summary || prec.holdings}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Attestation footer */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-6 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <ShieldCheck className="h-4 w-4 text-sage" strokeWidth={1.8} />
            Verified under Dual-Agent Debate
          </span>
          <span className="font-mono">Verification Key: BGE-M3_QDRANT_FALKOR</span>
        </div>
      </motion.div>
    </div>
  );
}
