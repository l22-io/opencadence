from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.anomalies import create_anomalies_router
from src.core.auth import create_jwt_token

JWT_SECRET = "test-secret-key-min-32-characters-long"  # noqa: S105


@pytest.fixture
def device_id():
    return uuid4()


@pytest.fixture
def other_device_id():
    return uuid4()


@pytest.fixture
def auth_headers(device_id):
    token = create_jwt_token([device_id], secret=JWT_SECRET)
    return {"Authorization": f"Bearer {token}"}


def _make_client(rows=None):
    mock_session_factory = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    if rows is None:
        session.execute.return_value = []
    else:
        mock_rows = []
        for r in rows:
            mock_row = MagicMock()
            mock_row._mapping = r
            mock_rows.append(mock_row)
        session.execute.return_value = mock_rows

    mock_session_factory.return_value = session
    app = FastAPI()
    app.include_router(
        create_anomalies_router(
            session_factory=mock_session_factory,
            jwt_secret=JWT_SECRET,
            jwt_algorithm="HS256",
        )
    )
    return TestClient(app)


def _anomaly_url(device_id, **kwargs):
    params = {
        "device_id": str(device_id),
        "start": "2026-03-13T00:00:00Z",
        "end": "2026-03-14T00:00:00Z",
        **kwargs,
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"/api/v1/anomalies?{qs}"


def test_query_anomalies(device_id, auth_headers) -> None:
    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    rows = [{
        "time": now,
        "device_id": device_id,
        "metric": "heart_rate",
        "value": 350.0,
        "reason": "Value 350.0 outside range [20, 300]",
        "severity": "warning",
        "context": {"min": 20, "max": 300},
    }]
    client = _make_client(rows=rows)
    response = client.get(_anomaly_url(device_id), headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["metric"] == "heart_rate"
    assert data[0]["severity"] == "warning"


def test_query_anomalies_empty(device_id, auth_headers) -> None:
    client = _make_client()
    response = client.get(_anomaly_url(device_id), headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_query_anomalies_device_scope(device_id, other_device_id, auth_headers) -> None:
    client = _make_client()
    response = client.get(
        _anomaly_url(other_device_id), headers=auth_headers
    )
    assert response.status_code == 403


def test_query_anomalies_missing_auth(device_id) -> None:
    client = _make_client()
    response = client.get(_anomaly_url(device_id))
    assert response.status_code == 401


def test_query_anomalies_with_metric_filter(device_id, auth_headers) -> None:
    client = _make_client()
    response = client.get(
        _anomaly_url(device_id, metric="heart_rate"), headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == []


def test_query_anomalies_pagination(device_id, auth_headers) -> None:
    client = _make_client()
    response = client.get(
        _anomaly_url(device_id, limit="50", offset="10"), headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == []
