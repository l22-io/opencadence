from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.auth import create_jwt_token
from src.core.registry import MetricRegistry
from src.fhir.router import create_fhir_router
from src.storage.repository import SampleRepository

JWT_SECRET = "test-secret-key-min-32-characters-long"


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
def mock_repo() -> AsyncMock:
    repo = AsyncMock(spec=SampleRepository)
    repo.query_raw.return_value = [
        {"time": datetime(2026, 3, 11, 10, 0, tzinfo=UTC), "value": 72.0, "unit": "bpm", "source": "test"}
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
def client(mock_repo: AsyncMock, registry: MetricRegistry) -> TestClient:
    app = FastAPI()
    mock_session_factory = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = session
    app.include_router(
        create_fhir_router(
            session_factory=mock_session_factory,
            repo=mock_repo,
            registry=registry,
            jwt_secret=JWT_SECRET,
            jwt_algorithm="HS256",
        )
    )
    return TestClient(app)


def _fhir_url(device_id: str) -> str:
    return (
        f"/fhir/Observation?device_id={device_id}&metric=heart_rate"
        f"&start=2026-03-11T00:00:00Z&end=2026-03-12T00:00:00Z"
    )


def test_fhir_observation_with_auth(client: TestClient, device_id, auth_headers) -> None:
    response = client.get(_fhir_url(str(device_id)), headers=auth_headers)
    assert response.status_code == 200
    bundle = response.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "searchset"
    assert bundle["total"] == 1
    entry = bundle["entry"][0]["resource"]
    assert entry["resourceType"] == "Observation"
    assert entry["valueQuantity"]["value"] == 72.0


def test_fhir_missing_auth(client: TestClient, device_id) -> None:
    response = client.get(_fhir_url(str(device_id)))
    assert response.status_code == 401


def test_fhir_unauthorized_device(client: TestClient, auth_headers) -> None:
    other_device = str(uuid4())
    response = client.get(_fhir_url(other_device), headers=auth_headers)
    assert response.status_code == 403
