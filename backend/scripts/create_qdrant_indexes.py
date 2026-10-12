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
    
    for col in collections:
        print(f"Creating index for 'case_id' in {col}...")
        try:
            qdrant.client.create_payload_index(
                collection_name=col,
                field_name="case_id",
                field_schema=qdrant.models.PayloadSchemaType.KEYWORD,
            )
            print(f"Successfully created index for 'case_id' in {col}")
        except Exception as e:
            print(f"Error creating index for {col}: {e}")

if __name__ == "__main__":
    main()
