#!/usr/bin/env python3
"""Indian Constitution Ingestion Pipeline.

Processes, chunks, embeds, and stores the Constitution dataset in Qdrant.
"""

import os
import sys
import json
import uuid
import time
from pathlib import Path
from typing import Any, List, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from langchain.text_splitter import RecursiveCharacterTextSplitter
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from app.core.config import settings


DATA_PATH = "/home/gokul/Downloads/final-year-project/json_output/constitution/constitution of india/data.json"
LOCAL_MODEL_PATH = "/home/gokul/Downloads/final-year-project/models/bge-m3"


def clean_text(text: str) -> str:
    """Clean the text to remove OCR artifacts, fix common spelling breaks, and normalize whitespace."""
    # Replace broken words
    text = text.replace("diffic ulties", "difficulties")
    text = text.replace("diffic-ulties", "difficulties")
    text = text.replace("diffic_ulties", "difficulties")
    
    # Normalize whitespaces within lines but preserve original structure
    lines = []
    for line in text.split("\n"):
        cleaned_line = " ".join(line.split())
        lines.append(cleaned_line)
    return "\n".join(lines)


# Initialize tokenizer count function
try:
    import tiktoken
    encoding = tiktoken.get_encoding("cl100k_base")
    def get_token_count(text: str) -> int:
        return len(encoding.encode(text))
except ImportError:
    logger.warning("tiktoken not installed, falling back to character approximation.")
    def get_token_count(text: str) -> int:
        return len(text) // 4


def process_and_chunk() -> List[Dict[str, Any]]:
    """Clean and split raw text pages into semantic legal chunks."""
    logger.info("Step 1: Starting data processing and chunking...")
    
    if not os.path.exists(DATA_PATH):
        logger.error(f"Input data path does not exist: {DATA_PATH}")
        sys.exit(1)
        
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n## ", "\n### ", "\nArticle ", "\nPart ", "\nSchedule ", "\n\n", "\n", " "],
        chunk_size=800,
        chunk_overlap=100,
        length_function=get_token_count
    )
    
    processed_chunks = []
    
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(f"Decoding error at line {line_num}: {e}")
                continue
                
            raw_text = item.get("text", "")
            cleaned = clean_text(raw_text)
            
            metadata = item.get("metadata", {})
            source_type = item.get("source_type", "pdf")
            doc_type = item.get("document_type", "act")
            
            # Split the text
            chunks = splitter.split_text(cleaned)
            total_chunks = len(chunks)
            
            for idx, chunk_text in enumerate(chunks):
                enriched_metadata = {
                    **metadata,
                    "chunk_index": idx,
                    "total_chunks": total_chunks,
                    "source_type": source_type,
                    "document_type": doc_type
                }
                
                processed_chunks.append({
                    "text": chunk_text,
                    "metadata": enriched_metadata,
                    "chunk_index": idx,
                    "total_chunks": total_chunks
                })
                
    logger.info(f"Chunking complete. Created {len(processed_chunks)} chunks.")
    return processed_chunks


def generate_embeddings(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate 1024-dimensional dense vectors using BGE-M3."""
    logger.info("Step 2: Starting embedding generation...")
    
    # Check if local model folder exists and is populated
    model_path = LOCAL_MODEL_PATH if os.path.exists(LOCAL_MODEL_PATH) and os.listdir(LOCAL_MODEL_PATH) else "BAAI/bge-m3"
    logger.info(f"Model source: {model_path}")
    
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Device: {device}")
    
    try:
        model = BGEM3FlagModel(model_path, use_fp16=True, device=device)
    except Exception as e:
        logger.warning(f"Could not load with FP16=True ({e}). Retrying with FP16=False.")
        model = BGEM3FlagModel(model_path, use_fp16=False, device=device)
        
    texts = [c["text"] for c in chunks]
    embeddings = []
    batch_size = 16
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        logger.info(f"Embedding batch {i // batch_size + 1} / {((len(texts) - 1) // batch_size) + 1}...")
        
        output = model.encode(
            batch_texts,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False
        )
        embeddings.extend(output["dense_vecs"])
        
    for chunk, embedding in zip(chunks, embeddings):
        if hasattr(embedding, "tolist"):
            chunk["embedding"] = embedding.tolist()
        else:
            chunk["embedding"] = list(embedding)
            
    logger.info("Embeddings successfully generated.")
    return chunks


def upsert_to_qdrant(chunks: List[Dict[str, Any]]):
    """Upsert vectors and metadata payloads into the Qdrant database."""
    logger.info("Step 3: Connecting to Qdrant and upserting data...")
    
    qdrant_url = getattr(settings, "QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=qdrant_url)
    
    collection_name = getattr(settings, "QDRANT_COLLECTION_DOCS", "legal_documents")
    
    try:
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
    except Exception as e:
        logger.error(f"Failed to check Qdrant collections: {e}")
        sys.exit(1)
        
    if not exists:
        logger.info(f"Creating collection '{collection_name}' with 1024 dimensions and Cosine distance...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=rest.VectorParams(
                size=1024,
                distance=rest.Distance.COSINE
            )
        )
    else:
        logger.info(f"Collection '{collection_name}' already exists.")
        
    points = []
    for chunk in chunks:
        point_id = str(uuid.uuid4())
        
        # Construct payload compatible with the project's search/QdrantManager specs
        payload = {
            "text": chunk["text"],
            "chunk_index": chunk["chunk_index"],
            "source": chunk["metadata"].get("filename", ""),
            "doc_type": chunk["metadata"].get("document_type", "act"),
            "act": chunk["metadata"].get("act_name", "Constitution"),
            "metadata": chunk["metadata"]
        }
        
        points.append(
            rest.PointStruct(
                id=point_id,
                vector=chunk["embedding"],
                payload=payload
            )
        )
        
    logger.info(f"Upserting {len(points)} points...")
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )
        logger.info(f"  Upserted batch {i // batch_size + 1} / {((len(points) - 1) // batch_size) + 1}...")
        
    logger.info("🎉 Ingestion complete!")


def main():
    start_time = time.time()
    chunks = process_and_chunk()
    chunks_with_embeddings = generate_embeddings(chunks)
    upsert_to_qdrant(chunks_with_embeddings)
    elapsed = time.time() - start_time
    logger.info(f"Pipeline completed in {elapsed:.2f} seconds.")


if __name__ == "__main__":
    main()
