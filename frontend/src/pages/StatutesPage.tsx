import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  BookOpen,
  Search,
  ChevronRight,
  ChevronDown,
  Bookmark,
  Scale,
  FileText,
  BookmarkCheck,
  Layers
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SectionNode {
  id: string;
  number: string;
  title: string;
  text: string;
  ipcMapping?: string;
}

interface ChapterNode {
  id: string;
  title: string;
  sections: SectionNode[];
}

interface ActNode {
  id: string;
  title: string;
  chapters: ChapterNode[];
}

export default function StatutesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSection, setSelectedSection] = useState<SectionNode | null>({
    id: 'bns-103',
    number: 'Section 103',
    title: 'Punishment for murder',
    text: 'Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine. (1) Except in the case of murder of a member of a Scheduled Caste or a Scheduled Tribe, where it shall be as provided...',
    ipcMapping: 'Section 302 of the Indian Penal Code (IPC)'
  });
  
  const [bookmarkedSections, setBookmarkedSections] = useState<string[]>(['bns-103']);
  const [expandedActs, setExpandedActs] = useState<string[]>(['bns']);
  const [expandedChapters, setExpandedChapters] = useState<string[]>(['bns-c5']);

  const actsData: ActNode[] = [
    {
      id: 'constitution',
      title: 'Constitution of India, 1950',
      chapters: [
        {
          id: 'const-c3',
          title: 'Part III - Fundamental Rights',
          sections: [
            { id: 'const-14', number: 'Article 14', title: 'Equality before law', text: 'The State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India.' },
            { id: 'const-19', number: 'Article 19', title: 'Protection of certain rights regarding freedom of speech', text: 'All citizens shall have the right— (a) to freedom of speech and expression; (b) to assemble peaceably and without arms...' },
            { id: 'const-21', number: 'Article 21', title: 'Protection of life and personal liberty', text: 'No person shall be deprived of his life or personal liberty except according to procedure established by law.' }
          ]
        }
      ]
    },
    {
      id: 'bns',
      title: 'Bharatiya Nyaya Sanhita, 2023 (BNS)',
      chapters: [
        {
          id: 'bns-c5',
          title: 'Chapter V - Offences Against the Human Body',
          sections: [
            { id: 'bns-100', number: 'Section 100', title: 'Culpable homicide', text: 'Whoever causes death by doing an act with the intention of causing death, or with the intention of causing such bodily injury as is likely to cause death, commits the offence of culpable homicide.', ipcMapping: 'Section 299 of IPC' },
            { id: 'bns-103', number: 'Section 103', title: 'Punishment for murder', text: 'Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine.', ipcMapping: 'Section 302 of IPC' }
          ]
        }
      ]
    }
  ];

  const toggleAct = (id: string) => {
    setExpandedActs(prev => prev.includes(id) ? prev.filter(a => a !== id) : [...prev, id]);
  };

  const toggleChapter = (id: string) => {
    setExpandedChapters(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]);
  };

  const toggleBookmark = (id: string) => {
    setBookmarkedSections(prev => prev.includes(id) ? prev.filter(b => b !== id) : [...prev, id]);
  };

  return (
    <div className="container mx-auto p-6 lg:p-8 flex flex-col h-[calc(100vh-4rem)] overflow-hidden">
      {/* Title & Search */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/5 pb-4 mb-4">
        <div className="text-left">
          <h1 className="text-2xl font-bold text-white">Statutory Codes Tree View</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Browse chapters, articles, and sections inside statutory frameworks.</p>
        </div>
        <div className="relative w-full max-w-xs">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search sections (e.g. Section 103)..."
            className="w-full rounded-xl border border-white/5 bg-card/40 py-2.5 pl-10 pr-4 text-xs text-white focus:outline-none"
          />
          <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-muted-foreground" />
        </div>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden relative">
        {/* Left Side: Expandable Statute Tree Panel */}
        <div className="flex-1 rounded-xl border border-white/5 bg-card/25 p-4 overflow-y-auto text-left h-full">
          <div className="space-y-4">
            {actsData.map((act) => {
              const actExpanded = expandedActs.includes(act.id);
              return (
                <div key={act.id} className="space-y-1">
                  {/* Act Header */}
                  <button
                    onClick={() => toggleAct(act.id)}
                    className="flex w-full items-center gap-2 rounded-lg bg-white/5 px-3 py-2 text-xs font-bold text-white hover:bg-white/10 transition-colors"
                  >
                    {actExpanded ? <ChevronDown className="h-4 w-4 text-primary shrink-0" /> : <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />}
                    <BookOpen className="h-4 w-4 text-primary shrink-0" />
                    <span className="truncate">{act.title}</span>
                  </button>

                  {/* Act Chapters */}
                  {actExpanded && (
                    <div className="pl-4 space-y-1.5 mt-1.5">
                      {act.chapters.map((chap) => {
                        const chapExpanded = expandedChapters.includes(chap.id);
                        return (
                          <div key={chap.id} className="space-y-1">
                            <button
                              onClick={() => toggleChapter(chap.id)}
                              className="flex w-full items-center gap-2 rounded-md bg-white/5 px-2 py-1.5 text-[11px] font-semibold text-slate-300 hover:bg-white/8 transition-colors"
                            >
                              {chapExpanded ? <ChevronDown className="h-3.5 w-3.5 text-primary shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />}
                              <span className="truncate">{chap.title}</span>
                            </button>

                            {/* Chapter Sections */}
                            {chapExpanded && (
                              <div className="pl-4 space-y-1 mt-1">
                                {chap.sections.map((sec) => (
                                  <button
                                    key={sec.id}
                                    onClick={() => setSelectedSection(sec)}
                                    className={`flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-[11px] text-left transition-all ${
                                      selectedSection?.id === sec.id
                                        ? 'bg-primary/10 text-primary font-bold'
                                        : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
                                    }`}
                                  >
                                    <FileText className="h-3.5 w-3.5 shrink-0" />
                                    <span className="font-semibold text-white">{sec.number}</span>
                                    <span className="truncate text-muted-foreground">— {sec.title}</span>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Side: Selected Section Reader Panel */}
        <div className="w-96 shrink-0 flex flex-col gap-4 overflow-y-auto pr-1">
          {selectedSection ? (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="rounded-xl border border-white/5 bg-card/30 backdrop-blur-md p-5 space-y-4 text-left flex flex-col h-full"
            >
              {/* Header section name & bookmark */}
              <div className="flex items-center justify-between border-b border-white/5 pb-3">
                <div className="flex items-center gap-2">
                  <Scale className="h-4.5 w-4.5 text-primary" />
                  <h3 className="font-bold text-white text-sm">{selectedSection.number}</h3>
                </div>
                <button
                  onClick={() => toggleBookmark(selectedSection.id)}
                  className="text-muted-foreground hover:text-white p-1 rounded transition-colors"
                >
                  {bookmarkedSections.includes(selectedSection.id) ? (
                    <BookmarkCheck className="h-4.5 w-4.5 text-primary" />
                  ) : (
                    <Bookmark className="h-4.5 w-4.5" />
                  )}
                </button>
              </div>

              {/* Title and full text */}
              <div className="flex-1 space-y-4 overflow-y-auto pr-1">
                <div>
                  <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Statute Title</span>
                  <h4 className="text-sm font-extrabold text-white mt-0.5">{selectedSection.title}</h4>
                </div>

                {selectedSection.ipcMapping && (
                  <div className="rounded-lg bg-primary/5 border border-primary/15 p-3">
                    <span className="text-[9px] font-bold text-primary uppercase tracking-wider">Corresponding IPC Provision</span>
                    <p className="text-xs text-white font-semibold mt-0.5">{selectedSection.ipcMapping}</p>
                  </div>
                )}

                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Statutory Text</span>
                  <p className="text-xs text-slate-300 leading-relaxed leading-5 pt-1 whitespace-pre-line">
                    {selectedSection.text}
                  </p>
                </div>
              </div>

              {/* Actions footer */}
              <div className="border-t border-white/5 pt-3">
                <Button size="sm" className="w-full bg-secondary text-white hover:bg-secondary/90">
                  Analyze Section under active case
                </Button>
              </div>
            </motion.div>
          ) : (
            <div className="rounded-xl border border-white/5 bg-card/25 p-5 text-center flex flex-col items-center justify-center h-full text-muted-foreground">
              <Layers className="h-8 w-8 mb-2" />
              <p className="text-xs">Select any statute article or section in the code tree to read the full legislative clauses.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
