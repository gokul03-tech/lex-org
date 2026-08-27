import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  FileText, ChevronRight, Clock, FolderOpen, X, Loader2,
  Scale, Upload, ArrowRight, Plus,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { CommandMenu } from '@/components/ui/command-menu';
import { LegalFeatureMarquee } from '@/components/ui/legal-feature-marquee';
import apiClient from '@/lib/api';
import { Trash2 } from 'lucide-react';

interface Case {
  id: string;
  title: string;
  description: string | null;
  case_type: string | null;
  status: string;
  created_at: string;
}

const CASE_TYPES = [
  'Criminal Defense',
  'Cyber Crime Defense',
  'Commercial Arbitration',
  'Constitutional Law',
  'Civil Dispute',
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: cases = [], isLoading: loading } = useQuery<Case[]>({
    queryKey: ['cases'],
    queryFn: async () => {
      const res = await apiClient.get('/cases/');
      return res.data ?? [];
    },
  });

  const [createOpen, setCreateOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newClient, setNewClient] = useState('');
  const [newType, setNewType] = useState('Criminal Defense');
  const [newDesc, setNewDesc] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleDeleteCase = async (e: React.MouseEvent, caseId: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this case dossier? All associated documents and analysis will be permanently deleted.')) {
      return;
    }
    try {
      await apiClient.delete(`/cases/${caseId}`);
      queryClient.invalidateQueries({ queryKey: ['cases'] });
    } catch (err) {
      console.error('Failed to delete case:', err);
      alert('Failed to delete case folder. Please try again.');
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
      formData.append('title', newTitle || (selectedFile ? selectedFile.name.replace(/\.[^/.]+$/, '') : 'Untitled Matter'));
      formData.append('case_type', newType);
      formData.append('description', `Client: ${newClient}. ${newDesc}`);

      const res = await apiClient.post('/cases/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      queryClient.invalidateQueries({ queryKey: ['cases'] });
      setNewTitle('');
      setNewClient('');
      setNewDesc('');
      setSelectedFile(null);
      setCreateOpen(false);

      navigate(`/cases/${res.data.id}`);
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

  const statusMeta = (status: string): { label: string; dot: string; text: string; bg: string; border: string } => {
    switch (status) {
      case 'analysis_complete':
      case 'report_generated':
        return { label: 'Analysis Compiled', dot: 'bg-sage', text: 'text-sage', bg: 'bg-sage/10', border: 'border-sage/30' };
      case 'documents_uploaded':
        return { label: 'Files Uploaded', dot: 'bg-brass', text: 'text-brass', bg: 'bg-brass/10', border: 'border-brass/30' };
      default:
        return { label: 'Draft', dot: 'bg-muted-foreground', text: 'text-muted-foreground', bg: 'bg-secondary', border: 'border-border' };
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-10 px-6 py-8 lg:px-10 lg:py-12">
      <CommandMenu />

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between"
      >
        <div className="space-y-2">
          <p className="eyebrow">Advisor Command Center</p>
          <h1 className="font-serif text-3xl font-semibold tracking-tight md:text-4xl">
            Good to see you, <span className="text-primary">Counsel</span>.
          </h1>
          <p className="max-w-xl text-[15px] leading-relaxed text-muted-foreground">
            Open a case dossier to inspect acts and sections, run multi-agent analysis,
            and generate advisory reports grounded in evidence.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} size="lg" className="gap-2 rounded-lg shadow-sm">
          <Plus className="h-4 w-4" /> New Case Dossier
        </Button>
      </motion.div>

      {/* Stats strip */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="grid grid-cols-3 divide-x divide-border overflow-hidden rounded-xl border border-border bg-card"
      >
        <div className="px-6 py-4">
          <p className="eyebrow mb-1">Active Dossiers</p>
          <p className="font-serif text-2xl font-semibold">{cases.length}</p>
        </div>
        <div className="px-6 py-4">
          <p className="eyebrow mb-1">Compiled</p>
          <p className="font-serif text-2xl font-semibold text-sage">
            {cases.filter((c) => ['analysis_complete', 'report_generated'].includes(c.status)).length}
          </p>
        </div>
        <div className="px-6 py-4">
          <p className="eyebrow mb-1">In Progress</p>
          <p className="font-serif text-2xl font-semibold text-brass">
            {cases.filter((c) => c.status === 'documents_uploaded').length}
          </p>
        </div>
      </motion.div>

      {/* Case folders */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2.5 font-serif text-xl font-semibold tracking-tight">
            <FolderOpen className="h-5 w-5 text-brass" strokeWidth={1.8} />
            Active Legal Folders
          </h2>
          <Button variant="ghost" onClick={() => navigate('/cases')} className="gap-1.5 text-[13px] font-medium text-muted-foreground hover:text-foreground">
            View all dossiers <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </div>

        {loading ? (
          <div className="grid gap-4 md:grid-cols-2">
            {[0, 1].map((i) => (
              <div key={i} className="card-elevated h-44 animate-pulse p-5" />
            ))}
          </div>
        ) : cases.length === 0 ? (
          <div className="card-elevated flex flex-col items-center gap-4 px-8 py-14 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full border border-brass/30 bg-brass/10">
              <Scale className="h-6 w-6 text-brass" strokeWidth={1.6} />
            </div>
            <div className="space-y-1.5">
              <h3 className="font-serif text-lg font-semibold">No dossiers yet</h3>
              <p className="mx-auto max-w-sm text-sm leading-relaxed text-muted-foreground">
                Initialize your first case file to begin AI-assisted analysis.
              </p>
            </div>
            <Button onClick={() => setCreateOpen(true)} className="gap-2 rounded-lg">
              <Plus className="h-4 w-4" /> Initialize Case File
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {cases.slice(0, 4).map((c, idx) => {
              const s = statusMeta(c.status);
              return (
                <motion.button
                  key={c.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  whileHover={{ y: -2 }}
                  onClick={() => navigate(`/cases/${c.id}`)}
                  className="card-elevated card-elevated-hover group flex cursor-pointer flex-col justify-between rounded-xl p-5 text-left"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${s.bg} ${s.text} ${s.border}`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
                        {s.label}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <span className="rounded border border-border bg-secondary px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
                          {c.case_type || 'General'}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => handleDeleteCase(e, c.id)}
                          className="rounded-md p-1 text-muted-foreground/50 transition hover:bg-destructive/10 hover:text-destructive"
                          title="Delete dossier"
                          aria-label="Delete dossier"
                        >
                          <Trash2 className="h-3.5 w-3.5" strokeWidth={1.7} />
                        </button>
                      </div>
                    </div>
                    <div>
                      <h3 className="font-serif text-base font-semibold leading-snug tracking-tight transition-colors group-hover:text-primary">
                        {cleanTitle(c.title)}
                      </h3>
                      {c.description && (
                        <p className="mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-muted-foreground">
                          {c.description}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="mt-5 flex items-center justify-between border-t border-border pt-3.5 text-xs text-muted-foreground">
                    <span className="inline-flex items-center gap-1.5 font-mono text-[11px]">
                      <Clock className="h-3 w-3" />
                      {new Date(c.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}
                    </span>
                    <span className="inline-flex items-center gap-1 text-[13px] font-medium text-primary transition-transform group-hover:translate-x-0.5">
                      {c.status === 'analysis_complete' ? 'Open' : 'Start analysis'}
                      <ChevronRight className="h-3.5 w-3.5" />
                    </span>
                  </div>
                </motion.button>
              );
            })}
          </div>
        )}
      </section>

      {/* Architecture marquee */}
      <LegalFeatureMarquee />

      {/* Create case modal */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setCreateOpen(false)}
            className="absolute inset-0 bg-foreground/40 backdrop-blur-[2px]"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ duration: 0.18 }}
            className="relative z-10 w-full max-w-lg overflow-hidden rounded-xl border border-border bg-card shadow-2xl"
          >
            <div className="border-b border-border px-6 pb-4 pt-6">
              <button
                onClick={() => setCreateOpen(false)}
                className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                aria-label="Close"
              >
                <X className="h-4.5 w-4.5" />
              </button>
              <p className="eyebrow mb-1">New Matter</p>
              <h2 className="font-serif text-xl font-semibold tracking-tight">Initialize Case Dossier</h2>
              <p className="mt-1 text-[13px] text-muted-foreground">
                Upload the primary document — the pipeline handles parsing and metadata extraction.
              </p>
            </div>

            <form onSubmit={handleCreateCase} className="space-y-5 px-6 py-5">
              <div>
                <label className="eyebrow mb-1.5 block">Case Document · PDF, DOCX, TXT *</label>
                <label className="relative block cursor-pointer rounded-lg border border-dashed border-input bg-secondary/60 px-4 py-6 text-center transition hover:border-brass/50 hover:bg-secondary">
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        const file = e.target.files[0];
                        setSelectedFile(file);
                        const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ');
                        setNewTitle(nameWithoutExt.charAt(0).toUpperCase() + nameWithoutExt.slice(1));
                      }
                    }}
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                  />
                  {selectedFile ? (
                    <div className="flex items-center justify-center gap-2.5 text-foreground">
                      <FileText className="h-5 w-5 text-brass" strokeWidth={1.7} />
                      <span className="max-w-[260px] truncate text-sm font-medium">{selectedFile.name}</span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-1.5 text-muted-foreground">
                      <Upload className="h-5 w-5 text-brass" strokeWidth={1.7} />
                      <span className="text-[13px] font-medium">Click to upload or drag &amp; drop</span>
                      <span className="font-mono text-[11px]">PDF · DOCX · TXT up to 50 MB</span>
                    </div>
                  )}
                </label>
              </div>

              <div>
                <label className="eyebrow mb-1.5 block">Case Title / Matter Reference</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Mehta Realty vs Shanti Devi"
                  className="w-full rounded-lg border border-input bg-card px-3.5 py-2.5 text-sm transition placeholder:text-muted-foreground/70 focus:border-brass/60 focus:outline-none focus:ring-2 focus:ring-brass/20"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="eyebrow mb-1.5 block">Client Name</label>
                  <input
                    type="text"
                    value={newClient}
                    onChange={(e) => setNewClient(e.target.value)}
                    placeholder="e.g. Shanti Devi"
                    className="w-full rounded-lg border border-input bg-card px-3.5 py-2.5 text-sm transition placeholder:text-muted-foreground/70 focus:border-brass/60 focus:outline-none focus:ring-2 focus:ring-brass/20"
                  />
                </div>
                <div>
                  <label className="eyebrow mb-1.5 block">Practice Area</label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value)}
                    className="w-full rounded-lg border border-input bg-card px-3.5 py-2.5 text-sm transition focus:border-brass/60 focus:outline-none focus:ring-2 focus:ring-brass/20"
                  >
                    {CASE_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="eyebrow mb-1.5 block">Brief Context / Notes</label>
                <textarea
                  rows={3}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Preliminary notes, charge details, key dates…"
                  className="w-full resize-none rounded-lg border border-input bg-card px-3.5 py-2.5 text-sm transition placeholder:text-muted-foreground/70 focus:border-brass/60 focus:outline-none focus:ring-2 focus:ring-brass/20"
                />
              </div>

              <div className="flex justify-end gap-2.5 border-t border-border pt-4">
                <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)} className="rounded-lg text-muted-foreground">
                  Cancel
                </Button>
                <Button type="submit" disabled={submitting} className="min-w-36 gap-2 rounded-lg">
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Initialize Dossier'}
                </Button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
}
