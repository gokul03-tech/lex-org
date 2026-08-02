import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Briefcase,
  Search,
  PlusCircle,
  FileText,
  Clock,
  ChevronRight,
  FolderOpen,
  Calendar,
  Layers,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Case {
  id: string;
  title: string;
  client: string;
  type: string;
  lastUpdated: string;
  status: 'In Progress' | 'Under Review' | 'Complete';
  brief: string;
}

export default function CasesPage() {
  const navigate = useNavigate();
  const [searchVal, setSearchVal] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [cases, setCases] = useState<Case[]>([
    {
      id: 'C101',
      title: 'State vs. Vikram Dev (Bail Application)',
      client: 'Vikram Dev',
      type: 'Criminal Defense',
      lastUpdated: '10 minutes ago',
      status: 'In Progress',
      brief: 'Accused arrested under Section 111 of BNS (Organised Crime) and Section 300 of IPC. Bail application pending review of cross-referenced precedent catalogs.'
    },
    {
      id: 'C102',
      title: 'Re: Sharma Property Infringement Dispute',
      client: 'Aarav Sharma',
      type: 'Civil Property Dispute',
      lastUpdated: '2 hours ago',
      status: 'Under Review',
      brief: 'Evaluating easement rights under Section 4 of the Easements Act, 1882. Property claims filed at High Court level.'
    }
  ]);

  // Form states
  const [newTitle, setNewTitle] = useState('');
  const [newClient, setNewClient] = useState('');
  const [newType, setNewType] = useState('Criminal Defense');
  const [newBrief, setNewBrief] = useState('');

  const handleCreateCase = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle || !newClient) return;

    const newCase: Case = {
      id: `C10${cases.length + 1}`,
      title: newTitle,
      client: newClient,
      type: newType,
      lastUpdated: 'Just now',
      status: 'In Progress',
      brief: newBrief
    };

    setCases(prev => [newCase, ...prev]);
    setNewTitle('');
    setNewClient('');
    setNewBrief('');
    setCreateOpen(false);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Complete': return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
      case 'Under Review': return 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
      default: return 'bg-blue-500/10 text-primary border border-primary/20';
    }
  };

  const filteredCases = cases.filter(c => 
    c.title.toLowerCase().includes(searchVal.toLowerCase()) || 
    c.client.toLowerCase().includes(searchVal.toLowerCase())
  );

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6">
      {/* Brand Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Active Case Files</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Manage, review, and evaluate legal arguments for your active client files.</p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="bg-primary hover:bg-primary/95 text-primary-foreground gap-2 font-semibold shadow-md shadow-primary/20">
          <PlusCircle className="h-4.5 w-4.5" />
          Create Case File
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
      <div className="grid gap-4 md:grid-cols-2">
        {filteredCases.map((c) => (
          <motion.div
            key={c.id}
            whileHover={{ y: -3 }}
            onClick={() => navigate(`/cases/${c.id}`)}
            className="glass-card rounded-xl p-5 border border-white/5 flex flex-col justify-between cursor-pointer group text-left"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-muted-foreground font-mono">{c.id}</span>
                <span className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${getStatusColor(c.status)}`}>
                  {c.status}
                </span>
              </div>
              <div>
                <h3 className="text-sm font-bold text-white group-hover:text-primary transition-colors">
                  {c.title}
                </h3>
                <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="font-semibold text-white">{c.client}</span>
                  <span>•</span>
                  <span>{c.type}</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                {c.brief}
              </p>
            </div>

            <div className="mt-5 border-t border-white/5 pt-3 flex items-center justify-between text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                Updated {c.lastUpdated}
              </span>
              <span className="flex items-center gap-0.5 font-bold text-primary group-hover:translate-x-1 transition-transform">
                Open Brief
                <ChevronRight className="h-3 w-3" />
              </span>
            </div>
          </motion.div>
        ))}
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
                Create New Case File
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
                    className="mt-1 w-full rounded-lg border border-white/5 bg-muted/50 p-2.5 text-white focus:outline-none"
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
                      className="mt-1 w-full rounded-lg border border-white/5 bg-muted/50 p-2.5 text-white focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="font-semibold text-muted-foreground uppercase tracking-wider">Case Type</label>
                    <select
                      value={newType}
                      onChange={(e) => setNewType(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-white/5 bg-muted/50 p-2.5 text-white focus:outline-none"
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
                    value={newBrief}
                    onChange={(e) => setNewBrief(e.target.value)}
                    placeholder="Describe the initial facts of the case..."
                    className="mt-1 w-full rounded-lg border border-white/5 bg-muted/50 p-2.5 text-white focus:outline-none resize-none"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)} className="text-white">
                    Cancel
                  </Button>
                  <Button type="submit" className="bg-primary hover:bg-primary/95 text-primary-foreground font-semibold">
                    Initialize File
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
