import * as React from 'react';
import { Command } from 'cmdk';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  FileText,
  BookOpen,
  Network,
  Download,
  RotateCcw,
  Scale,
  Sparkles,
} from 'lucide-react';

interface CommandMenuProps {
  onExportJson?: () => void;
  onExportPdf?: () => void;
  onRerunAnalysis?: () => void;
}

export function CommandMenu({
  onExportJson,
  onExportPdf,
  onRerunAnalysis,
}: CommandMenuProps) {
  const [open, setOpen] = React.useState(false);
  const navigate = useNavigate();

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key === 'k' && (e.metaKey || e.ctrlKey)) || e.key === '/') {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-slate-900/30 backdrop-blur-xs p-4 animate-in fade-in duration-150 text-left">
      <div
        className="fixed inset-0"
        onClick={() => setOpen(false)}
      />
      <Command
        className="relative z-50 w-full max-w-xl overflow-hidden rounded-2xl border border-slate-200 bg-white/95 shadow-2xl backdrop-blur-2xl text-slate-900"
      >
        <div className="flex items-center border-b border-slate-100 px-4">
          <Search className="h-4 w-4 text-slate-400 shrink-0 mr-2" />
          <Command.Input
            placeholder="Search cases, sections, precedents, or actions... (⌘K)"
            className="w-full bg-transparent py-3.5 text-sm outline-none placeholder:text-slate-400 font-sans"
            autoFocus
          />
          <kbd className="hidden sm:inline-flex rounded-md border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-500 font-semibold">
            ESC
          </kbd>
        </div>

        <Command.List className="max-h-80 overflow-y-auto p-2 text-xs space-y-1">
          <Command.Empty className="py-6 text-center text-slate-500">
            No legal records or commands found.
          </Command.Empty>

          <Command.Group heading="Navigation" className="px-2 py-1.5 font-mono text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            <Command.Item
              onSelect={() => {
                navigate('/dashboard');
                setOpen(false);
              }}
              className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-slate-700 hover:bg-sky-50 hover:text-sky-800 cursor-pointer transition"
            >
              <Scale className="h-4 w-4 text-sky-600" />
              <span className="font-medium">Dashboard & Case Workspace</span>
            </Command.Item>
            <Command.Item
              onSelect={() => {
                navigate('/cases');
                setOpen(false);
              }}
              className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-slate-700 hover:bg-sky-50 hover:text-sky-800 cursor-pointer transition"
            >
              <FileText className="h-4 w-4 text-sky-600" />
              <span className="font-medium">All Case Dossiers</span>
            </Command.Item>
            <Command.Item
              onSelect={() => {
                navigate('/admin');
                setOpen(false);
              }}
              className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-slate-700 hover:bg-purple-50 hover:text-purple-800 cursor-pointer transition"
            >
              <Network className="h-4 w-4 text-purple-600" />
              <span className="font-medium">Knowledge Graph & Ingestion Admin</span>
            </Command.Item>
          </Command.Group>

          <Command.Group heading="Actions" className="px-2 py-1.5 font-mono text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            <Command.Item
              onSelect={() => {
                onExportPdf?.();
                setOpen(false);
              }}
              className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-slate-700 hover:bg-emerald-50 hover:text-emerald-800 cursor-pointer transition"
            >
              <Download className="h-4 w-4 text-emerald-600" />
              <span className="font-medium">Export Judicial Brief (PDF Format)</span>
            </Command.Item>
            <Command.Item
              onSelect={() => {
                onExportJson?.();
                setOpen(false);
              }}
              className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-slate-700 hover:bg-emerald-50 hover:text-emerald-800 cursor-pointer transition"
            >
              <FileText className="h-4 w-4 text-emerald-600" />
              <span className="font-medium">Export Grounded Analysis JSON</span>
            </Command.Item>
            <Command.Item
              onSelect={() => {
                onRerunAnalysis?.();
                setOpen(false);
              }}
              className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-slate-700 hover:bg-amber-50 hover:text-amber-800 cursor-pointer transition"
            >
              <RotateCcw className="h-4 w-4 text-amber-600" />
              <span className="font-medium">Re-run 12-Agent Analysis Pipeline</span>
            </Command.Item>
          </Command.Group>

          <Command.Group heading="Statutes & Precedents Quick-Jump" className="px-2 py-1.5 font-mono text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            <Command.Item
              onSelect={() => setOpen(false)}
              className="flex items-center justify-between rounded-xl px-3 py-2 text-slate-700 hover:bg-sky-50 hover:text-sky-800 cursor-pointer transition"
            >
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-sky-600" />
                <span className="font-mono text-xs">Section 482 BNSS (Bail Power)</span>
              </div>
              <span className="font-mono text-[10px] text-slate-400">Statute</span>
            </Command.Item>
            <Command.Item
              onSelect={() => setOpen(false)}
              className="flex items-center justify-between rounded-xl px-3 py-2 text-slate-700 hover:bg-sky-50 hover:text-sky-800 cursor-pointer transition"
            >
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-sky-600" />
                <span className="font-mono text-xs">Section 63 BSA (Electronic Certificate)</span>
              </div>
              <span className="font-mono text-[10px] text-slate-400">Evidence</span>
            </Command.Item>
            <Command.Item
              onSelect={() => setOpen(false)}
              className="flex items-center justify-between rounded-xl px-3 py-2 text-slate-700 hover:bg-purple-50 hover:text-purple-800 cursor-pointer transition"
            >
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-purple-600" />
                <span className="font-medium text-xs">Sanjay Chandra v. CBI (2011) 1 SCC 694</span>
              </div>
              <span className="font-mono text-[10px] text-slate-400">Precedent</span>
            </Command.Item>
          </Command.Group>
        </Command.List>

        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-2 text-[10px] font-mono text-slate-400 bg-slate-50/50">
          <span>LexOrch-KG Command Palette</span>
          <span>Use ↑ ↓ to navigate, ↵ to select</span>
        </div>
      </Command>
    </div>
  );
}

export default CommandMenu;
