import { create } from 'zustand';

interface AppState {
  sidebarCollapsed: boolean;
  insightPanelOpen: boolean;
  activeModel: 'qwen' | 'deepseek';
  agentStatus: 'idle' | 'thinking' | 'analyzing' | 'verifying' | 'complete';
  globalSearchQuery: string;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setInsightPanelOpen: (open: boolean) => void;
  setActiveModel: (model: 'qwen' | 'deepseek') => void;
  setAgentStatus: (status: 'idle' | 'thinking' | 'analyzing' | 'verifying' | 'complete') => void;
  setGlobalSearchQuery: (query: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  insightPanelOpen: false,
  activeModel: 'qwen',
  agentStatus: 'idle',
  globalSearchQuery: '',
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setInsightPanelOpen: (open) => set({ insightPanelOpen: open }),
  setActiveModel: (model) => set({ activeModel: model }),
  setAgentStatus: (status) => set({ agentStatus: status }),
  setGlobalSearchQuery: (query) => set({ globalSearchQuery: query }),
}));
