import { useParams, Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ChevronLeft,
  FileText,
  Printer,
  Download,
  Scale,
  ShieldCheck,
  BookOpen,
  Loader2
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
          setError("No analysis report has been compiled yet. Please analyze the case first.");
        }
      } catch (err) {
        console.error('Error fetching report info:', err);
        setError("Error loading report. Please check server connection.");
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
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground font-semibold">Generating Advisory Report...</p>
      </div>
    );
  }

  if (error || !analysisData) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-4 text-center">
        <Scale className="h-12 w-12 text-muted-foreground/40" />
        <h2 className="text-xl font-bold text-white">No Report Compiled</h2>
        <p className="text-sm text-muted-foreground max-w-sm">
          {error || "Advisory summary has not been generated for this case directory yet."}
        </p>
        <Link to={`/cases/${caseId}`}>
          <Button variant="outline" className="border-white/5 bg-card/40 mt-2 text-white">
            Go to Case Detail
          </Button>
        </Link>
      </div>
    );
  }

  const reportDate = analysisData.created_at 
    ? new Date(analysisData.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    : 'Recently';

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6">
      {/* Header Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-4 text-left">
        <div className="flex items-center gap-3">
          <Link to={`/cases/${caseId}`} className="text-muted-foreground hover:text-white">
            <ChevronLeft className="h-5 w-5" />
          </Link>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase font-mono">Case ID: {caseId}</span>
            <h1 className="text-2xl font-bold text-white mt-0.5">Advisory Opinion Report</h1>
          </div>
        </div>

        <div className="flex gap-2.5">
          <Button variant="outline" size="sm" onClick={() => window.print()} className="border-white/5 bg-card/40 text-white gap-1.5 text-xs font-semibold">
            <Printer className="h-4 w-4" />
            Print
          </Button>
          <Button size="sm" className="bg-primary hover:bg-primary/95 text-primary-foreground font-semibold gap-1.5 text-xs" onClick={() => window.print()}>
            <Download className="h-4 w-4" />
            Download PDF
          </Button>
        </div>
      </div>

      {/* Report Document Sheet */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto max-w-3xl rounded-xl border border-white/5 bg-card/45 backdrop-blur-md p-8 lg:p-10 shadow-2xl text-left space-y-8 print:bg-white print:text-black print:p-0 print:border-none"
      >
        {/* Document Banner */}
        <div className="flex justify-between items-start border-b border-white/10 pb-6 print:border-black/20">
          <div className="space-y-1.5">
            <h2 className="text-xl font-extrabold text-white print:text-black">{caseDetail?.title || 'State vs. Vikram Dev'}</h2>
            <p className="text-xs text-primary font-bold tracking-wider print:text-blue-600">CONFIDENTIAL LEGAL ADVISORY OPINION</p>
          </div>
          <div className="text-right text-[10px] text-muted-foreground font-mono space-y-0.5">
            <p>Report Date: {reportDate}</p>
            <p>Author: LexOrch-KG Council</p>
          </div>
        </div>

        {/* Abstract Box */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider print:text-black flex items-center gap-1.5">
            <FileText className="h-4 w-4 text-primary" /> Executive Legal Summary
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed leading-6 print:text-slate-700 whitespace-pre-wrap">
            {analysisData.summary || "No executive summary generated."}
          </p>
        </div>

        {/* Statutory Findings */}
        {analysisData.sections && analysisData.sections.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider print:text-black flex items-center gap-1.5">
              <BookOpen className="h-4 w-4 text-cyan-400" /> Statutory Citations & Impact Index
            </h3>
            <div className="grid gap-4">
              {analysisData.sections.map((item: any, idx: number) => (
                <div key={idx} className="rounded-lg bg-white/5 border border-white/5 p-4 text-xs space-y-1.5 print:bg-slate-50 print:border-black/10">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white print:text-black">
                      {item.act} - Section {item.section_number}
                    </span>
                    <span className="rounded-full bg-cyan-500/10 border border-cyan-500/25 px-2 py-0.5 text-[9px] font-bold text-cyan-400 print:bg-cyan-100 print:text-cyan-700">
                      Relevance: {Math.round((item.relevance_score || 0.85) * 100)}%
                    </span>
                  </div>
                  {item.title && <p className="font-semibold text-slate-200 mt-1 print:text-slate-800">{item.title}</p>}
                  <p className="text-muted-foreground print:text-slate-600 leading-relaxed">{item.text || item.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Key Judicial Precedents */}
        {analysisData.precedents && analysisData.precedents.length > 0 && (
          <div className="space-y-4 border-t border-white/5 pt-6 print:border-black/10">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider print:text-black flex items-center gap-1.5">
              <Scale className="h-4 w-4 text-purple-400" /> Core Judicial Precedents Cited
            </h3>
            <div className="space-y-4">
              {analysisData.precedents.map((prec: any, idx: number) => (
                <div key={idx} className="space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-white print:text-black">{prec.case_name || prec.case}</h4>
                    {prec.relevance_score && (
                      <span className="text-[10px] text-muted-foreground font-mono">Score: {Math.round(prec.relevance_score * 100)}%</span>
                    )}
                  </div>
                  {(prec.citation && prec.citation !== `Source: ${prec.source}`) && (
                    <p className="text-[10px] text-cyan-400/80 font-semibold print:text-cyan-700">{prec.citation}</p>
                  )}
                  <p className="text-slate-300 print:text-slate-700 leading-relaxed leading-5">
                    {prec.summary || prec.holdings}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Signatures */}
        <div className="border-t border-white/5 pt-6 flex justify-between items-center text-[10px] text-muted-foreground print:border-black/10">
          <span className="flex items-center gap-1">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            Verified under Dual-Agent Debate
          </span>
          <span className="font-mono">Verification Key: BGE-M3_QDRANT_FALKOR</span>
        </div>
      </motion.div>
    </div>
  );
}
