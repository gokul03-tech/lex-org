# Novelty Modules

LexOrch-KG introduces 8 independent novelty modules, each with clear interfaces:

## 1. Dynamic Evidence Graph
**File**: `agents/knowledge_graph_agent.py`
**Algorithm**: Real-time FalkorDB graph mutation as new evidence is added to a case. Nodes represent legal entities (Parties, Sections, Evidence Items, Courts), edges represent relationships (REFERENCES, CONTRADICTS, CORROBORATES). Falls back to local JSON graph when FalkorDB unavailable.

## 2. Adaptive Multi-Stage RAG
**Files**: `rag/` (full directory)
**Algorithm**: Intent-aware retriever selection with 6 legal intent categories. Each intent has tuned weights for 4 parallel retrievers (vector, KG, citation, keyword). Results merged via weighted Reciprocal Rank Fusion (k=60) and reranked with cross-encoder.

## 3. Evidence Reliability Scoring
**File**: `agents/analysis.py` (evidence_reliability_agent)
**Algorithm**: Multi-factor scoring assessing: source credibility, corroboration count, chain-of-custody integrity, internal consistency, case relevance. Uses DeepSeek-R1 for nuanced verification. Outputs per-item and overall reliability scores (0-1).

## 4. Confidence Fusion Engine
**File**: `agents/analysis.py` (confidence_fusion_agent)
**Algorithm**: Weighted Dempster-Shafer-inspired belief fusion combining 12 agent confidence scores. Accounts for evidence reliability, contradiction count, and agent agreement. Produces a composite trust_score (0-1) with interpretable breakdown.

## 5. Contradiction Detection
**File**: `agents/analysis.py` (contradiction_detection_agent)
**Algorithm**: LLM-based pairwise statement comparison using DeepSeek-R1. Classifies contradictions by type (direct, material, minor, implicit), severity (high/medium/low), and resolvability. Includes confidence score for each detected contradiction.

## 6. Procedural State Tracking
**File**: `agents/analysis.py` (procedural_compliance_agent)
**Algorithm**: BNSS 2023 / CrPC 1973 procedure checklist mapped against case timeline. 6-point check: FIR registration, arrest procedure, evidence collection, bail consideration, charge sheet filing, jurisdiction. Produces per-aspect status (compliant/partially_compliant/non_compliant).

## 7. Strategy Recommendation with IRAC
**File**: `agents/analysis.py` (strategy_recommendation_agent)
**Algorithm**: IRAC-based strategy generation (Issue → Rule → Application → Conclusion). Generates multiple litigation strategies with structured pros/cons, success probability estimates, and resource implications. Uses DeepSeek-R1 for reasoning.

## 8. Explainability Graph
**File**: `agents/analysis.py` (explainability_agent)
**Algorithm**: Directed graph tracing the full reasoning chain: Query → Evidence → Legal Sections → Reasoning → Conclusion. Edge weights represent confidence. Supports both React Flow (interactive) and Cytoscape.js (KG visualization) renderings. JSON format for API transport.

## Integration Pattern

Each novelty module is self-contained with:
- Clear input/output contract via `AgentState` fields
- Try/except error isolation (no single module failure crashes the pipeline)
- Confidence score reporting
- Graceful degradation (falls back to simpler behavior when dependencies unavailable)
