import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText, X, ExternalLink, Download, Search, CheckCircle2,
  ChevronLeft, ChevronRight, Maximize2, Minimize2, ZoomIn, ZoomOut, Loader2, AlertCircle
} from 'lucide-react';
import apiClient from '@/lib/api';

export interface ActiveQuoteTarget {
  quote: string;
  page?: string | number;
  label?: string;
  confidence?: number;
}

interface PdfEvidenceViewerProps {
  caseId: string;
  documentTitle?: string;
  target?: ActiveQuoteTarget | null;
  onClose: () => void;
}

export function PdfEvidenceViewer({
  caseId,
  documentTitle = 'Uploaded Case Document',
  target,
  onClose,
}: PdfEvidenceViewerProps) {
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(100);
  const [expanded, setExpanded] = useState<boolean>(false);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loadingPdf, setLoadingPdf] = useState<boolean>(true);
  const [pdfError, setPdfError] = useState<string | null>(null);

  useEffect(() => {
    if (target?.page) {
      const p = typeof target.page === 'number' ? target.page : parseInt(String(target.page).split('-')[0], 10);
      if (!isNaN(p) && p > 0) {
        setCurrentPage(p);
      }
    }
  }, [target]);

  useEffect(() => {
    let active = true;
    setLoadingPdf(true);
    setPdfError(null);

    apiClient
      .get(`/documents/case/${caseId}/file`, { responseType: 'blob' })
      .then((res) => {
        if (!active) return;
        const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
        setBlobUrl(url);
      })
      .catch((err) => {
        if (!active) return;
        console.error('Failed to load PDF blob:', err);
        setPdfError('Could not load original PDF file. Please ensure document was uploaded.');
      })
      .finally(() => {
        if (active) setLoadingPdf(false);
      });

    return () => {
      active = false;
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [caseId]);

  const activePdfSrc = blobUrl ? `${blobUrl}#page=${currentPage}&zoom=${zoom}` : '';

  return (
    <AnimatePresence>
      <motion.aside
        initial={{ x: '100%', opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: '100%', opacity: 0 }}
        transition={{ type: 'spring', damping: 26, stiffness: 220 }}
        className={`fixed inset-y-0 right-0 z-50 flex flex-col border-l border-slate-200 bg-white shadow-2xl transition-all duration-300 ${
          expanded ? 'w-full md:w-3/4 lg:w-4/5' : 'w-full md:w-1/2 lg:w-[48%]'
        }`}
      >
        {/* Header */}
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-slate-50/80 px-4 backdrop-blur-md">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-200">
              <FileText className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <h3 className="truncate font-serif text-sm font-semibold text-slate-900">
                {documentTitle}
              </h3>
              <p className="font-mono text-[10px] text-slate-500 uppercase tracking-wider">
                Verbatim Evidence Grounding
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Zoom Controls */}
            <div className="hidden sm:flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-0.5">
              <button
                onClick={() => setZoom((z) => Math.max(z - 15, 60))}
                className="rounded p-1 text-slate-500 hover:bg-slate-100 cursor-pointer"
                title="Zoom Out"
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </button>
              <span className="font-mono text-[10px] font-medium px-1 text-slate-600">{zoom}%</span>
              <button
                onClick={() => setZoom((z) => Math.min(z + 15, 160))}
                className="rounded p-1 text-slate-500 hover:bg-slate-100 cursor-pointer"
                title="Zoom In"
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Expand / Minimize Width */}
            <button
              onClick={() => setExpanded(!expanded)}
              className="hidden sm:flex rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 hover:bg-slate-100 cursor-pointer"
              title={expanded ? 'Collapse' : 'Expand Split Screen'}
            >
              {expanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
            </button>

            {/* Open in new tab */}
            {blobUrl && (
              <a
                href={blobUrl}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 hover:bg-slate-100 cursor-pointer"
                title="Open raw PDF in new window"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}

            {/* Close Button */}
            <button
              onClick={onClose}
              className="rounded-lg bg-slate-100 p-1.5 text-slate-600 hover:bg-slate-200 hover:text-slate-900 ml-1 cursor-pointer"
              title="Close PDF viewer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Verbatim Grounded Quote Spotlight Banner */}
        {target?.quote && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            className="border-b border-amber-200 bg-amber-50/90 p-3.5 backdrop-blur-sm"
          >
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <div className="flex items-center gap-1.5">
                <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-amber-900">
                  {target.label || 'Document Verbatim Proof'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {target.page && (
                  <span className="rounded border border-amber-300 bg-amber-100/70 px-1.5 py-0.5 font-mono text-[10px] font-bold text-amber-900">
                    Source Page {target.page}
                  </span>
                )}
                {target.confidence != null && (
                  <span className="rounded border border-emerald-300 bg-emerald-100/70 px-1.5 py-0.5 font-mono text-[10px] font-bold text-emerald-800">
                    {target.confidence}% Match
                  </span>
                )}
              </div>
            </div>
            <blockquote className="font-serif text-[12.5px] italic leading-snug text-slate-800 bg-white/70 rounded-lg p-2 border border-amber-200/60">
              "{target.quote}"
            </blockquote>
          </motion.div>
        )}

        {/* Page Nav Bar */}
        <div className="flex items-center justify-between border-b border-slate-100 bg-white px-4 py-2">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
              disabled={currentPage <= 1}
              className="rounded p-1 text-slate-500 hover:bg-slate-100 disabled:opacity-40 cursor-pointer"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="font-mono text-xs text-slate-700">
              Page <span className="font-bold text-indigo-700">{currentPage}</span>
            </span>
            <button
              onClick={() => setCurrentPage((p) => p + 1)}
              className="rounded p-1 text-slate-500 hover:bg-slate-100 cursor-pointer"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 font-mono text-[11px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              <CheckCircle2 className="h-3 w-3" /> Zero Hallucination Audit Trail
            </span>
          </div>
        </div>

        {/* PDF Frame */}
        <div className="relative flex-1 bg-slate-100 flex items-center justify-center">
          {loadingPdf ? (
            <div className="flex flex-col items-center gap-3 text-slate-500">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
              <p className="font-mono text-xs">Authenticating and loading original PDF...</p>
            </div>
          ) : pdfError ? (
            <div className="flex flex-col items-center gap-2 text-rose-600 p-6 text-center max-w-sm">
              <AlertCircle className="h-8 w-8" />
              <p className="font-serif font-semibold text-sm">Document Preview Unavailable</p>
              <p className="text-xs text-slate-500">{pdfError}</p>
            </div>
          ) : blobUrl ? (
            <iframe
              key={`${activePdfSrc}-${currentPage}-${zoom}`}
              src={activePdfSrc}
              className="h-full w-full border-0"
              title="Evidence Source Document"
            />
          ) : null}
        </div>
      </motion.aside>
    </AnimatePresence>
  );
}
