"""Document upload lifecycle: real ids, status transitions, indexing, deletion."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient


class _FakeEmbedder:
    """Deterministic stand-in for the BGE-M3 embedder (no model load)."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def embed_chunks(self, chunks, text_key: str = "text"):
        for chunk in chunks:
            chunk["embedding"] = [0.0, 0.0, 0.0]
        return chunks


class _FakeQdrant:
    """Captures upserted chunks and never touches the network."""

    def __init__(self) -> None:
        self.upserts: list[list[dict]] = []

    def upsert_chunks(self, chunks, collection_name=None, batch_size: int = 100) -> int:
        self.upserts.append(chunks)
        return len(chunks)

    def is_available(self) -> bool:
        return False

    def delete(self, *args, **kwargs) -> None:  # pragma: no cover - not reached
        raise AssertionError("delete should not be called when unavailable")


async def _create_case(client: AsyncClient, headers: dict[str, str]) -> str:
    resp = await client.post("/api/v1/cases/", data={"title": "Doc Case"}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _fake_metadata(_text: str) -> dict:
    """Deterministic stand-in for the LLM-backed metadata extractor."""
    return {"court": {"value": "Test Court", "status": "extracted"}}


def _patch_ingestion(session_factory, fake_qdrant):
    """Patch the ingestion session factory, embedder, metadata and Qdrant manager."""
    return (
        patch("app.document_pipeline.ingestion.async_session_factory", session_factory),
        patch("app.document_pipeline.embedder.EmbeddingGenerator", _FakeEmbedder),
        patch("app.embeddings.qdrant_client.get_qdrant_manager", lambda: fake_qdrant),
        patch("app.agents.metadata_extractor.extract_metadata", _fake_metadata),
    )


@pytest.mark.asyncio
async def test_upload_returns_real_document_id(
    client: AsyncClient, user_factory, session_factory
) -> None:
    """The upload response id is the persisted document id (not a random UUID)."""
    headers, _ = await user_factory()
    case_id = await _create_case(client, headers)
    fake_qdrant = _FakeQdrant()

    p1, p2, p3, p4 = _patch_ingestion(session_factory, fake_qdrant)
    with p1, p2, p3, p4:
        resp = await client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "sample.txt",
                    b"IN THE HIGH COURT\nBail Application No. 5 of 2024.",
                    "text/plain",
                )
            },
            data={"case_id": case_id, "document_type": "judgment"},
            headers=headers,
        )

    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]

    # The id resolves through the status endpoint, proving it is the DB row id.
    status = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["id"] == doc_id
    assert status.json()["status"] == "complete"


@pytest.mark.asyncio
async def test_upload_transitions_status_and_indexes(
    client: AsyncClient, user_factory, session_factory
) -> None:
    """A completed upload is chunked, embedded and indexed with case provenance."""
    headers, _ = await user_factory()
    case_id = await _create_case(client, headers)
    fake_qdrant = _FakeQdrant()

    body = ("IN THE HIGH COURT OF KARNATAKA\n"
            "Criminal Petition No. 101 of 2024\n"
            "The petitioner seeks regular bail under Section 483 BNSS. " * 40)

    p1, p2, p3, p4 = _patch_ingestion(session_factory, fake_qdrant)
    with p1, p2, p3, p4:
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("petition.txt", body.encode(), "text/plain")},
            data={"case_id": case_id, "document_type": "judgment"},
            headers=headers,
        )
    assert resp.status_code == 201

    docs = await client.get("/api/v1/documents/", params={"case_id": case_id}, headers=headers)
    assert docs.status_code == 200
    assert len(docs.json()) == 1
    assert docs.json()[0]["status"] == "complete"

    assert fake_qdrant.upserts, "expected chunks to be indexed"
    indexed_chunks = fake_qdrant.upserts[0]
    assert indexed_chunks
    for chunk in indexed_chunks:
        assert chunk["metadata"]["case_id"] == case_id
        assert chunk["metadata"]["filename"] == "petition.txt"
        assert "chunk_id" in chunk["metadata"]
        assert "page_number" in chunk["metadata"]


@pytest.mark.asyncio
async def test_ingestion_persists_metadata_and_pages(
    client: AsyncClient, user_factory, session_factory
) -> None:
    """Metadata and per-page text survive the ingest lifecycle on the row."""
    headers, _ = await user_factory()
    case_id = await _create_case(client, headers)
    fake_qdrant = _FakeQdrant()

    p1, p2, p3, p4 = _patch_ingestion(session_factory, fake_qdrant)
    with p1, p2, p3, p4:
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("meta.txt", b"In the matter of bail. " * 30, "text/plain")},
            data={"case_id": case_id, "document_type": "judgment"},
            headers=headers,
        )
    doc_id = resp.json()["id"]

    from app.db.models import Document

    async with session_factory() as session:
        doc = await session.get(Document, doc_id)

    assert doc is not None
    assert doc.parsed_text
    assert "pages" in (doc.metadata_ or {})
    assert doc.metadata_["court"]["value"] == "Test Court"


@pytest.mark.asyncio
async def test_upload_rejects_foreign_case(client: AsyncClient, user_factory) -> None:
    """Uploading into another user's case returns 404."""
    owner_headers, _ = await user_factory()
    other_headers, _ = await user_factory()
    case_id = await _create_case(client, owner_headers)

    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("x.txt", b"hello", "text/plain")},
        data={"case_id": case_id, "document_type": "other"},
        headers=other_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ingestion_failure_sets_failed_status(
    client: AsyncClient, user_factory, session_factory
) -> None:
    """A parser crash leaves the row in a terminal `failed` state with an error."""
    headers, _ = await user_factory()
    case_id = await _create_case(client, headers)

    class _BoomParser:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def parse(self, *args, **kwargs):
            raise RuntimeError("corrupt pdf")

    with patch("app.document_pipeline.ingestion.async_session_factory", session_factory), patch(
        "app.document_pipeline.parser.DocumentParser", _BoomParser
    ):
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("broken.txt", b"whatever", "text/plain")},
            data={"case_id": case_id, "document_type": "other"},
            headers=headers,
        )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    status = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_reingest_is_claimed_once(
    client: AsyncClient, user_factory, session_factory
) -> None:
    """Only one runner may ingest a document; duplicates are rejected, not re-embedded."""
    headers, _ = await user_factory()
    case_id = await _create_case(client, headers)
    fake_qdrant = _FakeQdrant()

    body = b"IN THE HIGH COURT\nCriminal Petition No. 3 of 2024. Bail. " * 20

    from app.document_pipeline.ingestion import ingest_document

    p1, p2, p3, p4 = _patch_ingestion(session_factory, fake_qdrant)
    with p1, p2, p3, p4:
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("once.txt", body, "text/plain")},
            data={"case_id": case_id, "document_type": "judgment"},
            headers=headers,
        )
        assert resp.status_code == 201
        doc_id = resp.json()["id"]
        assert len(fake_qdrant.upserts) == 1

        # A second (e.g. analysis-inline) runner is rejected without re-embedding.
        again = await ingest_document(doc_id)
        assert again["status"] == "already_claimed"
        assert len(fake_qdrant.upserts) == 1

        # force=True is the explicit recovery path and does run again.
        forced = await ingest_document(doc_id, force=True)
        assert forced["status"] == "complete"
        assert len(fake_qdrant.upserts) == 2


@pytest.mark.asyncio
async def test_deleting_case_removes_documents(
    client: AsyncClient, user_factory, session_factory
) -> None:
    """Deleting a case cascades its documents and purges their vectors."""
    headers, _ = await user_factory()
    case_id = await _create_case(client, headers)
    fake_qdrant = _FakeQdrant()

    p1, p2, p3, p4 = _patch_ingestion(session_factory, fake_qdrant)
    with p1, p2, p3, p4:
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("to-delete.txt", b"content", "text/plain")},
            data={"case_id": case_id, "document_type": "other"},
            headers=headers,
        )
        assert resp.status_code == 201

        docs_before = await client.get(
            "/api/v1/documents/", params={"case_id": case_id}, headers=headers
        )
        assert len(docs_before.json()) == 1

        delete_resp = await client.delete(f"/api/v1/cases/{case_id}", headers=headers)
        assert delete_resp.status_code == 204

    docs_after = await client.get(
        "/api/v1/documents/", params={"case_id": case_id}, headers=headers
    )
    assert docs_after.json() == []

    # The primary file route for the deleted case now 404s.
    file_resp = await client.get(f"/api/v1/documents/case/{case_id}/file", headers=headers)
    assert file_resp.status_code == 404


@pytest.mark.asyncio
async def test_primary_document_file_is_ownership_scoped(client: AsyncClient, user_factory) -> None:
    """Another user cannot download a case's primary document."""
    owner_headers, _ = await user_factory()
    other_headers, _ = await user_factory()
    case_id = await _create_case(client, owner_headers)

    resp = await client.get(f"/api/v1/documents/case/{case_id}/file", headers=other_headers)
    assert resp.status_code == 404
