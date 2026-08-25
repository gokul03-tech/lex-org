import type {
  AnalysisModel, CategoryKind, EvidenceItem, FieldStatus, Issue, KgEdge,
  KgNode, MetaField, Precedent, StatuteItem, TaggedList, TimelineEvent,
} from '@/types/case-workspace';

type Any = Record<string, any>;

const JUNK_LABELS = new Set(['keyword', 'vector']);

export const cleanTitle = (raw?: string | null): string => {
  if (!raw) return '';
  return raw
    .replace(/\s+on\s+\d{1,2}\s+[A-Za-z]+,?\s+\d{4}.*$/i, '')
    .replace(/\.[A-Za-z0-9]{3,4}$/, '')
    .replace(/[_-]+/g, ' ')
    .trim();
};

const asStatus = (v: any): FieldStatus =>
  v === 'extracted' || v === 'inferred' ? v : 'not_found';

export function meta(raw: any, fallback = ''): MetaField {
  if (raw && typeof raw === 'object') {
    const val = raw.value;
    if (
      val !== undefined && val !== null && String(val).trim() !== '' &&
      String(val) !== 'Not found in document'
    ) {
      return { value: String(val), status: asStatus(raw.status ?? 'extracted') };
    }
    return { value: fallback, status: 'not_found' };
  }
  if (typeof raw === 'string' && raw.trim() && raw !== 'Not found in document') {
    return { value: raw.trim(), status: 'extracted' };
  }
  return { value: fallback, status: 'not_found' };
}

export function detectCategory(caseType?: string | null): CategoryKind {
  const t = (caseType || '').toLowerCase();
  if (t.includes('arbitration') || t.includes('commercial')) return 'arbitration';
  if (t.includes('writ') || t.includes('constitution')) return 'writ';
  if (t.includes('civil') || t.includes('property') || t.includes('contract')) return 'civil';
  return 'bail';
}

export const CATEGORY_ACCENT: Record<CategoryKind, { badge: string; dot: string; label: string }> = {
  bail: { badge: 'criminal', dot: 'bg-rose-500', label: 'Criminal / Bail' },
  arbitration: { badge: 'arbitration', dot: 'bg-amber-500', label: 'Arbitration' },
  writ: { badge: 'constitutional', dot: 'bg-emerald-500', label: 'Constitutional Writ' },
  civil: { badge: 'civil', dot: 'bg-sky-500', label: 'Civil Dispute' },
};

/** Category-aware submission column headings */
export function submissionHeadings(cat: CategoryKind): { a: string; b: string } {
  switch (cat) {
    case 'bail':
      return { a: 'State / Prosecution Case', b: 'Applicant / Defense Submissions' };
    case 'arbitration':
      return { a: 'Petitioner Submissions', b: 'Respondent Submissions' };
    case 'writ':
      return { a: 'Petitioner', b: 'Respondent / State' };
    case 'civil':
      return { a: 'Appellant / Plaintiff', b: 'Respondent / Defense' };
  }
}

/** Role word for conclusion sentences */
export function roleWord(cat: CategoryKind): string {
  switch (cat) {
    case 'bail': return 'applicant';
    case 'arbitration': case 'writ': return 'petitioner';
    case 'civil': return 'appellant';
  }
}

export function stageLabel(cat: CategoryKind): string {
  switch (cat) {
    case 'bail': return 'Regular Bail Application';
    case 'arbitration': return 'Section 34 Arbitral Challenge';
    case 'writ': return 'Writ Petition (Art. 226/32)';
    case 'civil': return 'Civil Suit — Trial Stage';
  }
}

function toList(v: any): string[] {
  if (!v) return [];
  if (Array.isArray(v)) return v.map((x) => (typeof x === 'string' ? x : x?.text || x?.item || '')).filter(Boolean);
  if (typeof v === 'string') {
    return v
      .split(/(?<=[.!?])\s+(?=[A-Z])/)
      .map((s) => s.trim())
      .filter((s) => s.length > 12);
  }
  return [];
}

const tagged = (items: string[], hasExplicitSource: boolean): TaggedList =>
  ({ items, source: hasExplicitSource ? 'document' : 'ai' });

function normalizeStatutes(sections: any, statutes: any): StatuteItem[] {
  const out: StatuteItem[] = [];
  const seen = new Set<string>();
  const push = (num: string, act: string, context?: string) => {
    if (!num && !act) return;
    const display = num && act ? `Section ${num.replace(/^Section\s+/i, '')} — ${act}` : num || act;
    const key = display.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ num, act, display, context });
  };

  if (Array.isArray(statutes)) {
    for (const s of statutes) {
      if (typeof s === 'string') push(s, '');
      else if (s?.num || s?.display) push(String(s.num ?? ''), String(s.act ?? ''), s.display ?? s.context);
    }
  }
  if (Array.isArray(sections)) {
    for (const s of sections) {
      if (typeof s === 'string') {
        push(s.replace(/\s*[—-]\s*/g, ' — '), '');
      } else if (s?.section_number || s?.section || s?.num) {
        const rawNum = s.num ?? s.section_number;
        const numPart = rawNum != null ? String(rawNum) : String(s.section ?? '');
        push(
          numPart,
          String(s.act ?? ''),
          s.title ? `${s.title}. ${s.text ?? s.description ?? ''}`.trim() : (s.relevance ?? s.text ?? s.description)
        );
      }
    }
  }
  return out.slice(0, 24);
}

function normalizeArticles(articles: any): StatuteItem[] {
  if (!Array.isArray(articles)) return [];
  return articles
    .map((a: any) => {
      if (typeof a === 'string') return { num: a, act: 'Constitution of India', display: a };
      const num = String(a.article ?? a.num ?? a.number ?? '');
      const act = String(a.act ?? 'Constitution of India');
      return { num, act, display: num ? `Article ${num.replace(/^Article\s+/i, '')}` : act, context: a.context ?? a.desc };
    })
    .filter((a) => a.display);
}

function normalizePrecedents(precedents: any, selfTitle: string, selfCitation: string): Precedent[] {
  if (!Array.isArray(precedents)) return [];
  const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
  const selfNorm = norm(selfTitle);
  return precedents
    .map((p: any): Precedent => {
      const name = String(p.case_name ?? p.name ?? p.case ?? '').replace(/^Source:\s*/i, '').trim();
      let citation = String(p.citation ?? '').trim();
      if (citation.startsWith('Source:')) citation = '';
      const year = p.year ? String(p.year) : (citation.match(/\((\d{4})\)/)?.[1] ?? undefined);
      let sim = typeof p.similarity === 'number' ? p.similarity : typeof p.relevance_score === 'number' ? p.relevance_score : undefined;
      if (sim !== undefined) sim = sim <= 1 ? Math.round(sim * 100) : Math.round(sim);
      if (sim !== undefined) sim = Math.max(0, Math.min(100, sim));
      return {
        name,
        citation: citation || (year ? `(${year})` : ''),
        year,
        similarity: sim,
        summary: p.summary ?? p.rule ?? p.holdings ?? undefined,
      };
    })
    .filter((p) => {
      if (!p.name || JUNK_LABELS.has(p.name.toLowerCase())) return false;
      if (selfNorm && norm(p.name) === selfNorm) return false;
      if (selfCitation && p.citation && norm(p.citation) === norm(selfCitation)) return false;
      return true;
    });
}

function normalizeEvidence(evidence: any): EvidenceItem[] {
  if (!Array.isArray(evidence)) return [];
  return evidence
    .filter((e) => !(typeof e === 'object' && e?.label && JUNK_LABELS.has(String(e.label).toLowerCase())))
    .map((e: any, i: number) => {
      const label = typeof e === 'string' ? `Evidentiary Record #${i + 1}` : String(e.label ?? e.label_text ?? `Record #${i + 1}`);
      const detail = typeof e === 'string' ? e : String(e.detail ?? e.description ?? e.text ?? '');
      const rel = String(e?.reliability ?? 'HIGH').toUpperCase();
      return { label, detail, reliability: rel === 'DISPUTED' || rel === 'LOW' ? 'DISPUTED' : 'HIGH' } as EvidenceItem;
    });
}

function normalizeTimeline(timeline: any): TimelineEvent[] {
  if (!Array.isArray(timeline)) return [];
  return timeline
    .map((t: any) => ({
      date: String(t.date ?? t.event_date ?? 'Record Date'),
      fact: String(t.fact ?? t.event ?? t.text ?? ''),
      page: t.page != null ? String(t.page) : undefined,
    }))
    .filter((t) => t.fact);
}

function normalizeIssues(legalIssues: any, issuesRaw: any): Issue[] {
  const arr = Array.isArray(issuesRaw) ? issuesRaw : Array.isArray(legalIssues) ? legalIssues : [];
  return arr
    .map((i: any): Issue => {
      if (typeof i === 'string') return { text: i, source: 'ai' };
      const src = String(i.source ?? i.origin ?? '').toLowerCase();
      return {
        text: String(i.text ?? i.issue ?? i.question ?? ''),
        source: src.includes('doc') || src.includes('fact') ? 'document' : 'ai',
        evidence: i.evidence ?? i.quote,
        page: i.page != null ? String(i.page) : undefined,
      };
    })
    .filter((i) => i.text);
}

function splitSentences(v: any): string[] {
  if (Array.isArray(v)) return v.map((x) => String(x)).filter(Boolean);
  if (typeof v === 'string' && v.trim()) {
    return v
      .split(/(?<=[.!?])\s+(?=[A-Z"(])/)
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return [];
}

function firstSentence(v: any): string {
  const list = splitSentences(v);
  return list[0] ?? '';
}

/** Remove repeated mentions of court name in summary beyond the first */
function dedupCourt(text: string, court: string): string {
  if (!court) return text;
  const esc = court.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  let seen = false;
  return text.replace(new RegExp(`\\b${esc}\\b`, 'gi'), (m) => {
    if (!seen) { seen = true; return m; }
    return '';
  }).replace(/\s{2,}/g, ' ').trim();
}

function normalizeKg(kg: any): { nodes: KgNode[]; edges: KgEdge[] } {
  const rawNodes: any[] = Array.isArray(kg?.nodes) ? kg.nodes : [];
  const rawEdges: any[] = Array.isArray(kg?.edges) ? kg.edges : [];

  const nodes: KgNode[] = rawNodes
    .filter((n) => !JUNK_LABELS.has(String(n.label ?? n.name ?? n.id ?? '').toLowerCase()))
    .map((n, idx) => {
      const label = String(n.label ?? n.name ?? n.id ?? `Node ${idx}`);
      const kindRaw = String(n.type ?? n.kind ?? n.group ?? 'other').toLowerCase();
      let kind: KgNode['kind'] = 'other';
      if (kindRaw.includes('case') || kindRaw.includes('matter')) kind = 'case';
      else if (kindRaw.includes('judge')) kind = 'judge';
      else if (kindRaw.includes('court') || kindRaw.includes('forum')) kind = 'court';
      else if (kindRaw.includes('act') || kindRaw.includes('statute')) kind = 'act';
      else if (kindRaw.includes('section') || kindRaw.includes('article')) kind = 'section';
      else if (kindRaw.includes('eviden')) kind = 'evidence';
      else if (kindRaw.includes('cit') || kindRaw.includes('preced')) kind = 'citation';
      else if (kindRaw.includes('part') || kindRaw.includes('person')) kind = 'party';
      return {
        id: String(n.id ?? n.node_id ?? `n-${idx}`),
        label,
        kind,
        page: n.page != null ? String(n.page) : n.source_page != null ? String(n.source_page) : undefined,
        quote: n.quote ?? n.snippet ?? n.evidence_quote,
        confidence: typeof n.confidence === 'number' ? Math.round(n.confidence <= 1 ? n.confidence * 100 : n.confidence) : undefined,
      };
    });

  const ids = new Set(nodes.map((n) => n.id));
  const edges: KgEdge[] = rawEdges
    .map((e, idx) => ({
      id: String(e.id ?? `e-${idx}`),
      source: String(e.source ?? e.from ?? e.src ?? ''),
      target: String(e.target ?? e.to ?? e.dst ?? ''),
      relation: String(e.type ?? e.label ?? e.relation ?? 'RELATES_TO').toUpperCase(),
    }))
    .filter((e) => ids.has(e.source) && ids.has(e.target));

  return { nodes, edges };
}

function buildTiles(md: Record<string, MetaField>) {
  const order: [string, string][] = [
    ['court', 'Court / Forum'],
    ['judges', 'Bench / Judges'],
    ['decision_date', 'Decision Date'],
    ['petitioner', 'Petitioner / Applicant'],
    ['respondent', 'Respondent / Defense'],
    ['case_number', 'Case / FIR Number'],
    ['acts', 'Primary Statute'],
    ['sections', 'Key Sections'],
    ['citations', 'Report Reference'],
    ['word_count', 'Document Scope'],
    ['procedural_stage', 'Procedural Stage'],
    ['ingestion_engine', 'Grounding Verification'],
  ];
  return order.map(([key, label]) => ({ key, label, field: md[key] ?? { value: 'Unstated in Record', status: 'not_found' as FieldStatus } }));
}

export interface NormalizeInput {
  analysis: Any | null;
  caseInfo: { title?: string; caseType?: string | null };
}

export function normalizeAnalysis({ analysis, caseInfo }: NormalizeInput): AnalysisModel | null {
  if (!analysis || typeof analysis !== 'object') return null;

  const mdRaw: Any = analysis.metadata ?? {};
  const docInfo: Any = analysis.document_info ?? {};
  const category = detectCategory(caseInfo.caseType);

  const getMetaField = (key: string): MetaField => {
    if (mdRaw[key]) return meta(mdRaw[key]);
    switch (key) {
      case 'court':
        return meta(docInfo.court ?? docInfo.court_name ?? analysis.court);
      case 'judges':
        return meta(docInfo.judges ?? docInfo.presiding_judges ?? analysis.judges);
      case 'decision_date':
        return meta(docInfo.decision_date ?? docInfo.date ?? analysis.decision_date);
      case 'petitioner':
        return meta(
          docInfo.petitioner ?? docInfo.applicant ??
          (Array.isArray(docInfo.parties) ? docInfo.parties[0] : null)
        );
      case 'respondent':
        return meta(
          docInfo.respondent ?? docInfo.accused ??
          (Array.isArray(docInfo.parties) && docInfo.parties.length > 1 ? docInfo.parties[1] : null)
        );
      case 'case_number':
        return meta(docInfo.case_number ?? docInfo.fir_number ?? docInfo.court_matter ?? analysis.case_number);
      case 'acts': {
        const legacyActs = Array.isArray(analysis.acts) && analysis.acts.length
          ? analysis.acts.map((a: any) => (typeof a === 'string' ? a : a.act)).filter(Boolean).join(', ')
          : null;
        return meta(legacyActs ?? docInfo.acts);
      }
      case 'sections': {
        const legacySecs = Array.isArray(analysis.sections) && analysis.sections.length
          ? analysis.sections.map((s: any) => (typeof s === 'string' ? s : s.section ?? s.section_number)).filter(Boolean).join(', ')
          : null;
        return meta(legacySecs ?? docInfo.sections);
      }
      case 'citations':
        return meta(docInfo.citation ?? docInfo.citations ??
          (Array.isArray(analysis.precedents) && analysis.precedents[0]?.citation));
      case 'word_count':
        return meta(docInfo.word_count ? `${docInfo.word_count} Words` : null);
      case 'procedural_stage':
        return { value: stageLabel(category), status: 'inferred' };
      case 'ingestion_engine':
        return { value: 'FalkorDB + Qdrant (BGE-M3)', status: 'extracted' };
      default:
        return { value: 'Unstated in Record', status: 'not_found' };
    }
  };

  const md: Record<string, MetaField> = {};
  for (const key of ['court', 'judges', 'decision_date', 'petitioner', 'respondent', 'case_number', 'acts', 'sections', 'citations', 'word_count', 'procedural_stage', 'ingestion_engine']) {
    md[key] = getMetaField(key);
  }

  const fallbackTitle = cleanTitle(caseInfo.title) || 'Active Case Dossier';
  const caseTitleMeta = mdRaw.case_title ? meta(mdRaw.case_title, fallbackTitle) : { value: fallbackTitle, status: 'extracted' as FieldStatus };

  const courtChip = md.court;
  const dateChip = md.decision_date;

  const actsList: string[] = Array.isArray(analysis.acts)
    ? analysis.acts.map((a: any) => (typeof a === 'string' ? a : String(a.act ?? a.name ?? ''))).filter(Boolean)
    : toList(docInfo.acts);

  // Dynamic statutes header from detected acts only — never hardcoded
  const headerActs = actsList.length ? actsList : Array.from(new Set(normalizeStatutes(analysis.sections, analysis.statutes).map((s) => s.act).filter(Boolean)));

  const selfCitation = md.citations.status !== 'not_found' ? md.citations.value.split(',')[0] ?? '' : '';
  const precedents = normalizePrecedents(analysis.precedents, caseTitleMeta.value, selfCitation);

  const citationsChip: MetaField =
    md.citations.status !== 'not_found'
      ? md.citations
      : precedents[0]?.citation
      ? { value: precedents[0].citation, status: 'extracted' }
      : { value: 'No Citation Stated', status: 'not_found' };

  const evidence = normalizeEvidence(analysis.evidence);
  const timeline = normalizeTimeline(analysis.timeline);
  const issues = normalizeIssues(analysis.legal_issues, analysis.issues);

  const sub = analysis.submissions ?? {};
  const args = analysis.arguments ?? {};
  const headings = submissionHeadings(category);
  const submissionsAItems = splitSentences(sub.a ?? args.prosecution);
  const submissionsBItems = splitSentences(sub.b ?? args.defense);

  const riskRaw: Any = analysis.risk ?? analysis.risk_analysis ?? {};
  const strengthsArr = Array.isArray(riskRaw.strengths) ? riskRaw.strengths : null;
  const gapsArr = Array.isArray(riskRaw.gaps ?? riskRaw.gaps_list) ? (riskRaw.gaps ?? riskRaw.gaps_list) : null;
  const actionArr = Array.isArray(riskRaw.action ?? riskRaw.action_plan) ? (riskRaw.action ?? riskRaw.action_plan) : null;

  const conclusionSrc = riskRaw.conclusion ?? analysis.legal_opinion ?? analysis.outcome;
  const conclusion = meta(conclusionSrc);

  // Timeline tail: decision date + operative outcome sentence
  if (conclusion.status !== 'not_found' && md.decision_date.status !== 'not_found') {
    const outcomeSentence = firstSentence(conclusion.value);
    if (outcomeSentence && !timeline.some((t) => t.fact.toLowerCase().includes(outcomeSentence.toLowerCase().slice(0, 30)))) {
      timeline.push({
        date: md.decision_date.value,
        fact: outcomeSentence,
        page: undefined,
      });
    }
  }

  // Calibrated trust score: explicit score, penalised when fields are not_found/inferred
  const explicit = typeof analysis.trust_score === 'number'
    ? analysis.trust_score * (analysis.trust_score <= 1 ? 100 : 1)
    : typeof analysis.confidence?.score === 'number'
    ? analysis.confidence.score * (analysis.confidence.score <= 1 ? 100 : 1)
    : 96;
  const unknownFields = Object.values(md).filter((f) => f.status === 'not_found').length;
  const inferredFields = Object.values(md).filter((f) => f.status === 'inferred').length;
  let trust = Math.round(explicit - unknownFields * 3 - inferredFields * 1.5);
  if (unknownFields + inferredFields > 0) trust = Math.min(trust, 97);
  trust = Math.max(35, Math.min(99, trust));

  const summaryRaw = analysis.summary ?? analysis.executive_summary ?? '';
  const summaryText = dedupCourt(String(summaryRaw), md.court.value);

  const agents = Array.isArray(analysis.agents)
    ? analysis.agents.map((a: any) => ({ name: String(a.name ?? a.agent ?? ''), ms: Number(a.ms ?? a.latency_ms ?? a.time_ms ?? 0) })).filter((a) => a.name)
    : [];

  return {
    caseTitle: caseTitleMeta,
    category,
    courtChip,
    dateChip,
    citationsChip,
    trustScore: trust,
    confidenceReason: analysis.confidence?.reason ?? '',
    summary: summaryText
      ? { value: summaryText, status: 'extracted' }
      : { value: 'No executive summary was generated for this dossier.', status: 'not_found' },
    metadataTiles: buildTiles(md),
    acts: headerActs,
    statutes: normalizeStatutes(analysis.sections, analysis.statutes),
    articles: normalizeArticles(analysis.articles),
    precedents,
    timeline,
    evidence,
    submissionsA: { heading: headings.a, items: submissionsAItems },
    submissionsB: { heading: headings.b, items: submissionsBItems },
    issues,
    riskStrengths: tagged(toList(strengthsArr), strengthsArr !== null),
    riskGaps: tagged(toList(gapsArr), gapsArr !== null),
    riskAction: tagged(toList(actionArr), actionArr !== null),
    conclusion,
    agents,
    kg: normalizeKg(analysis.kg_data ?? analysis.kg),
  };
}
