import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileSignature, X, Sparkles, Copy, Check, Download,
  Loader2, RefreshCw, Scale, ShieldCheck, FileText
} from 'lucide-react';
import apiClient from '@/lib/api';
import { Button } from '@/components/ui/button';

interface LegalDraftingStudioProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseTitle: string;
}

const DRAFT_OPTIONS = [
  {
    id: 'written_arguments',
    label: 'Written Submissions / Final Arguments',
    desc: 'Formal factual & statutory submissions grounded in binding High Court / Supreme Court precedents.',
  },
  {
    id: 'bail_application',
    label: 'Regular Bail Application (Sec 483 BNSS / 439 CrPC)',
    desc: 'Bail petition highlighting absence of flight risk, completed custody, and parity.',
  },
  {
    id: 'arbitration_petition',
    label: 'Section 11 Arbitration Petition',
    desc: 'Petition for appointment of sole arbitrator under Arbitration & Conciliation Act.',
  },
  {
    id: 'injunction_application',
    label: 'Interim Injunction Application (Order XXXIX CPC)',
    desc: 'Application asserting prima facie case, balance of convenience, and irreparable injury.',
  },
];

export function LegalDraftingStudio({
  isOpen,
  onClose,
  caseId,
  caseTitle,
}: LegalDraftingStudioProps) {
  const [selectedType, setSelectedType] = useState<string>('written_arguments');
  const [draftContent, setDraftContent] = useState<string>('');
  const [draftHeading, setDraftHeading] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  const generateDraft = async () => {
    setLoading(true);
    try {
      const res = await apiClient.post(`/analysis/case/${caseId}/draft`, {
        draft_type: selectedType,
      });
      setDraftContent(res.data.content || '');
      setDraftHeading(res.data.heading || 'COURT LEGAL DRAFT');
    } catch (err) {
      console.error('Failed to generate draft:', err);
      setDraftContent('Failed to synthesize draft from LLM. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!draftContent) return;
    navigator.clipboard.writeText(draftContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadDoc = () => {
    if (!draftContent) return;
    const blob = new Blob(['\ufeff', draftContent], { type: 'application/msword' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedType}_${caseId}.doc`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm animate-in fade-in duration-200">
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 12 }}
          className="relative flex h-[90vh] w-full max-w-5xl flex-col rounded-2xl border border-slate-200 bg-white shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-slate-50/80 px-6 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 text-white shadow-sm">
                <FileSignature className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-serif text-base font-bold text-slate-900">
                  One-Click Legal Drafting Studio
                </h2>
                <p className="font-mono text-[11px] text-slate-500">
                  {caseTitle} • Qwen 2.5 Local AI Auto-Pleadings
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="rounded-lg bg-slate-100 p-2 text-slate-500 hover:bg-slate-200 hover:text-slate-900 cursor-pointer transition"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Main Body */}
          <div className="flex flex-1 min-h-0 divide-x divide-slate-200 overflow-hidden">
            {/* Left: Template Selector */}
            <div className="w-80 shrink-0 space-y-3 overflow-y-auto bg-slate-50/50 p-4">
              <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Select Court Pleading Template
              </p>

              <div className="space-y-2">
                {DRAFT_OPTIONS.map((opt) => {
                  const isSelected = selectedType === opt.id;
                  return (
                    <button
                      key={opt.id}
                      onClick={() => setSelectedType(opt.id)}
                      className={`w-full cursor-pointer text-left rounded-xl border p-3.5 transition ${
                        isSelected
                          ? 'border-indigo-500 bg-indigo-50/70 shadow-xs ring-1 ring-indigo-300'
                          : 'border-slate-200 bg-white hover:border-indigo-200 hover:bg-slate-50'
                      }`}
                    >
                      <h4 className={`text-xs font-bold font-serif ${isSelected ? 'text-indigo-950' : 'text-slate-800'}`}>
                        {opt.label}
                      </h4>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
                        {opt.desc}
                      </p>
                    </button>
                  );
                })}
              </div>

              <div className="pt-2">
                <Button
                  onClick={generateDraft}
                  disabled={loading}
                  className="w-full gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 py-2.5 text-xs font-semibold text-white shadow-md hover:from-indigo-700 hover:to-violet-700 cursor-pointer"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Generating Court Pleading...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      Generate Draft with AI
                    </>
                  )}
                </Button>
              </div>

              <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-3">
                <div className="flex items-center gap-1.5 font-mono text-[10px] font-bold text-emerald-800">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" /> Grounded in Case Record
                </div>
                <p className="mt-0.5 text-[11px] text-emerald-700 leading-relaxed">
                  Facts, citations, and sections are directly injected from your dossier into High Court petition format.
                </p>
              </div>
            </div>

            {/* Right: Generated Textarea & Action Controls */}
            <div className="flex flex-1 min-h-0 flex-col bg-white">
              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-2.5 bg-slate-50/40">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-indigo-600" />
                  <span className="font-serif text-xs font-semibold text-slate-800 truncate">
                    {draftHeading || 'Generated Legal Draft'}
                  </span>
                </div>

                {draftContent && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleCopy}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 font-mono text-[11px] font-medium text-slate-700 hover:bg-slate-50 cursor-pointer shadow-xs"
                    >
                      {copied ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                      {copied ? 'Copied!' : 'Copy Text'}
                    </button>
                    <button
                      onClick={handleDownloadDoc}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1 font-mono text-[11px] font-medium text-white hover:bg-indigo-700 cursor-pointer shadow-xs"
                    >
                      <Download className="h-3 w-3" />
                      Download .DOC
                    </button>
                  </div>
                )}
              </div>

              <div className="flex-1 p-4 overflow-hidden flex flex-col">
                {draftContent ? (
                  <textarea
                    value={draftContent}
                    onChange={(e) => setDraftContent(e.target.value)}
                    className="h-full w-full resize-none rounded-xl border border-slate-200 bg-slate-50/40 p-4 font-mono text-[12px] leading-relaxed text-slate-800 outline-none focus:border-indigo-400 focus:bg-white focus:ring-1 focus:ring-indigo-300"
                    placeholder="Legal draft text..."
                  />
                ) : (
                  <div className="flex h-full flex-col items-center justify-center text-center p-8 space-y-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 border border-indigo-200">
                      <Scale className="h-6 w-6" />
                    </div>
                    <h3 className="font-serif text-sm font-semibold text-slate-800">
                      Ready to synthesize courtroom pleadings
                    </h3>
                    <p className="max-w-md text-xs text-slate-500 leading-relaxed">
                      Select a pleading template on the left and click <b>"Generate Draft with AI"</b>. The local Qwen 2.5 engine will structure the document using your analyzed case facts, issues, and binding authorities.
                    </p>
                    <Button
                      onClick={generateDraft}
                      disabled={loading}
                      variant="outline"
                      className="gap-2 rounded-xl text-xs"
                    >
                      <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
                      Generate {DRAFT_OPTIONS.find((d) => d.id === selectedType)?.label}
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
