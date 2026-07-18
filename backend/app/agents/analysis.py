"""LangGraph agent implementations for LexOrch-KG multi-agent legal analysis.

All 12 specialized agents: CaseUnderstanding, LegalResearch, KnowledgeGraph,
EvidenceReliability, ContradictionDetection, ProceduralCompliance,
LegalReasoning, StrategyRecommendation, RiskAssessment, ConfidenceFusion,
Explainability, and ReportGeneration.
"""

from __future__ import annotations

import json
import time
from typing import Any

from loguru import logger

from app.agents.supervisor import AgentState


# ── Helper: Agent metadata recording ───────────────────────
def _record_completion(state: AgentState, agent_name: str, confidence: float, output_key: str, output_value: Any) -> AgentState:
    """Record agent completion with confidence and output."""
    completed = state.get("completed_agents", [])
    state["completed_agents"] = completed + [agent_name]

    confidences = state.get("agent_confidence", {})
    confidences[agent_name] = confidence
    state["agent_confidence"] = confidences

    state[output_key] = output_value  # type: ignore[typeddict-unknown-key]
    return state


# ── Agent 1: Case Understanding Agent ──────────────────────
async def case_understanding_agent(state: AgentState) -> AgentState:
    """Analyze case documents, extract facts, entities, and timeline.

    Uses Qwen3 LLM for comprehension and entity extraction.
    Input: state.documents
    Output: case_summary, case_facts, entities, timeline
    """
    start_time = time.monotonic()
    logger.info(f"[CaseUnderstanding] Starting analysis for case: {state.get('case_id')}")

    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        documents = state.get("documents", [])
        query = state.get("query", "")

        if not documents and not query:
            state["case_summary"] = "No documents provided for analysis."
            state["case_facts"] = {}
            state["entities"] = {}
            state["timeline"] = []
            return _record_completion(state, "case_understanding", 0.5, "case_summary", state["case_summary"])

        # Build prompt from documents
        doc_texts = "\n\n---\n\n".join(
            d.get("text", d.get("parsed_text", ""))[:2000] for d in documents[:5]
        ) if documents else query

        prompt = f"""Analyze the following legal case document(s) and extract:

1. CASE FACTS: Summarize the key facts in 3-5 bullet points.
2. PARTIES: Identify the plaintiff/petitioner, defendant/respondent, and any other parties.
3. LEGAL ISSUES: Identify potential legal issues.
4. TIMELINE: Extract key dates and events in chronological order.
5. KEY ENTITIES: Identify any courts, judges, advocates, witnesses, organizations mentioned.

Respond in the following JSON format:
{{
    "summary": "Brief case summary",
    "facts": ["fact 1", "fact 2", ...],
    "parties": {{"plaintiff": "...", "defendant": "...", "others": ["..."]}},
    "legal_issues": ["issue 1", "issue 2", ...],
    "timeline": [{{"date": "...", "event": "..."}}],
    "entities": {{"courts": [], "judges": [], "advocates": [], "witnesses": [], "organizations": []}}
}}

Case Document(s):
{doc_texts}

Additional Query: {query}
"""
        provider = get_qwen_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "facts": {"type": "array", "items": {"type": "string"}},
                    "parties": {"type": "object"},
                    "legal_issues": {"type": "array", "items": {"type": "string"}},
                    "timeline": {"type": "array"},
                    "entities": {"type": "object"},
                },
            },
            system_prompt=QWEN_SYSTEM_PROMPT,
            temperature=0.1,
        )

        state["case_summary"] = result.get("summary", "")
        state["case_facts"] = result.get("facts", {})
        state["entities"] = result.get("entities", {})
        state["legal_issues"] = result.get("legal_issues", [])
        state["timeline"] = result.get("timeline", [])

        confidence = 0.85
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[CaseUnderstanding] Complete: confidence={confidence:.2f}, {duration_ms:.0f}ms")
        return _record_completion(state, "case_understanding", confidence, "case_summary", state["case_summary"])

    except Exception as exc:
        logger.error(f"[CaseUnderstanding] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"CaseUnderstanding: {exc}"]
        return _record_completion(state, "case_understanding", 0.0, "case_summary", f"Error: {exc}")


# ── Agent 2: Legal Research Agent ──────────────────────────
async def legal_research_agent(state: AgentState) -> AgentState:
    """Retrieve applicable acts, sections, and precedents using RAG.

    Input: state.legal_issues, state.case_facts, state.query
    Output: applicable_acts, applicable_sections, precedents
    """
    start_time = time.monotonic()
    logger.info(f"[LegalResearch] Searching for applicable law")

    try:
        from app.rag.rag_pipeline import RAGPipeline

        issues = state.get("legal_issues", [])
        query = state.get("query", "") or " ".join(issues) if issues else "legal case analysis"

        # Use the RAG pipeline for multi-source retrieval
        rag = RAGPipeline()
        rag_results = await rag.search(query, top_k=20)

        # Extract section references from RAG results
        sections: list[dict[str, Any]] = []
        acts: list[str] = []
        precedents: list[dict[str, Any]] = []

        for result in rag_results:
            if result.get("source") == "kg":
                metadata = result.get("metadata", {})
                if "section_number" in metadata:
                    sections.append({
                        "section_number": metadata.get("section_number"),
                        "act": metadata.get("act", "Unknown"),
                        "title": metadata.get("title", ""),
                        "text": result.get("text", "")[:500],
                        "relevance_score": result.get("score", 0.0),
                    })
                    if metadata.get("act"):
                        acts.append(metadata["act"])
                elif "case_name" in metadata:
                    precedents.append({
                        "case_name": metadata.get("case_name"),
                        "citation": metadata.get("citation", ""),
                        "relevance_score": result.get("score", 0.0),
                        "summary": result.get("text", "")[:300],
                    })

        # Deduplicate
        seen = set()
        unique_sections = []
        for s in sections:
            key = f"{s['section_number']}_{s['act']}"
            if key not in seen:
                seen.add(key)
                unique_sections.append(s)

        state["applicable_sections"] = unique_sections[:10]
        state["applicable_acts"] = list(set(acts))[:10]
        state["precedents"] = precedents[:5]

        confidence = 0.80 if unique_sections else 0.40
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[LegalResearch] Found {len(unique_sections)} sections, {len(precedents)} precedents ({duration_ms:.0f}ms)")
        return _record_completion(state, "legal_research", confidence, "applicable_sections", state["applicable_sections"])

    except Exception as exc:
        logger.error(f"[LegalResearch] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"LegalResearch: {exc}"]
        state["applicable_sections"] = []
        state["applicable_acts"] = []
        state["precedents"] = []
        return _record_completion(state, "legal_research", 0.0, "applicable_sections", [])


# ── Agent 3: Knowledge Graph Agent ─────────────────────────
async def knowledge_graph_agent(state: AgentState) -> AgentState:
    """Build dynamic evidence graph in Neo4j from extracted entities.

    Input: state.entities, state.case_id, state.applicable_sections
    Output: kg_data
    """
    start_time = time.monotonic()
    logger.info(f"[KnowledgeGraph] Building case graph")

    try:
        from app.kg.neo4j_client import get_neo4j_client

        kg_data: dict[str, Any] = {"nodes": [], "edges": [], "status": "unavailable"}

        neo4j = await get_neo4j_client()
        connected = await neo4j.verify_connectivity()

        if not connected:
            logger.warning("[KnowledgeGraph] Neo4j unavailable - creating local graph structure")
            # Build local graph from extracted entities
            entities = state.get("entities", {})
            sections = state.get("applicable_sections", [])

            # Nodes
            if state.get("case_id"):
                kg_data["nodes"].append({"id": state["case_id"], "type": "Case", "label": f"Case {state['case_id'][:8]}"})

            for party_name in entities.get("parties", {}).get("others", []):
                kg_data["nodes"].append({"id": party_name, "type": "Party", "label": party_name})

            for act in state.get("applicable_acts", []):
                kg_data["nodes"].append({"id": act, "type": "Act", "label": act})

            for section in sections[:10]:
                sec_id = f"{section.get('act', '')}_{section.get('section_number', '')}"
                kg_data["nodes"].append({"id": sec_id, "type": "Section", "label": f"Sec {section.get('section_number')} {section.get('act', '')}"})
                if state.get("case_id"):
                    kg_data["edges"].append({"source": state["case_id"], "target": sec_id, "type": "REFERENCES"})

            kg_data["status"] = "local"
        else:
            # Query Neo4j for related sections and precedents
            sections = state.get("applicable_sections", [])
            for section in sections[:10]:
                results = await neo4j.run_query(
                    """
                    MATCH (s:Section {section_number: $num, act: $act})
                    OPTIONAL MATCH (s)-[r]-(related:Section)
                    RETURN s, collect(DISTINCT {type: type(r), target_id: related.section_id, target_act: related.act}) as relations
                    LIMIT 5
                    """,
                    {"num": str(section.get("section_number")), "act": section.get("act", "")},
                )
                for record in results:
                    node = record.get("s", {})
                    if node:
                        kg_data["nodes"].append({"id": node.get("section_id", ""), "type": "Section", "label": node.get("title", "")})
                    for rel in record.get("relations", []):
                        if rel:
                            kg_data["edges"].append({"source": node.get("section_id", ""), "target": rel.get("target_id", ""), "type": rel.get("type", "")})

            kg_data["status"] = "neo4j"

        state["kg_data"] = kg_data
        confidence = 0.75 if kg_data["nodes"] else 0.30
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[KnowledgeGraph] Built graph: {len(kg_data['nodes'])} nodes, {len(kg_data['edges'])} edges ({duration_ms:.0f}ms)")
        return _record_completion(state, "knowledge_graph", confidence, "kg_data", kg_data)

    except Exception as exc:
        logger.error(f"[KnowledgeGraph] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"KnowledgeGraph: {exc}"]
        state["kg_data"] = {"nodes": [], "edges": [], "status": "error", "error": str(exc)}
        return _record_completion(state, "knowledge_graph", 0.0, "kg_data", state["kg_data"])


# ── Agent 4: Evidence Reliability Agent ────────────────────
async def evidence_reliability_agent(state: AgentState) -> AgentState:
    """Score evidence reliability using multi-factor analysis.

    Uses DeepSeek-R1 for verification and scoring.
    Input: state.documents, state.case_facts
    Output: evidence_assessment
    """
    start_time = time.monotonic()
    logger.info("[EvidenceReliability] Assessing evidence")

    try:
        from app.llm.deepseek import get_deepseek_provider, DEEPSEEK_SYSTEM_PROMPT

        documents = state.get("documents", [])
        if not documents:
            evidence = {"score": 0.5, "items": [], "summary": "No evidence documents provided."}
            state["evidence_assessment"] = evidence
            return _record_completion(state, "evidence_reliability", 0.5, "evidence_assessment", evidence)

        prompt = f"""Assess the reliability of evidence in the following case documents.

For each piece of evidence, score on:
- Source credibility (0-1)
- Corroboration level (0-1)
- Chain of custody (0-1)
- Internal consistency (0-1)
- Relevance to case (0-1)
Provide an overall reliability score (0-1).

Documents:
{chr(10).join(d.get('text', '')[:1000] for d in documents[:3])}

Respond with JSON:
{{"overall_score": 0.0, "items": [{{"description": "", "source_score": 0.0, "corroboration": 0.0, "chain_of_custody": 0.0, "consistency": 0.0, "relevance": 0.0, "overall": 0.0, "notes": ""}}], "summary": ""}}
"""
        provider = get_deepseek_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "overall_score": {"type": "number"},
                    "items": {"type": "array"},
                    "summary": {"type": "string"},
                },
            },
            system_prompt=DEEPSEEK_SYSTEM_PROMPT,
            temperature=0.1,
        )

        state["evidence_assessment"] = result
        confidence = result.get("overall_score", 0.5)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[EvidenceReliability] Overall score: {confidence:.2f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "evidence_reliability", confidence, "evidence_assessment", result)

    except Exception as exc:
        logger.error(f"[EvidenceReliability] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"EvidenceReliability: {exc}"]
        state["evidence_assessment"] = {"score": 0.0, "error": str(exc)}
        return _record_completion(state, "evidence_reliability", 0.0, "evidence_assessment", state["evidence_assessment"])


# ── Agent 5: Contradiction Detection Agent ─────────────────
async def contradiction_detection_agent(state: AgentState) -> AgentState:
    """Cross-reference statements and evidence to detect contradictions.

    Uses DeepSeek-R1 for pairwise contradiction analysis.
    Input: state.documents, state.evidence_assessment
    Output: contradictions
    """
    start_time = time.monotonic()
    logger.info("[ContradictionDetection] Scanning for contradictions")

    try:
        from app.llm.deepseek import get_deepseek_provider, DEEPSEEK_SYSTEM_PROMPT

        documents = state.get("documents", [])
        if len(documents) < 2:
            contradictions: list[dict[str, Any]] = [{"type": "insufficient_data", "message": "Need at least 2 documents for contradiction analysis."}]
            state["contradictions"] = contradictions
            return _record_completion(state, "contradiction_detection", 0.9, "contradictions", contradictions)

        prompt = f"""Analyze these legal documents for contradictions between statements, evidence, and facts.

Compare each pair of documents and identify:
1. Direct contradictions (one says X, another says not-X)
2. Material inconsistencies (differences that affect case outcome)
3. Minor discrepancies (timeline differences, terminology mismatches)
4. Implicit contradictions (one implies what another denies)

For each contradiction found, provide:
- The conflicting statements (with document references)
- Severity (high/medium/low)
- Confidence in the contradiction (0-1)
- Whether it's resolvable

Documents:
{chr(10).join(f"DOC {i+1}: {d.get('text', '')[:800]}" for i, d in enumerate(documents[:5]))}

Respond with JSON: {{"contradictions": [{{"type": "", "statement_a": "", "statement_b": "", "severity": "", "confidence": 0.0, "resolvable": false, "notes": ""}}], "overall_contradiction_score": 0.0}}
"""
        provider = get_deepseek_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "contradictions": {"type": "array"},
                    "overall_contradiction_score": {"type": "number"},
                },
            },
            system_prompt=DEEPSEEK_SYSTEM_PROMPT,
            temperature=0.1,
        )

        contradictions_found = result.get("contradictions", [])
        overall_score = result.get("overall_contradiction_score", 0.0)
        state["contradictions"] = contradictions_found

        # High contradiction score = more contradictions found = lower confidence in case
        confidence = max(0.1, 1.0 - overall_score)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[ContradictionDetection] Found {len(contradictions_found)} contradictions, score={overall_score:.2f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "contradiction_detection", confidence, "contradictions", contradictions_found)

    except Exception as exc:
        logger.error(f"[ContradictionDetection] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"ContradictionDetection: {exc}"]
        state["contradictions"] = [{"error": str(exc)}]
        return _record_completion(state, "contradiction_detection", 0.0, "contradictions", state["contradictions"])


# ── Agent 6: Procedural Compliance Agent ───────────────────
async def procedural_compliance_agent(state: AgentState) -> AgentState:
    """Check procedural compliance against BNSS 2023 / CrPC 1973.

    Input: state.case_facts, state.timeline
    Output: procedural_status
    """
    start_time = time.monotonic()
    logger.info("[ProceduralCompliance] Checking procedure")

    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        timeline = state.get("timeline", [])
        facts = state.get("case_facts", {})

        if not timeline and not facts:
            status = {"compliance_score": 0.5, "checks": [], "summary": "Insufficient data for procedural compliance check."}
            state["procedural_status"] = status
            return _record_completion(state, "procedural_compliance", 0.5, "procedural_status", status)

        prompt = f"""Assess procedural compliance in this legal case against BNSS 2023 (or CrPC 1973 if pre-July 2024).

Check the following procedural aspects:
1. FIR registration (timeliness, jurisdiction)
2. Arrest procedure (grounds, notification, medical examination)
3. Evidence collection (chain of custody, search procedure)
4. Bail consideration (grounds, hearing)
5. Charge sheet filing (timeline, contents)
6. Jurisdiction (territorial, subject matter)

Case facts and timeline:
{json.dumps({"facts": facts, "timeline": timeline}, indent=2)}

Respond with JSON:
{{"compliance_score": 0.0, "checks": [{{"aspect": "", "status": "compliant|partially_compliant|non_compliant|unable_to_determine", "score": 0.0, "notes": ""}}], "summary": ""}}
"""
        provider = get_qwen_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "compliance_score": {"type": "number"},
                    "checks": {"type": "array"},
                    "summary": {"type": "string"},
                },
            },
            system_prompt=QWEN_SYSTEM_PROMPT,
            temperature=0.1,
        )

        state["procedural_status"] = result
        confidence = result.get("compliance_score", 0.5)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[ProceduralCompliance] Score: {confidence:.2f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "procedural_compliance", confidence, "procedural_status", result)

    except Exception as exc:
        logger.error(f"[ProceduralCompliance] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"ProceduralCompliance: {exc}"]
        state["procedural_status"] = {"compliance_score": 0.0, "error": str(exc)}
        return _record_completion(state, "procedural_compliance", 0.0, "procedural_status", state["procedural_status"])


# ── Agent 7: Legal Reasoning Agent ─────────────────────────
async def legal_reasoning_agent(state: AgentState) -> AgentState:
    """Apply IRAC methodology for legal reasoning.

    Input: state.applicable_sections, state.case_facts, state.legal_issues
    Output: legal_reasoning, irac_analysis
    """
    start_time = time.monotonic()
    logger.info("[LegalReasoning] Applying IRAC methodology")

    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        sections = state.get("applicable_sections", [])
        facts = state.get("case_facts", {})
        issues = state.get("legal_issues", [])

        prompt = f"""Apply IRAC (Issue, Rule, Application, Conclusion) methodology to this legal case.

ISSUE: Identify the legal question(s)
RULE: State applicable legal provisions
APPLICATION: Apply law to facts
CONCLUSION: Reach a reasoned conclusion

Applicable Sections:
{json.dumps(sections[:5], indent=2)}

Legal Issues:
{json.dumps(issues, indent=2)}

Case Facts:
{json.dumps(facts, indent=2) if isinstance(facts, dict) else str(facts)[:1000]}

IMPORTANT: This is an advisory analysis for advocates, NOT a judicial decision.
Always note alternative interpretations where applicable.

Respond with JSON:
{{"issues_identified": ["..."], "rules": [{{"section": "", "provision": ""}}], "application": "", "conclusion": "", "alternative_interpretations": ["..."], "confidence": 0.0}}
"""
        provider = get_qwen_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "issues_identified": {"type": "array", "items": {"type": "string"}},
                    "rules": {"type": "array"},
                    "application": {"type": "string"},
                    "conclusion": {"type": "string"},
                    "alternative_interpretations": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
            },
            system_prompt=QWEN_SYSTEM_PROMPT,
            temperature=0.1,
        )

        state["irac_analysis"] = result
        state["legal_reasoning"] = f"ISSUES:\n{chr(10).join(result.get('issues_identified', []))}\n\nCONCLUSION:\n{result.get('conclusion', '')}"
        confidence = result.get("confidence", 0.7)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[LegalReasoning] IRAC complete, confidence={confidence:.2f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "legal_reasoning", confidence, "legal_reasoning", state["legal_reasoning"])

    except Exception as exc:
        logger.error(f"[LegalReasoning] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"LegalReasoning: {exc}"]
        state["legal_reasoning"] = f"Error during legal reasoning: {exc}"
        return _record_completion(state, "legal_reasoning", 0.0, "legal_reasoning", state["legal_reasoning"])


# ── Agent 8: Strategy Recommendation Agent ─────────────────
async def strategy_recommendation_agent(state: AgentState) -> AgentState:
    """Generate litigation strategies with pro/con analysis.

    Uses DeepSeek-R1 for structured debate and strategy generation.
    """
    start_time = time.monotonic()
    logger.info("[StrategyRecommendation] Generating strategies")

    try:
        from app.llm.deepseek import get_deepseek_provider, DEEPSEEK_SYSTEM_PROMPT

        reasoning = state.get("legal_reasoning", "")
        risk = state.get("risk_assessment", {})
        evidence = state.get("evidence_assessment", {})

        prompt = f"""Generate litigation strategies for this case. For each strategy provide:
- Strategy name and description
- Legal basis (sections/cases to rely on)
- Probability of success (0-1)
- Pros (advantages)
- Cons (risks/drawbacks)
- Recommended actions
- Alternative approaches if strategy fails

Case reasoning:
{reasoning[:1000]}

Evidence assessment:
{json.dumps(evidence, indent=2)[:500]}

Risk assessment:
{json.dumps(risk, indent=2)[:500]}

Respond with JSON:
{{"strategies": [{{"name": "", "description": "", "legal_basis": [], "success_probability": 0.0, "pros": [], "cons": [], "recommended_actions": [], "fallback": ""}}], "recommended_strategy": "", "overall_confidence": 0.0}}
"""
        provider = get_deepseek_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "strategies": {"type": "array"},
                    "recommended_strategy": {"type": "string"},
                    "overall_confidence": {"type": "number"},
                },
            },
            system_prompt=DEEPSEEK_SYSTEM_PROMPT,
            temperature=0.3,
        )

        state["strategy_options"] = result.get("strategies", [])
        confidence = result.get("overall_confidence", 0.6)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[StrategyRecommendation] {len(state['strategy_options'])} strategies ({duration_ms:.0f}ms)")
        return _record_completion(state, "strategy_recommendation", confidence, "strategy_options", state["strategy_options"])

    except Exception as exc:
        logger.error(f"[StrategyRecommendation] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"StrategyRecommendation: {exc}"]
        state["strategy_options"] = []
        return _record_completion(state, "strategy_recommendation", 0.0, "strategy_options", [])


# ── Agent 9: Risk Assessment Agent ─────────────────────────
async def risk_assessment_agent(state: AgentState) -> AgentState:
    """Evaluate case strengths, weaknesses, and outcome probabilities.

    Uses DeepSeek-R1 for risk modeling.
    """
    start_time = time.monotonic()
    logger.info("[RiskAssessment] Evaluating risks")

    try:
        from app.llm.deepseek import get_deepseek_provider, DEEPSEEK_SYSTEM_PROMPT

        evidence = state.get("evidence_assessment", {})
        contradictions = state.get("contradictions", [])
        reasoning = state.get("legal_reasoning", "")

        prompt = f"""Assess litigation risk for this case. Consider:
- Strength of evidence
- Presence of contradictions
- Legal merits
- Procedural compliance
- Precedent alignment
- Practical considerations (cost, time, witness availability)

Provide:
1. Overall case strength (0-1)
2. Key strengths
3. Key weaknesses
4. Outcome probability distribution (win/lose/settle)
5. Key risk factors
6. Mitigation recommendations

Evidence: {json.dumps(evidence, indent=2)[:500]}
Contradictions: {json.dumps(contradictions, indent=2)[:300]}
Reasoning: {reasoning[:500]}

Respond with JSON:
{{"overall_strength": 0.0, "strengths": [], "weaknesses": [], "outcome_probabilities": {{"favorable": 0.0, "unfavorable": 0.0, "settlement": 0.0}}, "key_risks": [], "mitigation": [], "confidence": 0.0}}
"""
        provider = get_deepseek_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "overall_strength": {"type": "number"},
                    "strengths": {"type": "array", "items": {"type": "string"}},
                    "weaknesses": {"type": "array", "items": {"type": "string"}},
                    "outcome_probabilities": {"type": "object"},
                    "key_risks": {"type": "array", "items": {"type": "string"}},
                    "mitigation": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
            },
            system_prompt=DEEPSEEK_SYSTEM_PROMPT,
            temperature=0.1,
        )

        state["risk_assessment"] = result
        confidence = result.get("confidence", 0.6)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[RiskAssessment] Strength: {result.get('overall_strength', 0):.2f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "risk_assessment", confidence, "risk_assessment", result)

    except Exception as exc:
        logger.error(f"[RiskAssessment] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"RiskAssessment: {exc}"]
        state["risk_assessment"] = {"error": str(exc)}
        return _record_completion(state, "risk_assessment", 0.0, "risk_assessment", state["risk_assessment"])


# ── Agent 10: Confidence Fusion Agent ──────────────────────
async def confidence_fusion_agent(state: AgentState) -> AgentState:
    """Aggregate per-agent confidence scores using weighted fusion.

    Implements Dempster-Shafer-inspired weighted fusion of 11 agent confidences
    to produce a single trust score for the analysis.
    """
    start_time = time.monotonic()
    logger.info("[ConfidenceFusion] Fusing agent confidences")

    try:
        confidences = state.get("agent_confidence", {})
        evidence_score = state.get("evidence_assessment", {}).get("overall_score", 0.5)
        contradiction_score = 1.0 - sum(c.get("confidence", 0) for c in state.get("contradictions", [])) / max(len(state.get("contradictions", [])) or 1, 1)
        compliance_score = state.get("procedural_status", {}).get("compliance_score", 0.5)

        # Weighted fusion
        weights = {
            "case_understanding": 0.10,
            "legal_research": 0.15,
            "knowledge_graph": 0.05,
            "evidence_reliability": 0.15,
            "contradiction_detection": 0.10,
            "procedural_compliance": 0.10,
            "legal_reasoning": 0.15,
            "strategy_recommendation": 0.10,
            "risk_assessment": 0.10,
            # explainability and report_generation are output agents
        }

        weighted_sum = 0.0
        total_weight = 0.0
        for agent, weight in weights.items():
            conf = confidences.get(agent, 0.0)
            if conf > 0:  # Only count agents that actually ran
                weighted_sum += conf * weight
                total_weight += weight

        trust_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Blend in evidence and compliance signals
        trust_score = (trust_score * 0.7) + (evidence_score * 0.15) + (compliance_score * 0.10) + (contradiction_score * 0.05)

        state["trust_score"] = max(0.0, min(1.0, trust_score))
        state["agent_confidence"] = {**confidences, "confidence_fusion": trust_score}

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[ConfidenceFusion] Trust score: {state['trust_score']:.3f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "confidence_fusion", state["trust_score"], "trust_score", state["trust_score"])

    except Exception as exc:
        logger.error(f"[ConfidenceFusion] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"ConfidenceFusion: {exc}"]
        state["trust_score"] = 0.0
        return _record_completion(state, "confidence_fusion", 0.0, "trust_score", 0.0)


# ── Agent 11: Explainability Agent ─────────────────────────
async def explainability_agent(state: AgentState) -> AgentState:
    """Build explainability graph showing reasoning chain and evidence links.

    Creates a directed graph: Query -> Evidence -> Reasoning -> Conclusion
    with confidence edge weights and trust factor annotations.
    """
    start_time = time.monotonic()
    logger.info("[Explainability] Building explanation graph")

    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        reasoning = state.get("legal_reasoning", "")
        sections = state.get("applicable_sections", [])
        evidence = state.get("evidence_assessment", {})
        trust = state.get("trust_score", 0.5)

        # Build explainability graph structure
        graph: dict[str, Any] = {
            "nodes": [
                {"id": "query", "type": "Query", "label": state.get("query", "Legal Analysis Request")[:80]},
                {"id": "evidence", "type": "Evidence", "label": f"Evidence ({evidence.get('overall_score', 'N/A')})"},
                {"id": "reasoning", "type": "Reasoning", "label": "IRAC Legal Reasoning"},
                {"id": "conclusion", "type": "Conclusion", "label": "Legal Conclusion"},
                {"id": "trust", "type": "Trust", "label": f"Trust Score: {trust:.2f}"},
            ],
            "edges": [
                {"source": "query", "target": "evidence", "weight": 0.9, "type": "informs"},
                {"source": "evidence", "target": "reasoning", "weight": evidence.get("overall_score", 0.5), "type": "supports"},
                {"source": "reasoning", "target": "conclusion", "weight": state.get("agent_confidence", {}).get("legal_reasoning", 0.7), "type": "leads_to"},
                {"source": "conclusion", "target": "trust", "weight": trust, "type": "calibrated_by"},
            ],
        }

        # Add section nodes
        for i, section in enumerate(sections[:8]):
            node_id = f"section_{i}"
            graph["nodes"].append({
                "id": node_id,
                "type": "Section",
                "label": f"Sec {section.get('section_number')} {section.get('act', '')}",
            })
            graph["edges"].append({
                "source": node_id,
                "target": "reasoning",
                "weight": section.get("relevance_score", 0.5),
                "type": "grounds",
            })

        # Add contradiction nodes if any
        contradictions = state.get("contradictions", [])
        for i, c in enumerate(contradictions[:5]):
            node_id = f"contradiction_{i}"
            graph["nodes"].append({
                "id": node_id,
                "type": "Contradiction",
                "label": c.get("type", f"Contradiction {i+1}"),
            })
            graph["edges"].append({
                "source": node_id,
                "target": "trust",
                "weight": -c.get("confidence", 0),
                "type": "reduces",
            })

        state["explanation_graph"] = graph

        confidence = 0.9
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[Explainability] Graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges ({duration_ms:.0f}ms)")
        return _record_completion(state, "explainability", confidence, "explanation_graph", graph)

    except Exception as exc:
        logger.error(f"[Explainability] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"Explainability: {exc}"]
        state["explanation_graph"] = {"nodes": [], "edges": [], "error": str(exc)}
        return _record_completion(state, "explainability", 0.0, "explanation_graph", state["explanation_graph"])


# ── Agent 12: Report Generation Agent ──────────────────────
async def report_generation_agent(state: AgentState) -> AgentState:
    """Assemble final 16-section legal advisory report from all agent outputs.

    Uses Qwen3 for executive summary and synthesis.
    """
    start_time = time.monotonic()
    logger.info("[ReportGeneration] Assembling final report")

    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        summary = state.get("case_summary", "")
        facts = state.get("case_facts", {})
        issues = state.get("legal_issues", [])
        acts = state.get("applicable_acts", [])
        sections = state.get("applicable_sections", [])
        precedents = state.get("precedents", [])
        evidence = state.get("evidence_assessment", {})
        contradictions = state.get("contradictions", [])
        risk = state.get("risk_assessment", {})
        procedural = state.get("procedural_status", {})
        strategies = state.get("strategy_options", [])
        trust = state.get("trust_score", 0.0)
        confidences = state.get("agent_confidence", {})
        explanation = state.get("explanation_graph", {})
        kg = state.get("kg_data", {})
        reasoning = state.get("legal_reasoning", "")

        # Generate executive summary
        exec_prompt = f"""Write an executive summary for a legal advisory report. Be concise and professional.

Case: {summary[:500]}
Key Issues: {', '.join(issues[:5])}
Key Sections: {', '.join(f"Sec {s.get('section_number')} {s.get('act', '')}" for s in sections[:5])}
Trust Score: {trust:.2f}

Write a 3-4 sentence executive summary in plain English suitable for an advocate."""
        provider = get_qwen_provider()
        exec_summary = provider.generate(exec_prompt, system_prompt=QWEN_SYSTEM_PROMPT, max_tokens=300)

        report = {
            "title": "Legal Advisory Report",
            "case_id": state.get("case_id", ""),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "sections": [
                {"title": "Executive Summary", "content": exec_summary, "order": 1},
                {"title": "Case Facts", "content": str(facts) if facts else summary, "order": 2},
                {"title": "Legal Issues Identified", "content": issues, "order": 3},
                {"title": "Applicable Acts", "content": acts, "order": 4},
                {"title": "Applicable Sections", "content": [{"section": s.get("section_number"), "act": s.get("act"), "title": s.get("title", ""), "text": s.get("text", "")} for s in sections], "order": 5},
                {"title": "Supporting Judgments", "content": precedents, "order": 6},
                {"title": "Evidence Analysis", "content": evidence, "order": 7},
                {"title": "Contradiction Analysis", "content": contradictions, "order": 8},
                {"title": "Risk Assessment", "content": risk, "order": 9},
                {"title": "Procedural Compliance", "content": procedural, "order": 10},
                {"title": "Strategy Recommendation", "content": strategies, "order": 11},
                {"title": "Trust Score", "content": {"score": trust, "breakdown": confidences}, "order": 12},
                {"title": "Confidence Scores", "content": confidences, "order": 13},
                {"title": "Explainability Graph", "content": explanation, "order": 14},
                {"title": "Knowledge Graph Snapshot", "content": kg, "order": 15},
                {"title": "References and Disclaimer", "content": "This report is AI-generated for advisory purposes only. It does not constitute legal advice. All legal decisions must be made by a qualified advocate. Review all citations and analysis before use.", "order": 16},
            ],
            "trust_score": trust,
            "confidence_scores": confidences,
            "explanation_graph": explanation,
            "knowledge_graph": kg,
        }

        state["final_report"] = report
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[ReportGeneration] Report complete ({duration_ms:.0f}ms)")
        return _record_completion(state, "report_generation", trust, "final_report", report)

    except Exception as exc:
        logger.error(f"[ReportGeneration] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"ReportGeneration: {exc}"]
        state["final_report"] = {"error": str(exc)}
        return _record_completion(state, "report_generation", 0.0, "final_report", state["final_report"])
