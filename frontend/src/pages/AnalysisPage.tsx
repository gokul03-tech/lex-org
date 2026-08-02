import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Brain,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  FileText,
  ChevronLeft,
  Sparkles,
  ArrowRight,
  TrendingUp,
  Award
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function AnalysisPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [debating, setDebating] = useState(false);

  const qwenAnalystReport = {
    agentName: 'Qwen-3 (Legal Analyst)',
    summary: 'The primary offence under scrutiny falls under Section 111 of BNS (Organised Crime). The suspect\'s activity logs suggest secondary employment in logistical operations with no direct connection to the core syndicate decision-making framework.',
    statutoryFiling: 'Applying Section 482 of the BNSS, bail is highly justifiable since custodial interrogation is completed, no past criminal record is registered, and there is no evidence of tampering with evidence.',
    confidence: '91.4%'
  };

  const deepseekVerifierReport = {
    agentName: 'DeepSeek-R1 (Devil\'s Advocate)',
    contraindications: 'Prosecution holds call transcripts connecting the suspect to a primary co-accused on the day of the arrest, which could be argued as active participation in the conspiracy.',
    rebuttals: 'Defense must argue that these calls were strictly relating to legitimate transport logistics and do not establish mens rea (guilty mind) for organised crime under Section 111.',
    recommendation: 'Highlight the lack of financial trail/bank transfers between the syndicate account and the accused to weaken the conspiracy claim. File a detailed reply clarifying the communication transcripts.'
  };

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6">
      {/* Header Back button */}
      <div className="flex items-center gap-3">
        <Link to={`/cases/${caseId}`} className="text-muted-foreground hover:text-white">
          <ChevronLeft className="h-5 w-5" />
        </Link>
        <div className="text-left">
          <span className="text-[10px] font-bold text-muted-foreground uppercase font-mono">Case ID: {caseId}</span>
          <h1 className="text-2xl font-bold text-white mt-0.5">Dual-Agent Legal Advisory Report</h1>
        </div>
      </div>

      {/* DUAL COLUMN AGENT CARDS */}
      <div className="grid gap-8 lg:grid-cols-2">
        {/* Analyst Card */}
        <motion.div
          initial={{ opacity: 0, x: -15 }}
          animate={{ opacity: 1, x: 0 }}
          className="rounded-xl border border-blue-500/10 bg-blue-500/5 backdrop-blur-md p-6 text-left space-y-4 shadow-lg"
        >
          <div className="flex items-center justify-between border-b border-blue-500/10 pb-3">
            <div className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              <h2 className="text-sm font-bold text-white">{qwenAnalystReport.agentName}</h2>
            </div>
            <span className="rounded-full bg-blue-500/15 border border-blue-500/20 px-2.5 py-0.5 text-[10px] font-semibold text-primary">
              Summary Agent
            </span>
          </div>

          <div className="space-y-3.5 text-xs text-muted-foreground">
            <div>
              <span className="text-[10px] font-bold text-white uppercase tracking-wider">Legal Assessment summary</span>
              <p className="mt-1 leading-relaxed text-slate-300">{qwenAnalystReport.summary}</p>
            </div>
            <div>
              <span className="text-[10px] font-bold text-white uppercase tracking-wider">Statutory Inferences</span>
              <p className="mt-1 leading-relaxed text-slate-300">{qwenAnalystReport.statutoryFiling}</p>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-white/5 p-3">
              <span className="font-medium text-white">Advisory Confidence Score</span>
              <span className="text-sm font-extrabold text-primary">{qwenAnalystReport.confidence}</span>
            </div>
          </div>
        </motion.div>

        {/* Verifier Card */}
        <motion.div
          initial={{ opacity: 0, x: 15 }}
          animate={{ opacity: 1, x: 0 }}
          className="rounded-xl border border-purple-500/10 bg-purple-500/5 backdrop-blur-md p-6 text-left space-y-4 shadow-lg"
        >
          <div className="flex items-center justify-between border-b border-purple-500/10 pb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-purple-400" />
              <h2 className="text-sm font-bold text-white">{deepseekVerifierReport.agentName}</h2>
            </div>
            <span className="rounded-full bg-purple-500/15 border border-purple-500/20 px-2.5 py-0.5 text-[10px] font-semibold text-purple-400">
              Verifier Agent
            </span>
          </div>

          <div className="space-y-3.5 text-xs text-muted-foreground">
            <div>
              <span className="text-[10px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-500" /> Contradiction & Risks Check
              </span>
              <p className="mt-1 leading-relaxed text-slate-300">{deepseekVerifierReport.contraindications}</p>
            </div>
            <div>
              <span className="text-[10px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> Strategic Defense Rebuttal
              </span>
              <p className="mt-1 leading-relaxed text-slate-300">{deepseekVerifierReport.rebuttals}</p>
            </div>
            <div>
              <span className="text-[10px] font-bold text-white uppercase tracking-wider">Verification Recommendations</span>
              <p className="mt-1 leading-relaxed text-slate-300">{deepseekVerifierReport.recommendation}</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Synthesized Legal Advisory report */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-xl border border-white/5 bg-card/20 backdrop-blur-md p-6 text-left space-y-4"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-cyan-400 animate-pulse" />
          <h2 className="text-base font-bold text-white">Synthesized Agent Advisory Recommendation</h2>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Both agents have deliberated the case facts against active precedents retrieved from Qdrant and relationship edges mapped in FalkorDB. The legal team is advised to prioritize a bail petition under Section 482 of the BNSS, utilizing the argument that there are no financial trails connecting the suspect to the organised crime syndicate, and citing *Sanjay Chandra v. CBI* to secure immediate relief.
        </p>

        <div className="flex flex-wrap gap-4 pt-2 text-xs">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Award className="h-4.5 w-4.5 text-primary" /> Joint Consensus: <span className="font-semibold text-white">Reached</span>
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <TrendingUp className="h-4.5 w-4.5 text-emerald-400" /> Overall Legal Viability: <span className="font-semibold text-white text-emerald-400">High (87.2%)</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
