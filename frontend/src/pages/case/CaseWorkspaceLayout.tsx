import { useCallback, useEffect, useState } from 'react';
import { Outlet, useLocation, useNavigate, useParams, useOutletContext } from 'react-router-dom';
import { motion } from 'framer-motion';
import { RefreshCw } from 'lucide-react';
import { ChatDrawer } from '@/components/ui/chat-drawer';
import { CommandMenu } from '@/components/ui/command-menu';
import { CaseHeader } from '@/components/case/CaseHeader';
import { ModuleRail, MODULES } from '@/components/case/ModuleRail';
import { EmptyState, PageSkeleton } from '@/components/case/primitives';
import { useCaseWorkspace } from '@/hooks/useCaseWorkspace';
import { exportDocx, exportJson } from '@/lib/exporters';
import apiClient from '@/lib/api';
import type { WorkspaceData } from '@/types/case-workspace';

export interface WorkspaceOutlet {
  caseId: string;
  data: WorkspaceData | undefined;
  isLoading: boolean;
  refresh: () => void;
  openChat: () => void;
}

const MODULE_PATHS = ['', 'statutes', 'evidence', 'graph', 'risk'];

export function useWorkspace(): WorkspaceOutlet {
  return useOutletContext<WorkspaceOutlet>();
}

export default function CaseWorkspaceLayout() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { data, isLoading, isError, refetch } = useCaseWorkspace(caseId);

  const [chatOpen, setChatOpen] = useState(false);
  const refresh = useCallback(() => refetch(), [refetch]);
  const openChat = useCallback(() => setChatOpen(true), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const target = e.target as HTMLElement | null;
      if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return;
      if ((target as HTMLElement | null)?.isContentEditable) return;
      const idx = ['1', '2', '3', '4', '5'].indexOf(e.key);
      if (idx === -1 || !caseId) return;
      e.preventDefault();
      const sub = MODULE_PATHS[idx];
      navigate(`/cases/${caseId}${sub ? `/${sub}` : ''}`);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [caseId, navigate]);

  const handleExport = useCallback(
    (format: 'pdf' | 'json' | 'docx') => {
      if (!caseId) return;
      if (format === 'json') exportJson(data?.rawAnalysis, caseId);
      else if (format === 'docx' && data?.analysis) exportDocx(data.analysis, caseId);
      else window.print();
    },
    [data, caseId]
  );

  const handleDelete = useCallback(() => {
    if (!caseId) return;
    if (!window.confirm('Are you sure you want to delete this case dossier? All associated documents and analysis will be permanently deleted.')) {
      return;
    }
    apiClient
      .delete(`/cases/${caseId}`)
      .then(() => navigate('/cases'))
      .catch((err) => {
        console.error('Failed to delete case:', err);
        alert('Failed to delete case folder. Please try again.');
      });
  }, [caseId, navigate]);

  if (!caseId) return null;

  const outletValue: WorkspaceOutlet = {
    caseId,
    data,
    isLoading,
    refresh,
    openChat,
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <CommandMenu
        onExportJson={() => handleExport('json')}
        onExportPdf={() => handleExport('pdf')}
      />
      {data ? (
        <div className="print:hidden">
          <CaseHeader data={data} onExport={handleExport} onDelete={handleDelete} />
        </div>
      ) : (
        <header className="border-b border-slate-200/80 bg-[#FAF9F6]/85 px-6 pb-5 pt-5 backdrop-blur-md lg:px-10 print:hidden">
          <div className="h-9 w-2/3 animate-pulse rounded-lg bg-slate-200/70" />
        </header>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto grid max-w-[1600px] items-start gap-6 px-6 py-6 lg:grid-cols-[248px_minmax(0,1fr)] lg:px-10">
          {!isLoading && !isError && (
            <>
              {/* Mobile module tabs */}
              <div className="flex gap-1.5 overflow-x-auto rounded-xl border border-slate-200/80 bg-white/80 p-1.5 backdrop-blur-md lg:hidden">
                {MODULES.map((mod) => {
                  const target = `/cases/${caseId}${mod.to ? `/${mod.to}` : ''}`;
                  const active =
                    mod.to === ''
                      ? location.pathname === target
                      : location.pathname.startsWith(target);
                  return (
                    <button
                      key={mod.to}
                      onClick={() => navigate(target)}
                      className={`shrink-0 cursor-pointer rounded-lg px-3.5 py-2 text-xs font-medium transition ${
                        active
                          ? 'bg-gradient-to-r from-sky-600 to-indigo-600 text-white shadow-sm'
                          : 'text-slate-500 hover:bg-slate-100'
                      }`}
                    >
                      {mod.to === '' ? 'Summary' : mod.label}
                    </button>
                  );
                })}
              </div>

              {/* Desktop module rail */}
              <div className="hidden lg:block">
                <ModuleRail
                  caseId={caseId}
                  analysis={data?.analysis ?? null}
                  onAskAI={openChat}
                  onExportJson={() => handleExport('json')}
                />
              </div>
            </>
          )}

          <motion.main
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22 }}
            className="min-w-0"
          >
            {isLoading ? (
              <PageSkeleton />
            ) : isError ? (
              <EmptyState
                icon={RefreshCw}
                title="Could not load this dossier"
                description="The workspace could not reach the analysis service. Check the backend connection and retry."
                action={
                  <button onClick={() => refetch()} className="daylight-btn-primary cursor-pointer rounded-lg px-4 py-2 text-sm">
                    Retry
                  </button>
                }
              />
            ) : (
              <Outlet context={outletValue} />
            )}
          </motion.main>
        </div>
      </div>

      <ChatDrawer
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
        caseTitle={data?.analysis?.caseTitle.value || data?.caseInfo.title || 'Case'}
        suggestionChips={[
          'Summarize the strongest statutory basis in this matter.',
          'Which precedents bind this court and why?',
          'What are the top procedural risks in the record?',
        ]}
        onSendMessage={async (msg, model) => {
          try {
            const res = await apiClient.post('/analysis/chat', {
              case_id: caseId,
              message: msg,
              model_name: model,
            });
            return res.data?.reply || res.data?.content || 'Analysis synthesized based on statutory grounding.';
          } catch {
            return 'The advisory service is unavailable right now. Please retry shortly.';
          }
        }}
      />
    </div>
  );
}
