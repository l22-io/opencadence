from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.core.events import InProcessEventBus
from src.core.registry import MetricRegistry
from src.ingestion.router import create_ingest_router
from src.ingestion.service import IngestionService


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
def client(registry: MetricRegistry) -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    bus = InProcessEventBus(max_queue_depth=100)
    service = IngestionService(registry=registry)
    app.include_router(create_ingest_router(service=service, event_bus=bus))
    return TestClient(app)


def test_ingest_valid_payload(client: TestClient) -> None:
    device_id = str(uuid4())
    response = client.post(
        "/api/v1/ingest",
        json={
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
        },
    )
    assert response.status_code == 202
    assert response.json()["accepted"] == 1


def test_ingest_unknown_metric(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ingest",
        json={
            "device_id": str(uuid4()),
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
    )
    assert response.status_code == 422
    assert "errors" in response.json()["detail"]
