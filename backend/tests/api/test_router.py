from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.router import create_api_router
from src.storage.repository import SampleRepository


@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = AsyncMock(spec=SampleRepository)
    repo.query_raw.return_value = [
        {"time": datetime(2026, 3, 11, 10, 0, tzinfo=UTC), "value": 72.0, "unit": "bpm", "source": "test"}
    ]
    repo.query_aggregates.return_value = [
        {
            "time": datetime(2026, 3, 11, 10, 0, tzinfo=UTC),
            "min_value": 60.0, "max_value": 85.0,
            "mean_value": 72.0, "stddev_value": 5.0, "sample_count": 12,
        }
    ]
    return repo


@pytest.fixture
def client(mock_repo: AsyncMock) -> TestClient:
    app = FastAPI()
    mock_session_factory = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = session
    app.include_router(
        create_api_router(session_factory=mock_session_factory, repo=mock_repo)
    )
    return TestClient(app)


def test_query_raw_data(client: TestClient, mock_repo: AsyncMock) -> None:
    device_id = str(uuid4())
    response = client.get(
        f"/api/v1/data?device_id={device_id}&metric=heart_rate"
        f"&start=2026-03-11T00:00:00Z&end=2026-03-12T00:00:00Z&resolution=raw"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "heart_rate"
    assert data["resolution"] == "raw"
    assert len(data["samples"]) == 1


def test_query_aggregate_data(client: TestClient, mock_repo: AsyncMock) -> None:
    device_id = str(uuid4())
    response = client.get(
        f"/api/v1/data?device_id={device_id}&metric=heart_rate"
        f"&start=2026-03-11T00:00:00Z&end=2026-03-12T00:00:00Z&resolution=1min"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["resolution"] == "1min"
