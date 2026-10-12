import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embeddings.qdrant_client import get_qdrant_manager
from app.core.config import settings

def main():
    qdrant = get_qdrant_manager()
    collections = [settings.QDRANT_COLLECTION_DOCS, settings.QDRANT_COLLECTION_SECTIONS]
    
    for col in collections:
        try:
            count = qdrant.client.count(
                collection_name=col,
                exact=True
            ).count
            print(f"Collection {col}: {count} points")
        except Exception as e:
            print(f"Error counting {col}: {e}")

if __name__ == "__main__":
    main()
