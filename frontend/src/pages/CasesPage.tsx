import React, { useState, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, FileText, Clock, ChevronRight, FolderOpen, X, Loader2,
  Trash2, LayoutGrid, Table as TableIcon, Upload, ArrowUpRight,
  HelpCircle, Scale, BookOpen, Network, Gavel, Plus,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { HowItWorksModal } from '@/components/ui/how-it-works-modal';
import apiClient from '@/lib/api';

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

export default function CasesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: cases = [], isLoading: loading } = useQuery<Case[]>({
    queryKey: ['cases'],
    queryFn: async () => {
      const res = await apiClient.get('/cases/');
      return res.data ?? [];
    },
  });

  const [searchVal, setSearchVal] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [createOpen, setCreateOpen] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);

  const [newTitle, setNewTitle] = useState('');
  const [newClient, setNewClient] = useState('');
  const [newType, setNewType] = useState('Criminal Defense');
  const [newDesc, setNewDesc] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const createInFlightRef = useRef(false);

  const handleDeleteCase = async (e: React.MouseEvent, caseId: string) => {
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
    if (!newTitle.trim() && !selectedFile) return;
    if (createInFlightRef.current) return;
    createInFlightRef.current = true;

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
      createInFlightRef.current = false;
    }
  };

  const cleanTitle = (raw: string) => {
    if (!raw) return 'Untitled Case';
    return raw.replace(/\s+on\s+\d{1,2}\s+[A-Za-z]+,?\s+\d{4}.*$/i, '').trim();
  };

  const categoryCards = useMemo(() => {
    return [
      {
        id: 'All',
        label: 'All Dossiers',
        subtitle: 'Complete inventory',
        count: cases.length,
        icon: FolderOpen,
      },
      {
        id: 'Criminal Defense',
        label: 'Criminal / Bail',
        subtitle: 'BNS · BNSS · BSA S.63',
        count: cases.filter(c => (c.case_type || '').toLowerCase().includes('criminal') || (c.case_type || '').toLowerCase().includes('bail')).length,
        icon: Gavel,
      },
      {
        id: 'Cyber Crime Defense',
        label: 'Cybercrime',
        subtitle: 'IT Act 66D · BNS S.111',
        count: cases.filter(c => (c.case_type || '').toLowerCase().includes('cyber')).length,
        icon: Network,
      },
      {
        id: 'Commercial Arbitration',
        label: 'Arbitration',
        subtitle: 'Arb. Act S.34 · S.11',
        count: cases.filter(c => (c.case_type || '').toLowerCase().includes('arbitration') || (c.case_type || '').toLowerCase().includes('commercial')).length,
        icon: Scale,
      },
      {
        id: 'Constitutional Law',
        label: 'Constitutional Writ',
        subtitle: 'Art. 226 · Art. 32',
        count: cases.filter(c => (c.case_type || '').toLowerCase().includes('writ') || (c.case_type || '').toLowerCase().includes('constitution')).length,
        icon: BookOpen,
      },
      {
        id: 'Civil Dispute',
        label: 'Civil Dispute',
        subtitle: 'CPC · Specific Relief',
        count: cases.filter(c => (c.case_type || '').toLowerCase().includes('civil')).length,
        icon: FileText,
      },
    ];
  }, [cases]);

  const getCategoryVariant = (type: string | null): 'criminal' | 'cybercrime' | 'arbitration' | 'constitutional' | 'civil' => {
    const t = (type || '').toLowerCase();
    if (t.includes('criminal') || t.includes('bail') || t.includes('ndps')) return 'criminal';
    if (t.includes('cyber')) return 'cybercrime';
    if (t.includes('arbitration') || t.includes('commercial')) return 'arbitration';
    if (t.includes('writ') || t.includes('constitution')) return 'constitutional';
    return 'civil';
  };

  const statusMeta = (status: string): { label: string; dot: string; text: string; bg: string; border: string } => {
    switch (status) {
      case 'analysis_complete':
      case 'report_generated':
        return { label: 'Analysis Ready', dot: 'bg-sage', text: 'text-sage', bg: 'bg-sage/10', border: 'border-sage/30' };
      case 'documents_uploaded':
        return { label: 'Files Ready', dot: 'bg-brass', text: 'text-brass', bg: 'bg-brass/10', border: 'border-brass/30' };
      default:
        return { label: 'Draft Matter', dot: 'bg-muted-foreground', text: 'text-muted-foreground', bg: 'bg-secondary', border: 'border-border' };
    }
  };

  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      const matchSearch =
        c.title.toLowerCase().includes(searchVal.toLowerCase()) ||
        (c.description && c.description.toLowerCase().includes(searchVal.toLowerCase())) ||
        (c.case_type && c.case_type.toLowerCase().includes(searchVal.toLowerCase())) ||
        c.id.toLowerCase().includes(searchVal.toLowerCase());

      const matchCategory =
        selectedCategory === 'All' ||
        (c.case_type && c.case_type.toLowerCase().includes(selectedCategory.toLowerCase().split(' ')[0]));

      return matchSearch && matchCategory;
    });
  }, [cases, searchVal, selectedCategory]);

  const inputCls =
    'w-full rounded-lg border border-input bg-card px-3.5 py-2.5 text-sm transition placeholder:text-muted-foreground/70 focus:border-brass/60 focus:outline-none focus:ring-2 focus:ring-brass/20';

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-6 py-8 lg:px-10 lg:py-12">
      <HowItWorksModal
        isOpen={tourOpen}
        onClose={() => setTourOpen(false)}
        onStartCase={() => setCreateOpen(true)}
      />

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
      >
        <div className="space-y-1.5">
          <p className="eyebrow">Dossier Registry</p>
          <h1 className="font-serif text-3xl font-semibold tracking-tight">Case Dossiers</h1>
          <p className="text-[15px] text-muted-foreground">
            Manage, search, and analyze statutory legal case files.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2.5">
          <Button variant="outline" onClick={() => setTourOpen(true)} className="gap-2 rounded-lg bg-card">
            <HelpCircle className="h-4 w-4 text-brass" strokeWidth={1.7} />
            How it works
          </Button>
          <Button onClick={() => setCreateOpen(true)} className="gap-2 rounded-lg shadow-sm">
            <Plus className="h-4 w-4" /> New Case File
          </Button>
        </div>
      </motion.div>

      {/* Practice-area filter */}
      <section className="space-y-3.5">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-lg font-semibold tracking-tight">Filter by Practice Area</h2>
          <span className="font-mono text-[11px] text-muted-foreground">
            {filteredCases.length} matching case{filteredCases.length === 1 ? '' : 's'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {categoryCards.map((cat) => {
            const active = selectedCategory === cat.id;
            const Icon = cat.icon;
            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`group flex cursor-pointer flex-col justify-between rounded-xl border p-4 text-left transition-all duration-200 ${
                  active
                    ? 'border-primary/60 bg-card shadow-md ring-1 ring-primary/20'
                    : 'border-border bg-card hover:border-brass/40 hover:shadow-sm'
                }`}
              >
                <div className="mb-2.5 flex items-center justify-between">
                  <Icon
                    className={`h-[18px] w-[18px] ${active ? 'text-primary' : 'text-muted-foreground group-hover:text-brass'}`}
                    strokeWidth={1.7}
                  />
                  <span
                    className={`rounded px-1.5 py-0.5 font-mono text-[11px] font-semibold ${
                      active ? 'bg-primary text-primary-foreground' : 'border border-border bg-secondary text-muted-foreground'
                    }`}
                  >
                    {cat.count}
                  </span>
                </div>
                <h3 className="font-serif text-[13px] font-semibold leading-tight">{cat.label}</h3>
                <p className="mt-1 truncate font-mono text-[10px] text-muted-foreground">{cat.subtitle}</p>
              </button>
            );
          })}
        </div>
      </section>

      {/* Search + view controls */}
      <div className="flex flex-col items-stretch justify-between gap-3 md:flex-row md:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={searchVal}
            onChange={(e) => setSearchVal(e.target.value)}
            placeholder="Search by title, client, matter reference…"
            className={`${inputCls} pl-10`}
          />
          {searchVal && (
            <button
              onClick={() => setSearchVal('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted-foreground hover:text-foreground"
              aria-label="Clear search"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1 rounded-lg border border-border bg-card p-1">
          {([['grid', LayoutGrid, 'Grid'], ['table', TableIcon, 'Docket']] as const).map(([mode, Icon, label]) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`flex cursor-pointer items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition ${
                viewMode === mode ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="h-3.5 w-3.5" /> {label}
            </button>
          ))}
        </div>
      </div>

      {/* Cases display */}
      {loading ? (
        <div className="flex h-64 flex-col items-center justify-center gap-3">
          <Loader2 className="h-7 w-7 animate-spin text-primary" strokeWidth={1.6} />
          <span className="font-mono text-xs text-muted-foreground">Loading dossiers…</span>
        </div>
      ) : filteredCases.length === 0 ? (
        <div className="card-elevated flex flex-col items-center gap-4 px-8 py-14 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full border border-brass/30 bg-brass/10">
            <FolderOpen className="h-6 w-6 text-brass" strokeWidth={1.6} />
          </div>
          <div className="space-y-1.5">
            <h3 className="font-serif text-lg font-semibold">No matching case files</h3>
            <p className="mx-auto max-w-md text-sm leading-relaxed text-muted-foreground">
              {searchVal || selectedCategory !== 'All'
                ? 'No records match your current filters. Reset them to see every dossier.'
                : 'Your registry is empty. Initialize a case file to launch the multi-agent pipeline.'}
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            {(searchVal || selectedCategory !== 'All') && (
              <Button
                variant="outline"
                onClick={() => {
                  setSearchVal('');
                  setSelectedCategory('All');
                }}
                className="rounded-lg bg-card"
              >
                Clear filters
              </Button>
            )}
            <Button onClick={() => setCreateOpen(true)} className="gap-2 rounded-lg">
              <Plus className="h-4 w-4" /> Initialize Case File
            </Button>
          </div>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {filteredCases.map((c, idx) => {
            const catVariant = getCategoryVariant(c.case_type);
            const s = statusMeta(c.status);
            return (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(idx * 0.04, 0.3) }}
                whileHover={{ y: -3 }}
                onClick={() => navigate(`/cases/${c.id}`)}
                className="card-elevated card-elevated-hover group relative flex cursor-pointer flex-col justify-between overflow-hidden rounded-xl p-5 pt-6 text-left"
              >
                <span className="absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-primary via-primary/80 to-brass opacity-80" />

                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant={catVariant} size="sm">
                      {c.case_type || 'Civil / General'}
                    </Badge>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => handleDeleteCase(e, c.id)}
                        className="rounded-md p-1 text-muted-foreground/50 transition hover:bg-destructive/10 hover:text-destructive"
                        title="Delete dossier"
                      >
                        <Trash2 className="h-3.5 w-3.5" strokeWidth={1.7} />
                      </button>
                    </div>
                  </div>

                  <div>
                    <h3 className="line-clamp-2 font-serif text-base font-semibold leading-snug tracking-tight transition-colors group-hover:text-primary">
                      {cleanTitle(c.title)}
                    </h3>
                    <p className="mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-muted-foreground">
                      {c.description || 'No brief facts uploaded yet. Open this dossier to trigger ingestion.'}
                    </p>
                  </div>
                </div>

                <div className="mt-5 flex items-end justify-between border-t border-border pt-3.5">
                  <div className="flex flex-col gap-1.5">
                    <span className={`inline-flex items-center gap-1.5 self-start rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${s.bg} ${s.text} ${s.border}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
                      {s.label}
                    </span>
                    <span className="inline-flex items-center gap-1 font-mono text-[10px] text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {new Date(c.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <ChevronRight className="h-4 w-4 text-muted-foreground transition-all group-hover:translate-x-0.5 group-hover:text-brass" />
                </div>
              </motion.div>
            );
          })}
        </div>
      ) : (
        <div className="card-elevated overflow-hidden rounded-xl">
          <table className="w-full border-collapse text-left text-[13px]">
            <thead className="border-b border-border bg-secondary/70">
              <tr className="eyebrow">
                <th className="px-5 py-3.5 font-medium">Matter</th>
                <th className="px-5 py-3.5 font-medium">Practice Area</th>
                <th className="px-5 py-3.5 font-medium">Registered</th>
                <th className="px-5 py-3.5 font-medium">Status</th>
                <th className="px-5 py-3.5 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredCases.map((c) => {
                const catVariant = getCategoryVariant(c.case_type);
                const s = statusMeta(c.status);
                return (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/cases/${c.id}`)}
                    className="cursor-pointer transition hover:bg-secondary/50"
                  >
                    <td className="px-5 py-3.5">
                      <div className="font-serif font-semibold leading-snug">{cleanTitle(c.title)}</div>
                      <span className="font-mono text-[10px] text-muted-foreground">{c.id}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge variant={catVariant} size="sm">
                        {c.case_type || 'General'}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-[11px] text-muted-foreground">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${s.bg} ${s.text} ${s.border}`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
                        {s.label}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => navigate(`/cases/${c.id}`)}
                          className="rounded-md p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-primary"
                          title="Open analysis"
                        >
                          <ArrowUpRight className="h-4 w-4" strokeWidth={1.7} />
                        </button>
                        <button
                          onClick={(e) => handleDeleteCase(e, c.id)}
                          className="rounded-md p-1.5 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive"
                          title="Delete case"
                        >
                          <Trash2 className="h-4 w-4" strokeWidth={1.7} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create modal */}
      <AnimatePresence>
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
              <div className="relative border-b border-border px-6 pb-4 pt-6">
                <button
                  onClick={() => setCreateOpen(false)}
                  className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                  aria-label="Close"
                >
                  <X className="h-4.5 w-4.5" />
                </button>
                <p className="eyebrow mb-1">New Matter</p>
                <h2 className="font-serif text-xl font-semibold tracking-tight">Initialize Legal Dossier</h2>
                <p className="mt-1 text-[13px] text-muted-foreground">
                  Upload a document or define matter details to launch the pipeline.
                </p>
              </div>

              <form onSubmit={handleCreateCase} className="space-y-5 px-6 py-5">
                <div>
                  <label className="eyebrow mb-1.5 block">Upload Case Brief · PDF, DOCX, TXT *</label>
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
                      </div>
                    )}
                  </label>
                </div>

                <div>
                  <label className="eyebrow mb-1.5 block">Case Title / Matter Reference</label>
                  <input type="text" required value={newTitle} onChange={(e) => setNewTitle(e.target.value)} placeholder="e.g. State of Maharashtra v. Vikram Dev" className={inputCls} />
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="eyebrow mb-1.5 block">Client / Party Name</label>
                    <input type="text" value={newClient} onChange={(e) => setNewClient(e.target.value)} placeholder="e.g. Vikram Dev" className={inputCls} />
                  </div>
                  <div>
                    <label className="eyebrow mb-1.5 block">Practice Area</label>
                    <select value={newType} onChange={(e) => setNewType(e.target.value)} className={inputCls}>
                      {CASE_TYPES.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="eyebrow mb-1.5 block">Brief Matter Notes</label>
                  <textarea rows={3} value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="Factual context or charge sheet notes…" className={`${inputCls} resize-none`} />
                </div>

                <div className="flex justify-end gap-2.5 border-t border-border pt-4">
                  <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)} className="rounded-lg text-muted-foreground">
                    Cancel
                  </Button>
                  <Button type="submit" disabled={submitting} className="min-w-36 gap-2 rounded-lg">
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Create Dossier'}
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
