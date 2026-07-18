# LexOrch-KG: Trust-Aware Multi-Agent Legal Advisory Framework

**Dynamic Evidence Knowledge Graphs × Adaptive Multi-Stage RAG × Explainable AI × LangGraph**

LexOrch-KG is a production-ready AI legal advisory platform that helps advocates understand cases, retrieve relevant law, and generate explainable advisory reports. It employs 12 specialized LangGraph agents orchestrated by a Supervisor, adaptive multi-stage RAG across 4 retrieval channels, a Neo4j knowledge graph seeded from the GovIntel dataset, and a secure Docker sandbox for LLM execution.

## Architecture

```
User → React 19 Frontend → FastAPI Backend → 12 LangGraph Agents → RAG Pipeline
                                                    ↓                      ↓
                                              Neo4j KG            Qdrant (BGE-M3)
                                                    ↓                      ↓
                                              GovIntel Edges       Acts + QA Embeddings
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker (optional, for sandbox)
- Neo4j (optional, for KG features)
- Qdrant (optional, for vector search)

### Development Setup

```bash
# Clone and enter
cd final-year-project

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../configs/.env.example ../.env
# Edit .env to configure LLM_BACKEND=mock for development
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Docker Deployment

```bash
docker compose -f docker/docker-compose.yml up -d
```

## Project Structure

```
backend/
├── app/
│   ├── agents/          # 12 LangGraph agents + supervisor
│   ├── rag/             # Adaptive multi-stage RAG pipeline
│   ├── kg/              # Neo4j knowledge graph
│   ├── llm/             # LLM providers (llama.cpp, mock)
│   ├── document_pipeline/ # PDF parsing, OCR, chunking
│   ├── embeddings/      # BGE-M3 + Qdrant client
│   ├── sandbox/         # Secure Docker/process sandbox
│   ├── evaluation/      # Benchmark runner + metrics
│   ├── db/              # SQLAlchemy models + migrations
│   ├── api/             # FastAPI routes
│   └── core/            # Config, security, logging
frontend/
├── src/
│   ├── components/      # Shadcn/UI + layout
│   ├── pages/           # React Router pages
│   └── stores/          # Zustand auth store
datasets/
├── acts/                # ~60 Indian Acts PDFs
└── datasets/legal_corpus/
    ├── GovIntel/        # 14,280 training pairs + 4,305 KG edges
    └── BNS_BNSS_BSA/    # 6,354 QA pairs
```

## Key Features

- **12 LangGraph Agents**: Case Understanding, Legal Research, Knowledge Graph, Evidence Reliability, Contradiction Detection, Procedural Compliance, Legal Reasoning, Strategy Recommendation, Risk Assessment, Confidence Fusion, Explainability, Report Generation
- **Adaptive Multi-Stage RAG**: Intent Detection → Query Rewriting → 4-Way Parallel Retrieval → RRF Merge → Cross-Encoder Rerank
- **Neo4j Knowledge Graph**: Seeded from GovIntel edge/section JSONs with cross-code, judgment, deterministic, and autonomous edges
- **Evidence Reliability Scoring**: Multi-factor analysis (source credibility, corroboration, chain of custody)
- **Confidence Fusion**: Weighted Dempster-Shafer fusion across 12 agent confidences
- **Trust Score**: Composite from evidence reliability × agent agreement × contradiction count
- **Explainability Graph**: Directed graph tracing Query → Evidence → Reasoning → Conclusion

## Technologies

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy, Alembic, Celery |
| Agents | LangGraph, Pydantic |
| LLM | llama.cpp (Qwen3-32B, DeepSeek-R1-32B), Mock |
| Vector DB | Qdrant (HNSW) |
| Embeddings | BGE-M3 (sentence-transformers) |
| Graph DB | Neo4j (Cypher) |
| OCR | PaddleOCR |
| PDF | PyMuPDF, pdfplumber |
| Frontend | React 19, Vite, TailwindCSS, Shadcn/UI |
| Sandbox | Docker SDK for Python |
| Eval | GovIntel + BNS_BNSS_BSA datasets |

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Agent Design](docs/AGENTS.md)
- [RAG Pipeline](docs/RAG.md)
- [Knowledge Graph](docs/KG.md)
- [Evaluation](docs/EVALUATION.md)
- [Sandbox Security](docs/SANDBOX.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Novelty Modules](docs/NOVELTY.md)

## License

Research project. See datasets/ for dataset-specific licenses (GovIntel, BNS_BNSS_BSA).
# lex-org
