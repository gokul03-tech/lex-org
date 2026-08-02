"""Indian Kanoon API integration service."""

from __future__ import annotations

from typing import Any
import httpx
from loguru import logger

from app.core.config import settings


class IndianKanoonService:
    """Service to interact with the Indian Kanoon API.

    API documentation: http://api.indiankanoon.org
    """

    def __init__(self, api_key: str | None = None, api_base: str | None = None) -> None:
        self.api_key = api_key or settings.INDIANKANOON_API_KEY
        self.api_base = (api_base or settings.INDIANKANOON_API_BASE).rstrip("/")

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
        }
        if self.api_key:
            # Indian Kanoon expects "Token <key>" authorization format
            headers["Authorization"] = f"Token {self.api_key}"
        return headers

    async def search_judgments(self, query: str, page_num: int = 0) -> dict[str, Any]:
        """Search Indian Kanoon database for judgments.

        Args:
            query: The search term (e.g. "cyber crime doctypes:supremecourt").
            page_num: Page index (starts at 0).

        Returns:
            JSON response dictionary.
        """
        if not self.api_key:
            raise ValueError("Indian Kanoon API Key is not configured.")

        url = f"{self.api_base}/search/"
        params = {
            "formInput": query,
            "pagenum": page_num,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=self._get_headers())
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error(f"Indian Kanoon API search error: {exc}")
            raise

    async def get_judgment(self, doc_id: str) -> dict[str, Any]:
        """Fetch details for a specific judgment by document ID.

        Args:
            doc_id: The document identifier (tid).

        Returns:
            JSON response dictionary containing the doc text and metadata.
        """
        if not self.api_key:
            raise ValueError("Indian Kanoon API Key is not configured.")

        url = f"{self.api_base}/doc/{doc_id}/"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error(f"Indian Kanoon API fetch doc {doc_id} error: {exc}")
            raise
