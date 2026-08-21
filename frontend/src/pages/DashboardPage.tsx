import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Briefcase, FileText, CheckCircle2, Cpu, PlusCircle, Search, 
  ChevronRight, Clock, FolderOpen, X, Loader2, Sparkles, Scale, Info, Upload
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { LegalFeatureMarquee } from '@/components/ui/legal-feature-marquee';
import { CommandMenu } from '@/components/ui/command-menu';
import apiClient from '@/lib/api';

interface Case {
  id: string;
  title: string;
  description: string | null;
  case_type: string | null;
  status: string;
  created_at: string;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  
  // Create case form states
  const [newTitle, setNewTitle] = useState('');
  const [newClient, setNewClient] = useState('');
  const [newType, setNewType] = useState('Criminal Defense');
  const [newDesc, setNewDesc] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get('/cases/');
      setCases(res.data);
    } catch (err) {
      console.error('Error fetching cases:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile && !newTitle.trim()) return;

    setSubmitting(true);
    try {
      const formData = new FormData();
      if (selectedFile) {
        formData.append('file', selectedFile);
      }
      formData.append('title', newTitle || (selectedFile ? selectedFile.name.replace(/\.[^/.]+$/, "") : 'Untitled Matter'));
      formData.append('case_type', newType);
      formData.append('description', `Client: ${newClient}. ${newDesc}`);

      const res = await apiClient.post('/cases/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setCases((prev) => [res.data, ...prev]);
      setNewTitle('');
      setNewClient('');
      setNewDesc('');
      setSelectedFile(null);
      setCreateOpen(false);
      
      navigate(`/cases/${res.data.id}/analysis`);
    } catch (err) {
      console.error('Failed to create case:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const cleanTitle = (raw: string) => {
    if (!raw) return 'Untitled Case';
    return raw.replace(/\s+on\s+\d{1,2}\s+[A-Za-z]+,?\s+\d{4}.*$/i, '').trim();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'analysis_complete':
      case 'report_generated':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-700 border border-emerald-200">
            <span className="h-1 w-1 rounded-full bg-emerald-500" />
            Analysis Compiled
          </span>
        );
      case 'documents_uploaded':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2.5 py-0.5 text-[10px] font-semibold text-sky-700 border border-sky-200">
            <span className="h-1 w-1 rounded-full bg-sky-500" />
            Files Uploaded
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[10px] font-semibold text-amber-700 border border-amber-200">
            <span className="h-1 w-1 rounded-full bg-amber-500" />
            Draft
          </span>
        );
    }
  };

  const stats = [
    { label: 'Active Case Files', val: cases.length.toString(), desc: 'Case directories in progress', icon: Briefcase, color: 'text-sky-600', bg: 'bg-sky-50 border-sky-100' },
    { label: 'Ingestion Engine', val: 'Online', desc: 'Qdrant & FalkorDB connected', icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-100' },
    { label: 'AI Reasoning Core', val: 'Active', desc: 'DeepSeek-R1 & Qwen3 verified', icon: Cpu, color: 'text-indigo-600', bg: 'bg-indigo-50 border-indigo-100' },
  ];

  return (
    <div className="container mx-auto p-6 lg:p-10 space-y-8 text-left relative max-w-7xl">
      <CommandMenu />

      {/* Welcome Banner in Daylight Chambers theme */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white/90 p-8 shadow-xs backdrop-blur-md flex flex-col md:flex-row justify-between items-start md:items-center gap-6"
      >
        <div className="max-w-2xl space-y-2.5">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 border border-sky-200 px-3.5 py-1 text-xs font-semibold text-sky-700 shadow-2xs">
            <Sparkles className="h-3.5 w-3.5" />
            LexOrch-KG Legal Intelligence Core
          </span>
          <h1 className="font-serif text-3xl md:text-4xl font-bold tracking-tight text-slate-900">
            Advisor Command Center
          </h1>
          <p className="text-slate-600 text-sm leading-relaxed">
            Upload legal case briefs, inspect acts & sections, and generate interactive knowledge graphs. Select or initialize a case file to begin analysis.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            onClick={() => {
              const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
              document.dispatchEvent(event);
            }} 
            variant="outline"
            className="border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-mono text-xs px-3.5 py-5 rounded-2xl gap-2 cursor-pointer shadow-2xs"
          >
            <Search className="h-4 w-4 text-slate-400" />
            <span className="hidden sm:inline">Search (⌘K)</span>
          </Button>
          <Button 
            onClick={() => setCreateOpen(true)} 
            className="daylight-btn-primary px-5 py-5 text-xs rounded-2xl shrink-0 shadow-md gap-2 transition-all cursor-pointer font-semibold"
          >
            <PlusCircle className="h-4.5 w-4.5" /> Initialize Case File
          </Button>
        </div>
      </motion.div>

      {/* Metric Cards Row */}
      <div className="grid gap-5 sm:grid-cols-3">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-xs flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold text-slate-500 uppercase tracking-wider">{stat.label}</span>
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl border ${stat.bg} ${stat.color}`}>
                  <Icon className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4">
                <span className="font-serif text-3xl font-bold text-slate-900 tracking-tight">{stat.val}</span>
                <p className="text-xs text-slate-500 mt-1 font-medium">{stat.desc}</p>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Active Case Folders Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-serif text-lg font-bold text-slate-900 flex items-center gap-2">
            <FolderOpen className="h-5 w-5 text-sky-600" /> Active Legal Folders
          </h3>
          <Button
            variant="ghost"
            onClick={() => navigate('/cases')}
            className="text-xs font-semibold text-sky-700 hover:text-sky-800"
          >
            View All Dossiers →
          </Button>
        </div>

        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <Loader2 className="h-7 w-7 animate-spin text-sky-600" />
          </div>
        ) : cases.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500 shadow-xs">
            No active legal folders created yet. Click "Initialize Case File" above to get started.
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {cases.slice(0, 4).map((c) => (
              <motion.div
                key={c.id}
                whileHover={{ y: -3 }}
                onClick={() => navigate(`/cases/${c.id}/analysis`)}
                className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-xs hover:shadow-lg hover:border-slate-300 transition-all flex flex-col justify-between cursor-pointer text-left"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-slate-400 font-mono bg-slate-50 border border-slate-100 px-2 py-0.5 rounded-md">
                      {c.id}
                    </span>
                    {getStatusBadge(c.status)}
                  </div>
                  <div>
                    <h3 className="font-serif text-sm font-bold text-slate-900 group-hover:text-sky-700 transition-colors">
                      {cleanTitle(c.title)}
                    </h3>
                    <span className="text-[11px] text-slate-500 mt-1 block font-medium">
                      Category: {c.case_type || 'Unspecified'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">
                    {c.description || 'No detailed case facts uploaded yet. Open case brief folder to run AI ingestion.'}
                  </p>
                </div>

                <div className="mt-5 border-t border-slate-100 pt-3 flex items-center justify-between text-[11px] text-slate-400">
                  <span className="flex items-center gap-1 font-mono">
                    <Clock className="h-3 w-3" />
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                  <span className="flex items-center gap-0.5 font-bold text-sky-700 group-hover:translate-x-1 transition-transform">
                    {c.status === 'analysis_complete' ? 'Open Dashboard' : 'Start Analysis'}
                    <ChevronRight className="h-3.5 w-3.5" />
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Legal Architecture & Interactive Marquee Section */}
      <LegalFeatureMarquee />

      {/* CREATE NEW CASE DIALOG MODAL */}
      <AnimatePresence>
        {createOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setCreateOpen(false)}
              className="absolute inset-0 bg-slate-900/40 backdrop-blur-xs"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="relative w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl text-left z-10"
            >
              <button
                onClick={() => setCreateOpen(false)}
                className="absolute right-4 top-4 text-slate-400 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>

              <h2 className="font-serif text-xl font-bold text-slate-900 flex items-center gap-2">
                <Scale className="h-5 w-5 text-sky-600" />
                Initialize Legal Folder
              </h2>
              <p className="text-xs text-slate-500 mt-1">Define case matter coordinates before triggering AI ingestion pipeline.</p>

              <form onSubmit={handleCreateCase} className="mt-5 space-y-4 text-xs">
                <div>
                  <label className="font-mono text-[10px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">Upload Case Document (PDF, DOCX, TXT) *</label>
                  <div className="border border-dashed border-slate-300 rounded-2xl p-4 bg-slate-50/70 hover:bg-slate-50 transition text-center relative cursor-pointer">
                    <input
                      type="file"
                      accept=".pdf,.docx,.txt"
                      onChange={(e) => {
                        if (e.target.files?.[0]) {
                          const file = e.target.files[0];
                          setSelectedFile(file);
                          const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "").replace(/[_-]/g, " ");
                          setNewTitle(nameWithoutExt.charAt(0).toUpperCase() + nameWithoutExt.slice(1));
                        }
                      }}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    {selectedFile ? (
                      <div className="flex items-center justify-center gap-2 text-slate-800">
                        <FileText className="h-5 w-5 text-sky-600" />
                        <span className="font-bold truncate max-w-[240px]">{selectedFile.name}</span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-1.5 text-slate-500">
                        <Upload className="h-6 w-6 text-sky-600" />
                        <span className="font-medium">Drag & drop or click to choose file</span>
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <label className="font-mono text-[10px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">Case Title / Matter Reference</label>
                  <input
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="e.g. State vs. John Doe (Organized Cyber Fraud)"
                    className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-slate-900 focus:outline-none focus:border-sky-500 shadow-2xs"
                  />
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="font-mono text-[10px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">Client Name</label>
                    <input
                      type="text"
                      value={newClient}
                      onChange={(e) => setNewClient(e.target.value)}
                      placeholder="e.g. Vikram Dev"
                      className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-slate-900 focus:outline-none focus:border-sky-500 shadow-2xs"
                    />
                  </div>

                  <div>
                    <label className="font-mono text-[10px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">Category Type</label>
                    <select
                      value={newType}
                      onChange={(e) => setNewType(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-slate-900 focus:outline-none focus:border-sky-500 shadow-2xs"
                    >
                      <option value="Criminal Defense">Criminal Defense</option>
                      <option value="Cyber Crime Defense">Cyber Crime Defense</option>
                      <option value="Commercial Arbitration">Commercial Arbitration</option>
                      <option value="Constitutional Law">Constitutional Law</option>
                      <option value="Civil Dispute">Civil Dispute</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="font-mono text-[10px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">Brief Context / Notes</label>
                  <textarea
                    rows={3}
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="Add preliminary notes regarding charge sheet logs..."
                    className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-slate-900 focus:outline-none focus:border-sky-500 shadow-2xs resize-none"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)} className="text-slate-600 rounded-xl">
                    Cancel
                  </Button>
                  <Button type="submit" disabled={submitting} className="daylight-btn-primary px-5 py-2.5 rounded-xl font-semibold">
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Initialize Folder'}
                  </Button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
