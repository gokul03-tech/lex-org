import sys
from qdrant_client import QdrantClient
from FlagEmbedding import BGEM3FlagModel
from loguru import logger

def main():
    logger.info("Initializing Qdrant client...")
    client = QdrantClient("http://localhost:6333", check_compatibility=False)
    
    # 1. Check collection status
    collection_name = "legal_documents"
    logger.info(f"Checking collection info for '{collection_name}'...")
    try:
        col_info = client.get_collection(collection_name)
        logger.info(f"Collection state: {col_info.status}")
        logger.info(f"Collection details: {col_info}")
    except Exception as e:
        logger.error(f"Failed to retrieve collection: {e}")
        sys.exit(1)
        
    # 2. Initialize BGE-M3 model locally
    model_path = "/home/gokul/Downloads/final-year-project/models/bge-m3"
    logger.info(f"Loading BGE-M3 model from {model_path} on CUDA...")
    model = BGEM3FlagModel(model_path, use_fp16=True, device='cuda')
    
    # 3. Perform a query search
    query_text = "What are the fundamental rights under the Constitution of India?"
    logger.info(f"Generating embedding for query: '{query_text}'...")
    query_vector = model.encode(query_text, return_dense=True, return_sparse=False, return_colbert_vecs=False)["dense_vecs"].tolist()
    
    logger.info("Searching in Qdrant...")
    search_results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=3,
        with_payload=True
    ).points
    
    logger.info("--- Search Results ---")
    for idx, hit in enumerate(search_results):
        print(f"\n[{idx + 1}] Score: {hit.score:.4f}")
        print(f"    File: {hit.payload.get('file_path')}")
        print(f"    Type: {hit.payload.get('doc_type')}")
        text_snippet = hit.payload.get('text', '')
        if len(text_snippet) > 300:
            text_snippet = text_snippet[:300] + "..."
        print(f"    Text snippet: {text_snippet}")

if __name__ == "__main__":
    main()
