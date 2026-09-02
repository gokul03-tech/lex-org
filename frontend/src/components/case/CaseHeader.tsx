import { Link } from 'react-router-dom';
import { ChevronLeft, Scale, Calendar, BookOpen, Download, FileText, FileType, Trash2, FileSignature } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { MiniGauge, StatusDot } from './primitives';
import type { WorkspaceData } from '@/types/case-workspace';

interface CaseHeaderProps {
  data: WorkspaceData;
  onExport: (format: 'pdf' | 'docx') => void;
  onOpenDrafting?: () => void;
  onDelete?: () => void;
}

export function CaseHeader({ data, onExport, onOpenDrafting, onDelete }: CaseHeaderProps) {
  const a = data.analysis;
  const title = a?.caseTitle.value || data.caseInfo.title || 'Case Dossier';

  const chip =
    'inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white/80 px-2.5 py-1 font-mono text-[11px] text-slate-600 shadow-sm backdrop-blur-sm';

  return (
    <header className="border-b border-slate-200/80 bg-[#FAF9F6]/85 px-6 pb-5 pt-5 backdrop-blur-md lg:px-10">
      {/* Breadcrumb */}
      <nav className="mb-2 flex items-center gap-1.5 text-xs text-slate-500">
        <Link to="/cases" className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 transition hover:bg-slate-100 hover:text-slate-800">
          <ChevronLeft className="h-3 w-3" /> All Dossiers
        </Link>
        <span className="text-slate-300">/</span>
        <span className="max-w-md truncate font-medium text-slate-700">{title}</span>
      </nav>

      <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-center">
        <div className="min-w-0 space-y-2">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-tr from-sky-600 to-indigo-600 text-white shadow-sm">
              <Scale className="h-[18px] w-[18px]" strokeWidth={1.8} />
            </div>
            <h1 className="truncate font-serif text-xl font-semibold tracking-tight text-slate-900 md:text-2xl" title={title}>
              {title}
            </h1>
            {a && <StatusDot status={a.caseTitle.status} compact />}
          </div>

          {/* Chips — hidden when empty */}
          {(a?.courtChip.status !== 'not_found' || a?.dateChip.status !== 'not_found' || a?.citationsChip.status !== 'not_found') && (
            <div className="flex flex-wrap items-center gap-2">
              {a && a.courtChip.status !== 'not_found' && (
                <span className={`${chip} !text-indigo-700`}>
                  <Scale className="h-3 w-3" strokeWidth={1.8} />
                  {a.courtChip.value}
                </span>
              )}
              {a && a.dateChip.status !== 'not_found' && (
                <span className={chip}>
                  <Calendar className="h-3 w-3 text-slate-400" strokeWidth={1.8} />
                  {a.dateChip.value}
                </span>
              )}
              {a && a.citationsChip.status !== 'not_found' && (
                <span className={chip}>
                  <BookOpen className="h-3 w-3 text-violet-500" strokeWidth={1.8} />
                  {a.citationsChip.value}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {a && (
            <div className="mr-1 hidden items-center gap-2 rounded-lg border border-slate-200 bg-white/80 px-2.5 py-1.5 shadow-sm sm:flex">
              <MiniGauge score={a.trustScore} />
              <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-slate-500">Trust</span>
            </div>
          )}
          {onOpenDrafting && (
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenDrafting}
              className="h-9 gap-1.5 rounded-lg text-[13px] border-violet-300 bg-gradient-to-r from-violet-50 to-indigo-50 text-violet-800 hover:from-violet-100 hover:to-indigo-100 shadow-xs"
            >
              <FileSignature className="h-3.5 w-3.5 text-violet-600" /> Draft Pleadings
            </Button>
          )}
          <Button size="sm" onClick={() => onExport('pdf')} className="h-9 gap-1.5 rounded-lg text-[13px] bg-indigo-600 hover:bg-indigo-700 text-white">
            <FileText className="h-3.5 w-3.5" /> PDF Brief
          </Button>
          <Button variant="outline" size="sm" onClick={() => onExport('docx')} className="h-9 gap-1.5 rounded-lg text-[13px] border-slate-300">
            <FileType className="h-3.5 w-3.5 text-indigo-600" /> Word DOCX
          </Button>
          {onDelete && (
            <Button variant="outline" size="sm" onClick={onDelete} className="h-9 gap-1.5 rounded-lg text-[13px] text-destructive hover:bg-destructive/10 hover:text-destructive">
              <Trash2 className="h-3.5 w-3.5" /> Delete
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
