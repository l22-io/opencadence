from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.router import create_api_router
from src.core.auth import create_jwt_token
from src.storage.repository import SampleRepository

JWT_SECRET = "test-secret-key-min-32-characters-long"  # noqa: S105


@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = AsyncMock(spec=SampleRepository)
    repo.query_raw.return_value = [
        {
            "time": datetime(2026, 3, 11, 10, 0, tzinfo=UTC),
            "value": 72.0, "unit": "bpm", "source": "test",
        }
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
def device_id():
    return uuid4()


@pytest.fixture
def auth_headers(device_id):
    token = create_jwt_token([device_id], secret=JWT_SECRET)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(mock_repo: AsyncMock) -> TestClient:
    app = FastAPI()
    mock_session_factory = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = session
    app.include_router(
        create_api_router(
            session_factory=mock_session_factory,
            repo=mock_repo,
            jwt_secret=JWT_SECRET,
            jwt_algorithm="HS256",
        )
    )
    return TestClient(app)


def _query_url(device_id: str) -> str:
    return (
        f"/api/v1/data?device_id={device_id}&metric=heart_rate"
        f"&start=2026-03-11T00:00:00Z&end=2026-03-12T00:00:00Z&resolution=raw"
    )


def test_query_raw_data(client: TestClient, device_id, auth_headers) -> None:
    response = client.get(_query_url(str(device_id)), headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "heart_rate"
    assert data["resolution"] == "raw"
    assert len(data["samples"]) == 1


def test_query_aggregate_data(client: TestClient, device_id, auth_headers) -> None:
    url = (
        f"/api/v1/data?device_id={device_id}&metric=heart_rate"
        f"&start=2026-03-11T00:00:00Z&end=2026-03-12T00:00:00Z&resolution=1min"
    )
    response = client.get(url, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["resolution"] == "1min"


def test_query_missing_auth(client: TestClient, device_id) -> None:
    response = client.get(_query_url(str(device_id)))
    assert response.status_code == 401


def test_query_unauthorized_device(client: TestClient, auth_headers) -> None:
    other_device = str(uuid4())
    response = client.get(_query_url(other_device), headers=auth_headers)
    assert response.status_code == 403
