# LexOrch-KG Agent Design

## Overview

LexOrch-KG employs 12 specialized LangGraph agents orchestrated by a Supervisor using LangGraph's StateGraph with conditional routing. Each agent is a Python function that reads from a shared `AgentState` TypedDict, performs its specialized task, writes outputs back to state, and reports a confidence score.

## Supervisor

The Supervisor (`agents/supervisor.py`) implements:
- `AgentState`: 40+ field TypedDict shared across all agents
- `build_supervisor_graph()`: Constructs StateGraph with all 12 agent nodes
- `supervisor_router()`: Determines next agent based on `completed_agents` list
- `run_analysis_pipeline()`: Entry point for external callers

## Agent Sequence

```
CaseUnderstanding → LegalResearch → KnowledgeGraph → EvidenceReliability
→ ContradictionDetection → ProceduralCompliance → LegalReasoning
→ StrategyRecommendation → RiskAssessment → ConfidenceFusion
→ Explainability → ReportGeneration → END
```

## Individual Agents

### 1. CaseUnderstandingAgent
- **Purpose**: Analyze case documents, extract facts, entities, timeline
- **LLM**: Qwen3
- **Input**: `documents`, `query`
- **Output**: `case_summary`, `case_facts`, `entities`, `timeline`, `legal_issues`
- **Novelty**: Multi-document cross-referencing for entity resolution

### 2. LegalResearchAgent
- **Purpose**: Retrieve applicable acts, sections, precedents via RAG
- **LLM**: Qwen3 (for synthesis)
- **Input**: `legal_issues`, `query`
- **Output**: `applicable_acts`, `applicable_sections`, `precedents`
- **Novelty**: 4-way parallel retrieval with intent-adaptive weighting

### 3. KnowledgeGraphAgent
- **Purpose**: Build dynamic evidence graph in FalkorDB
- **LLM**: None (graph operations)
- **Input**: `entities`, `applicable_sections`
- **Output**: `kg_data` (nodes + edges)
- **Novelty**: Real-time graph mutation as evidence is added; falls back to local graph when FalkorDB unavailable

### 4. EvidenceReliabilityAgent
- **Purpose**: Score evidence reliability using multi-factor analysis
- **LLM**: DeepSeek-R1
- **Input**: `documents`, `case_facts`
- **Output**: `evidence_assessment`
- **Novelty**: Multi-factor scoring (source credibility, corroboration, chain of custody, consistency, relevance)

### 5. ContradictionDetectionAgent
- **Purpose**: Cross-reference statements to detect contradictions
- **LLM**: DeepSeek-R1
- **Input**: `documents`, `evidence_assessment`
- **Output**: `contradictions`
- **Novelty**: Pairwise statement comparison with severity classification and resolvability assessment

### 6. ProceduralComplianceAgent
- **Purpose**: Check procedural compliance against BNSS 2023
- **LLM**: Qwen3
- **Input**: `case_facts`, `timeline`
- **Output**: `procedural_status`
- **Novelty**: 6-point checklist: FIR, arrest, evidence, bail, chargesheet, jurisdiction

### 7. LegalReasoningAgent
- **Purpose**: Apply IRAC methodology
- **LLM**: Qwen3
- **Input**: `case_facts`, `applicable_sections`, `precedents`
- **Output**: `legal_reasoning`, `irac_analysis`
- **Novelty**: Structured IRAC with explicit mapping of facts to legal elements

### 8. StrategyRecommendationAgent
- **Purpose**: Generate litigation strategies with pros/cons
- **LLM**: DeepSeek-R1
- **Input**: All prior agent outputs
- **Output**: `strategy_options`
- **Novelty**: Multi-option generation with success probability estimates

### 9. RiskAssessmentAgent
- **Purpose**: Evaluate case strengths, weaknesses, outcome probabilities
- **LLM**: DeepSeek-R1
- **Input**: All prior agent outputs
- **Output**: `risk_assessment`
- **Novelty**: Bayesian-inspired outcome probability estimation

### 10. ConfidenceFusionAgent
- **Purpose**: Aggregate per-agent confidence using weighted fusion
- **LLM**: None (computation)
- **Input**: `agent_confidence`
- **Output**: `trust_score`
- **Novelty**: Dempster-Shafer-inspired weighted belief fusion

### 11. ExplainabilityAgent
- **Purpose**: Build explanation graph showing reasoning chain
- **LLM**: Qwen3
- **Input**: All prior agent outputs
- **Output**: `explanation_graph`
- **Novelty**: Directed graph: Query → Evidence → Reasoning → Conclusion with confidence edge weights

### 12. ReportGenerationAgent
- **Purpose**: Assemble 16-section final report
- **LLM**: Qwen3 (for executive summary)
- **Input**: All prior agent outputs
- **Output**: `final_report`
- **Novelty**: Interactive graph views via React Flow + Cytoscape.js

## Agent State Schema

```python
class AgentState(TypedDict, total=False):
    # Input
    case_id: str
    query: str
    documents: list[dict]
    
    # Case Understanding
    case_summary: str
    case_facts: dict
    entities: dict
    timeline: list[dict]
    
    # Legal Research
    legal_issues: list[str]
    applicable_acts: list[str]
    applicable_sections: list[dict]
    precedents: list[dict]
    
    # ... all other agent outputs ...
    
    # Control
    completed_agents: list[str]
    errors: list[str]
    agent_confidence: dict[str, float]
    trust_score: float
```
