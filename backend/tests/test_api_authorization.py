"""Authorization and ownership isolation tests for the API surface."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _create_case(
    client: AsyncClient, headers: dict[str, str], title: str = "Test Case"
) -> str:
    resp = await client.post(
        "/api/v1/cases/",
        data={"title": title, "case_type": "Criminal Defense"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_routes_require_authentication(client: AsyncClient) -> None:
    """Protected routes return 401 without a bearer token."""
    assert (await client.get("/api/v1/cases/")).status_code == 401
    assert (await client.get("/api/v1/documents/")).status_code == 401
    kanoon = await client.get(
        "/api/v1/indiankanoon/search", params={"query": "bail"}
    )
    assert kanoon.status_code == 401
    assert (await client.get("/api/v1/admin/status")).status_code == 401
    assert (await client.get("/api/v1/analysis/case/some-id/stream")).status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient) -> None:
    """A malformed token is rejected with 401."""
    resp = await client.get(
        "/api/v1/cases/", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_public_admin_registration_blocked(client: AsyncClient) -> None:
    """A client cannot self-register an administrator account."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "evil-admin@example.com",
            "password": "password123",
            "full_name": "Evil",
            "role": "admin",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_advocate_registration_allowed(client: AsyncClient) -> None:
    """Normal role registration still works and returns the created user."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "advocate@example.com",
            "password": "password123",
            "full_name": "Advocate",
            "role": "advocate",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "advocate"


@pytest.mark.asyncio
async def test_cross_user_case_access_is_404(client: AsyncClient, user_factory) -> None:
    """User B cannot read or mutate user A's case via any verb."""
    owner_headers, _ = await user_factory()
    other_headers, _ = await user_factory()
    case_id = await _create_case(client, owner_headers)

    assert (await client.get(f"/api/v1/cases/{case_id}", headers=owner_headers)).status_code == 200
    assert (await client.get(f"/api/v1/cases/{case_id}", headers=other_headers)).status_code == 404
    assert (
        await client.put(
            f"/api/v1/cases/{case_id}", json={"title": "hacked"}, headers=other_headers
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/cases/{case_id}", headers=other_headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_case_list_is_scoped_to_owner(client: AsyncClient, user_factory) -> None:
    """Listing cases never leaks another user's cases."""
    owner_headers, _ = await user_factory()
    other_headers, _ = await user_factory()
    await _create_case(client, owner_headers, "Owner Case")

    owner_list = await client.get("/api/v1/cases/", headers=owner_headers)
    other_list = await client.get("/api/v1/cases/", headers=other_headers)

    assert len(owner_list.json()) == 1
    assert other_list.json() == []


@pytest.mark.asyncio
async def test_admin_routes_enforce_role(client: AsyncClient, user_factory) -> None:
    """Admin routes reject non-admins and accept admins."""
    advocate_headers, _ = await user_factory(role="advocate")
    admin_headers, _ = await user_factory(role="admin")

    assert (await client.get("/api/v1/admin/status", headers=advocate_headers)).status_code == 403
    assert (await client.get("/api/v1/admin/status", headers=admin_headers)).status_code == 200
    assert (await client.get("/api/v1/admin/users", headers=advocate_headers)).status_code == 403
    users = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert users.status_code == 200
    assert users.json()["total"] >= 2


@pytest.mark.asyncio
async def test_reports_require_ownership(client: AsyncClient, user_factory) -> None:
    """Report routes are authenticated and ownership-scoped."""
    owner_headers, _ = await user_factory()
    other_headers, _ = await user_factory()
    case_id = await _create_case(client, owner_headers)

    assert (await client.post(f"/api/v1/reports/case/{case_id}")).status_code == 401
    assert (
        await client.post(f"/api/v1/reports/case/{case_id}", headers=other_headers)
    ).status_code == 404
    assert (
        await client.post(f"/api/v1/reports/case/{case_id}", headers=owner_headers)
    ).status_code == 200


@pytest.mark.asyncio
async def test_analysis_endpoints_are_ownership_scoped(client: AsyncClient, user_factory) -> None:
    """Analysis (GET/POST/chat/draft/stream) never crosses case ownership."""
    owner_headers, _ = await user_factory()
    other_headers, _ = await user_factory()
    case_id = await _create_case(client, owner_headers)

    assert (
        await client.get(f"/api/v1/analysis/case/{case_id}", headers=other_headers)
    ).status_code == 404
    assert (
        await client.post(f"/api/v1/analysis/case/{case_id}", headers=other_headers)
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/analysis/case/{case_id}/chat",
            json={"question": "hi"},
            headers=other_headers,
        )
    ).status_code == 404
    assert (
        await client.post(f"/api/v1/analysis/case/{case_id}/draft", json={}, headers=other_headers)
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/analysis/case/{case_id}/stream", headers=other_headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_indiankanoon_import_requires_ownership(client: AsyncClient, user_factory) -> None:
    """Importing a judgment into another user's case is rejected before any fetch."""
    owner_headers, _ = await user_factory()
    other_headers, _ = await user_factory()
    case_id = await _create_case(client, owner_headers)

    resp = await client.post(
        f"/api/v1/indiankanoon/import/{case_id}/12345", headers=other_headers
    )
    assert resp.status_code == 404
