from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.auth import create_jwt_token
from src.deadletter.router import create_dead_letter_router

JWT_SECRET = "test-secret-key-min-32-characters-long"  # noqa: S105


def _mock_dl_row(id_=1, replayed=False):
    now = datetime(2026, 3, 14, 10, 0, tzinfo=UTC)
    row = MagicMock()
    row._mapping = {
        "id": id_,
        "event_type": "DataReceived",
        "payload": {
            "device_id": str(uuid4()),
            "batch": [
                {
                    "metric": "heart_rate",
                    "value": 72.0,
                    "unit": "bpm",
                    "timestamp": "2026-03-14T12:00:00Z",
                    "source": "healthkit",
                }
            ],
        },
        "error": "connection refused",
        "module": "storage",
        "created_at": now,
        "replayed_at": now if replayed else None,
    }
    return row


def _mock_result(rows, first_row=None):
    """Create a mock SQLAlchemy result that supports iteration and .first()."""
    result = MagicMock()
    result.__iter__ = MagicMock(return_value=iter(rows))
    result.first.return_value = first_row
    return result


def _make_client(rows=None, event_bus=None):
    mock_session = AsyncMock()
    if rows is not None:
        first = rows[0] if rows else None
        mock_session.execute.return_value = _mock_result(rows, first_row=first)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    session_factory = MagicMock(return_value=mock_session)

    if event_bus is None:
        event_bus = AsyncMock()
        event_bus.publish = AsyncMock(return_value=True)

    app = FastAPI()
    app.include_router(
        create_dead_letter_router(
            session_factory=session_factory,
            event_bus=event_bus,
            jwt_secret=JWT_SECRET,
            jwt_algorithm="HS256",
        )
    )
    return TestClient(app), mock_session, event_bus


@pytest.fixture
def auth_headers():
    token = create_jwt_token([uuid4()], secret=JWT_SECRET)
    return {"Authorization": f"Bearer {token}"}


def test_list_dead_letters(auth_headers):
    rows = [_mock_dl_row(id_=1), _mock_dl_row(id_=2)]
    client, _, _ = _make_client(rows=rows)

    response = client.get("/api/v1/dead-letters", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[0]["event_type"] == "DataReceived"


def test_list_dead_letters_replayed_filter(auth_headers):
    rows = [_mock_dl_row(id_=1, replayed=True)]
    client, _, _ = _make_client(rows=rows)

    response = client.get(
        "/api/v1/dead-letters?status=replayed",
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_list_dead_letters_missing_auth():
    client, _, _ = _make_client(rows=[])
    response = client.get("/api/v1/dead-letters")
    assert response.status_code == 401


def test_replay_dead_letter(auth_headers):
    row = _mock_dl_row(id_=1, replayed=False)
    client, session, event_bus = _make_client(rows=[row])

    response = client.post("/api/v1/dead-letters/1/replay", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "replayed"
    event_bus.publish.assert_called_once()


def test_replay_already_replayed(auth_headers):
    row = _mock_dl_row(id_=1, replayed=True)
    client, _, _ = _make_client(rows=[row])

    response = client.post("/api/v1/dead-letters/1/replay", headers=auth_headers)
    assert response.status_code == 409


def test_replay_not_found(auth_headers):
    client, _, _ = _make_client(rows=[])

    response = client.post("/api/v1/dead-letters/999/replay", headers=auth_headers)
    assert response.status_code == 404


def test_replay_queue_full(auth_headers):
    row = _mock_dl_row(id_=1, replayed=False)
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock(return_value=False)
    client, _, _ = _make_client(rows=[row], event_bus=event_bus)

    response = client.post("/api/v1/dead-letters/1/replay", headers=auth_headers)
    assert response.status_code == 503
