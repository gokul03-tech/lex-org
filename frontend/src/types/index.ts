export interface Case {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  case_type: string | null;
  court_name: string | null;
  case_number: string | null;
  filing_date: string | null;
  status: CaseStatus;
  created_at: string;
  updated_at: string;
}

export type CaseStatus =
  | 'draft'
  | 'documents_uploaded'
  | 'analyzing'
  | 'analysis_complete'
  | 'report_generated'
  | 'archived';

export interface Document {
  id: string;
  case_id: string;
  filename: string;
  document_type: string;
  status: string;
  parsed_text: string | null;
  chunk_count: number;
  page_count: number | null;
  created_at: string;
}

export interface AgentResult {
  agent_name: string;
  confidence: number;
  output: Record<string, unknown>;
  execution_time_ms: number;
  error: string | null;
}

export interface Analysis {
  id: string;
  case_id: string;
  status: string;
  agent_results: AgentResult[];
  confidence_scores: Record<string, number>;
  trust_score: number;
  created_at: string;
}

export interface ReportSection {
  title: string;
  content: string | Record<string, unknown>;
  order: number;
}

export interface Report {
  id: string;
  case_id: string;
  sections: ReportSection[];
  trust_score: number;
  confidence_scores: Record<string, number>;
  explanation_graph: Record<string, unknown> | null;
  knowledge_graph: Record<string, unknown> | null;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'advocate' | 'researcher' | 'student' | 'admin';
  is_active: boolean;
  created_at: string;
}

export interface RAGResult {
  chunk_id: string;
  text: string;
  score: number;
  source: string;
  metadata: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
