import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Briefcase, Search, PlusCircle, FileText, Clock, ChevronRight,
  FolderOpen, Calendar, Layers, X, Loader2, Trash2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import apiClient from '@/lib/api';

interface Case {
  id: string;
  title: string;
  description: string | null;
  case_type: string | null;
  status: string;
  created_at: string;
}

export default function CasesPage() {
  const navigate = useNavigate();
  const [searchVal, setSearchVal] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);

  // Form states
  const [newTitle, setNewTitle] = useState('');
  const [newClient, setNewClient] = useState('');
  const [newType, setNewType] = useState('Criminal Defense');
  const [newDesc, setNewDesc] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleDeleteCase = async (e: React.MouseEvent, caseId: string) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this case folder? All associated documents and analysis will be permanently deleted.")) {
      return;
    }
    try {
      await apiClient.delete(`/cases/${caseId}`);
      setCases((prev) => prev.filter((c) => c.id !== caseId));
    } catch (err) {
      console.error("Failed to delete case:", err);
      alert("Failed to delete case folder. Please try again.");
    }
  };

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
    if (!newTitle.trim()) return;

    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('title', newTitle);
      formData.append('case_type', newType);
      formData.append('description', `Client: ${newClient}. ${newDesc}`);

      const res = await apiClient.post('/cases/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setCases((prev) => [res.data, ...prev]);
      setNewTitle('');
      setNewClient('');
      setNewDesc('');
      setCreateOpen(false);
      navigate(`/cases/${res.data.id}/analysis`);
    } catch (err) {
      console.error('Failed to create case:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'analysis_complete':
      case 'report_generated':
        return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
      case 'documents_uploaded':
        return 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
      default:
        return 'bg-blue-500/10 text-primary border border-primary/20';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'analysis_complete': return 'Analysis Compiled';
      case 'report_generated': return 'Report Generated';
      case 'documents_uploaded': return 'Files Uploaded';
      default: return 'Draft';
    }
  };

  const filteredCases = cases.filter(c => 
    c.title.toLowerCase().includes(searchVal.toLowerCase()) || 
    (c.description && c.description.toLowerCase().includes(searchVal.toLowerCase()))
  );

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6">
      {/* Brand Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-4">
        <div className="text-left">
          <h1 className="text-2xl font-bold text-white">Active Case Folders</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Manage, review, and evaluate legal arguments for your active client files.</p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="bg-primary hover:bg-primary/95 text-primary-foreground gap-2 font-semibold shadow-md shadow-primary/20 transition-all cursor-pointer">
          <PlusCircle className="h-4.5 w-4.5" />
          Create Case Folder
        </Button>
      </div>

      {/* Quick Search */}
      <div className="relative max-w-md">
        <input
          type="text"
          value={searchVal}
          onChange={(e) => setSearchVal(e.target.value)}
          placeholder="Search by case title or client name..."
          className="w-full rounded-xl border border-white/5 bg-card/40 py-2.5 pl-10 pr-4 text-xs text-white focus:outline-none"
        />
        <Search className="absolute left-3.5 top-3 h-4 w-4 text-muted-foreground" />
      </div>

      {/* Cases List */}
      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Loader2 className="h-7 w-7 animate-spin text-primary" />
        </div>
      ) : filteredCases.length === 0 ? (
        <div className="rounded-xl border border-white/5 bg-card/10 p-8 text-center text-xs text-muted-foreground">
          No case folders found matching your query.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filteredCases.map((c) => (
            <motion.div
              key={c.id}
              whileHover={{ y: -3 }}
              onClick={() => navigate(`/cases/${c.id}/analysis`)}
              className="glass-card rounded-xl p-5 border border-white/5 bg-card/15 hover:bg-card/25 transition-all flex flex-col justify-between cursor-pointer group text-left"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-muted-foreground font-mono bg-white/5 border border-white/5 px-2 py-0.5 rounded">{c.id}</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => handleDeleteCase(e, c.id)}
                      className="p-1 rounded hover:bg-red-500/10 hover:text-red-400 text-muted-foreground transition-colors cursor-pointer"
                      title="Delete Case Folder"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                    <span className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${getStatusColor(c.status)}`}>
                      {getStatusLabel(c.status)}
                    </span>
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white group-hover:text-primary transition-colors">
                    {c.title}
                  </h3>
                  <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span className="font-semibold text-slate-300">Category: {c.case_type || 'Unspecified'}</span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                  {c.description || 'No detailed facts added yet. Open brief directory to parse legal documents.'}
                </p>
              </div>

              <div className="mt-5 border-t border-white/5 pt-3 flex items-center justify-between text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1 font-mono">
                  <Clock className="h-3.5 w-3.5" />
                  {new Date(c.created_at).toLocaleDateString()}
                </span>
                <span className="flex items-center gap-0.5 font-bold text-primary group-hover:translate-x-1 transition-transform">
                  Open Ingestion Folder
                  <ChevronRight className="h-3 w-3" />
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* CREATE NEW CASE DIALOG MODAL */}
      <AnimatePresence>
        {createOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setCreateOpen(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            {/* Modal Box */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-lg rounded-2xl border border-white/5 bg-card p-6 shadow-2xl text-left"
            >
              <button
                onClick={() => setCreateOpen(false)}
                className="absolute right-4 top-4 text-muted-foreground hover:text-white"
              >
                <X className="h-4.5 w-4.5" />
              </button>

              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <FolderOpen className="h-5 w-5 text-primary" />
                Create New Case Folder
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">Setup a case brief directory to reference statutory analyses.</p>

              <form onSubmit={handleCreateCase} className="mt-4 space-y-4 text-xs">
                <div>
                  <label className="font-semibold text-muted-foreground uppercase tracking-wider">Case Matter Title</label>
                  <input
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="e.g. State vs. John Doe (Section 300)"
                    className="mt-1 w-full rounded-lg border border-white/5 bg-background p-2.5 text-white focus:outline-none"
                  />
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="font-semibold text-muted-foreground uppercase tracking-wider">Client Name</label>
                    <input
                      type="text"
                      required
                      value={newClient}
                      onChange={(e) => setNewClient(e.target.value)}
                      placeholder="e.g. John Doe"
                      className="mt-1 w-full rounded-lg border border-white/5 bg-background p-2.5 text-white focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="font-semibold text-muted-foreground uppercase tracking-wider">Case Category</label>
                    <select
                      value={newType}
                      onChange={(e) => setNewType(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-white/5 bg-background p-2.5 text-white focus:outline-none"
                    >
                      <option value="Criminal Defense">Criminal Defense</option>
                      <option value="Civil Litigations">Civil Litigations</option>
                      <option value="Property Claim">Property Claim</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="font-semibold text-muted-foreground uppercase tracking-wider">Brief Description / Facts</label>
                  <textarea
                    rows={4}
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="Describe the initial facts of the case..."
                    className="mt-1 w-full rounded-lg border border-white/5 bg-background p-2.5 text-white focus:outline-none resize-none"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)} className="text-white">
                    Cancel
                  </Button>
                  <Button type="submit" disabled={submitting} className="bg-primary hover:bg-primary/95 text-primary-foreground font-semibold px-4">
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
