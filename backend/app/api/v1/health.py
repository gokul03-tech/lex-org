from fastapi import APIRouter
from app.embeddings.qdrant_client import get_qdrant_manager
from app.kg.falkordb_client import get_falkordb_client
from app.core.config import settings

router = APIRouter()


@router.get("/retrieval")
async def get_retrieval_health() -> dict:
    """Check health and statistics for the Qdrant and FalkorDB databases."""
    qdrant = get_qdrant_manager()
    q_avail = qdrant.is_available()
    q_info = {}
    
    if q_avail:
        try:
            col_docs = qdrant.client.get_collection(collection_name=settings.QDRANT_COLLECTION_DOCS)
            col_secs = qdrant.client.get_collection(collection_name=settings.QDRANT_COLLECTION_SECTIONS)
            q_info = {
                "status": "healthy",
                "collection_docs_points": col_docs.points_count if col_docs else 0,
                "collection_sections_points": col_secs.points_count if col_secs else 0,
                "vector_dimension": settings.QDRANT_VECTOR_SIZE,
            }
        except Exception as exc:
            q_info = {"status": "degraded", "error": str(exc)}
    else:
        q_info = {"status": "unhealthy"}

    falkor = await get_falkordb_client()
    f_avail = await falkor.verify_connectivity()
    f_info = {"status": "healthy" if f_avail else "unhealthy"}

    return {
        "qdrant": q_info,
        "knowledge_graph": f_info,
        "keyword_index": "healthy",
        "status": "healthy" if q_avail and f_avail else "degraded",
    }
