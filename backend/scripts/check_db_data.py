import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embeddings.qdrant_client import get_qdrant_manager

def check_data():
    manager = get_qdrant_manager()

    if not manager.is_available():
        print("❌ Qdrant is not available.")
        return

    collections = [
        ("legal_documents", "Main Legal Documents/Acts"),
        ("legal_sections", "Legal QA Pairs/Sections")
    ]

    print("--- Qdrant Database Content ---")
    for col_name, description in collections:
        print(f"\nCollection: {col_name} ({description})")
        try:
            info = manager.client.get_collection(collection_name=col_name)
            print(f"  - Points Count: {info.points_count}")

            # Sample search
            sample = manager.search([0.0] * 1024, top_k=1, collection_name=col_name)
            if sample:
                p = sample[0]
                print(f"  - Sample Text: {p['text'][:100]}...")
                print(f"  - Sample Source: {p.get('source', 'N/A')}")
            else:
                print("  - No data found in collection.")
        except Exception as e:
            print(f"  - Error: {e}")

if __name__ == "__main__":
    check_data()
