# LexOrch-KG: Trust-Aware Multi-Agent Legal Advisory Framework

**LexOrch-KG** is an end-to-end, trust-aware multi-agent legal advisory framework specializing in Indian Criminal Law and Statutory Analysis. Designed for advocates, it processes case documents (such as court judgments, petitions, and briefs) to generate highly grounded, trust-calibrated 16-section advisory reports. 

By combining dense vector search (**Qdrant**) with a Graph-relational Database (**FalkorDB**) in a hybrid Retrieval-Augmented Generation (RAG) architecture, LexOrch-KG eliminates common LLM hallucinations and traces every extracted fact, legal issue, and statute back to its source page in the document.

---

## 🏗️ System Architecture

The application is structured into three main layers:

```mermaid
graph TD
    User([Advocate / User UI]) <--> Frontend[Vite + React Frontend]
    Frontend <--> Backend[FastAPI Application Server]
    
    subgraph Storage & Retrieval
        Backend <--> Qdrant[(Qdrant Vector DB)]
        Backend <--> FalkorDB[(FalkorDB Graph DB)]
        Backend <--> SQLite[(SQLite Metadata DB)]
    end
    
    subgraph Inference & Workers
        Backend <--> Celery[Celery Task Queue]
        Celery <--> Redis[(Redis Broker)]
        Backend <--> LLM[Local LLMs: Qwen / DeepSeek-R1 Distill]
    end
```

### 1. Frontend (Vite + React + TypeScript)
* **Visual Interface**: Sleek dark-mode glassmorphic theme designed using Tailwind CSS and Framer Motion.
* **SSE Progress Tracker**: Connects to FastAPI Server-Sent Events (SSE) to display a real-time progress checklist of the multi-agent ingestion and reasoning cycle.
* **Grounded Metadata Cards**: Renders document parameters (petitioner, respondent, dates, citations) using structured value/status pairs, preventing guess fallbacks.
* **Provenance Visualizer**: Under every legal issue and fact, the UI displays a provenance footer highlighting the **file name**, **page number**, **confidence score**, and **exact supporting sentence** from the source document.
* **Explainability Graph**: Renders a D3.js force-directed 2D/3D graph visualization representing entity relations, sections, and precedent nodes.
* **Grounded Chatbot**: Includes a case-specific chatbot that executes vector queries restricted to the uploaded document to prevent out-of-context hallucinations.

### 2. Backend (FastAPI + Celery + SQLAlchemy)
* **API Gateway**: Exposes asynchronous endpoints, handles dependency injection, manages user auth/sessions, and handles uploads.
* **Celery Workers**: Distributes CPU-intensive operations (PDF parsing, OCR extraction, embeddings generation, and agent reasoning loops) to background processes backed by a Redis broker.
* **Logging**: Detailed file and terminal logging powered by Loguru for monitoring agent progress.

### 3. Retrieval & Storage Layer
* **Qdrant Vector DB**: Indexes chunks of the Indian Constitution, central Acts, and uploaded case documents using the BGE-M3 embedding model (1024 dimensions).
* **FalkorDB Graph DB**: Built as a Redis graph module, it maps semantic links, sections, citations, and court precedents.
* **SQLite Database**: Serves as the relational database for user accounts, case records, document lists, and compiled analysis reports.

---

## 🤖 Multi-Agent Pipeline & LangGraph Flow

The backend orchestrates analysis via a stateful multi-agent system powered by **LangGraph** and local LLM models:

```mermaid
flowchart TD
    Start([Upload Doc]) --> Agent1[Document Processing Agent]
    Agent1 --> Agent2[Metadata Agent]
    Agent2 --> Agent3[Legal Research Agent]
    Agent3 --> Agent4[Knowledge Graph Agent]
    Agent4 --> Agent5[IRAC Reasoning Agent]
    Agent5 --> Agent6[Source Validation Agent]
    Agent6 --> Agent7[Report Compiler Agent]
    Agent7 --> End([Generate 16-Section Report])
```

1. **Document Processing Agent**: Extracts character text from the PDF page-by-page. Automatically triggers a PaddleOCR fallback if page character count is lower than 100 to parse scanned documents.
2. **Metadata Agent**: Extracts case metadata (court name, petitioner, respondent, date) into structured objects: `{"value": ..., "status": "extracted" | "not_found"}`.
3. **Legal Research Agent**: Conducts dense vector searches and BM25 keyword lexical searches to locate relevant central Acts, Constitution articles, and precedents.
4. **Knowledge Graph Agent**: Models and links entities, citations, and precedents inside FalkorDB.
5. **IRAC Legal Reasoning Agent**: Formulates legal arguments based on the Issue-Rule-Application-Conclusion paradigm.
6. **Source Validation Agent (The Grounding Layer)**: Re-scans all generated facts, issues, and strategic claims against the original document pages using a string-overlap algorithm to extract page numbers, confidence levels, and direct quotes. Non-relevant precedents (similarity score < 40%) are automatically pruned.
7. **Report Compiler Agent**: Assembles the executive summary and synthesizes the finalized trust-calibrated report.

---

## 📂 Repository Structure

```text
├── backend/                   # FastAPI backend application
│   ├── app/                   # API, core configs, services, and models
│   │   ├── agents/            # Multi-agent analyst & verification logic
│   │   ├── api/               # API Router endpoints (v1 routes)
│   │   ├── core/              # Config settings, logging, and security
│   │   ├── db/                # DB sessions, models, and migrations
│   │   ├── document_pipeline/ # PDF Parsing, page chunking, and OCR fallback
│   │   ├── embeddings/        # BGE-M3 model & Qdrant manager integration
│   │   ├── kg/                # FalkorDB client, entity extractors, and query builders
│   │   ├── llm/               # Provider bindings (Mock, Qwen, Transformers, LlamaCPP)
│   │   ├── rag/               # Vector, keyword, citation retrievers and rerankers
│   │   └── schemas/           # Pydantic serialization models
│   ├── scripts/               # Ingestion and download scripts
│   └── tests/                 # Unit & integration testing suites
├── configs/                   # Env configuration templates
├── datasets/                  # Source Acts PDFs & legal corpora
├── docker/                    # Dockerfiles & docker-compose configurations
├── frontend/                  # React + TS + TailwindCSS web application
│   ├── src/
│   │   ├── components/        # Layout, D3 CaseGraph, and UI primitives
│   │   ├── pages/             # Dashboard, Cases, Analysis, and Auth pages
│   │   ├── stores/            # State management (Zustand)
│   │   └── types/             # Frontend type definitions
└── models/                    # Local model weight storage (BGE-M3, LLMs)
```

---

## 🛠️ Getting Started

### Prerequisites
* Docker & Docker Compose
* Python 3.10 - 3.13
* Node.js (v18+) & npm

---

### Step-by-Step Installation

#### 1. Configure Environments
Copy the config template in the project root:
```bash
cp configs/.env.example .env
```
Ensure to also copy or maintain `.env` inside the `backend/` folder.

#### 2. Start the Databases (Docker)
Ensure Docker is running, then pull and start the Qdrant and FalkorDB containers:
```bash
# Start Qdrant (v1.10.0) on port 6333
docker run -d -p 6333:6333 -p 6334:6334 --name lexorch-qdrant qdrant/qdrant:v1.10.0

# Start FalkorDB on port 6379 (connecting to port 6379 of Redis engine wrapper)
docker run -d -p 6379:6379 --name falkordb falkordb/falkordb:latest
```

#### 3. Setup Backend Environment
Navigate to `backend/`, create a virtual environment, and install dependencies in editable mode:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```
*(If you have an NVIDIA GPU, verify that PyTorch is installed with CUDA support to enable fast local BGE-M3 embeddings).*

#### 4. Download local BGE-M3 Embeddings
To download and save the BGE-M3 model weights locally for offline acceleration, run:
```bash
python setup_bge_m3.py
```
This saves the model weights under `models/bge-m3/`.

#### 5. Ingest Legal Corpora
Seed your vector database with the core legal dataset (Indian Constitution and central Acts):
```bash
# Ingest the Indian Constitution
python scripts/ingest_constitution.py

# Ingest other central Acts and dataset corpus files
python scripts/ingest_datasets.py
```

#### 6. Run the Servers

##### Launch the Backend API:
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*API docs will be available at: `http://localhost:8000/docs`*

##### Launch the Frontend React Client:
```bash
cd frontend
npm install
npm run dev
```
*Open your browser and navigate to: `http://localhost:5173`*

---

## 📊 Codebase Statistics

The application contains **15,854 total lines of code** divided as follows:

| Layer | Area / Component | File Count | Lines of Code | Language |
| :--- | :--- | :---: | :---: | :---: |
| **Backend Core** | LangGraph Agents | 4 | 1,414 | Python |
| | API Routers & Gateways | 12 | 1,372 | Python |
| | Document Extraction & Parser | 7 | 1,029 | Python |
| | Retrieval, Search & Reranking | 8 | 1,180 | Python |
| | LLM Integration & Providers | 8 | 1,558 | Python |
| | FalkorDB Knowledge Graph | 6 | 1,114 | Python |
| | DB Sessions & Schemas | 10 | 1,280 | Python |
| | Task Queue & Celery Config | 10 | 1,003 | Python |
| **Tests & Scripts**| Automated Unit/Integration Tests | 4 | 344 | Python |
| | Seed Ingestion Scripts | 3 | 661 | Python |
| **Frontend** | React Pages | 9 | 2,408 | TypeScript / TSX |
| | UI Components & Layout | 12 | 1,178 | TypeScript / TSX |
| | State Stores & Types | 6 | 210 | TypeScript / TS |
| | Stylesheets (CSS) | 1 | 108 | CSS |

---

## 🧪 Verification & Testing

### 1. Database Health Check API
You can check container connections, vector collection counts, and dimensions via:
👉 **`GET http://localhost:8000/api/v1/health/retrieval`**

### 2. Verify Qdrant Dashboard
Monitor embedded points and collections directly:
👉 **`http://localhost:6333/dashboard`**

### 3. Run Automated Tests
Run pytest in the backend directory to execute unit and provider tests:
```bash
.venv/bin/pytest
```

---

## 📜 License
This project is licensed under the Apache-2.0 License. See the LICENSE file for details.