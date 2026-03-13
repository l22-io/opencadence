from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.storage.repository import SampleRepository


@pytest.fixture
def repo() -> SampleRepository:
    return SampleRepository()


@pytest.fixture
def device_id():
    return uuid4()


@pytest.mark.asyncio
async def test_query_devices(repo: SampleRepository, device_id) -> None:
    session = AsyncMock()
    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    mock_row = AsyncMock()
    mock_row._mapping = {
        "id": device_id,
        "name": "iPhone 15",
        "source_type": "apple_health",
        "created_at": now,
        "revoked_at": None,
    }
    session.execute.return_value = [mock_row]

    result = await repo.query_devices(session, [device_id])

    assert len(result) == 1
    assert result[0]["id"] == device_id
    assert result[0]["name"] == "iPhone 15"
    assert result[0]["revoked_at"] is None
    session.execute.assert_called_once()
