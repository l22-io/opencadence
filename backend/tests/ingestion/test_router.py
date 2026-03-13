from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.auth import generate_api_key, hash_api_key
from src.core.events import InProcessEventBus
from src.core.rate_limiter import RateLimiter
from src.core.registry import MetricRegistry
from src.ingestion.router import create_ingest_router
from src.ingestion.service import IngestionService
from src.storage.models import Device


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
def device_and_key():
    device_id = uuid4()
    raw_key = generate_api_key(device_id)
    hashed = hash_api_key(raw_key)
    device = Device(
        id=device_id,
        name="test-device",
        api_key_hash=hashed,
        source_type="healthkit",
        revoked_at=None,
    )
    return device, raw_key


@pytest.fixture
def mock_session_factory(device_and_key):
    device, _ = device_and_key
    session = AsyncMock()
    session.get.return_value = device

    @asynccontextmanager
    async def factory():
        yield session

    return factory


@pytest.fixture
def client(registry: MetricRegistry, mock_session_factory) -> TestClient:
    app = FastAPI()
    bus = InProcessEventBus(max_queue_depth=100)
    service = IngestionService(registry=registry)
    app.include_router(
        create_ingest_router(
            service=service, event_bus=bus, session_factory=mock_session_factory,
        )
    )
    return TestClient(app)


def _payload(device_id: str) -> dict:
    return {
        "device_id": device_id,
        "batch": [
            {
                "metric": "heart_rate",
                "value": 72.0,
                "unit": "bpm",
                "timestamp": datetime.now(UTC).isoformat(),
                "source": "test",
            }
        ],
    }


def test_ingest_valid_payload(client: TestClient, device_and_key) -> None:
    device, raw_key = device_and_key
    response = client.post(
        "/api/v1/ingest",
        json=_payload(str(device.id)),
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 202
    assert response.json()["accepted"] == 1


def test_ingest_missing_api_key(client: TestClient, device_and_key) -> None:
    device, _ = device_and_key
    response = client.post("/api/v1/ingest", json=_payload(str(device.id)))
    assert response.status_code == 401


def test_ingest_device_id_mismatch(client: TestClient, device_and_key) -> None:
    _, raw_key = device_and_key
    other_device_id = str(uuid4())
    response = client.post(
        "/api/v1/ingest",
        json=_payload(other_device_id),
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 403


def test_ingest_unknown_metric(client: TestClient, device_and_key) -> None:
    device, raw_key = device_and_key
    response = client.post(
        "/api/v1/ingest",
        json={
            "device_id": str(device.id),
            "batch": [
                {
                    "metric": "unknown",
                    "value": 42.0,
                    "unit": "x",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "source": "test",
                }
            ],
        },
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 422
    assert "errors" in response.json()["detail"]


def _make_rate_limited_client(registry, mock_session_factory, mock_redis):
    """Create a test client with a rate limiter."""
    app = FastAPI()
    bus = InProcessEventBus(max_queue_depth=100)
    service = IngestionService(registry=registry)
    limiter = RateLimiter(redis=mock_redis, max_requests=2, window_seconds=60)
    app.include_router(
        create_ingest_router(
            service=service, event_bus=bus,
            session_factory=mock_session_factory, rate_limiter=limiter,
        )
    )
    return TestClient(app)


def test_ingest_rate_limited(
    registry: MetricRegistry, mock_session_factory, device_and_key,
) -> None:
    device, raw_key = device_and_key
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=3)  # over limit of 2
    mock_redis.ttl = AsyncMock(return_value=45)

    client = _make_rate_limited_client(registry, mock_session_factory, mock_redis)
    response = client.post(
        "/api/v1/ingest",
        json=_payload(str(device.id)),
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded"


from src.metrics.instruments import SAMPLES_INGESTED


def _ingested_counter_value(metric_type):
    try:
        return SAMPLES_INGESTED.labels(metric_type=metric_type)._value.get()
    except KeyError:
        return 0.0


def test_ingest_increments_samples_counter(client: TestClient, device_and_key) -> None:
    device, raw_key = device_and_key
    before = _ingested_counter_value("heart_rate")
    client.post(
        "/api/v1/ingest",
        json=_payload(str(device.id)),
        headers={"X-API-Key": raw_key},
    )
    after = _ingested_counter_value("heart_rate")
    assert after - before == 1
