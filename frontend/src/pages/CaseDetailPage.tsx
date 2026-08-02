import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Briefcase,
  Calendar,
  User,
  Scale,
  Brain,
  FileText,
  Clock,
  ChevronRight,
  BookOpen,
  History,
  AlertCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'overview' | 'statutes' | 'timeline'>('overview');

  const caseData = {
    id: caseId || 'C101',
    title: 'State vs. Vikram Dev (Bail Application)',
    client: 'Vikram Dev',
    type: 'Criminal Defense',
    status: 'In Progress',
    created: 'Jul 20, 2026',
    facts: 'The accused, Vikram Dev, was apprehended on charges relating to an alleged organized financial crime network. The prosecution alleges violations under Section 111 of BNS. The defense maintains that the accused is a secondary employee with no decision-making power, and that bail should be granted since custodial interrogation is no longer required and BGE-M3 vector searches did not locate similar flight risks.',
    statutes: [
      { id: 'S1', code: 'BNSS, 2023', section: 'Section 482', desc: 'Bail conditions for non-bailable offences.' },
      { id: 'S2', code: 'BNS, 2023', section: 'Section 111', desc: 'Punishment for organized crime.' }
    ],
    timeline: [
      { step: 'Case Initialized', date: 'Jul 20, 2026', desc: 'Client folder created and initial brief loaded.' },
      { step: 'Documents Ingested', date: 'Jul 22, 2026', desc: 'Upload of police reports and arrest logs.' },
      { step: 'Vector Search Executed', date: 'Jul 27, 2026', desc: 'Completed semantic retrieval across 522k Qdrant points.' }
    ]
  };

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6">
      {/* Header Case Details */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-5">
        <div className="text-left">
          <span className="text-[10px] font-bold text-primary font-mono">{caseData.id}</span>
          <h1 className="text-2xl font-bold text-white mt-1">{caseData.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <User className="h-4 w-4" /> Client: {caseData.client}
            </span>
            <span className="flex items-center gap-1">
              <Briefcase className="h-4 w-4" /> Type: {caseData.type}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="h-4 w-4" /> Created: {caseData.created}
            </span>
          </div>
        </div>

        {/* Action triggers */}
        <div className="flex flex-wrap gap-3">
          <Link to={`/cases/${caseData.id}/analysis`}>
            <Button className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold gap-1.5 shadow-md shadow-primary/20">
              <Brain className="h-4.5 w-4.5" />
              Dual-Agent Analysis
            </Button>
          </Link>
          <Link to={`/cases/${caseData.id}/report`}>
            <Button variant="outline" className="border-white/5 bg-card/40 text-white font-semibold gap-1.5">
              <FileText className="h-4.5 w-4.5 text-cyan-400" />
              Compile Report
            </Button>
          </Link>
        </div>
      </div>

      {/* Tabs list */}
      <div className="flex border-b border-white/5">
        {(['overview', 'statutes', 'timeline'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-2.5 text-xs font-bold uppercase tracking-wider transition-all border-b-2 ${
              activeTab === tab
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-white'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <div className="mt-4">
        {activeTab === 'overview' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-xl border border-white/5 bg-card/20 backdrop-blur-md p-6 text-left space-y-4"
          >
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <AlertCircle className="h-4.5 w-4.5 text-primary" />
              Case Facts & Client Summary
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
              {caseData.facts}
            </p>
          </motion.div>
        )}

        {activeTab === 'statutes' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid gap-4 sm:grid-cols-2"
          >
            {caseData.statutes.map((stat) => (
              <div key={stat.id} className="rounded-xl border border-white/5 bg-card/25 p-5 text-left space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-primary">
                  <BookOpen className="h-4 w-4" />
                  {stat.code} - {stat.section}
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {stat.desc}
                </p>
              </div>
            ))}
          </motion.div>
        )}

        {activeTab === 'timeline' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-xl border border-white/5 bg-card/20 backdrop-blur-md p-6 text-left space-y-6"
          >
            <div className="relative pl-6 border-l border-white/5 space-y-6">
              {caseData.timeline.map((step, idx) => (
                <div key={idx} className="relative">
                  {/* Timeline bullet dot */}
                  <span className="absolute -left-8.5 top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-card border border-primary/45 shadow-sm shadow-primary/20">
                    <span className="h-2 w-2 rounded-full bg-primary" />
                  </span>
                  <div className="space-y-1">
                    <div className="flex items-baseline gap-2">
                      <h4 className="text-sm font-bold text-white">{step.step}</h4>
                      <span className="text-[10px] text-muted-foreground font-mono">{step.date}</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
