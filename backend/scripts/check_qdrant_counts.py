import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embeddings.qdrant_client import get_qdrant_manager
from app.core.config import settings

def main():
    qdrant = get_qdrant_manager()
    if not qdrant.is_available():
        print("Qdrant unavailable")
        return

    collections = [settings.QDRANT_COLLECTION_DOCS, settings.QDRANT_COLLECTION_SECTIONS]
    total_points = 0
    
    for col in collections:
        info = qdrant.get_collection_info(col)
        count = info.get("points_count", 0)
        print(f"Collection {col}: {count} points")
        total_points += count
    
    print("-" * 30)
    print(f"Total Points in Qdrant: {total_points}")

if __name__ == "__main__":
    main()
