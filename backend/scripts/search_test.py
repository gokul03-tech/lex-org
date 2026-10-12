import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embeddings.qdrant_client import get_qdrant_manager
from app.embeddings.bge_m3 import get_bge_m3

def main():
    qdrant = get_qdrant_manager()
    embedder = get_bge_m3()
    
    query_text = "Kalyan Chandra Sarkar"
    print(f"Searching for: {query_text}")
    
    # Get embedding for the query
    query_vector = embedder.encode([query_text])[0].tolist()
    
    # Search in legal_documents
    results = qdrant.search(
        query_vector=query_vector,
        top_k=5,
        collection_name="legal_documents"
    )
    
    if not results:
        print("No results found in legal_documents")
    else:
        for r in results:
            print(f"Score: {r['score']} | Text: {r['text'][:100]}...")

if __name__ == "__main__":
    main()
