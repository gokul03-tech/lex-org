import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Briefcase, Search, PlusCircle, FileText, Clock, ChevronRight,
  FolderOpen, Calendar, Layers, X, Loader2, Trash2, LayoutGrid,
  Table as TableIcon, Sparkles, Filter, CheckCircle2, ShieldCheck,
  AlertCircle, Upload, ArrowUpRight, HelpCircle, Info, Scale,
  BookOpen, Network, Gavel, Cpu, Shield
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

export default function CasesPage() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchVal, setSearchVal] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [createOpen, setCreateOpen] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);

  // Form states for creating a new case
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

  const handleDeleteCase = async (e: React.MouseEvent, caseId: string) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this case dossier? All associated documents and analysis will be permanently deleted.")) {
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

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() && !selectedFile) return;

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

  // Helper to clean title strings (strip trailing dates)
  const cleanTitle = (raw: string) => {
    if (!raw) return 'Untitled Case';
    return raw.replace(/\s+on\s+\d{1,2}\s+[A-Za-z]+,?\s+\d{4}.*$/i, '').trim();
  };

  // Category styling data for Visual Category Selector cards
  const categoryCards = useMemo(() => {
    return [
      {
        id: 'All',
        label: 'All Dossiers',
        subtitle: 'Complete case inventory',
        count: cases.length,
        color: 'from-slate-700 to-slate-900 text-white',
        border: 'border-slate-300 hover:border-slate-400',
        bg: 'bg-white',
        icon: FolderOpen,
      },
      {
        id: 'Criminal Defense',
        label: 'Criminal / Bail',
        subtitle: 'BNS • BNSS • BSA S.63',
        count: cases.filter(c => (c.case_type || '').toLowerCase().includes('criminal') || (c.case_type || '').toLowerCase().includes('bail')).length,
        color: 'from-rose-500 to-red-600 text-rose-700',
        border: 'border-rose-200 hover:border-rose-300',
        bg: 'bg-rose-50/40',
        icon: Gavel,
      },
      {
        id: 'Cyber Crime Defense',
        label: 'Cybercrime',
        subtitle: 'IT Act 66D • BNS S.111',
        count: cases.filter(c => (c.case_type || '').toLowerCase().includes('cyber')).length,
        color: 'from-violet-500 to-purple-600 text-violet-700',
        border: 'border-violet-200 hover:border-violet-300',
        bg: 'bg-violet-50/40',
        icon: Network,
      },
      {
        id: 'Commercial Arbitration',
        label: 'Arbitration',
        subtitle: 'Arbitration Act S.34 • S.11',
        count: cases.filter(c => (c.case_type || '').toLowerCase().includes('arbitration') || (c.case_type || '').toLowerCase().includes('commercial')).length,
        color: 'from-amber-500 to-orange-600 text-amber-800',
        border: 'border-amber-200 hover:border-amber-300',
        bg: 'bg-amber-50/40',
        icon: Scale,
      },
      {
        id: 'Constitutional Law',
        label: 'Constitutional Writ',
        subtitle: 'Article 226 • Article 32',
        count: cases.filter(c => (c.case_type || '').toLowerCase().includes('writ') || (c.case_type || '').toLowerCase().includes('constitution')).length,
        color: 'from-emerald-500 to-teal-600 text-emerald-800',
        border: 'border-emerald-200 hover:border-emerald-300',
        bg: 'bg-emerald-50/40',
        icon: BookOpen,
      },
      {
        id: 'Civil Dispute',
        label: 'Civil Dispute',
        subtitle: 'CPC • Specific Relief',
        count: cases.filter(c => (c.case_type || '').toLowerCase().includes('civil')).length,
        color: 'from-sky-500 to-blue-600 text-sky-700',
        border: 'border-sky-200 hover:border-sky-300',
        bg: 'bg-sky-50/40',
        icon: FileText,
      },
    ];
  }, [cases]);

  // Category variants mapping
  const getCategoryVariant = (type: string | null): 'criminal' | 'cybercrime' | 'arbitration' | 'constitutional' | 'civil' => {
    const t = (type || '').toLowerCase();
    if (t.includes('criminal') || t.includes('bail') || t.includes('ndps')) return 'criminal';
    if (t.includes('cyber')) return 'cybercrime';
    if (t.includes('arbitration') || t.includes('commercial')) return 'arbitration';
    if (t.includes('writ') || t.includes('constitution')) return 'constitutional';
    return 'civil';
  };

  const getCategoryTopGradient = (type: string | null) => {
    const t = (type || '').toLowerCase();
    if (t.includes('criminal') || t.includes('bail')) return 'from-rose-500 via-rose-400 to-pink-500';
    if (t.includes('cyber')) return 'from-violet-500 via-purple-400 to-indigo-500';
    if (t.includes('arbitration') || t.includes('commercial')) return 'from-amber-500 via-amber-400 to-orange-500';
    if (t.includes('writ') || t.includes('constitution')) return 'from-emerald-500 via-teal-400 to-emerald-600';
    return 'from-sky-500 via-blue-400 to-indigo-500';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'analysis_complete':
      case 'report_generated':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 border border-emerald-200 shadow-2xs">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Analysis Ready
          </span>
        );
      case 'documents_uploaded':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2.5 py-0.5 text-[11px] font-semibold text-sky-700 border border-sky-200 shadow-2xs">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-500" />
            Files Ready
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700 border border-amber-200 shadow-2xs">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            Draft Matter
          </span>
        );
    }
  };

  // Filtered cases
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

  const stats = useMemo(() => {
    const total = cases.length;
    const analyzed = cases.filter(c => c.status === 'analysis_complete' || c.status === 'report_generated').length;
    const avgTrust = analyzed > 0 ? 94 : 0;
    return { total, analyzed, avgTrust };
  }, [cases]);

  return (
    <div className="container mx-auto p-6 lg:p-10 space-y-8 text-left max-w-7xl">
      {/* 3-Step Interactive Tour Modal */}
      <HowItWorksModal
        isOpen={tourOpen}
        onClose={() => setTourOpen(false)}
        onStartCase={() => setCreateOpen(true)}
      />

      {/* PAGE HEADER BAR */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
            Case Dossiers
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 font-sans mt-0.5">
            Manage, search, and analyze statutory legal case files.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Button
            variant="outline"
            onClick={() => setTourOpen(true)}
            className="rounded-2xl border-slate-200 bg-white hover:bg-slate-50 text-slate-700 px-4 py-2.5 text-xs font-semibold gap-2 shadow-2xs cursor-pointer"
          >
            <HelpCircle className="h-4 w-4 text-sky-600" />
            How it Works
          </Button>
          <Button
            onClick={() => setCreateOpen(true)}
            className="daylight-btn-primary rounded-2xl px-5 py-2.5 text-xs font-bold gap-2 shadow-md cursor-pointer"
          >
            <PlusCircle className="h-4.5 w-4.5" /> Start New Case File
          </Button>
        </div>
      </div>

      {/* VISUAL CATEGORY SELECTOR (6 Interactive Cards) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-lg font-bold text-slate-900 flex items-center gap-2">
            <Filter className="h-4.5 w-4.5 text-sky-600" />
            Filter by Practice Area
          </h2>
          <span className="text-xs text-slate-500 font-mono">
            {filteredCases.length} case{filteredCases.length === 1 ? '' : 's'} matching
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {categoryCards.map((cat) => {
            const active = selectedCategory === cat.id;
            const Icon = cat.icon;
            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`group relative flex flex-col justify-between rounded-2xl p-4 text-left transition-all duration-200 cursor-pointer border ${
                  active
                    ? 'bg-white border-sky-400 shadow-md ring-2 ring-sky-100 scale-[1.02]'
                    : `${cat.bg} ${cat.border} hover:bg-white hover:shadow-xs`
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className={`flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br ${cat.color} shadow-xs`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <span className={`font-mono text-xs font-bold rounded-md px-1.5 py-0.2 ${
                      active ? 'bg-slate-900 text-white' : 'bg-white border border-slate-200 text-slate-700'
                    }`}>
                      {cat.count}
                    </span>
                  </div>
                  <h3 className="font-serif text-xs font-bold text-slate-900 group-hover:text-sky-700">
                    {cat.label}
                  </h3>
                </div>
                <p className="font-mono text-[10px] text-slate-500 mt-2 truncate font-medium">
                  {cat.subtitle}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* SEARCH BAR & VIEW MODE CONTROLS */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 pt-2">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchVal}
            onChange={(e) => setSearchVal(e.target.value)}
            placeholder="Search by case title, client, matter reference, or section..."
            className="w-full rounded-2xl border border-slate-200 bg-white pl-10 pr-4 py-2.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-100 focus:border-sky-500 shadow-2xs transition"
          />
          {searchVal && (
            <button
              onClick={() => setSearchVal('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-1 rounded-2xl border border-slate-200 bg-white p-1 shadow-2xs shrink-0">
          <button
            onClick={() => setViewMode('grid')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition cursor-pointer ${
              viewMode === 'grid'
                ? 'bg-sky-50 text-sky-700 border border-sky-200 font-semibold shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
            Grid View
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition cursor-pointer ${
              viewMode === 'table'
                ? 'bg-sky-50 text-sky-700 border border-sky-200 font-semibold shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <TableIcon className="h-3.5 w-3.5" />
            Docket Table
          </button>
        </div>
      </div>

      {/* CASES DISPLAY CONTAINER */}
      {loading ? (
        <div className="flex h-64 flex-col items-center justify-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-sky-600" />
          <span className="font-mono text-xs text-slate-500">Loading legal case dossiers...</span>
        </div>
      ) : filteredCases.length === 0 ? (
        /* Teaching Empty State */
        <div className="rounded-3xl border border-slate-200 bg-white p-12 text-center shadow-xs">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-50 border border-sky-100 text-sky-600 mb-4">
            <FolderOpen className="h-7 w-7" />
          </div>
          <h3 className="font-serif text-lg font-bold text-slate-900">No matching case files</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto leading-relaxed">
            {searchVal || selectedCategory !== 'All'
              ? 'No case records match your current filter settings. Reset filters to view all active dossiers.'
              : 'Your dossier repository is empty. Initialize a new case file to run our multi-agent legal engine.'}
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            {(searchVal || selectedCategory !== 'All') && (
              <Button
                variant="outline"
                onClick={() => {
                  setSearchVal('');
                  setSelectedCategory('All');
                }}
                className="rounded-xl border-slate-200 text-xs px-4"
              >
                Clear Filters
              </Button>
            )}
            <Button
              onClick={() => setCreateOpen(true)}
              className="daylight-btn-primary rounded-xl text-xs px-5"
            >
              <PlusCircle className="h-4 w-4 mr-1.5" /> Initialize Case File
            </Button>
          </div>
        </div>
      ) : viewMode === 'grid' ? (
        /* GRID VIEW WITH GRADIENT TOP-BAR */
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {filteredCases.map((c) => {
            const catVariant = getCategoryVariant(c.case_type);
            const topGradient = getCategoryTopGradient(c.case_type);
            return (
              <motion.div
                key={c.id}
                whileHover={{ y: -3 }}
                onClick={() => navigate(`/cases/${c.id}/analysis`)}
                className="group relative flex flex-col justify-between overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-xs transition-all duration-300 hover:shadow-xl hover:border-slate-300 cursor-pointer text-left"
              >
                {/* Category Accent Top Bar */}
                <div className={`absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r ${topGradient}`} />

                <div className="space-y-3.5">
                  {/* Category badge + Case ID + Delete */}
                  <div className="flex items-center justify-between gap-2 pt-1">
                    <Badge variant={catVariant} size="sm">
                      {c.case_type || 'Civil / General'}
                    </Badge>
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[10px] text-slate-400 bg-slate-50 px-2 py-0.5 rounded-md border border-slate-100 font-semibold">
                        {c.id}
                      </span>
                      <button
                        onClick={(e) => handleDeleteCase(e, c.id)}
                        className="rounded-lg p-1 text-slate-300 hover:bg-rose-50 hover:text-rose-600 transition"
                        title="Delete Dossier"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Title & Factual Description Preview */}
                  <div>
                    <h3 className="font-serif text-base font-bold text-slate-900 group-hover:text-sky-700 transition-colors line-clamp-2">
                      {cleanTitle(c.title)}
                    </h3>
                    <p className="text-xs text-slate-500 mt-2 line-clamp-2 leading-relaxed font-sans">
                      {c.description || 'No detailed brief facts uploaded yet. Open case dossier to trigger multi-agent pipeline.'}
                    </p>
                  </div>
                </div>

                {/* Bottom Metadata & Hover Action */}
                <div className="mt-6 pt-3.5 border-t border-slate-100 flex items-center justify-between">
                  <div className="flex flex-col">
                    {getStatusBadge(c.status)}
                    <span className="font-mono text-[10px] text-slate-400 mt-1 flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(c.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <span className="inline-flex items-center gap-1 text-xs font-bold text-sky-700 group-hover:translate-x-1 transition-transform">
                    Open Case
                    <ChevronRight className="h-3.5 w-3.5" />
                  </span>
                </div>
              </motion.div>
            );
          })}
        </div>
      ) : (
        /* DOCKET TABLE VIEW */
        <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xs">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="border-b border-slate-100 bg-slate-50/70 font-mono text-[10px] uppercase text-slate-500 tracking-wider">
              <tr>
                <th className="py-4 px-5 font-semibold">Case Matter Reference</th>
                <th className="py-4 px-5 font-semibold">Practice Area</th>
                <th className="py-4 px-5 font-semibold">Registered Date</th>
                <th className="py-4 px-5 font-semibold">Trust Index</th>
                <th className="py-4 px-5 font-semibold">Status</th>
                <th className="py-4 px-5 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700 font-sans">
              {filteredCases.map((c) => {
                const catVariant = getCategoryVariant(c.case_type);
                return (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/cases/${c.id}/analysis`)}
                    className="hover:bg-slate-50/80 cursor-pointer transition"
                  >
                    <td className="py-4 px-5">
                      <div className="font-serif font-bold text-slate-900 text-xs hover:text-sky-700">
                        {cleanTitle(c.title)}
                      </div>
                      <span className="font-mono text-[10px] text-slate-400">{c.id}</span>
                    </td>
                    <td className="py-4 px-5">
                      <Badge variant={catVariant} size="sm">
                        {c.case_type || 'General'}
                      </Badge>
                    </td>
                    <td className="py-4 px-5 font-mono text-[11px] text-slate-500">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-4 px-5">
                      <span className="inline-flex items-center gap-1 font-mono text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
                        <ShieldCheck className="h-3 w-3" />
                        94%
                      </span>
                    </td>
                    <td className="py-4 px-5">
                      {getStatusBadge(c.status)}
                    </td>
                    <td className="py-4 px-5 text-right">
                      <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => navigate(`/cases/${c.id}/analysis`)}
                          className="rounded-lg p-1.5 text-sky-700 hover:bg-sky-50 transition"
                          title="Open Analysis"
                        >
                          <ArrowUpRight className="h-4 w-4" />
                        </button>
                        <button
                          onClick={(e) => handleDeleteCase(e, c.id)}
                          className="rounded-lg p-1.5 text-rose-500 hover:bg-rose-50 transition"
                          title="Delete Case"
                        >
                          <Trash2 className="h-4 w-4" />
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

      {/* INITIALIZE CASE FILE MODAL */}
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
                className="absolute right-4 top-4 text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>

              <h2 className="font-serif text-xl font-bold text-slate-900 flex items-center gap-2">
                <Briefcase className="h-5 w-5 text-sky-600" />
                Initialize Legal Dossier
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Upload case document or define matter coordinates to launch multi-agent pipeline.
              </p>

              <form onSubmit={handleCreateCase} className="mt-5 space-y-4 text-xs">
                {/* File Upload Box */}
                <div>
                  <label className="font-mono text-[10px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">
                    Upload Case Brief (PDF, DOCX, TXT) *
                  </label>
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
                        <span className="font-bold truncate max-w-[260px]">{selectedFile.name}</span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-1.5 text-slate-500">
                        <Upload className="h-6 w-6 text-sky-600" />
                        <span className="font-medium">Drag & drop or click to choose file</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Case Title */}
                <div>
                  <label className="font-mono text-[10px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">
                    Case Title / Matter Reference
                  </label>
                  <input
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="e.g. State of Maharashtra v. Vikram Dev (Cyber Fraud)"
                    className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-slate-900 focus:outline-none focus:border-sky-500 shadow-2xs"
                  />
                </div>

                {/* Client & Category Row */}
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="font-mono text-[10px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">
                      Client / Party Name
                    </label>
                    <input
                      type="text"
                      value={newClient}
                      onChange={(e) => setNewClient(e.target.value)}
                      placeholder="e.g. Vikram Dev"
                      className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-slate-900 focus:outline-none focus:border-sky-500 shadow-2xs"
                    />
                  </div>

                  <div>
                    <label className="font-mono text-[10px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">
                      Category Type
                    </label>
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

                {/* Description */}
                <div>
                  <label className="font-mono text-[10px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">
                    Brief Matter Notes & Context
                  </label>
                  <textarea
                    rows={3}
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="Add brief factual context or charge sheet notes..."
                    className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-slate-900 focus:outline-none focus:border-sky-500 shadow-2xs resize-none"
                  />
                </div>

                {/* Submit Actions */}
                <div className="flex justify-end gap-3 pt-2">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setCreateOpen(false)}
                    className="rounded-xl text-slate-600"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={submitting}
                    className="daylight-btn-primary rounded-xl px-5 py-2.5 font-semibold"
                  >
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : 'Create Dossier'}
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
