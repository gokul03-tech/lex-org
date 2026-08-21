import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  FileText,
  Network,
  Scale,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Search,
  Cpu,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface HowItWorksModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStartCase: () => void;
}

const steps = [
  {
    step: '01',
    title: 'Upload Case Dossier & Grounded Extraction',
    tagline: 'Deterministic fact extraction with page-level provenance',
    description:
      'Upload your legal petition, judgment, or charge sheet (PDF/DOCX/TXT). The multi-agent parser extracts parties, judges, statutory sections, and timeline events verbatim without hallucinations.',
    icon: FileText,
    accent: 'text-sky-600 bg-sky-50 border-sky-200',
    color: 'from-sky-500 to-blue-600',
  },
  {
    step: '02',
    title: 'Hybrid RAG & FalkorDB Knowledge Graph',
    tagline: 'Deep statutory cross-referencing and Cypher reasoning',
    description:
      'Combines BGE-M3 dense vector search, BM25 keyword matching, and FalkorDB knowledge graph traversal to link case facts with BNS, BNSS, BSA, and Supreme Court precedents.',
    icon: Network,
    accent: 'text-purple-600 bg-purple-50 border-purple-200',
    color: 'from-purple-500 to-indigo-600',
  },
  {
    step: '03',
    title: 'Explainable IRAC Advisory & Trust Matrix',
    tagline: 'Courtroom-ready brief with evidence reliability scoring',
    description:
      'Generates an Issue-Rule-Application-Conclusion advisory report. Every argument is backed by a Trust Score and interactive provenance popovers directly citing the source records.',
    icon: ShieldCheck,
    accent: 'text-emerald-600 bg-emerald-50 border-emerald-200',
    color: 'from-emerald-500 to-teal-600',
  },
];

export function HowItWorksModal({ isOpen, onClose, onStartCase }: HowItWorksModalProps) {
  const [currentStep, setCurrentStep] = React.useState(0);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-xs"
      />

      {/* Modal Container */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        className="relative w-full max-w-2xl overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 md:p-8 shadow-2xl z-10 text-left"
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-5 top-5 rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition cursor-pointer"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Header */}
        <div className="space-y-1.5 mb-6">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 border border-sky-200 px-3 py-0.5 text-xs font-semibold text-sky-700">
            <Sparkles className="h-3 w-3" />
            10-Second Product Guide
          </div>
          <h2 className="font-serif text-2xl font-bold text-slate-900">
            How LexOrch-KG Works
          </h2>
          <p className="text-xs text-slate-600">
            A three-step deterministic legal intelligence workflow engineered for Indian Law.
          </p>
        </div>

        {/* Step Cards / Carousel */}
        <div className="space-y-3">
          {steps.map((item, idx) => {
            const Icon = item.icon;
            const isCurrent = currentStep === idx;
            return (
              <div
                key={item.step}
                onClick={() => setCurrentStep(idx)}
                className={`relative flex items-start gap-4 rounded-2xl border p-4 transition-all duration-200 cursor-pointer ${
                  isCurrent
                    ? 'border-sky-300 bg-sky-50/50 shadow-xs ring-2 ring-sky-100'
                    : 'border-slate-200 bg-white hover:bg-slate-50'
                }`}
              >
                <div
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border font-mono font-bold text-sm ${item.accent}`}
                >
                  <Icon className="h-5 w-5" />
                </div>

                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-serif text-sm font-bold text-slate-900">
                      {item.title}
                    </h3>
                    <span className="font-mono text-[10px] font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-md">
                      STEP {item.step}
                    </span>
                  </div>
                  <p className="font-mono text-[11px] font-semibold text-sky-700">
                    {item.tagline}
                  </p>
                  <p className="text-xs text-slate-600 leading-relaxed pt-0.5">
                    {item.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer Actions */}
        <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            <span>Grounded • Zero Hallucinations • Verifiable</span>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              onClick={onClose}
              className="rounded-xl border-slate-200 text-xs px-4 h-9 font-medium"
            >
              Close
            </Button>
            <Button
              onClick={() => {
                onClose();
                onStartCase();
              }}
              className="daylight-btn-primary rounded-xl text-xs px-5 h-9 font-semibold flex items-center gap-1.5"
            >
              Start New Case <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default HowItWorksModal;
