import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Briefcase, FileText, CheckCircle2, Cpu, PlusCircle, Search, 
  ChevronRight, Clock, FolderOpen, X, Loader2, Sparkles, Scale, Info
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
    if (!newTitle.trim()) return;

    setSubmitting(true);
    try {
      const res = await apiClient.post('/cases/', {
        title: newTitle,
        description: `Client: ${newClient}. ${newDesc}`,
        case_type: newType,
      });
      
      setCases((prev) => [res.data, ...prev]);
      setNewTitle('');
      setNewClient('');
      setNewDesc('');
      setCreateOpen(false);
      
      // Redirect directly to the analysis upload view of this case
      navigate(`/cases/${res.data.id}/analysis`);
    } catch (err) {
      console.error('Failed to create case:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadgeClass = (status: string) => {
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

  const stats = [
    { label: 'Active Case Files', val: cases.length.toString(), desc: 'Case directories in progress', icon: Briefcase, color: 'text-primary' },
    { label: 'Ingestion Status', val: 'Online', desc: 'Qdrant & FalkorDB connected', icon: CheckCircle2, color: 'text-emerald-400' },
    { label: 'AI Reasoning Core', val: 'Active', desc: 'Dual-agent analyst verified', icon: Cpu, color: 'text-cyan-400' },
  ];

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-8 text-left relative">
      {/* Background glow shadow */}
      <div className="absolute left-[20%] top-[20%] h-96 w-96 rounded-full bg-primary/5 blur-[120px] pointer-events-none"></div>

      {/* Welcome banner */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-2xl border border-white/5 bg-card/40 backdrop-blur-md p-8 shadow-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-6"
      >
        <div className="max-w-2xl space-y-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            <Sparkles className="h-3.5 w-3.5 animate-pulse" />
            LexOrch-KG Legal Intelligence Core
          </span>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Advisor Command Center
          </h1>
          <p className="text-muted-foreground text-sm leading-relaxed">
            Upload legal case briefs, inspect acts & sections, and generate interactive knowledge graphs. Select or initialize a case file to begin analysis.
          </p>
        </div>
        <Button 
          onClick={() => setCreateOpen(true)} 
          className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold px-5 py-5 text-xs rounded-xl shrink-0 shadow-lg shadow-primary/20 gap-1.5 transition-all cursor-pointer"
        >
          <PlusCircle className="h-4.5 w-4.5" /> Initialize Case File
        </Button>
      </motion.div>

      {/* Metric Cards Row */}
      <div className="grid gap-6 sm:grid-cols-3">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="glass-card rounded-xl p-6 border border-white/5 bg-card/20 backdrop-blur-md flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">{stat.label}</span>
                <Icon className={`h-5 w-5 ${stat.color}`} />
              </div>
              <div className="mt-4">
                <span className="text-2xl font-extrabold text-white tracking-tight">{stat.val}</span>
                <p className="text-xs text-muted-foreground mt-1">{stat.desc}</p>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Case brief lists */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
          <FolderOpen className="h-4.5 w-4.5 text-primary" /> Active Legal Folders
        </h3>

        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <Loader2 className="h-7 w-7 animate-spin text-primary" />
          </div>
        ) : cases.length === 0 ? (
          <div className="rounded-xl border border-white/5 bg-card/10 p-8 text-center text-xs text-muted-foreground">
            No active legal folders created yet. Click "Initialize Case File" above to get started.
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {cases.map((c) => (
              <motion.div
                key={c.id}
                whileHover={{ y: -3 }}
                onClick={() => navigate(`/cases/${c.id}/analysis`)}
                className="glass-card rounded-xl p-5 border border-white/5 bg-card/15 hover:bg-card/25 transition-all flex flex-col justify-between cursor-pointer group text-left"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-bold text-muted-foreground font-mono bg-white/5 border border-white/5 px-2 py-0.5 rounded">{c.id}</span>
                    <span className={`rounded-full px-2.5 py-0.5 text-[9px] font-bold ${getStatusBadgeClass(c.status)}`}>
                      {getStatusLabel(c.status)}
                    </span>
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-white group-hover:text-primary transition-colors">
                      {c.title}
                    </h3>
                    <span className="text-[10px] text-muted-foreground mt-1 block font-medium">Type: {c.case_type || 'Unspecified'}</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                    {c.description || 'No detailed case facts uploaded yet. Open case brief folder to run AI ingestion.'}
                  </p>
                </div>

                <div className="mt-5 border-t border-white/5 pt-3 flex items-center justify-between text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1 font-mono">
                    <Clock className="h-3.5 w-3.5" />
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                  <span className="flex items-center gap-0.5 font-bold text-primary group-hover:translate-x-1 transition-transform">
                    {c.status === 'analysis_complete' ? 'Open Dashboard' : 'Start Analysis'}
                    <ChevronRight className="h-3 w-3" />
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

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
              className="absolute inset-0 bg-black/75 backdrop-blur-sm"
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
                <Scale className="h-5 w-5 text-primary" />
                Initialize Legal Folder
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">Define case matter coordinates before triggering AI ingestion pipeline.</p>

              <form onSubmit={handleCreateCase} className="mt-5 space-y-4 text-xs">
                <div>
                  <label className="font-semibold text-muted-foreground uppercase tracking-wider">Case Title / Matter Reference</label>
                  <input
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="e.g. State vs. John Doe (Organized Cyber Fraud)"
                    className="mt-1 w-full rounded-lg border border-white/5 bg-background p-2.5 text-white focus:outline-none focus:border-primary/50"
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
                      placeholder="e.g. Vikram Dev"
                      className="mt-1 w-full rounded-lg border border-white/5 bg-background p-2.5 text-white focus:outline-none focus:border-primary/50"
                    />
                  </div>

                  <div>
                    <label className="font-semibold text-muted-foreground uppercase tracking-wider">Case Category Type</label>
                    <select
                      value={newType}
                      onChange={(e) => setNewType(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-white/5 bg-background p-2.5 text-white focus:outline-none"
                    >
                      <option value="Criminal Defense">Criminal Defense</option>
                      <option value="Cyber Crime Defense">Cyber Crime Defense</option>
                      <option value="Civil Dispute">Civil Dispute</option>
                      <option value="Constitutional Law">Constitutional Law</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="font-semibold text-muted-foreground uppercase tracking-wider">Brief Fact Summary / Core Matter Description</label>
                  <textarea
                    rows={4}
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="Add brief contextual summaries or preliminary notes regarding charge sheet logs..."
                    className="mt-1 w-full rounded-lg border border-white/5 bg-background p-2.5 text-white focus:outline-none resize-none focus:border-primary/50"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)} className="text-white">
                    Cancel
                  </Button>
                  <Button type="submit" disabled={submitting} className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold px-4 py-2.5">
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
