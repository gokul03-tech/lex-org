import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ChevronLeft,
  FileText,
  Printer,
  Download,
  Share2,
  Scale,
  Award,
  ShieldCheck,
  CheckCircle2,
  BookOpen
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function ReportPage() {
  const { caseId } = useParams<{ caseId: string }>();

  const reportData = {
    caseId: caseId || 'C101',
    title: 'State vs. Vikram Dev (Bail Application)',
    client: 'Vikram Dev',
    date: 'August 2, 2026',
    author: 'LexOrch-KG Multi-Agent Council',
    abstract: 'This document contains a synthesized legal advisory report prepared by Qwen-3 and verified by DeepSeek-R1. The analysis targets Section 111 (Organised Crime) of the Bharatiya Nyaya Sanhita (BNS), 2023, regarding a pending bail petition for the accused, Vikram Dev. Based on relational knowledge graphs and vector semantic searches of 46,000+ judgments, the counsel is advised to petition the High Court under Section 482 of the BNSS.',
    findings: [
      { id: '1', statute: 'BNSS, 2023 - Section 482', impact: 'High', description: 'Sets out the primary procedural conditions for bail release in non-bailable offences. Highly applicable since custodial interrogation is complete and co-operation is verified.' },
      { id: '2', statute: 'BNS, 2023 - Section 111', impact: 'Moderate', description: ' syndicate connections must be disproven by demonstrating a lack of direct financial transactions and lack of criminal records.' }
    ],
    precedents: [
      { case: 'Sanjay Chandra v. CBI (AIR 2012 SC 83)', holdings: 'Held that bail is the rule and jail is the exception. Pre-conviction detention cannot be punitive. Primary rationale for bail is securing presence at trial.' }
    ]
  };

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6">
      {/* Header Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-4 text-left">
        <div className="flex items-center gap-3">
          <Link to={`/cases/${reportData.caseId}`} className="text-muted-foreground hover:text-white">
            <ChevronLeft className="h-5 w-5" />
          </Link>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase font-mono">Case ID: {reportData.caseId}</span>
            <h1 className="text-2xl font-bold text-white mt-0.5">Advisory Opinion Report</h1>
          </div>
        </div>

        <div className="flex gap-2.5">
          <Button variant="outline" size="sm" onClick={() => window.print()} className="border-white/5 bg-card/40 text-white gap-1.5 text-xs font-semibold">
            <Printer className="h-4 w-4" />
            Print
          </Button>
          <Button size="sm" className="bg-primary hover:bg-primary/95 text-primary-foreground font-semibold gap-1.5 text-xs">
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
            <h2 className="text-xl font-extrabold text-white print:text-black">LEXORCH-KG LEGAL ADVISORY</h2>
            <p className="text-xs text-primary font-bold tracking-wider print:text-blue-600">CONFIDENTIAL OPINION LEAFLET</p>
          </div>
          <div className="text-right text-[10px] text-muted-foreground font-mono space-y-0.5">
            <p>Report Date: {reportData.date}</p>
            <p>Author: {reportData.author}</p>
          </div>
        </div>

        {/* Abstract Box */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider print:text-black flex items-center gap-1.5">
            <FileText className="h-4 w-4 text-primary" /> Executive Summary
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed leading-6 print:text-slate-700">
            {reportData.abstract}
          </p>
        </div>

        {/* Statutory Findings */}
        <div className="space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider print:text-black flex items-center gap-1.5">
            <BookOpen className="h-4 w-4 text-cyan-400" /> Statutory Citations & Impact Index
          </h3>
          <div className="grid gap-4">
            {reportData.findings.map((item) => (
              <div key={item.id} className="rounded-lg bg-white/5 border border-white/5 p-4 text-xs space-y-1.5 print:bg-slate-50 print:border-black/10">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white print:text-black">{item.statute}</span>
                  <span className="rounded-full bg-red-500/10 border border-red-500/25 px-2 py-0.5 text-[9px] font-bold text-red-400 print:bg-red-100 print:text-red-700">
                    Impact: {item.impact}
                  </span>
                </div>
                <p className="text-muted-foreground print:text-slate-600 leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Key Judicial Precedents */}
        <div className="space-y-4 border-t border-white/5 pt-6 print:border-black/10">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider print:text-black flex items-center gap-1.5">
            <Scale className="h-4 w-4 text-purple-400" /> Core Judicial Precedents Cited
          </h3>
          {reportData.precedents.map((prec, idx) => (
            <div key={idx} className="space-y-2 text-xs">
              <h4 className="font-bold text-white print:text-black">{prec.case}</h4>
              <p className="text-slate-300 print:text-slate-700 leading-relaxed leading-5">
                {prec.holdings}
              </p>
            </div>
          ))}
        </div>

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
