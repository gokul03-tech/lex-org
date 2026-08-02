import os
import json
import uuid
import time
import torch
from loguru import logger
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ==========================================
# 1. CONFIGURATION
# ==========================================
INPUT_DIR = "/home/gokul/Downloads/final-year-project/json_output"
MODEL_PATH = "/home/gokul/Downloads/final-year-project/models/bge-m3"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "legal_documents"
EMBEDDING_DIM = 1024
BATCH_SIZE = 32

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def load_documents(file_path: str) -> list[dict]:
    """Load JSON/JSONL files robustly, handling single objects, lists, and line-by-line JSONL."""
    # Try reading as single JSON (object or list)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
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
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    documents.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"JSONDecodeError in {os.path.basename(file_path)} at line {line_num}: {e}")
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

    # Load BGE-M3 model
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"Loading BGE-M3 Model from {MODEL_PATH} on {device}...")
    try:
        model = BGEM3FlagModel(MODEL_PATH, use_fp16=(device == 'cuda'), device=device)
        logger.info(f"✅ Model loaded successfully on {device}")
    except Exception as e:
        logger.error(f"Failed to load BGE-M3 model: {e}")
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
            output = model.encode(
                texts,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
                max_length=512
            )
            dense_vecs = output["dense_vecs"]
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
                "source": item["metadata"].get("filename") or item["metadata"].get("source") or item["source_file"],
                "doc_type": item["metadata"].get("document_type") or item["metadata"].get("doc_type") or "act",
                "act": item["metadata"].get("act_name") or item["metadata"].get("act") or "Unknown"
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
                    "metadata": metadata
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

    logger.info(f"🎉 INGESTION COMPLETE! Processed {total_files_processed} files, created & stored {total_chunks} chunks in Qdrant.")

if __name__ == "__main__":
    process_and_embed()
