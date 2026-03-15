from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.devices import create_devices_router
from src.core.auth import create_jwt_token

JWT_SECRET = "test-secret-key-min-32-characters-long"  # noqa: S105


@pytest.fixture
def device_id():
    return uuid4()


@pytest.fixture
def auth_headers(device_id):
    token = create_jwt_token([device_id], secret=JWT_SECRET)
    return {"Authorization": f"Bearer {token}"}


def _make_client(device_id, rows=None):
    mock_session_factory = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    if rows is None:
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": device_id,
            "name": "iPhone 15",
            "source_type": "apple_health",
            "created_at": now,
            "revoked_at": None,
        }
        session.execute.return_value = [mock_row]
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
        create_devices_router(
            session_factory=mock_session_factory,
            jwt_secret=JWT_SECRET,
            jwt_algorithm="HS256",
        )
    )
    return TestClient(app)


def test_list_devices(device_id, auth_headers) -> None:
    client = _make_client(device_id)
    response = client.get("/api/v1/devices", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "iPhone 15"
    assert data[0]["active"] is True


def test_list_devices_revoked(device_id, auth_headers) -> None:
    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    rows = [
        {
            "id": device_id,
            "name": "Old Watch",
            "source_type": "apple_health",
            "created_at": now,
            "revoked_at": now,
        }
    ]
    client = _make_client(device_id, rows=rows)
    response = client.get("/api/v1/devices", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data[0]["active"] is False


def test_list_devices_missing_auth(device_id) -> None:
    client = _make_client(device_id)
    response = client.get("/api/v1/devices")
    assert response.status_code == 401
