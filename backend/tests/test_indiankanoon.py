"""Unit tests for Indian Kanoon API service and routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.indiankanoon import import_judgment
from app.services.indiankanoon import IndianKanoonService


@pytest.mark.asyncio
async def test_search_judgments() -> None:
    """Test searching judgments via IndianKanoonService."""
    service = IndianKanoonService(api_key="test-api-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "tid": 12345,
                "title": "State vs John Doe",
                "publishdate": "2023-01-01",
            }
        ]
    }

    # Mock the AsyncClient.get method
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        results = await service.search_judgments("cyber crime", page_num=0)

        assert results["results"][0]["tid"] == 12345
        assert results["results"][0]["title"] == "State vs John Doe"
        mock_get.assert_called_once()

        # Check headers and query params
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Token test-api-key"
        assert call_kwargs["params"]["formInput"] == "cyber crime"
        assert call_kwargs["params"]["pagenum"] == 0


@pytest.mark.asyncio
async def test_get_judgment() -> None:
    """Test fetching judgment details via IndianKanoonService."""
    service = IndianKanoonService(api_key="test-api-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tid": 54321,
        "title": "Jane Doe vs Union of India",
        "doc": "Full text of the judgment here.",
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        doc = await service.get_judgment("54321")

        assert doc["tid"] == 54321
        assert "Full text" in doc["doc"]
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_import_judgment_success() -> None:
    """Test importing a judgment successfully into a case."""
    mock_db = MagicMock()
    # Mock database execute to simulate finding an existing Case
    mock_case_result = MagicMock()
    mock_case_result.scalar_one_or_none.return_value = MagicMock(id="test-case-id")
    mock_db.execute = AsyncMock(return_value=mock_case_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # Mock the get_judgment service method
    mock_judgment_data = {
        "title": "Imported Landmark Case",
        "doc": "This is the raw content of the case.",
        "author": "Justice Malhotra",
        "bench": "Division Bench",
        "publishdate": "2024-05-15",
        "docsource": "Supreme Court",
    }

    with patch.object(IndianKanoonService, "get_judgment", new_callable=AsyncMock) as mock_get_judgment:
        mock_get_judgment.return_value = mock_judgment_data

        response = await import_judgment(
            case_id="test-case-id",
            doc_id="9999",
            db=mock_db,
        )

        assert "Successfully imported" in response["message"]
        assert response["title"] == "Imported Landmark Case"
        assert response["char_count"] > 0

        # Verify DB interactions
        mock_db.add.assert_called_once()
        added_doc = mock_db.add.call_args[0][0]
        assert added_doc.case_id == "test-case-id"
        assert added_doc.document_type == "judgment"
        assert added_doc.metadata_["author"] == "Justice Malhotra"
        assert added_doc.metadata_["source"] == "indian_kanoon"


@pytest.mark.asyncio
async def test_import_judgment_case_not_found() -> None:
    """Test that importing raises 404 error if case does not exist."""
    mock_db = MagicMock()
    mock_case_result = MagicMock()
    mock_case_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_case_result)

    with pytest.raises(HTTPException) as exc_info:
        await import_judgment(
            case_id="invalid-case-id",
            doc_id="9999",
            db=mock_db,
        )

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail
