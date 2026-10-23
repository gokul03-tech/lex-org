import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embeddings.qdrant_client import get_qdrant_manager

def main():
    qdrant = get_qdrant_manager()
    if not qdrant.is_available():
        print("Qdrant unavailable")
        return

    try:
        collections = qdrant.client.get_collections()
        print("Collections in Qdrant:")
        for c in collections.collections:
            print(f"- {c.name}")
    except Exception as e:
        print(f"Error fetching collections: {e}")

if __name__ == "__main__":
    main()
