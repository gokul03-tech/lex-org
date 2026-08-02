import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  SlidersHorizontal,
  ChevronRight,
  BookOpen,
  Scale,
  Calendar,
  User,
  ExternalLink,
  Bookmark,
  ChevronDown
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SearchResult {
  id: string;
  title: string;
  act: string;
  section?: string;
  court?: string;
  judge?: string;
  year: string;
  snippet: string;
  score: number;
}

export default function LegalResearchPage() {
  const [query, setQuery] = useState('');
  const [court, setCourt] = useState('All');
  const [year, setYear] = useState('');
  const [judge, setJudge] = useState('');
  const [section, setSection] = useState('');
  const [results, setResults] = useState<SearchResult[]>([
    {
      id: 'R1',
      title: 'K.S. Puttaswamy v. Union of India',
      act: 'Constitution of India',
      section: 'Article 21',
      court: 'Supreme Court of India',
      judge: 'D.Y. Chandrachud, J.',
      year: '2017',
      snippet: 'Privacy is a constitutionally protected right which emerges primarily from the guarantee of life and personal liberty in Article 21 of the Constitution. Elements of privacy arise in varying contexts from the other facets of freedom...',
      score: 0.94
    },
    {
      id: 'R2',
      title: 'Navtej Singh Johar v. Union of India',
      act: 'Constitution of India / BNS',
      section: 'Article 21 / Section 103',
      court: 'Supreme Court of India',
      judge: 'Dipak Misra, C.J.',
      year: '2018',
      snippet: 'The constitutional protection of personal liberty and autonomy extends to individual choice in intimate partnerships. Under Article 21, the right to dignity guarantees the freedom to express affection without fear of criminal prosecution...',
      score: 0.88
    }
  ]);
  
  const [filtersOpen, setFiltersOpen] = useState(true);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // In a real integration, this triggers a backend search request.
    // For now, we mock the result set.
  };

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-6">
      <div className="flex items-center justify-between border-b border-white/5 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Statutory & Case Law Search</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Explore sections, articles, and judgments with advanced query filters.</p>
        </div>
      </div>

      {/* Main Search Panel */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search across acts, sections, or case keywords (e.g. bail conditions for economic offences)..."
              className="w-full rounded-xl border border-white/5 bg-card/40 py-3 pl-11 pr-4 text-sm text-white focus:border-primary focus:outline-none"
            />
            <Search className="absolute left-4 top-3.5 h-4.5 w-4.5 text-muted-foreground" />
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={() => setFiltersOpen(!filtersOpen)}
            className={`gap-2 h-11 border-white/5 ${filtersOpen ? 'bg-primary/10 text-primary' : 'bg-card/20'}`}
          >
            <SlidersHorizontal className="h-4.5 w-4.5" />
            Filters
          </Button>
          <Button type="submit" className="h-11 bg-primary px-6 text-primary-foreground font-semibold">
            Search
          </Button>
        </div>

        {/* Collapsible Advanced Filters */}
        <AnimatePresence>
          {filtersOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden rounded-xl border border-white/5 bg-card/20 backdrop-blur-md"
            >
              <div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
                {/* Court Filter */}
                <div className="space-y-1.5 text-left">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Jurisdiction/Court</label>
                  <select
                    value={court}
                    onChange={(e) => setCourt(e.target.value)}
                    className="w-full rounded-lg border border-white/5 bg-muted/50 p-2 text-xs text-white focus:border-primary focus:outline-none appearance-none"
                  >
                    <option value="All" className="bg-card">All Courts</option>
                    <option value="SC" className="bg-card">Supreme Court of India</option>
                    <option value="DHC" className="bg-card">Delhi High Court</option>
                    <option value="BHC" className="bg-card">Bombay High Court</option>
                  </select>
                </div>

                {/* Section/Article Filter */}
                <div className="space-y-1.5 text-left">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Specific Section / Article</label>
                  <input
                    type="text"
                    value={section}
                    onChange={(e) => setSection(e.target.value)}
                    placeholder="e.g. Section 302, Article 21"
                    className="w-full rounded-lg border border-white/5 bg-muted/50 p-2 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>

                {/* Judge Filter */}
                <div className="space-y-1.5 text-left">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Presiding Judge</label>
                  <input
                    type="text"
                    value={judge}
                    onChange={(e) => setJudge(e.target.value)}
                    placeholder="e.g. D.Y. Chandrachud"
                    className="w-full rounded-lg border border-white/5 bg-muted/50 p-2 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>

                {/* Year Filter */}
                <div className="space-y-1.5 text-left">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Decision Year</label>
                  <input
                    type="text"
                    value={year}
                    onChange={(e) => setYear(e.target.value)}
                    placeholder="e.g. 2017, 2023"
                    className="w-full rounded-lg border border-white/5 bg-muted/50 p-2 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </form>

      {/* Results Section */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider text-left">
          Search Results ({results.length} matched)
        </h3>

        <div className="grid gap-4">
          {results.map((res) => (
            <motion.div
              key={res.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-xl border border-white/5 bg-card/30 hover:border-primary/20 backdrop-blur-md p-5 text-left flex flex-col gap-3 group transition-all"
            >
              {/* Header Metadata */}
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-primary/10 border border-primary/25 px-2 py-0.5 text-[9px] font-bold text-primary">
                    Similarity: {Math.round(res.score * 100)}%
                  </span>
                  <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                    <BookOpen className="h-3 w-3" />
                    {res.act} {res.section ? `(${res.section})` : ''}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button className="text-muted-foreground hover:text-white p-1 rounded">
                    <Bookmark className="h-3.5 w-3.5" />
                  </button>
                  <button className="text-muted-foreground hover:text-white p-1 rounded">
                    <ExternalLink className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              {/* Title / Precedent Name */}
              <h2 className="text-sm font-bold text-white group-hover:text-primary transition-colors">
                {res.title}
              </h2>

              {/* Snippet text */}
              <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                {res.snippet}
              </p>

              {/* Footer info: Court, Judge, Year */}
              <div className="flex flex-wrap items-center gap-4 text-[10px] text-muted-foreground border-t border-white/5 pt-3 mt-1">
                {res.court && (
                  <span className="flex items-center gap-1">
                    <Scale className="h-3 w-3" />
                    {res.court}
                  </span>
                )}
                {res.judge && (
                  <span className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    {res.judge}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  Decided: {res.year}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
