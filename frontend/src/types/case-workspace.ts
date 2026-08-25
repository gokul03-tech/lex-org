export type FieldStatus = 'extracted' | 'inferred' | 'not_found';

export interface MetaField {
  value: string;
  status: FieldStatus;
}

export type CategoryKind = 'bail' | 'arbitration' | 'writ' | 'civil';

export interface Issue {
  text: string;
  source: 'document' | 'ai';
  evidence?: string;
  page?: string;
}

export interface StatuteItem {
  num: string;
  act: string;
  display: string;
  context?: string;
}

export interface Precedent {
  name: string;
  citation: string;
  year?: string;
  similarity?: number;
  summary?: string;
}

export interface TimelineEvent {
  date: string;
  fact: string;
  page?: string;
}

export interface EvidenceItem {
  label: string;
  detail: string;
  reliability: 'HIGH' | 'DISPUTED';
}

export interface TaggedList {
  items: string[];
  source: 'document' | 'ai';
}

export interface KgNode {
  id: string;
  label: string;
  kind: 'case' | 'party' | 'judge' | 'court' | 'act' | 'section' | 'evidence' | 'citation' | 'other';
  page?: string;
  quote?: string;
  confidence?: number;
}

export interface KgEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
}

export interface AnalysisModel {
  caseTitle: MetaField;
  category: CategoryKind;
  courtChip: MetaField;
  dateChip: MetaField;
  citationsChip: MetaField;
  trustScore: number;
  confidenceReason: string;
  summary: MetaField;
  metadataTiles: { key: string; label: string; field: MetaField }[];
  acts: string[];
  statutes: StatuteItem[];
  articles: StatuteItem[];
  precedents: Precedent[];
  timeline: TimelineEvent[];
  evidence: EvidenceItem[];
  submissionsA: { heading: string; items: string[] };
  submissionsB: { heading: string; items: string[] };
  issues: Issue[];
  riskStrengths: TaggedList;
  riskGaps: TaggedList;
  riskAction: TaggedList;
  conclusion: MetaField;
  agents: { name: string; ms: number }[];
  kg: { nodes: KgNode[]; edges: KgEdge[] };
}

export interface WorkspaceData {
  caseId: string;
  caseInfo: CaseInfo;
  analysis: AnalysisModel | null;
  rawAnalysis: unknown;
}

export interface CaseInfo {
  id: string;
  title: string;
  caseType: string | null;
  status: string;
  createdAt: string;
  description: string | null;
}
