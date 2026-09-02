import { Link, NavLink } from 'react-router-dom';
import {
  LayoutGrid, BookOpen, Users, Network, Brain,
  MessageSquare, Download, FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AnalysisModel } from '@/types/case-workspace';

export const MODULES = [
  { to: '', label: 'Advisory Summary', icon: LayoutGrid, key: '1', end: true },
  { to: 'statutes', label: 'Statutes & Precedents', icon: BookOpen, key: '2' },
  { to: 'evidence', label: 'Evidence & Trial', icon: Users, key: '3' },
  { to: 'graph', label: 'Knowledge Graph', icon: Network, key: '4' },
  { to: 'risk', label: 'Risk & Strategy', icon: Brain, key: '5' },
] as const;

interface ModuleRailProps {
  caseId: string;
  analysis: AnalysisModel | null;
  onAskAI: () => void;
}

export function ModuleRail({ caseId, analysis, onAskAI }: ModuleRailProps) {
  const counts: Record<string, number | undefined> = {
    '': analysis?.issues.length,
    statutes: analysis ? analysis.statutes.length + analysis.precedents.length : undefined,
    evidence: analysis?.evidence.length,
    graph: analysis?.kg.nodes.length,
    risk: undefined,
  };

  return (
    <aside className="sticky top-6 space-y-3">
      <nav className="space-y-1.5 rounded-2xl border border-slate-200/80 bg-white/80 p-3 shadow-sm backdrop-blur-md">
        <p className="eyebrow px-2 pb-1.5 pt-1">Workspace Modules</p>

        {MODULES.map((mod) => {
          const Icon = mod.icon;
          return (
            <NavLink
              key={mod.to}
              to={`/cases/${caseId}${mod.to ? `/${mod.to}` : ''}`}
              end={'end' in mod ? mod.end : false}
              title={`${mod.label} (press ${mod.key})`}
              className={({ isActive }) =>
                cn(
                  'group flex items-center justify-between rounded-xl px-3 py-2.5 text-[13px] transition-all',
                  isActive
                    ? 'bg-gradient-to-r from-sky-50 via-indigo-50 to-violet-50 font-semibold text-indigo-800 ring-1 ring-indigo-200'
                    : 'text-slate-600 hover:bg-slate-100/70 hover:text-slate-900'
                )
              }
            >
              <span className="flex items-center gap-2.5">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-slate-500 transition group-hover:bg-white group-aria-[current=page]:bg-gradient-to-tr group-aria-[current=page]:from-sky-600 group-aria-[current=page]:to-indigo-600 group-aria-[current=page]:text-white">
                  <Icon className="h-4 w-4" />
                </span>
                <span>{mod.label}</span>
              </span>
              <span className="flex items-center gap-1.5">
                {counts[mod.to] != null && counts[mod.to]! > 0 && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-semibold text-slate-500 group-aria-[current=page]:bg-white group-aria-[current=page]:text-indigo-700">
                    {counts[mod.to]}
                  </span>
                )}
                <kbd className="hidden rounded border border-slate-200 bg-slate-50 px-1 font-mono text-[9px] text-slate-400 lg:inline-block">
                  {mod.key}
                </kbd>
              </span>
            </NavLink>
          );
        })}
      </nav>

      <div className="space-y-2 rounded-2xl border border-slate-200/80 bg-white/80 p-3 shadow-sm backdrop-blur-md">
        <button
          onClick={onAskAI}
          className="flex w-full cursor-pointer items-center gap-2.5 rounded-xl bg-gradient-to-r from-violet-50 to-indigo-50 px-3.5 py-2.5 text-[13px] font-semibold text-violet-800 ring-1 ring-violet-200 transition hover:from-violet-100 hover:to-indigo-100"
        >
          <MessageSquare className="h-4 w-4 text-violet-600" strokeWidth={1.8} />
          Ask LexOS AI
        </button>
        <Link
          to={`/cases/${caseId}/report`}
          className="flex w-full items-center gap-2.5 rounded-xl px-3.5 py-2 text-[12px] font-medium text-slate-500 transition hover:text-indigo-700 hover:bg-slate-50"
        >
          <FileText className="h-3.5 w-3.5" strokeWidth={1.8} />
          Compiled Opinion Report
        </Link>
      </div>
    </aside>
  );
}
