# LexOrch-KG Architecture

## System Overview

LexOrch-KG follows a microservices-inspired modular monolith architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                    React 19 Frontend (Vite)                      │
│  Login → Dashboard → Case Upload → Analysis → Report Viewer     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST /api/v1
┌──────────────────────────▼──────────────────────────────────────┐
│                   FastAPI Backend (Python 3.11)                  │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────────┐ │
│  │ Auth     │ │ Document │  │ Analysis   │ │ Report           │ │
│  │ (JWT)    │ │ Pipeline │  │ API        │ │ Generation       │ │
│  └──────────┘ └──────────┘ └─────┬──────┘ └──────────────────┘ │
│                                    │                              │
│  ┌─────────────────────────────────▼──────────────────────────┐ │
│  │         LangGraph Supervisor + 12 Agents                    │ │
│  │  CaseUnderstanding → LegalResearch → ... → ReportGeneration │ │
│  └──────────┬──────────────┬──────────────┬───────────────────┘ │
│             │              │              │                      │
│  ┌──────────▼──┐ ┌────────▼──┐ ┌────────▼──────────┐           │
│  │ RAG Pipeline│ │ Neo4j KG  │ │ LLM Providers     │           │
│  │ (5-stage)   │ │ (Cypher)  │ │ (Mock/Qwen/DS-R1) │           │
│  └──────┬──────┘ └───────────┘ └───────────────────┘           │
│         │                                                        │
└─────────┼────────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────────┐
│                     Data Layer                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ SQLite   │  │ Qdrant   │  │ Neo4j    │  │ Redis (Celery)   │ │
│  │ (Users,  │  │ (Vector  │  │ (Graph   │  │ (Async Tasks)    │ │
│  │  Cases)  │  │  Search) │  │  DB)     │  │                  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Document Upload Flow
1. User uploads PDF/DOCX/TXT → `POST /documents/upload`
2. Celery task picks up: Parse → OCR (if needed) → Clean → Chunk → Embed
3. Chunks + embeddings → Qdrant (`legal_documents` collection)
4. Entities extracted → Neo4j (if available)
5. Document status updated to `complete`

### Case Analysis Flow
1. User requests analysis → `POST /analysis/run`
2. Supervisor initializes `AgentState` with case documents
3. StateGraph executes 12 agents sequentially with conditional routing
4. Each agent:
   - Reads relevant state fields
   - Calls LLM (Qwen3 or DeepSeek-R1) via sandbox
   - Writes output to state
   - Records confidence score
5. Confidence fusion computes composite trust score
6. Report generation assembles 16-section final report
7. Results stored in SQLite `Analysis` table

### RAG Retrieval Flow
1. Query detected for legal intent (6 categories)
2. Query rewritten into 3-5 variants (LLM or rule-based)
3. 4 parallel retrievers execute:
   - Vector (Qdrant HNSW with BGE-M3)
   - Knowledge Graph (Neo4j Cypher traversal)
   - Citation (regex extraction + direct lookup)
   - Keyword (BM25 over indexed corpus)
4. RRF merges with intent-adaptive source weights
5. Cross-encoder reranks top candidates

## Component Details

### LangGraph Supervisor
- StateGraph with `AgentState` TypedDict (40+ fields)
- 12 nodes + conditional routing
- Error isolation: each agent's failure doesn't crash the pipeline
- `completed_agents` list tracks progress

### LLM Layer
- Abstract `LLMProvider` with `generate()`, `generate_structured()`, `stream_generate()`
- Three backends: `LlamaCppProvider`, `MockProvider`, OpenAI-compatible
- Qwen3-32B: Case understanding, legal analysis, report writing, explainability
- DeepSeek-R1-32B: Evidence verification, contradiction detection, strategy, reasoning
- Mock provider: Deterministic responses for development without GPU

### Sandbox
- `ProcessSandboxBackend`: Subprocess with resource limits (default dev)
- `DockerSandboxBackend`: Docker container with CPU/memory/network limits
- `NoOpSandboxBackend`: Direct execution (unsafe, development only)
- Config-controlled fallback chain: docker → process → none
