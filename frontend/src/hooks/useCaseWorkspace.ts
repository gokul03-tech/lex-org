import { useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api';
import { normalizeAnalysis } from '@/lib/analysis-normalizer';
import type { WorkspaceData } from '@/types/case-workspace';

export function useCaseWorkspace(caseId: string | undefined) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['case-workspace', caseId],
    enabled: Boolean(caseId),
    queryFn: async (): Promise<WorkspaceData> => {
      const caseRes = await apiClient.get(`/cases/${caseId}`);
      const raw = caseRes.data ?? {};

      let analysisRaw: unknown = null;
      try {
        const analysisRes = await apiClient.get(`/analysis/case/${caseId}`);
        if (analysisRes.data) analysisRaw = analysisRes.data;
      } catch {
        analysisRaw = null;
      }

      const caseInfo = {
        id: String(raw.id ?? caseId),
        title: String(raw.title ?? ''),
        caseType: (raw.case_type as string | null) ?? null,
        status: String(raw.status ?? ''),
        createdAt: String(raw.created_at ?? ''),
        description: (raw.description as string | null) ?? null,
      };

      return {
        caseId: String(caseId),
        caseInfo,
        analysis: normalizeAnalysis({
          analysis: analysisRaw as Record<string, any> | null,
          caseInfo: { title: caseInfo.title, caseType: caseInfo.caseType },
        }),
        rawAnalysis: analysisRaw,
      };
    },
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['case-workspace', caseId] });

  return { ...query, refresh };
}
