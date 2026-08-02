import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Scale,
  Search,
  SlidersHorizontal,
  Calendar,
  User,
  Download,
  Bookmark,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  X,
  FileText
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Judgment {
  id: string;
  title: string;
  citation: string;
  court: string;
  judge: string;
  date: string;
  summary: string;
  content: string;
}

export default function JudgmentsPage() {
  const [searchVal, setSearchVal] = useState('');
  const [court, setCourt] = useState('All');
  const [selectedJudgment, setSelectedJudgment] = useState<Judgment | null>(null);

  const judgmentsData: Judgment[] = [
    {
      id: 'J1',
      title: 'Sanjay Chandra v. CBI',
      citation: 'AIR 2012 SC 83',
      court: 'Supreme Court of India',
      judge: 'G.S. Singhvi, H.L. Dattu, JJ.',
      date: 'Nov 23, 2011',
      summary: 'Landmark decision concerning guidelines for grant of bail in economic offences. Reasserted that the primary purpose of bail is to secure the presence of the accused at trial, and bail is the rule while jail is the exception.',
      content: 'This appeal is directed against the order of the High Court of Delhi refusing to grant bail to the appellants... The allegations against the appellants are violations under Sections 120-B, 420, 468 and 471 of the IPC... The principal rule of our criminal jurisprudence is that bail is the rule and jail is the exception. Pre-conviction detention is not meant to be punitive. Since custodial interrogation is completed and charge-sheet is filed, there is no justification to keep the accused incarcerated...'
    },
    {
      id: 'J2',
      title: 'Arnesh Kumar v. State of Bihar',
      citation: '(2014) 8 SCC 273',
      court: 'Supreme Court of India',
      judge: 'C.K. Prasad, Pinaki Chandra Ghose, JJ.',
      date: 'Jul 02, 2014',
      summary: 'Important guidelines to prevent arbitrary arrests by police officers under Section 498-A of IPC (cruelty). Required police to record reasons before initiating arrests.',
      content: 'The petitioner, apprehending arrest, filed a petition for anticipatory bail... We find that arrests are often used as tools of harassment by police officers. Under Section 41 of the CrPC (now Section 35 of the BNSS), police must verify the necessity of arrest against established criteria and record written reasons. No arrest should be made in a routine manner without verification...'
    }
  ];

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6">
      {/* Title Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-4">
        <div className="text-left">
          <h1 className="text-2xl font-bold text-white">Court Judgments Search</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Access historic and modern precedents from the Supreme Court and High Courts.</p>
        </div>
      </div>

      {/* Advanced search bar */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <input
            type="text"
            value={searchVal}
            onChange={(e) => setSearchVal(e.target.value)}
            placeholder="Search judgments by case name or citation (e.g. Sanjay Chandra v. CBI)..."
            className="w-full rounded-xl border border-white/5 bg-card/40 py-2.5 pl-10 pr-4 text-xs text-white focus:outline-none"
          />
          <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-muted-foreground" />
        </div>
        <select
          value={court}
          onChange={(e) => setCourt(e.target.value)}
          className="rounded-xl border border-white/5 bg-card/40 px-4 py-2.5 text-xs text-white focus:outline-none appearance-none"
        >
          <option value="All" className="bg-card">All Jurisdictions</option>
          <option value="SC" className="bg-card">Supreme Court</option>
          <option value="HC" className="bg-card">High Court</option>
        </select>
        <Button className="bg-primary text-primary-foreground font-semibold px-6">
          Query Catalog
        </Button>
      </div>

      {/* Judgments List Table */}
      <div className="rounded-xl border border-white/5 bg-card/20 overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-white/5 text-muted-foreground text-[10px] uppercase tracking-wider">
              <th className="p-4">Case Title / Citation</th>
              <th className="p-4">Jurisdiction</th>
              <th className="p-4">Bench</th>
              <th className="p-4">Decision Date</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {judgmentsData.map((jug) => (
              <tr key={jug.id} className="hover:bg-white/5 transition-colors">
                <td className="p-4 text-left">
                  <div className="font-semibold text-white">{jug.title}</div>
                  <span className="text-[10px] text-muted-foreground mt-0.5 block font-mono">{jug.citation}</span>
                </td>
                <td className="p-4 text-muted-foreground">{jug.court}</td>
                <td className="p-4 text-muted-foreground max-w-xs truncate">{jug.judge}</td>
                <td className="p-4 text-muted-foreground">{jug.date}</td>
                <td className="p-4 text-right flex items-center justify-end gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedJudgment(jug)}
                    className="text-primary hover:bg-primary/10 gap-1 text-[11px]"
                  >
                    Read Online
                    <ChevronRight className="h-3 w-3" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-white">
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* FULL READ JUDGMENT MODAL DRAWERS */}
      <AnimatePresence>
        {selectedJudgment && (
          <div className="fixed inset-0 z-50 flex items-center justify-end">
            {/* Backdrop overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedJudgment(null)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            {/* Drawer Sheet */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="relative h-full w-full max-w-2xl bg-card border-l border-white/5 p-6 flex flex-col gap-6 shadow-2xl text-left"
            >
              <button
                onClick={() => setSelectedJudgment(null)}
                className="absolute left-6 top-6 text-muted-foreground hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>

              {/* Header Title details */}
              <div className="pt-10 space-y-2 border-b border-white/5 pb-4">
                <span className="text-[10px] font-bold text-primary font-mono uppercase tracking-wider">
                  {selectedJudgment.citation}
                </span>
                <h2 className="text-lg font-bold text-white leading-snug">{selectedJudgment.title}</h2>
                <div className="grid gap-2 sm:grid-cols-2 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1.5">
                    <Scale className="h-4 w-4 text-cyan-400" />
                    {selectedJudgment.court}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <User className="h-4 w-4" />
                    Bench: {selectedJudgment.judge}
                  </div>
                </div>
              </div>

              {/* Judgment Text body */}
              <div className="flex-1 overflow-y-auto pr-2 space-y-4">
                {/* AI generated summary box */}
                <div className="rounded-lg bg-primary/5 border border-primary/15 p-4 space-y-2">
                  <span className="text-[10px] font-bold text-primary uppercase tracking-wider flex items-center gap-1">
                    <FileText className="h-3.5 w-3.5" />
                    Syllabus / Case Abstract
                  </span>
                  <p className="text-xs text-slate-300 leading-relaxed leading-5">
                    {selectedJudgment.summary}
                  </p>
                </div>

                {/* Full judgment text */}
                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Full Judgment Text</span>
                  <p className="text-xs text-slate-300 leading-relaxed leading-6 pt-1 whitespace-pre-line font-serif">
                    {selectedJudgment.content}
                  </p>
                </div>
              </div>

              {/* Footer action buttons */}
              <div className="border-t border-white/5 pt-4 flex gap-4">
                <Button className="flex-1 bg-primary text-primary-foreground font-semibold hover:bg-primary/95">
                  Reference in Active Case File
                </Button>
                <Button variant="outline" className="border-white/5 text-white bg-card hover:bg-white/5">
                  Download PDF
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
