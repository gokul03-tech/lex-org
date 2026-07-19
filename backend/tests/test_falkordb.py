import pytest
from app.kg import falkordb_client

@pytest.fixture(autouse=True)
def reset_client():
    falkordb_client._falkordb_client = None
    yield
    falkordb_client._falkordb_client = None

@pytest.mark.asyncio
async def test_falkordb_connectivity():
    client = await falkordb_client.get_falkordb_client()
    connected = await client.verify_connectivity()
    assert connected is True

@pytest.mark.asyncio
async def test_falkordb_crud():
    client = await falkordb_client.get_falkordb_client()
    
    # Create Section node
    await client.run_write(
        "MERGE (s:Section {section_id: $sid}) SET s.title = $title, s.act = $act",
        {"sid": "test_pytest_1", "title": "Pytest Test Title", "act": "Pytest Act"}
    )
    
    # Query Section node
    res = await client.run_query(
        "MATCH (s:Section {section_id: $sid}) RETURN s.title AS title, s.act AS act",
        {"sid": "test_pytest_1"}
    )
    assert len(res) == 1
    assert res[0]["title"] == "Pytest Test Title"
    assert res[0]["act"] == "Pytest Act"
    
    # Delete Section node
    await client.run_write(
        "MATCH (s:Section {section_id: $sid}) DELETE s",
        {"sid": "test_pytest_1"}
    )
    
    # Query again and check empty
    res_after = await client.run_query(
        "MATCH (s:Section {section_id: $sid}) RETURN s",
        {"sid": "test_pytest_1"}
    )
    assert len(res_after) == 0
