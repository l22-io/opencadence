from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.auth import create_jwt_token
from src.core.registry import MetricRegistry
from src.storage.repository import SampleRepository
from src.streaming.broadcaster import WebSocketBroadcaster
from src.streaming.router import create_stream_router

JWT_SECRET = "test-secret-key-min-32-characters-long"  # noqa: S105


@pytest.fixture
def registry(tmp_path: Path) -> MetricRegistry:
    metric_file = tmp_path / "heart_rate.yaml"
    metric_file.write_text("""
name: heart_rate
label: Heart Rate
unit: bpm
valid_range:
  min: 20
  max: 300
aggregation: mean
processors: []
fhir:
  code: "8867-4"
  system: "http://loinc.org"
  display: "Heart rate"
""")
    return MetricRegistry.from_directory(tmp_path)


@pytest.fixture
def broadcaster():
    return WebSocketBroadcaster()


@pytest.fixture
def client(broadcaster, registry):
    app = FastAPI()
    repo = SampleRepository()
    app.include_router(
        create_stream_router(
            broadcaster=broadcaster,
            session_factory=None,
            repo=repo,
            registry=registry,
            jwt_secret=JWT_SECRET,
            jwt_algorithm="HS256",
        )
    )
    return TestClient(app)


def test_ws_missing_token(client):
    with pytest.raises(Exception), client.websocket_connect("/api/v1/stream"):  # noqa: B017
        pass


def test_ws_invalid_token(client):
    with pytest.raises(Exception), client.websocket_connect("/api/v1/stream?token=bad"):  # noqa: B017
        pass


def test_ws_connect_and_subscribe(client, broadcaster):
    device_id = uuid4()
    token = create_jwt_token([device_id], secret=JWT_SECRET)
    with client.websocket_connect(f"/api/v1/stream?token={token}") as ws:
        ws.send_json(
            {
                "action": "subscribe",
                "device_ids": [str(device_id)],
                "metrics": ["heart_rate"],
            }
        )
        response = ws.receive_json()
        assert response["type"] == "subscribed"
        assert str(device_id) in response["device_ids"]


def test_ws_subscribe_unauthorized_device(client):
    device_id = uuid4()
    other_id = uuid4()
    token = create_jwt_token([device_id], secret=JWT_SECRET)
    with client.websocket_connect(f"/api/v1/stream?token={token}") as ws:
        ws.send_json(
            {
                "action": "subscribe",
                "device_ids": [str(other_id)],
            }
        )
        response = ws.receive_json()
        assert response["type"] == "error"
        assert "not authorized" in response["message"].lower()


def test_ws_subscribe_unknown_metric(client, registry):
    device_id = uuid4()
    token = create_jwt_token([device_id], secret=JWT_SECRET)
    with client.websocket_connect(f"/api/v1/stream?token={token}") as ws:
        ws.send_json(
            {
                "action": "subscribe",
                "device_ids": [str(device_id)],
                "metrics": ["nonexistent"],
            }
        )
        response = ws.receive_json()
        assert response["type"] == "error"
        assert "nonexistent" in response["message"]


def test_ws_unsubscribe(client):
    device_id = uuid4()
    token = create_jwt_token([device_id], secret=JWT_SECRET)
    with client.websocket_connect(f"/api/v1/stream?token={token}") as ws:
        ws.send_json(
            {
                "action": "subscribe",
                "device_ids": [str(device_id)],
            }
        )
        ws.receive_json()  # subscribed ack

        ws.send_json(
            {
                "action": "unsubscribe",
                "device_ids": [str(device_id)],
            }
        )
        response = ws.receive_json()
        assert response["type"] == "unsubscribed"


def _make_backfill_client(broadcaster, registry):
    """Client with a mock session_factory that returns backfill rows."""
    mock_session = AsyncMock()
    mock_row = MagicMock()
    # MagicMock ignores underscore-prefixed kwargs in constructor, so set explicitly
    mock_row._mapping = {
        "time": datetime(2026, 3, 13, 10, 30, tzinfo=UTC),
        "value": 68.0,
        "unit": "bpm",
        "source": "healthkit",
    }
    mock_session.execute.return_value = [mock_row]

    @asynccontextmanager
    async def session_factory():
        yield mock_session

    app = FastAPI()
    repo = SampleRepository()
    app.include_router(
        create_stream_router(
            broadcaster=broadcaster,
            session_factory=session_factory,
            repo=repo,
            registry=registry,
            jwt_secret=JWT_SECRET,
            jwt_algorithm="HS256",
        )
    )
    return TestClient(app)


def test_ws_subscribe_with_since_sends_backfill(broadcaster, registry):
    device_id = uuid4()
    token = create_jwt_token([device_id], secret=JWT_SECRET)
    client = _make_backfill_client(broadcaster, registry)

    with client.websocket_connect(f"/api/v1/stream?token={token}") as ws:
        ws.send_json(
            {
                "action": "subscribe",
                "device_ids": [str(device_id)],
                "metrics": ["heart_rate"],
                "since": "2026-03-13T10:00:00Z",
            }
        )

        # First: backfill data
        msg = ws.receive_json()
        assert msg["type"] == "backfill"
        assert msg["data"]["value"] == 68.0
        assert msg["data"]["device_id"] == str(device_id)
        assert msg["data"]["metric"] == "heart_rate"

        # Then: backfill_complete
        msg = ws.receive_json()
        assert msg["type"] == "backfill_complete"

        # Then: subscribed ack
        msg = ws.receive_json()
        assert msg["type"] == "subscribed"
