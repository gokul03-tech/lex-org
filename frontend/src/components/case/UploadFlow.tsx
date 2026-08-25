import { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Check, Loader2, Upload } from 'lucide-react';
import apiClient from '@/lib/api';

interface IngestionStage {
  stage: string;
  label: string;
  status: 'pending' | 'in_progress' | 'completed';
  progress: number;
}

const INITIAL_STAGES: IngestionStage[] = [
  { stage: 'upload_complete', label: 'Upload Complete', status: 'pending', progress: 0 },
  { stage: 'reading_doc', label: 'Reading Document', status: 'pending', progress: 0 },
  { stage: 'metadata_extraction', label: 'Extracting Metadata', status: 'pending', progress: 0 },
  { stage: 'parsing_content', label: 'Parsing Legal Content', status: 'pending', progress: 0 },
  { stage: 'detecting_acts', label: 'Detecting Acts', status: 'pending', progress: 0 },
  { stage: 'detecting_sections', label: 'Detecting Sections', status: 'pending', progress: 0 },
  { stage: 'detecting_articles', label: 'Detecting Articles', status: 'pending', progress: 0 },
  { stage: 'detecting_parties', label: 'Detecting Parties', status: 'pending', progress: 0 },
  { stage: 'detecting_judges', label: 'Detecting Judges', status: 'pending', progress: 0 },
  { stage: 'chunking_document', label: 'Chunking Document', status: 'pending', progress: 0 },
  { stage: 'creating_embeddings', label: 'Creating Embeddings', status: 'pending', progress: 0 },
  { stage: 'searching_cases', label: 'Searching Similar Cases', status: 'pending', progress: 0 },
  { stage: 'building_graph', label: 'Building Knowledge Graph', status: 'pending', progress: 0 },
  { stage: 'multi_agent_reasoning', label: 'Multi-Agent Legal Reasoning', status: 'pending', progress: 0 },
  { stage: 'citation_validation', label: 'Citation Validation', status: 'pending', progress: 0 },
  { stage: 'confidence_calculation', label: 'Confidence Calculation', status: 'pending', progress: 0 },
  { stage: 'completed', label: 'Completed Successfully', status: 'pending', progress: 0 },
];

interface UploadFlowProps {
  caseId: string;
  hasStoredDocs?: boolean;
  onCompleted: () => void;
}

export function UploadFlow({ caseId, hasStoredDocs = false, onCompleted }: UploadFlowProps) {
  const [stages, setStages] = useState<IngestionStage[]>(INITIAL_STAGES);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);

  const uploadInFlightRef = useRef(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const startAnalysisStream = () => {
    eventSourceRef.current?.close();
    setAnalyzing(true);
    setStages(INITIAL_STAGES.map((s) => ({ ...s })));

    const eventSource = new EventSource(`/api/v1/analysis/case/${caseId}/stream`);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.stage === 'all_done') {
        eventSource.close();
        eventSourceRef.current = null;
        setAnalyzing(false);
        onCompleted();
      } else {
        setStages((prev) =>
          prev.map((stage) =>
            stage.stage === data.stage
              ? {
                  ...stage,
                  status: data.status === 'in_progress' ? 'in_progress' : 'completed',
                  progress: data.progress || 100,
                }
              : stage
          )
        );
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      eventSourceRef.current = null;
      setAnalyzing(false);
      onCompleted();
    };
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || uploadInFlightRef.current) return;
    uploadInFlightRef.current = true;

    setUploadingFile(true);
    setUploadProgress(10);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('case_id', caseId);
    formData.append('document_type', 'judgment');
    formData.append('description', 'Uploaded document for multi-agent legal analysis.');

    try {
      setUploadProgress(40);
      await apiClient.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploadProgress(100);
      setUploadingFile(false);
      startAnalysisStream();
    } catch (err) {
      console.error('Upload failed:', err);
      setUploadingFile(false);
      setUploadProgress(null);
    } finally {
      uploadInFlightRef.current = false;
    }
  };

  if (analyzing) {
    return (
      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto max-w-3xl space-y-6 rounded-2xl border border-slate-200/80 bg-white/80 p-7 shadow-md backdrop-blur-md"
      >
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-indigo-600" strokeWidth={2} />
            <h2 className="font-serif text-base font-semibold tracking-tight text-slate-900">
              Multi-Agent Processing Engine
            </h2>
          </div>
          <span className="font-mono text-[11px] uppercase tracking-wider text-slate-500">12 agents active</span>
        </div>

        <div className="grid gap-2.5 sm:grid-cols-2">
          {stages.map((stage) => (
            <div
              key={stage.stage}
              className={`flex items-center justify-between rounded-xl border p-3 text-[13px] transition-all ${
                stage.status === 'completed'
                  ? 'border-emerald-200 bg-emerald-50/70 font-medium text-emerald-800'
                  : stage.status === 'in_progress'
                  ? 'border-indigo-300 bg-indigo-50/70 font-semibold text-indigo-900 ring-2 ring-indigo-100'
                  : 'border-slate-100 bg-slate-50/50 text-slate-400'
              }`}
            >
              <div className="flex items-center gap-2.5">
                {stage.status === 'completed' ? (
                  <Check className="h-4 w-4 text-emerald-600" strokeWidth={3} />
                ) : stage.status === 'in_progress' ? (
                  <Loader2 className="h-4 w-4 animate-spin text-indigo-600" strokeWidth={2} />
                ) : (
                  <span className="ml-1 mr-3 h-1.5 w-1.5 rounded-full bg-slate-300" />
                )}
                <span>{stage.label}</span>
              </div>
              {stage.status === 'in_progress' && (
                <span className="font-mono text-[10px] font-bold text-indigo-700">{stage.progress}%</span>
              )}
            </div>
          ))}
        </div>
      </motion.section>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto flex max-w-2xl flex-col items-center gap-4 rounded-2xl border border-dashed border-slate-300 bg-white/70 px-8 py-14 text-center shadow-sm backdrop-blur-sm"
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-full border border-sky-100 bg-sky-50">
        <Upload className="h-6 w-6 animate-pulse text-sky-600" strokeWidth={1.6} />
      </div>
      <div className="space-y-1.5">
        <h2 className="font-serif text-xl font-semibold tracking-tight text-slate-900">
          Upload the legal dossier
        </h2>
        <p className="mx-auto max-w-md text-sm leading-relaxed text-slate-500">
          LexOrch-KG deterministically parses case briefs, constructs FalkorDB knowledge graphs,
          and runs twelve specialized reasoning agents.
        </p>
      </div>

      <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
        <label className="daylight-btn-primary inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl px-6 py-3 text-sm tracking-wide">
          {uploadingFile ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Uploading… {uploadProgress ?? 0}%
            </>
          ) : (
            <>Select Case Document · PDF, DOCX, TXT</>
          )}
          <input
            type="file"
            disabled={uploadingFile}
            accept=".pdf,.docx,.txt"
            onChange={handleFileUpload}
            className="hidden"
          />
        </label>

        {hasStoredDocs && (
          <button
            onClick={startAnalysisStream}
            className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-indigo-200 bg-white px-5 py-3 text-sm font-semibold text-indigo-700 shadow-sm transition hover:border-indigo-300 hover:bg-indigo-50"
          >
            Run AI Ingestion
          </button>
        )}
      </div>
    </motion.div>
  );
}
