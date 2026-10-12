import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embeddings.qdrant_client import get_qdrant_manager

def main():
    qdrant = get_qdrant_manager()
    print(f"URL: {qdrant.url}")
    print(f"API Key set: {bool(qdrant.api_key)}")
    
    try:
        qdrant._init_client()
        print("Client initialized")
        
        collections = qdrant.client.get_collections()
        print("Successfully fetched collections")
        for c in collections.collections:
            print(f"- {c.name}")
            
    except Exception as e:
        print(f"Detailed Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
