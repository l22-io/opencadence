from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from src.core.models import IngestPayload, Sample
from src.core.registry import MetricRegistry
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
def service(registry: MetricRegistry) -> IngestionService:
    return IngestionService(registry=registry)


def test_validate_valid_payload(service: IngestionService) -> None:
    payload = IngestPayload(
        device_id=uuid4(),
        batch=[
            Sample(
                metric="heart_rate",
                value=72.0,
                unit="bpm",
                timestamp=datetime.now(UTC),
                source="test",
            )
        ],
    )
    errors = service.validate(payload)
    assert errors == []


def test_validate_unknown_metric(service: IngestionService) -> None:
    payload = IngestPayload(
        device_id=uuid4(),
        batch=[
            Sample(
                metric="unknown_metric",
                value=42.0,
                unit="units",
                timestamp=datetime.now(UTC),
                source="test",
            )
        ],
    )
    errors = service.validate(payload)
    assert len(errors) == 1
    assert "unknown_metric" in errors[0]


def test_validate_future_timestamp(service: IngestionService) -> None:
    future = datetime.now(UTC) + timedelta(hours=1)
    payload = IngestPayload(
        device_id=uuid4(),
        batch=[
            Sample(
                metric="heart_rate",
                value=72.0,
                unit="bpm",
                timestamp=future,
                source="test",
            )
        ],
    )
    errors = service.validate(payload)
    assert len(errors) == 1
    assert "future" in errors[0].lower()
