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
async def test_query_anomalies(repo: SampleRepository, device_id) -> None:
    session = AsyncMock()
    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    mock_row = AsyncMock()
    mock_row._mapping = {
        "time": now,
        "device_id": device_id,
        "metric": "heart_rate",
        "value": 350.0,
        "reason": "Value 350.0 outside range [20, 300]",
        "severity": "warning",
        "context": {"min": 20, "max": 300},
    }
    session.execute.return_value = [mock_row]

    start = datetime(2026, 3, 13, 0, 0, tzinfo=UTC)
    end = datetime(2026, 3, 14, 0, 0, tzinfo=UTC)
    result = await repo.query_anomalies(session, device_id, start, end)

    assert len(result) == 1
    assert result[0]["metric"] == "heart_rate"
    assert result[0]["value"] == 350.0
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_query_anomalies_with_metric_filter(
    repo: SampleRepository, device_id
) -> None:
    session = AsyncMock()
    session.execute.return_value = []

    start = datetime(2026, 3, 13, 0, 0, tzinfo=UTC)
    end = datetime(2026, 3, 14, 0, 0, tzinfo=UTC)
    result = await repo.query_anomalies(
        session, device_id, start, end, metric="heart_rate"
    )

    assert result == []
    call_args = session.execute.call_args
    query_text = str(call_args[0][0].text)
    assert "metric = :metric" in query_text
