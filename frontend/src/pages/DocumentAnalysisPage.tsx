import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
  BookOpen,
  Scale,
  Brain,
  MessageSquare,
  Sparkles,
  Layers
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ExtractedEntity {
  category: 'Act' | 'Section' | 'Article' | 'Citation';
  value: string;
  context: string;
}

interface Document {
  id: string;
  name: string;
  size: string;
  status: 'processing' | 'ready' | 'error';
  summary?: string;
  entities?: ExtractedEntity[];
}

export default function DocumentAnalysisPage() {
  const [documents, setDocuments] = useState<Document[]>([
    {
      id: '1',
      name: 'Maternity Benefit Act, 1961.pdf',
      size: '1.4 MB',
      status: 'ready',
      summary: 'This central statute regulates the employment of women in certain establishments for certain periods before and after child-birth and provides for maternity benefit and certain other benefits. It covers establishments employing 10 or more persons, providing payment at the rate of the average daily wage for the period of her actual absence.',
      entities: [
        { category: 'Act', value: 'Maternity Benefit Act, 1961', context: 'The short title of the primary statute.' },
        { category: 'Section', value: 'Section 4', context: 'Employment of, or work by, women prohibited during certain periods.' },
        { category: 'Section', value: 'Section 5', context: 'Right to payment of maternity benefit.' },
        { category: 'Citation', value: '1961 Act No. 53', context: 'Official gazette registry citation for the central act.' }
      ]
    }
  ]);

  const [activeDocId, setActiveDocId] = useState<string>('1');
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [docQuery, setDocQuery] = useState('');
  const [docAnswers, setDocAnswers] = useState<Record<string, string>>({});
  const [queryLoading, setQueryLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeDoc = documents.find(d => d.id === activeDocId);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFiles(e.dataTransfer.files);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFiles(e.target.files);
    }
  };

  const processFiles = (files: FileList) => {
    setUploading(true);
    setUploadProgress(10);
    
    // Simulate upload and background extraction pipeline
    const file = files[0];
    const newDocId = (documents.length + 1).toString();
    
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setUploading(false);
          setDocuments((prevDocs) => [
            ...prevDocs,
            {
              id: newDocId,
              name: file.name,
              size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
              status: 'ready',
              summary: `Analysis report for ${file.name}. The system successfully extracted statutory nodes and indexed clauses to Qdrant. A comprehensive legal abstract has been stored.`,
              entities: [
                { category: 'Act', value: 'Indian Penal Code', context: 'Extracted from references in text.' },
                { category: 'Section', value: 'Section 300', context: 'Definition of culpable homicide.' }
              ]
            }
          ]);
          setActiveDocId(newDocId);
          return 100;
        }
        return prev + 30;
      });
    }, 600);
  };

  const handleDocQuerySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!docQuery.trim() || !activeDocId) return;

    setQueryLoading(true);
    setTimeout(() => {
      const answers: Record<string, string> = {
        'payment': 'Maternity benefit is payable at the rate of the average daily wage. The maximum period for which any woman shall be entitled to maternity benefit shall be twelve weeks, of which not more than six weeks shall precede the date of her expected delivery.',
        'establishment': 'The Act applies to every factory, mine, or plantation (including any such establishment belonging to Government) and to every establishment wherein persons are employed for the exhibition of equestrian, acrobatic and other performances.'
      };
      
      const qLower = docQuery.toLowerCase();
      let match = 'The document does not explicitly outline details regarding your specific keyword. However, based on similar statutes, normal compliance guidelines apply.';
      
      if (qLower.includes('pay') || qLower.includes('wage') || qLower.includes('salary')) {
        match = answers['payment'];
      } else if (qLower.includes('establishment') || qLower.includes('apply') || qLower.includes('applies')) {
        match = answers['establishment'];
      }

      setDocAnswers(prev => ({ ...prev, [docQuery]: match }));
      setDocQuery('');
      setQueryLoading(false);
    }, 1200);
  };

  const handleDeleteDoc = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDocuments(prev => prev.filter(d => d.id !== id));
    if (activeDocId === id && documents.length > 1) {
      setActiveDocId(documents.find(d => d.id !== id)?.id || '');
    }
  };

  return (
    <div className="container mx-auto p-6 lg:p-8 flex flex-col h-[calc(100vh-4rem)] overflow-hidden">
      <div className="flex items-center gap-2 mb-6">
        <Layers className="h-5 w-5 text-primary" />
        <h1 className="text-2xl font-bold text-white">Document Analysis Workspace</h1>
      </div>

      <div className="grid gap-8 lg:grid-cols-3 flex-1 overflow-hidden">
        {/* Left Side: Upload Zone & Document Manager */}
        <div className="lg:col-span-1 flex flex-col gap-6 overflow-y-auto pr-2">
          {/* File Upload Zone */}
          <div
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            className={`relative rounded-xl border border-dashed p-6 text-center transition-all ${
              dragActive ? 'border-primary bg-primary/5' : 'border-white/10 bg-card/20 hover:border-white/20'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileChange}
              accept=".pdf,.docx,.html,.txt"
              className="hidden"
            />
            <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-3" />
            <p className="text-sm font-semibold text-white">Drag & drop files here</p>
            <p className="text-xs text-muted-foreground mt-1">Supports PDF, DOCX, HTML, TXT (Max 50MB)</p>
            <Button size="sm" onClick={triggerFileInput} className="mt-4 bg-secondary text-white hover:bg-secondary/80">
              Browse Files
            </Button>

            {uploading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center rounded-xl bg-background/90 p-4">
                <Loader2 className="h-6 w-6 animate-spin text-primary mb-2" />
                <span className="text-xs font-semibold text-white">Uploading & Parsing Document...</span>
                <div className="mt-3 h-1 w-32 rounded-full bg-secondary">
                  <div className="h-1 rounded-full bg-primary" style={{ width: `${uploadProgress}%` }}></div>
                </div>
              </div>
            )}
          </div>

          {/* Active Documents List */}
          <div className="rounded-xl border border-white/5 bg-card/20 p-4 flex-1 flex flex-col gap-3">
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Indexed Documents</h3>
            <div className="space-y-2 overflow-y-auto flex-1">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => setActiveDocId(doc.id)}
                  className={`flex items-center justify-between rounded-lg border p-3 cursor-pointer transition-all ${
                    activeDocId === doc.id
                      ? 'border-primary bg-primary/5'
                      : 'border-white/5 bg-white/5 hover:border-white/15'
                  }`}
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <FileText className={cn("h-4 w-4 shrink-0", activeDocId === doc.id ? "text-primary" : "text-muted-foreground")} />
                    <div className="flex flex-col text-left overflow-hidden">
                      <span className="truncate text-xs font-semibold text-white">{doc.name}</span>
                      <span className="text-[10px] text-muted-foreground">{doc.size}</span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteDoc(doc.id, e)}
                    className="text-muted-foreground hover:text-red-400 p-1 rounded transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Side: Extraction Reports & Context Q&A */}
        <div className="lg:col-span-2 flex flex-col gap-6 overflow-y-auto pl-2">
          {activeDoc ? (
            <>
              {/* Executive Summary */}
              <div className="rounded-xl border border-white/5 bg-card/20 p-6 space-y-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4.5 w-4.5 text-primary" />
                  <h2 className="text-base font-bold text-white">AI-Generated Legal Abstract</h2>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{activeDoc.summary}</p>
              </div>

              {/* Extracted Entity Tags */}
              <div className="rounded-xl border border-white/5 bg-card/20 p-6 space-y-4">
                <div className="flex items-center gap-2">
                  <Brain className="h-4.5 w-4.5 text-cyan-400" />
                  <h2 className="text-base font-bold text-white">Extracted Statutory Connections</h2>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {activeDoc.entities?.map((ent, idx) => (
                    <div key={idx} className="rounded-lg bg-white/5 border border-white/5 p-3 text-left">
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${
                          ent.category === 'Act' ? 'bg-blue-500/15 text-blue-400' : 'bg-cyan-500/15 text-cyan-400'
                        }`}>
                          {ent.category}
                        </span>
                        <span className="text-xs font-bold text-white">{ent.value}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">{ent.context}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Context Q&A Chat */}
              <div className="rounded-xl border border-white/5 bg-card/20 p-6 flex flex-col gap-4">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4.5 w-4.5 text-purple-400" />
                  <h2 className="text-base font-bold text-white">Ask Questions About Document</h2>
                </div>

                <div className="space-y-4 max-h-60 overflow-y-auto">
                  {Object.entries(docAnswers).map(([q, ans], idx) => (
                    <div key={idx} className="space-y-2 text-xs">
                      <div className="rounded-lg bg-primary/10 border border-primary/20 p-2.5 text-white max-w-[85%] ml-auto">
                        <strong>Q: </strong> {q}
                      </div>
                      <div className="rounded-lg bg-white/5 border border-white/5 p-3 text-muted-foreground leading-relaxed text-left max-w-[90%] mr-auto">
                        <strong>A: </strong> {ans}
                      </div>
                    </div>
                  ))}
                  {queryLoading && (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mr-auto">
                      <Loader2 className="h-3 w-3 animate-spin text-primary" />
                      Parsing document embeddings for matching answer...
                    </div>
                  )}
                </div>

                <form onSubmit={handleDocQuerySubmit} className="relative flex items-center mt-2">
                  <input
                    type="text"
                    value={docQuery}
                    onChange={(e) => setDocQuery(e.target.value)}
                    placeholder="Ask standard questions (e.g. what is the eligibility or applicability?)..."
                    className="w-full rounded-xl border border-white/5 bg-muted/40 py-2.5 pl-4 pr-24 text-xs text-white focus:outline-none"
                  />
                  <Button
                    type="submit"
                    size="sm"
                    className="absolute right-1.5 top-1.5 h-7.5 bg-primary px-3 text-xs hover:bg-primary/90"
                  >
                    Send Query
                  </Button>
                </form>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
              <AlertCircle className="h-8 w-8 text-muted-foreground mb-2" />
              <span>Select or upload a document to begin analysis reports.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
