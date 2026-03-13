from pathlib import Path
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
    app.include_router(create_stream_router(
        broadcaster=broadcaster,
        session_factory=None,
        repo=repo,
        registry=registry,
        jwt_secret=JWT_SECRET,
        jwt_algorithm="HS256",
    ))
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
        ws.send_json({
            "action": "subscribe",
            "device_ids": [str(device_id)],
            "metrics": ["heart_rate"],
        })
        response = ws.receive_json()
        assert response["type"] == "subscribed"
        assert str(device_id) in response["device_ids"]


def test_ws_subscribe_unauthorized_device(client):
    device_id = uuid4()
    other_id = uuid4()
    token = create_jwt_token([device_id], secret=JWT_SECRET)
    with client.websocket_connect(f"/api/v1/stream?token={token}") as ws:
        ws.send_json({
            "action": "subscribe",
            "device_ids": [str(other_id)],
        })
        response = ws.receive_json()
        assert response["type"] == "error"
        assert "not authorized" in response["message"].lower()


def test_ws_subscribe_unknown_metric(client, registry):
    device_id = uuid4()
    token = create_jwt_token([device_id], secret=JWT_SECRET)
    with client.websocket_connect(f"/api/v1/stream?token={token}") as ws:
        ws.send_json({
            "action": "subscribe",
            "device_ids": [str(device_id)],
            "metrics": ["nonexistent"],
        })
        response = ws.receive_json()
        assert response["type"] == "error"
        assert "nonexistent" in response["message"]


def test_ws_unsubscribe(client):
    device_id = uuid4()
    token = create_jwt_token([device_id], secret=JWT_SECRET)
    with client.websocket_connect(f"/api/v1/stream?token={token}") as ws:
        ws.send_json({
            "action": "subscribe",
            "device_ids": [str(device_id)],
        })
        ws.receive_json()  # subscribed ack

        ws.send_json({
            "action": "unsubscribe",
            "device_ids": [str(device_id)],
        })
        response = ws.receive_json()
        assert response["type"] == "unsubscribed"
