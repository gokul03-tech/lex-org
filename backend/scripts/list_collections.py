import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embeddings.qdrant_client import get_qdrant_manager

def list_all():
    manager = get_qdrant_manager()
    try:
        collections = manager.client.get_collections()
        print("All collections in Qdrant:")
        for col in collections.collections:
            print(f"- {col.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_all()
