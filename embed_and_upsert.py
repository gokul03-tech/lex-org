import json
import os
import time
import uuid

import httpx
import numpy as np
import torch
from FlagEmbedding import BGEM3FlagModel
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

# ==========================================
# 1. CONFIGURATION
# ==========================================
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def _load_dotenv() -> None:
    """Load .env / backend/.env into os.environ without overriding existing vars."""
    for path in (os.path.join(_REPO_ROOT, ".env"), os.path.join(_REPO_ROOT, "backend", ".env")):
        if not os.path.exists(path):
            continue
        try:
            for raw in open(path, encoding="utf-8", errors="ignore"):
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Could not read {path}: {exc}")


_load_dotenv()

INPUT_DIR = os.environ.get("LEXORCH_JSON_INPUT_DIR", os.path.join(_REPO_ROOT, "json_output"))
MODEL_PATH = os.environ.get(
    "LEXORCH_EMBEDDING_MODEL_DIR", os.path.join(_REPO_ROOT, "models", "bge-m3")
)
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = "legal_documents"
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "1024"))
BATCH_SIZE = int(os.environ.get("LEXORCH_EMBED_BATCH_SIZE", "32"))

# Embedding backend: "auto" (cloud if API key present, else local) | "local" | "cloud"
EMBEDDING_BACKEND = os.environ.get("LEXORCH_EMBEDDING_BACKEND", "auto").lower()
EMBEDDING_API_BASE = os.environ.get(
    "EMBEDDING_API_BASE", "https://api.siliconflow.cn/v1"
).rstrip("/")
EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", "")
EMBEDDING_CLOUD_MODEL = os.environ.get("EMBEDDING_CLOUD_MODEL", "BAAI/bge-m3")
EMBEDDING_ALLOW_LOCAL_FALLBACK = os.environ.get(
    "EMBEDDING_ALLOW_LOCAL_FALLBACK", "true"
).lower() not in ("0", "false", "no")

# ==========================================
# 1b. EMBEDDING BACKENDS
# ==========================================
class NonRetryableEmbeddingError(RuntimeError):
    """Raised for client errors (e.g. 401/403) that must not be retried."""


class CloudEmbedder:
    """OpenAI-compatible embeddings client (e.g. SiliconFlow BGE-M3)."""

    def __init__(self, api_base: str, api_key: str, model_id: str, dim: int = 1024,
                 max_retries: int = 5) -> None:
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model_id = model_id
        self.dim = dim
        self.max_retries = max_retries

    def encode(self, texts: list[str]) -> list[list[float]]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        payload = {"model": self.model_id, "input": texts}
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = httpx.post(
                    f"{self.api_base}/embeddings", json=payload, headers=headers, timeout=120.0
                )
                if resp.status_code >= 400:
                    detail = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    # 429 / 5xx are transient; other 4xx are permanent (bad key, etc.)
                    if resp.status_code == 429 or resp.status_code >= 500:
                        raise RuntimeError(detail)
                    raise NonRetryableEmbeddingError(detail)
                data = resp.json()
                vecs = np.array([item["embedding"] for item in data["data"]], dtype=np.float32)
                norms = np.linalg.norm(vecs, axis=1, keepdims=True)
                norms[norms < 1e-8] = 1.0
                return (vecs / norms).tolist()
            except NonRetryableEmbeddingError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"Cloud embedding attempt {attempt}/{self.max_retries} failed: {exc}"
                )
                if attempt == self.max_retries:
                    raise
                time.sleep(min(2 ** attempt, 30))
        raise RuntimeError("Cloud embedding failed")


class Encoder:
    """Embedding dispatcher: cloud (OpenAI-compatible) with local fallback.

    The local path is the original FlagEmbedding BGE-M3 model; the cloud path
    calls an OpenAI-compatible /embeddings endpoint (SiliconFlow by default).
    """

    def __init__(self) -> None:
        self._local_model = None
        use_cloud = EMBEDDING_BACKEND == "cloud" or (
            EMBEDDING_BACKEND == "auto" and bool(EMBEDDING_API_KEY)
        )
        if use_cloud:
            self.cloud = CloudEmbedder(
                EMBEDDING_API_BASE, EMBEDDING_API_KEY, EMBEDDING_CLOUD_MODEL, EMBEDDING_DIM
            )
            self.backend = "cloud"
            logger.info(f"Encoder backend: cloud ({EMBEDDING_API_BASE}, {EMBEDDING_CLOUD_MODEL})")
        else:
            self.cloud = None
            self.backend = "local"

    def _load_local(self):
        if self._local_model is not None:
            return self._local_model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Encoder backend: local BGE-M3 from {MODEL_PATH} on {device}")
        self._local_model = BGEM3FlagModel(MODEL_PATH, use_fp16=(device == "cuda"), device=device)
        return self._local_model

    def encode(self, texts: list[str]) -> list[list[float]]:
        if self.backend == "cloud":
            try:
                return self.cloud.encode(texts)
            except Exception as exc:  # noqa: BLE001
                if not EMBEDDING_ALLOW_LOCAL_FALLBACK:
                    raise
                logger.warning(f"Cloud embedding failed ({exc}); switching to local BGE-M3")
                self.backend = "local"
        model = self._load_local()
        out = model.encode(
            texts, return_dense=True, return_sparse=False, return_colbert_vecs=False, max_length=512
        )
        vecs = out["dense_vecs"]
        return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vecs]



# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def load_documents(file_path: str) -> list[dict]:
    """Load JSON/JSONL files robustly, handling single objects, lists, and line-by-line JSONL."""
    # Try reading as single JSON (object or list)
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return data
                return [data]
            except json.JSONDecodeError:
                # Fall back to JSONL parsing
                pass
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return []

    # Read line-by-line (JSONL)
    documents = []
    try:
        with open(file_path, encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    documents.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"JSONDecodeError in {os.path.basename(file_path)} "
                        f"at line {line_num}: {e}"
                    )
    except Exception as e:
        logger.error(f"Failed to read {file_path} as JSONL: {e}")
    return documents

def get_text_content(doc: dict) -> str:
    """Extract and format textual content from document fields."""
    if "text" in doc and doc["text"]:
        return doc["text"]
    elif "question" in doc and "answer" in doc:
        return f"Q: {doc['question']}\nA: {doc['answer']}"
    elif "section_text" in doc and doc["section_text"]:
        return doc["section_text"]
    return ""

# ==========================================
# 3. MAIN RUNNER
# ==========================================
def process_and_embed():
    logger.info("Initializing embedding and upsert script...")

    # Select embedding backend (cloud OpenAI-compatible, with local fallback)
    try:
        encoder = Encoder()
    except Exception as e:
        logger.error(f"Failed to initialize embedding backend: {e}")
        return

    # Connect to Qdrant
    logger.info(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    try:
        # Create collection if it doesn't exist
        collections = client.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)
        if not exists:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=rest.VectorParams(size=EMBEDDING_DIM, distance=rest.Distance.COSINE)
            )
            logger.info(f"✅ Created Qdrant collection: {COLLECTION_NAME}")
        else:
            logger.info(f"✅ Qdrant collection '{COLLECTION_NAME}' already exists.")
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant or create collection: {e}")
        return

    # Text splitter setup
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", "Article ", "Section ", " ", ""]
    )

    # Walk directory to find all JSON/JSONL files recursively
    logger.info(f"Walking input directory: {INPUT_DIR}")
    all_files = []
    for root, _, filenames in os.walk(INPUT_DIR):
        for filename in filenames:
            if filename.endswith(".json") or filename.endswith(".jsonl"):
                all_files.append(os.path.join(root, filename))

    logger.info(f"📂 Found {len(all_files)} total files under {INPUT_DIR}")

    # Helper function to process and upsert a batch of chunks
    def upsert_batch(batch):
        if not batch:
            return

        texts = [item["text"] for item in batch]

        # Batch encode
        logger.info(f"Generating embeddings for batch of {len(batch)} chunks...")
        try:
            dense_vecs = encoder.encode(texts)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return

        points = []
        for item, vector in zip(batch, dense_vecs):
            # Check vector type
            if hasattr(vector, "tolist"):
                vector_list = vector.tolist()
            else:
                vector_list = list(vector)

            # Generate unique deterministic point ID based on unique chunk string
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, item["unique_str"]))

            payload = {
                "text": item["text"],
                "chunk_index": item["chunk_index"],
                "source": item["metadata"].get("filename")
                or item["metadata"].get("source")
                or item["source_file"],
                "doc_type": item.get("document_type") or item["metadata"].get("doc_type") or "act",
                "act": item["metadata"].get("act_name") or item["metadata"].get("act") or "Unknown",
                "source_type": item.get("source_type"),
                "court": item["metadata"].get("court"),
            }

            points.append(rest.PointStruct(
                id=chunk_id,
                vector=vector_list,
                payload=payload
            ))

        max_retries = 5
        retry_delay = 3
        for attempt in range(1, max_retries + 1):
            try:
                client.upsert(collection_name=COLLECTION_NAME, points=points)
                logger.info(f"   ⬆️ Successfully upserted {len(points)} points to Qdrant.")
                break
            except Exception as e:
                logger.warning(f"   ⚠️ Upsert attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    logger.info(f"   Sleeping for {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to upsert points to Qdrant after {max_retries} attempts.")


    # Process and chunk files
    batch_chunks = []
    total_chunks = 0
    total_files_processed = 0

    for file_path in all_files:
        # Skip edge files or non-content files
        if "graph" in file_path.lower() or "edges" in file_path.lower():
            logger.debug(f"Skipping graph edge/relationship file: {os.path.basename(file_path)}")
            continue

        logger.info(f"📄 Processing file: {os.path.basename(file_path)}")
        documents = load_documents(file_path)
        if not documents:
            continue

        file_chunks_count = 0
        for doc_index, doc in enumerate(documents):
            text = get_text_content(doc)
            metadata = doc.get("metadata") or {}
            doc_id = doc.get("id") or f"doc_{doc_index}"

            if not text or len(text.strip()) < 10:
                continue

            # Split into chunks
            chunks = text_splitter.split_text(text)
            for chunk_index, chunk in enumerate(chunks):
                # Ensure unique string for UUID generation
                unique_str = f"{file_path}_{doc_id}_chunk_{chunk_index}_{total_chunks}"

                batch_chunks.append({
                    "text": chunk,
                    "chunk_index": chunk_index,
                    "source_file": os.path.basename(file_path),
                    "unique_str": unique_str,
                    "metadata": metadata,
                    "document_type": doc.get("document_type"),
                    "source_type": doc.get("source_type")
                })
                total_chunks += 1
                file_chunks_count += 1

                # If batch is full, upsert it
                if len(batch_chunks) >= BATCH_SIZE:
                    upsert_batch(batch_chunks)
                    batch_chunks = []

        logger.info(f"Finished {os.path.basename(file_path)}: created {file_chunks_count} chunks.")
        total_files_processed += 1

    # Ingest remaining chunks
    if batch_chunks:
        upsert_batch(batch_chunks)

    logger.info(
        f"🎉 INGESTION COMPLETE! Processed {total_files_processed} files, "
        f"created & stored {total_chunks} chunks in Qdrant."
    )

if __name__ == "__main__":
    process_and_embed()
