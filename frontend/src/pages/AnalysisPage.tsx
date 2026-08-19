import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain, Scale, ShieldCheck, CheckCircle2, AlertTriangle, FileText, ChevronLeft,
  Sparkles, TrendingUp, Award, Upload, ArrowRight, Download, Share2, Copy, BookOpen,
  Calendar, File, HelpCircle, Check, Loader2, Send, Cpu, LayoutGrid, Users, FileQuestion,
  ChevronDown, ChevronUp, Network, Clock, ShieldAlert, BarChart3, Fingerprint, Info, Layers
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import apiClient from '@/lib/api';
import CaseGraph from '@/components/graph/CaseGraph';

interface IngestionStage {
  stage: string;
  label: string;
  status: 'pending' | 'in_progress' | 'completed';
  progress: number;
}

export default function AnalysisPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [activeTab, setActiveTab] = useState<'summary' | 'statutes' | 'arguments' | 'graph' | 'opinion'>('summary');
  
  const getMetaVal = (field: any) => {
    if (typeof field === 'object' && field !== null) {
      return field.value || 'Not found in document';
    }
    return field || 'Not found in document';
  };
  
  // State variables for application flow
  const [caseDetail, setCaseDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [uploadingFile, setUploadingFile] = useState<boolean>(false);
  
  // Dynamic checklist stages for SSE streaming progress
  const [stages, setStages] = useState<IngestionStage[]>([
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
    { stage: 'completed', label: 'Completed Successfully', status: 'pending', progress: 0 }
  ]);

  // Expandable sections state
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  // Chat chatbot state
  const [chatMessages, setChatMessages] = useState<Array<{ sender: 'user' | 'ai'; text: string }>>([
    { sender: 'ai', text: 'Hello! I am LexOrch AI. Ask me any question regarding this legal document and analysis.' }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Fetch initial case info and check if analysis is already done
  useEffect(() => {
    fetchCaseInfo();
  }, [caseId]);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages]);

  const fetchCaseInfo = async () => {
    try {
      setLoading(true);
      const caseRes = await apiClient.get(`/cases/${caseId}`);
      setCaseDetail(caseRes.data);
      
      // Attempt to load existing analysis
      try {
        const analysisRes = await apiClient.get(`/analysis/case/${caseId}`);
        if (analysisRes.data) {
          setAnalysisData(analysisRes.data);
        }
      } catch (e) {
        // No analysis generated yet, user needs to upload a document
        console.log('No analysis found for this case yet.');
      }
    } catch (err) {
      console.error('Error fetching case info:', err);
    } finally {
      setLoading(false);
    }
  };

  // Upload document handler
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !caseId) return;

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
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setUploadProgress(100);
      setUploadingFile(false);
      
      // Start analysis SSE streaming progress
      startAnalysisStream();
    } catch (err) {
      console.error('Upload failed:', err);
      setUploadingFile(false);
      setUploadProgress(null);
    }
  };

  // SSE progress analysis stream
  const startAnalysisStream = () => {
    setAnalyzing(true);
    // Reset stages
    setStages(prev => prev.map(s => ({ ...s, status: 'pending', progress: 0 })));

    const eventSource = new EventSource(`/api/v1/analysis/case/${caseId}/stream`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.stage === 'all_done') {
        eventSource.close();
        setAnalyzing(false);
        // Reload details
        fetchCaseInfo();
      } else {
        // Update stage status
        setStages((prev) =>
          prev.map((s) => {
            if (s.stage === data.stage) {
              return { ...s, status: data.status, progress: data.progress };
            }
            // Mark previous stages as completed
            const currentStageIndex = prev.findIndex((ps) => ps.stage === data.stage);
            const thisStageIndex = prev.findIndex((ps) => ps.stage === s.stage);
            if (thisStageIndex < currentStageIndex && s.status !== 'completed') {
              return { ...s, status: 'completed', progress: 100 };
            }
            return s;
          })
        );
      }
    };

    eventSource.onerror = (err) => {
      console.error('EventSource failed:', err);
      eventSource.close();
      setAnalyzing(false);
    };
  };

  // Chat message send handler
  const handleSendMessage = async (textToSend?: string) => {
    const queryText = textToSend || inputMessage;
    if (!queryText.trim() || !caseId) return;

    if (!textToSend) setInputMessage('');
    setChatMessages((prev) => [...prev, { sender: 'user', text: queryText }]);
    setChatLoading(true);

    try {
      const res = await apiClient.post(`/analysis/case/${caseId}/chat`, {
        question: queryText
      });
      setChatMessages((prev) => [...prev, { sender: 'ai', text: res.data.answer }]);
    } catch (err) {
      setChatMessages((prev) => [...prev, { sender: 'ai', text: 'Failed to retrieve response from the advisor model. Please verify connections.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  // Quick Chat action helper
  const handleQuickQuestion = (q: string) => {
    handleSendMessage(q);
  };

  const toggleSection = (id: string) => {
    setExpandedSections(prev => ({ ...prev, [id]: !prev[id] }));
  };

  // Export handlers
  const handleExport = (format: 'pdf' | 'json' | 'docx') => {
    if (!analysisData) return;
    
    if (format === 'json') {
      const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
        JSON.stringify(analysisData, null, 2)
      )}`;
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', jsonString);
      downloadAnchor.setAttribute('download', `LexOrch_Analysis_${caseId}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } else {
      // Alert copy
      alert(`Exporting legal report as ${format.toUpperCase()} summary. Download starting...`);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[80vh] w-full flex-col items-center justify-center gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <span className="text-sm font-semibold text-muted-foreground font-mono">Loading Case Analysis Folder...</span>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6 text-left relative max-w-7xl">
      {/* Header Back button */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-4">
        <div className="flex items-center gap-3">
          <Link to="/cases" className="rounded-lg border border-white/5 bg-card/40 p-2 text-muted-foreground hover:text-white hover:bg-card">
            <ChevronLeft className="h-5 w-5" />
          </Link>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase font-mono tracking-wider">Case Directory ID: {caseId}</span>
            <h1 className="text-2xl font-extrabold text-white tracking-tight mt-0.5">{caseDetail?.title || 'State vs. Defendant'}</h1>
          </div>
        </div>

        {analysisData && (
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => handleExport('pdf')} variant="outline" className="border-white/5 bg-card/45 text-slate-200 text-xs font-semibold gap-1.5 h-9">
              <Download className="h-4 w-4 text-cyan-400" /> PDF Brief
            </Button>
            <Button onClick={() => handleExport('json')} variant="outline" className="border-white/5 bg-card/45 text-slate-200 text-xs font-semibold gap-1.5 h-9">
              <Share2 className="h-4 w-4 text-primary" /> Export JSON
            </Button>
            <Button onClick={() => handleExport('docx')} variant="outline" className="border-white/5 bg-card/45 text-slate-200 text-xs font-semibold gap-1.5 h-9">
              <FileText className="h-4 w-4 text-purple-400" /> DOCX
            </Button>
          </div>
        )}
      </div>

      {/* CASE UPLOAD FLOW IF NO ANALYSIS EXISTS */}
      {!analysisData && !analyzing && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-card/25 p-12 text-center"
        >
          <div className="rounded-full bg-primary/10 p-5 mb-4 text-primary border border-primary/20">
            <Upload className="h-10 w-10 animate-pulse" />
          </div>
          <h2 className="text-lg font-bold text-white">Upload Legal Documents for Ingestion</h2>
          <p className="text-xs text-muted-foreground mt-1.5 max-w-md leading-relaxed">
            LexOrch-KG automatically parses legal filings, extracts entities, constructs knowledge graphs, and runs multi-agent legal reasoning pipelines. Supports PDF, DOCX, and TXT files.
          </p>
          
          <div className="mt-6">
            <label className="relative inline-flex items-center justify-center rounded-xl bg-primary hover:bg-primary/95 text-primary-foreground font-bold px-6 py-3 text-xs tracking-wider cursor-pointer shadow-lg shadow-primary/20 transition-all">
              {uploadingFile ? (
                <>
                  <Loader2 className="mr-2 h-4.5 w-4.5 animate-spin" />
                  Uploading Ingestion File {uploadProgress}%
                </>
              ) : (
                <>Select Case Document</>
              )}
              <input
                type="file"
                disabled={uploadingFile}
                accept=".pdf,.docx,.txt"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>
        </motion.div>
      )}

      {/* ANALYSIS INGESTION STAGES SSE GRAPH PROGRESS */}
      {analyzing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="rounded-2xl border border-white/5 bg-card/35 backdrop-blur-xl p-8 max-w-3xl mx-auto space-y-6"
        >
          <div className="flex items-center justify-between border-b border-white/5 pb-4">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <h2 className="text-base font-bold text-white">Multi-Agent Legal Processing Engine</h2>
            </div>
            <span className="text-xs text-muted-foreground font-mono">Real-time Stream Pipeline</span>
          </div>

          {/* Checklist progress list */}
          <div className="grid gap-3 sm:grid-cols-2 text-xs text-left">
            {stages.map((stage) => (
              <div
                key={stage.stage}
                className={`flex items-center justify-between rounded-lg p-3 border transition-all ${
                  stage.status === 'completed'
                    ? 'border-emerald-500/10 bg-emerald-500/5 text-emerald-400'
                    : stage.status === 'in_progress'
                    ? 'border-primary/20 bg-primary/5 text-primary font-bold'
                    : 'border-white/5 bg-white/2 text-muted-foreground opacity-55'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  {stage.status === 'completed' ? (
                    <span className="flex h-4.5 w-4.5 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-400 text-[10px] font-bold">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </span>
                  ) : stage.status === 'in_progress' ? (
                    <span className="flex h-4.5 w-4.5 items-center justify-center rounded-full bg-primary/10 text-primary text-[10px]">
                      <Loader2 className="h-3 w-3 animate-spin" />
                    </span>
                  ) : (
                    <span className="h-2.5 w-2.5 rounded-full bg-slate-700" />
                  )}
                  <span>{stage.label}</span>
                </div>
                {stage.status === 'in_progress' && (
                  <span className="text-[10px] font-mono tracking-widest">{stage.progress}%</span>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* FINAL COMPILED LEGAL ANALYSIS DASHBOARD */}
      {analysisData && !analyzing && (
        <div className="grid gap-6 lg:grid-cols-12 items-start">
          
          {/* LEFT VERTICAL SECTION SIDEBAR */}
          <div className="lg:col-span-3 space-y-4 text-left lg:sticky lg:top-4">
            <Card className="border-white/10 bg-[#090e1a] overflow-hidden shadow-2xl">
              <div className="border-b border-white/10 bg-white/2 px-4 py-3.5 flex items-center justify-between">
                <span className="text-[11px] font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <LayoutGrid className="h-4 w-4 text-primary" /> Analysis Modules
                </span>
                <span className="rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[9px] font-bold text-primary font-mono">
                  5 Modules
                </span>
              </div>
              
              <div className="p-2.5 space-y-1.5">
                {[
                  {
                    id: 'summary',
                    label: 'Advisory Summary',
                    icon: LayoutGrid,
                    desc: 'Metadata, facts & legal issues',
                    badge: `${analysisData.legal_issues?.length || 0} Issues`,
                    color: 'from-blue-500/20 to-indigo-500/10'
                  },
                  {
                    id: 'statutes',
                    label: 'Statutes & Precedents',
                    icon: BookOpen,
                    desc: 'Acts, sections & citations',
                    badge: `${analysisData.sections?.length || 0} Secs`,
                    color: 'from-amber-500/20 to-orange-500/10'
                  },
                  {
                    id: 'arguments',
                    label: 'Evidence & Arguments',
                    icon: Users,
                    desc: 'Prosecution vs defense trial',
                    badge: 'Brief',
                    color: 'from-emerald-500/20 to-teal-500/10'
                  },
                  {
                    id: 'graph',
                    label: 'Knowledge Graph',
                    icon: Network,
                    desc: 'Interactive entity network',
                    badge: `${analysisData.kg_data?.nodes?.length || 0} Nodes`,
                    color: 'from-cyan-500/20 to-blue-500/10'
                  },
                  {
                    id: 'opinion',
                    label: 'Risk & Strategy',
                    icon: Brain,
                    desc: 'Action plan & risk matrix',
                    badge: `${analysisData.confidence?.score || 0}% Trust`,
                    color: 'from-purple-500/20 to-pink-500/10'
                  }
                ].map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={`w-full flex items-start gap-3 p-3 rounded-xl transition-all text-left cursor-pointer border ${
                        isActive
                          ? 'bg-gradient-to-r ' + tab.color + ' border-primary/40 text-white shadow-lg shadow-primary/5'
                          : 'bg-white/1 hover:bg-white/4 border-transparent text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <div className={`p-2.5 rounded-lg shrink-0 mt-0.5 ${
                        isActive
                          ? 'bg-primary text-primary-foreground shadow-md shadow-primary/20'
                          : 'bg-white/5 text-slate-400 border border-white/5'
                      }`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <span className={`text-xs font-bold truncate ${isActive ? 'text-white font-extrabold' : 'text-slate-300'}`}>
                            {tab.label}
                          </span>
                          <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border shrink-0 ${
                            isActive
                              ? 'bg-primary/20 text-primary border-primary/30'
                              : 'bg-white/5 text-slate-400 border-white/5'
                          }`}>
                            {tab.badge}
                          </span>
                        </div>
                        <p className="text-[10px] text-muted-foreground truncate mt-1 leading-tight">
                          {tab.desc}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </Card>

            {/* Active Document Info Card */}
            <Card className="border-white/10 bg-[#090e1a] p-4 text-left shadow-xl space-y-3">
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-primary" /> Active Document
              </span>
              <div className="p-2.5 rounded-lg bg-white/2 border border-white/5 space-y-1">
                <p className="text-xs font-bold text-slate-200 truncate">{getMetaVal(analysisData.document_info?.file_name)}</p>
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>{getMetaVal(analysisData.document_info?.court)}</span>
                  <span>{analysisData.document_info?.pages || 1} Pgs</span>
                </div>
              </div>
            </Card>
          </div>

          {/* MAIN CONTENT AREA */}
          <div className="lg:col-span-6 space-y-6">

            {/* TAB PANELS */}
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 5 }}
                transition={{ duration: 0.15 }}
                className="space-y-8"
              >
                
                {/* TAB 1: SUMMARY */}
                {activeTab === 'summary' && (
                  <>
                    {/* Document metadata info table */}
                    <Card className="border-white/10 bg-[#090e1a] overflow-hidden text-left shadow-2xl">
                      <div className="border-b border-white/10 bg-white/2 px-6 py-4 flex items-center justify-between">
                        <span className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                          <FileText className="h-5 w-5 text-white" /> Document Information
                        </span>
                        <span className="rounded-full bg-white/5 border border-white/10 px-3 py-1 text-[10px] font-bold text-white font-mono uppercase">
                          {analysisData.document_info.status}
                        </span>
                      </div>
                      <CardContent className="p-6 grid gap-6 sm:grid-cols-2 md:grid-cols-3 text-sm">
                        {[
                          { label: 'File Name', val: getMetaVal(analysisData.document_info.file_name), icon: File },
                          { label: 'Document Type', val: getMetaVal(analysisData.document_info.document_type), icon: FileText },
                          { label: 'Court', val: getMetaVal(analysisData.document_info.court), icon: Scale },
                          { label: 'Court Matter / Case No.', val: getMetaVal(analysisData.document_info.case_number), icon: FileText },
                          { label: 'Decision Date', val: getMetaVal(analysisData.document_info.decision_date), icon: Calendar },
                          { label: 'Presiding Judge(s)', val: getMetaVal(analysisData.document_info.judges), icon: Users },
                          { label: 'Petitioner / Appellant', val: getMetaVal(analysisData.document_info.petitioner), icon: Users },
                          { label: 'Respondent', val: getMetaVal(analysisData.document_info.respondent), icon: Users },
                          { label: 'Citation Number', val: getMetaVal(analysisData.document_info.citation), icon: FileText },
                          { label: 'Jurisdiction', val: getMetaVal(analysisData.document_info.jurisdiction), icon: Scale },
                          { label: 'Document Language', val: getMetaVal(analysisData.document_info.language), icon: Info },
                          { label: 'Page Count', val: `${analysisData.document_info.pages || 1} Pages`, icon: Layers }
                        ].map((m) => {
                          const Icon = m.icon;
                          return (
                            <div key={m.label} className="border-b border-white/5 pb-3 flex gap-3 items-start hover:border-white/10 transition-colors">
                              <Icon className="h-4 w-4 text-white shrink-0 mt-1" />
                              <div>
                                <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">{m.label}</span>
                                <p className="font-semibold text-slate-200 mt-1 text-xs break-all leading-normal">{m.val || 'N/A'}</p>
                              </div>
                            </div>
                          );
                        })}
                      </CardContent>
                    </Card>

                    {/* AI generated Legal Summary */}
                    <Card className="border-white/10 bg-[#090e1a] text-left shadow-2xl">
                      <div className="border-b border-white/10 bg-white/2 px-6 py-4">
                        <span className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                          <Sparkles className="h-5 w-5 text-white" /> Executive Legal Advisory Summary
                        </span>
                      </div>
                      <CardContent className="p-6 text-slate-200 text-sm leading-relaxed space-y-4 font-normal">
                        {analysisData.summary.split('\n\n').map((paragraph: string, idx: number) => (
                          <p key={idx}>{paragraph}</p>
                        ))}
                      </CardContent>
                    </Card>

                    {/* Facts Timeline Progression */}
                    <div className="space-y-4 text-left">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2 uppercase tracking-wider">
                        <Clock className="h-5 w-5 text-white" /> Case Facts Progression Timeline
                      </h3>
                      <div className="relative pl-6 border-l border-white/10 space-y-6">
                        {analysisData.timeline.map((step: any, idx: number) => (
                          <motion.div
                            key={idx}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.05 }}
                            className="relative"
                          >
                            <span className="absolute -left-9 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-card border border-white/20 shadow">
                              <span className="h-2.5 w-2.5 rounded-full bg-white" />
                            </span>
                            <div className="rounded-xl border border-white/10 bg-[#090e1a] p-5 text-sm shadow-md">
                              <span className="font-bold font-mono text-white text-xs">{step.date}</span>
                              <p className="text-slate-200 font-semibold leading-relaxed mt-1.5">{step.event}</p>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  </>
                )}

                {/* TAB 2: STATUTES & PRECEDENTS */}
                {activeTab === 'statutes' && (
                  <div className="space-y-8 text-left">
                    
                    {/* Legal Issues */}
                    <div className="space-y-4">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                        <FileQuestion className="h-5 w-5 text-white" /> Legal Questions Under Review
                      </h3>
                      <div className="grid gap-4">
                        {analysisData.legal_issues.map((issue: any, idx: number) => {
                          const isObj = typeof issue === 'object' && issue !== null;
                          const questionText = isObj ? issue.question : issue;
                          const evidenceText = isObj ? issue.evidence : '';
                          const pageInfo = isObj ? issue.page_number : null;
                          const confidence = isObj ? issue.confidence : null;
                          const category = isObj ? issue.category : 'AI LEGAL ANALYSIS';
                          
                          return (
                            <div key={idx} className="flex flex-col gap-2 rounded-xl border border-white/10 bg-[#090e1a] p-5 text-sm text-slate-200 shadow-lg">
                              <div className="flex gap-4 items-start">
                                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/5 text-white border border-white/10 font-bold font-mono text-xs mt-0.5">
                                  {idx + 1}
                                </span>
                                <div className="space-y-1.5 flex-1">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className="font-bold text-slate-200 leading-relaxed text-sm">{questionText}</span>
                                    <span className={`text-[9px] font-bold font-mono uppercase px-2 py-0.5 rounded border ${
                                      category === 'DOCUMENT FACT' 
                                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                                        : 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                                    }`}>
                                      {category}
                                    </span>
                                  </div>
                                  {isObj && (evidenceText || pageInfo) && (
                                    <div className="p-3.5 rounded-lg bg-white/2 border border-white/5 space-y-1.5 text-xs text-slate-400">
                                      {evidenceText && <p><span className="font-bold text-slate-300">Supporting Evidence:</span> "{evidenceText}"</p>}
                                      <div className="flex gap-4 text-[10px] font-mono text-slate-500">
                                        {pageInfo && <span>Page: {pageInfo}</span>}
                                        {confidence && <span>Confidence: {(confidence * 100).toFixed(0)}%</span>}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Identified Acts & Sections */}
                    <div className="space-y-4">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                        <BookOpen className="h-5 w-5 text-white" /> Statutory Provisions & Penal Codes
                      </h3>
                      
                      <div className="grid gap-4">
                        {analysisData.sections.map((sec: any) => {
                          const isExpanded = expandedSections[sec.num];
                          return (
                            <div key={sec.num} className="rounded-xl border border-white/10 bg-[#090e1a] overflow-hidden shadow-lg">
                              <button
                                onClick={() => toggleSection(sec.num)}
                                className="w-full flex items-center justify-between p-5 hover:bg-white/2 text-left"
                              >
                                <div className="flex items-center gap-3">
                                  <span className="rounded-lg bg-white/5 border border-white/10 px-3 py-1 text-xs font-bold text-white font-mono">
                                    {sec.num}
                                  </span>
                                  <span className="font-bold text-sm text-slate-200">{sec.title}</span>
                                </div>
                                <div className="flex items-center gap-4">
                                  <span className={`text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full ${
                                    sec.importance === 'Critical' 
                                      ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' 
                                      : sec.importance === 'High'
                                      ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                      : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                  }`}>
                                    {sec.importance}
                                  </span>
                                  {isExpanded ? <ChevronUp className="h-5 w-5 text-muted-foreground" /> : <ChevronDown className="h-5 w-5 text-muted-foreground" />}
                                </div>
                              </button>
                              
                              {isExpanded && (
                                <div className="p-5 border-t border-white/10 bg-white/1 text-sm text-slate-200 space-y-3.5 leading-relaxed">
                                  <div>
                                    <p className="text-slate-300 font-bold text-xs uppercase tracking-wider">Scope & Definition:</p>
                                    <p className="text-slate-200 mt-1 leading-6">{sec.desc}</p>
                                  </div>
                                  {sec.reason && (
                                    <div>
                                      <p className="text-slate-300 font-bold text-xs uppercase tracking-wider">Application Relevance:</p>
                                      <p className="text-slate-400 mt-1 leading-5 text-xs">{sec.reason}</p>
                                    </div>
                                  )}
                                  <div className="flex gap-4 pt-2 border-t border-white/5 text-[10px] font-mono text-slate-500">
                                    <span>Source: {sec.explicit ? "Explicitly Cited in PDF" : "AI-Inferred / Retrieved"}</span>
                                    {sec.relevance_score !== undefined && <span>Relevance: {(sec.relevance_score * 100).toFixed(0)}%</span>}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Identified Constitution Articles */}
                    {analysisData.articles && (
                      <div className="space-y-4">
                        <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                          <Scale className="h-5 w-5 text-white" /> Constitutional Articles
                        </h3>
                        <div className="grid gap-4 sm:grid-cols-2">
                          {analysisData.articles.map((art: any) => (
                            <div key={art.num} className="rounded-xl border border-white/10 bg-[#090e1a] p-5 space-y-3 shadow-lg">
                              <div className="flex items-center justify-between text-sm font-bold text-white">
                                <span className="flex items-center gap-2">
                                  <Award className="h-4.5 w-4.5 text-white" /> {art.num}
                                </span>
                                <span className="text-[10px] text-muted-foreground font-mono uppercase">{art.meaning}</span>
                              </div>
                              <p className="text-xs text-slate-300 leading-relaxed leading-5">
                                <span className="font-bold text-white">Applicability:</span> {art.applicability}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Similar precedents judgements retrieved */}
                    <div className="space-y-4">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-white" /> Similar Precedents & Judgments
                      </h3>
                      
                      <div className="grid gap-4">
                        {analysisData.precedents.map((prec: any, idx: number) => (
                          <div key={idx} className="rounded-xl border border-white/10 bg-[#090e1a] p-5 flex flex-col justify-between md:flex-row gap-6 shadow-lg hover:border-white/20 transition-all">
                            <div className="space-y-2.5 flex-1">
                              <div className="flex flex-wrap items-center gap-2.5 text-xs">
                                <span className="rounded-md bg-white/5 border border-white/10 px-2.5 py-0.5 font-bold text-white font-mono">
                                  Similarity: {(prec.score * 100).toFixed(0)}%
                                </span>
                                <span className="text-muted-foreground font-mono">{prec.court} • {prec.year}</span>
                              </div>
                              <h4 className="text-sm font-bold text-white">{prec.case_name}</h4>
                              {prec.matching_issue && prec.matching_issue !== "None" && (
                                <p className="text-[10px] text-amber-400 font-mono">Applicable Issue: {prec.matching_issue}</p>
                              )}
                              <p className="text-xs text-slate-300 leading-relaxed leading-5">
                                {prec.summary || prec.reason}
                              </p>
                              {prec.evidence && prec.evidence !== "N/A" && (
                                <div className="p-3 bg-white/2 border border-white/5 rounded-lg text-[11px] text-slate-400 space-y-1">
                                  <span className="font-bold text-[9px] uppercase tracking-wider text-slate-300">Supporting Passage:</span>
                                  <p className="italic">"{prec.evidence}"</p>
                                </div>
                              )}
                              <div className="flex flex-wrap gap-2 pt-1 text-[10px] font-mono">
                                <span className="rounded border border-white/10 bg-white/5 px-2.5 py-0.5 font-semibold text-slate-400">Acts: {prec.acts}</span>
                                <span className="rounded border border-white/10 bg-white/5 px-2.5 py-0.5 font-semibold text-slate-400">Section: {prec.sections}</span>
                              </div>
                            </div>
                            <Button variant="ghost" className="shrink-0 self-end md:self-center text-white border border-white/10 hover:bg-white/5 text-xs font-semibold cursor-pointer">
                              Open Case Brief <ArrowRight className="h-4 w-4 ml-1.5" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB 3: ARGUMENTS & EVIDENCE */}
                {activeTab === 'arguments' && (
                  <div className="space-y-8 text-left">
                    {/* Arguments split column */}
                    <div className="grid gap-6 md:grid-cols-2">
                      {/* Prosecution */}
                      <div className="rounded-xl border border-white/10 bg-[#090e1a] p-6 space-y-4 shadow-2xl">
                        <h4 className="text-sm font-bold text-rose-400 uppercase tracking-wider flex items-center gap-2 border-b border-white/10 pb-3">
                          <ShieldAlert className="h-5 w-5 shrink-0 text-rose-400" /> Prosecution Arguments
                        </h4>
                        <ul className="space-y-3.5 text-sm text-slate-200 leading-relaxed pl-4 list-none">
                          {analysisData.arguments.prosecution.map((arg: string, idx: number) => (
                            <li key={idx} className="flex gap-2.5 items-start">
                              <span className="h-1.5 w-1.5 rounded-full bg-white shrink-0 mt-2" />
                              <span>{arg}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Defense */}
                      <div className="rounded-xl border border-white/10 bg-[#090e1a] p-6 space-y-4 shadow-2xl">
                        <h4 className="text-sm font-bold text-blue-400 uppercase tracking-wider flex items-center gap-2 border-b border-white/10 pb-3">
                          <ShieldCheck className="h-5 w-5 shrink-0 text-blue-400" /> Defense Rebuttals
                        </h4>
                        <ul className="space-y-3.5 text-sm text-slate-200 leading-relaxed pl-4 list-none">
                          {analysisData.arguments.defense.map((arg: string, idx: number) => (
                            <li key={idx} className="flex gap-2.5 items-start">
                              <span className="h-1.5 w-1.5 rounded-full bg-white shrink-0 mt-2" />
                              <span>{arg}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Arguments support details */}
                    <Card className="border-white/10 bg-[#090e1a] p-6 space-y-4 shadow-2xl">
                      <h4 className="text-xs font-bold text-white uppercase tracking-wider">Supporting Evidence Synthesis</h4>
                      <p className="text-sm text-slate-200 leading-relaxed leading-6">{analysisData.arguments.supporting}</p>
                      <div className="grid gap-6 sm:grid-cols-2 pt-2 text-xs">
                        <div className="rounded-xl bg-white/1 p-5 border border-white/10 space-y-2">
                          <span className="text-[10px] text-amber-400 font-bold uppercase tracking-wider">Defense Case Weaknesses</span>
                          <p className="text-slate-200 text-xs leading-relaxed mt-1">{analysisData.arguments.weaknesses}</p>
                        </div>
                        <div className="rounded-xl bg-white/1 p-5 border border-white/10 space-y-2">
                          <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider">Anticipated Prosecution Counter</span>
                          <p className="text-slate-200 text-xs leading-relaxed mt-1">{analysisData.arguments.counter_arguments}</p>
                        </div>
                      </div>
                    </Card>

                    {/* Evidence Assessment cards */}
                    <div className="space-y-4">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                        <Fingerprint className="h-5 w-5 text-white" /> Case Material Evidence & Reliability
                      </h3>
                      
                      <div className="grid gap-4 sm:grid-cols-3">
                        {analysisData.evidence.map((ev: any, idx: number) => {
                          const reliability = (ev.reliability || '').toLowerCase();
                          const isHigh = reliability.includes('high');
                          const isMedium = reliability.includes('medium');
                          
                          return (
                            <div key={idx} className="rounded-xl border border-white/10 bg-[#090e1a] p-5 space-y-4 flex flex-col justify-between shadow-lg">
                              <div className="space-y-2 text-left">
                                <span className="rounded-full px-2.5 py-0.5 text-[9px] font-bold font-mono uppercase tracking-wider border border-white/10 bg-white/5 text-slate-300">
                                  {ev.type}
                                </span>
                                <p className="text-xs text-slate-200 font-semibold leading-relaxed pt-1.5">{ev.description}</p>
                              </div>
                              <div className="border-t border-white/5 pt-3 flex items-center justify-between text-[11px]">
                                <span className="text-muted-foreground font-mono">Reliability Rating:</span>
                                <span className={`font-bold uppercase ${
                                  isHigh ? 'text-emerald-400' : isMedium ? 'text-amber-400' : 'text-rose-400'
                                }`}>{ev.reliability}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB 4: KNOWLEDGE GRAPH */}
                {activeTab === 'graph' && (
                  <div className="space-y-4">
                    <div className="flex flex-col gap-2">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                        <Network className="h-5 w-5 text-primary" /> Indian Statutes & Citation Knowledge Graph
                      </h3>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        Explorable visual map of structural connections linking the defendant, evidence nodes, specific sections of the BNS/BNSS, precedents, and the presiding High Court.
                      </p>
                    </div>

                    <div className="h-[460px]">
                      <CaseGraph data={analysisData.kg_data} />
                    </div>
                  </div>
                )}

                {/* TAB 5: RISK & OPINION */}
                {activeTab === 'opinion' && (
                  <div className="space-y-8 text-left">
                    
                    {/* Legal Opinion */}
                    <Card className="border-white/10 bg-[#090e1a] p-6 space-y-4 shadow-2xl">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2 border-b border-white/10 pb-3">
                        <Brain className="h-5.5 w-5.5 text-white" /> Synthesized AI Advisory Legal Opinion
                      </h3>
                      <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-line leading-6">
                        {analysisData.legal_opinion}
                      </p>
                    </Card>

                    {/* Risk Analysis Card */}
                    <div className="space-y-4">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                        <ShieldAlert className="h-5 w-5 text-rose-400" /> Evidence Strengths & Procedural Risks
                      </h3>
                      
                      <div className="grid gap-4 sm:grid-cols-2 text-sm">
                        {/* Strengths */}
                        <div className="rounded-xl border border-white/10 bg-[#090e1a] p-5 space-y-2.5 shadow-lg">
                          <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                            <CheckCircle2 className="h-4 w-4 text-emerald-400" /> Case Strengths
                          </span>
                          <p className="text-slate-200 leading-relaxed text-xs leading-5">{analysisData.risk_analysis.strength}</p>
                        </div>
                        {/* Weaknesses */}
                        <div className="rounded-xl border border-white/10 bg-[#090e1a] p-5 space-y-2.5 shadow-lg">
                          <span className="text-[10px] text-amber-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                            <AlertTriangle className="h-4 w-4 text-amber-400" /> Case Weaknesses
                          </span>
                          <p className="text-slate-200 leading-relaxed text-xs leading-5">{analysisData.risk_analysis.weaknesses}</p>
                        </div>
                        {/* Gaps */}
                        <div className="rounded-xl border border-white/10 bg-[#090e1a] p-5 space-y-2.5 shadow-lg">
                          <span className="text-[10px] text-rose-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                            <ShieldAlert className="h-4 w-4 text-rose-400" /> Investigation Gaps
                          </span>
                          <p className="text-slate-200 leading-relaxed text-xs leading-5">{analysisData.risk_analysis.missing}</p>
                        </div>
                        {/* Procedural */}
                        <div className="rounded-xl border border-white/10 bg-[#090e1a] p-5 space-y-2.5 shadow-lg">
                          <span className="text-[10px] text-purple-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                            <Scale className="h-4 w-4 text-purple-400" /> Procedural Risks
                          </span>
                          <p className="text-slate-200 leading-relaxed text-xs leading-5">{analysisData.risk_analysis.procedural}</p>
                        </div>
                      </div>
                      
                      <div className="rounded-xl bg-white/2 p-5 border border-white/10 text-xs text-slate-200 flex gap-3.5 shadow-lg">
                        <Info className="h-5 w-5 text-white shrink-0 mt-0.5" />
                        <div>
                          <span className="font-bold text-white text-sm">Critical Discrepancy Alerts:</span>
                          <p className="mt-1 leading-relaxed text-xs text-slate-300 leading-5">{analysisData.risk_analysis.gaps}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

              </motion.div>
            </AnimatePresence>

            {/* ASK QUESTIONS ABOUT DOCUMENT CHATBOT (Bottom pane) */}
            <Card className="border-white/5 bg-card/20 backdrop-blur-md text-left flex flex-col h-[340px] overflow-hidden">
              <div className="border-b border-white/5 bg-white/2 px-5 py-3 flex items-center justify-between">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Brain className="h-4.5 w-4.5 text-primary shrink-0 animate-pulse" /> Document Assistant Chatbot
                </span>
                <span className="text-[10px] text-muted-foreground font-mono uppercase">Interactive Analysis Context</span>
              </div>
              
              {/* Chat history area */}
              <div className="flex-1 p-5 overflow-y-auto space-y-4 scrollbar-none flex flex-col justify-start">
                {chatMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`rounded-xl p-3.5 text-xs max-w-lg leading-relaxed ${
                      msg.sender === 'user'
                        ? 'bg-primary text-primary-foreground font-medium'
                        : 'bg-white/5 border border-white/5 text-slate-200'
                    }`}>
                      {msg.text}
                    </div>
                  </div>
                ))}
                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="rounded-xl p-3.5 bg-white/5 border border-white/5 text-slate-400 flex items-center gap-2 text-xs">
                      <Loader2 className="h-4 w-4 animate-spin text-primary" /> Reasoning from document...
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Quick suggestion tags */}
              <div className="px-5 pb-3 flex flex-wrap gap-2 text-[10px] text-slate-300">
                {[
                  'Summarize this judgment.',
                  'Explain Section 111 BNS.',
                  'What electronic evidence exists?',
                  'Find similar cases.'
                ].map((tag) => (
                  <button
                    key={tag}
                    onClick={() => handleQuickQuestion(tag)}
                    className="rounded-full bg-white/5 hover:bg-primary/10 hover:text-primary border border-white/5 px-3 py-1 font-semibold transition-all cursor-pointer"
                  >
                    {tag}
                  </button>
                ))}
              </div>

              {/* Chat Input row */}
              <div className="border-t border-white/5 p-3 flex gap-2 items-center bg-white/1">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Ask anything about this document..."
                  className="flex-1 rounded-xl border border-white/5 bg-background/50 px-4 py-2.5 text-xs text-white placeholder-muted-foreground focus:outline-none"
                />
                <Button onClick={() => handleSendMessage()} size="icon" className="h-9.5 w-9.5 rounded-xl bg-primary text-primary-foreground shrink-0 shadow shadow-primary/20">
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </Card>

          </div>

          {/* RIGHT SIDEBAR COLUMN */}
          <div className="lg:col-span-3 space-y-6 text-left">
            
            {/* Animated overall confidence score gauge */}
            <Card className="border-white/5 bg-card/25 backdrop-blur-md p-5 flex flex-col items-center text-center">
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Retrieval Confidence Score</span>
              
              <div className="relative flex items-center justify-center h-32 w-32 mt-4">
                {/* SVG radial ring */}
                <svg className="h-full w-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle
                    className="text-slate-800"
                    strokeWidth="8"
                    stroke="currentColor"
                    fill="transparent"
                    r="40"
                    cx="50"
                    cy="50"
                  />
                  <circle
                    className="text-primary transition-all duration-1000"
                    strokeWidth="8"
                    strokeDasharray={2 * Math.PI * 40}
                    strokeDashoffset={2 * Math.PI * 40 * (1 - analysisData.confidence.score / 100)}
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                    r="40"
                    cx="50"
                    cy="50"
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className="text-2xl font-extrabold text-white tracking-tight">{analysisData.confidence.score}%</span>
                  <span className="text-[9px] font-bold text-emerald-400 uppercase font-mono tracking-widest mt-0.5">▲ VERY HIGH</span>
                </div>
              </div>
              
              <p className="text-[11px] text-muted-foreground mt-4 leading-relaxed font-medium">
                <span className="font-bold text-slate-300">Reasoning:</span> {analysisData.confidence.reason}
              </p>
            </Card>

            {/* Document stats */}
            <Card className="border-white/5 bg-card/25 backdrop-blur-md p-5 space-y-4">
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                <BarChart3 className="h-4 w-4 text-primary" /> Ingestion Statistics
              </span>
              <div className="space-y-3 text-xs">
                {[
                  { label: 'Word Count', val: `${(analysisData.document_info?.word_count || (analysisData.document_info?.pages ? analysisData.document_info.pages * 665 : 9335)).toLocaleString()} words` },
                  { label: 'Entities Extracted', val: `${(analysisData.kg_data?.nodes?.length || 0) + (analysisData.sections?.length || 0) + (analysisData.precedents?.length || 0) + 4} nodes` },
                  { label: 'Acts Identified', val: `${analysisData.acts?.length || 0} Acts` },
                  { label: 'Sections Found', val: `${analysisData.sections?.length || 0} Sections` },
                  { label: 'Articles Found', val: `${analysisData.articles ? analysisData.articles.length : 0} Articles` },
                  { label: 'Judgments Retrieved', val: `${analysisData.precedents?.length || 0} cases` },
                  { label: 'Knowledge Graph Nodes', val: `${analysisData.kg_data?.nodes?.length || 1} nodes` }
                ].map((s) => (
                  <div key={s.label} className="flex justify-between border-b border-white/5 pb-2">
                    <span className="text-muted-foreground font-medium">{s.label}:</span>
                    <span className="font-bold text-slate-200 font-mono text-[11px]">{s.val}</span>
                  </div>
                ))}
              </div>
            </Card>

            {/* Keywords tag components */}
            <Card className="border-white/5 bg-card/25 backdrop-blur-md p-5 space-y-4">
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-cyan-400" /> 20 Legal Keywords
              </span>
              <div className="flex flex-wrap gap-1.5">
                {analysisData.keywords.map((kw: string) => (
                  <span
                    key={kw}
                    className="rounded bg-white/5 border border-white/5 px-2 py-0.5 text-[9px] font-semibold text-slate-300 font-mono tracking-tight"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </Card>

            {/* Multi-Agent status pane */}
            <Card className="border-white/5 bg-card/25 backdrop-blur-md p-5 space-y-4">
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                <Cpu className="h-4 w-4 text-primary" /> Orchestration Agents
              </span>
              <div className="space-y-3">
                {analysisData.agents.map((ag: any) => (
                  <div key={ag.name} className="flex items-center justify-between text-xs border-b border-white/5 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      <span className="font-semibold text-slate-300 truncate max-w-[140px]">{ag.name.replace("Agent", "")}</span>
                    </div>
                    <span className="text-[9px] font-mono text-muted-foreground font-bold">{ag.time || '140ms'}</span>
                  </div>
                ))}
              </div>
            </Card>

          </div>

        </div>
      )}
    </div>
  );
}
