import os
from app.embeddings.qdrant_client import get_qdrant_manager
from loguru import logger

def test_connection():
    print("Testing Qdrant Connection...")
    manager = get_qdrant_manager()

    print(f"Target URL: {manager.url}")

    if manager.is_available():
        print("✅ SUCCESS: Qdrant is available!")
    else:
        print("❌ FAILURE: Qdrant is unavailable.")
        # Try to get the actual error
        try:
            manager.client.get_collections()
        except Exception as e:
            print(f"Detailed Error: {e}")

if __name__ == "__main__":
    test_connection()
