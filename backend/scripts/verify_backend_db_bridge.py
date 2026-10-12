import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embeddings.qdrant_client import get_qdrant_manager
from app.core.config import settings

def verify():
    print("Checking Backend <-> Database Communication...")
    
    # 1. Test Connection
    qdrant = get_qdrant_manager()
    if not qdrant.is_available():
        print("❌ FAILURE: Backend cannot connect to Qdrant Cloud.")
        return False
    print("✅ SUCCESS: Connection to Qdrant Cloud established.")

    # 2. Test Collection Access
    try:
        collections = qdrant.client.get_collections()
        col_names = [c.name for c in collections.collections]
        print(f"✅ SUCCESS: Found collections: {col_names}")
    except Exception as e:
        print(f"❌ FAILURE: Could not fetch collections: {e}")
        return False

    # 3. Test Data Retrieval (Fetch 1 point from legal_documents)
    try:
        points = qdrant.client.scroll(
            collection_name=settings.QDRANT_COLLECTION_DOCS,
            limit=1,
            with_payload=True
        )[0]
        if points:
            print(f"✅ SUCCESS: Successfully retrieved a data point. Sample source: {points[0].payload.get('source', 'N/A')}")
        else:
            print("⚠️ WARNING: Connected, but no data points found in legal_documents.")
    except Exception as e:
        print(f"❌ FAILURE: Error retrieving data: {e}")
        return False

    print("\nFinal Verdict: Backend is communicating perfectly with the Database.")
    return True

if __name__ == "__main__":
    verify()
