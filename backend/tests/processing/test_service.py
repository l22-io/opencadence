from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.core.models import IngestPayload, Sample
from src.core.registry import MetricRegistry
from src.metrics.instruments import ANOMALIES_FLAGGED
from src.processing.service import ProcessingService


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
processors:
  - validators.RangeValidator
fhir:
  code: "8867-4"
  system: "http://loinc.org"
  display: "Heart rate"
""")
    return MetricRegistry.from_directory(tmp_path)


@pytest.fixture
def service(registry: MetricRegistry) -> ProcessingService:
    return ProcessingService(registry=registry)


def test_process_valid_samples(service: ProcessingService) -> None:
    device_id = uuid4()
    payload = IngestPayload(
        device_id=device_id,
        batch=[
            Sample(
                metric="heart_rate",
                value=72.0,
                unit="bpm",
                timestamp=datetime.now(UTC),
                source="test",
            ),
        ],
    )
    result = service.process(device_id, payload.batch)
    assert len(result.processed_samples) == 1
    assert len(result.anomalies) == 0


def test_process_flags_anomalies(service: ProcessingService) -> None:
    device_id = uuid4()
    payload = IngestPayload(
        device_id=device_id,
        batch=[
            Sample(
                metric="heart_rate",
                value=350.0,
                unit="bpm",
                timestamp=datetime.now(UTC),
                source="test",
            ),
        ],
    )
    result = service.process(device_id, payload.batch)
    assert len(result.processed_samples) == 1
    assert len(result.anomalies) == 1


def _anomaly_counter_value(metric_type, validator):
    try:
        return ANOMALIES_FLAGGED.labels(metric_type=metric_type, validator=validator)._value.get()
    except KeyError:
        return 0.0


def test_process_increments_anomaly_counter(service: ProcessingService) -> None:
    before = _anomaly_counter_value("heart_rate", "RangeValidator")
    sample = Sample(
        metric="heart_rate",
        value=350.0,
        unit="bpm",
        timestamp=datetime.now(UTC),
        source="test",
    )
    service.process(uuid4(), [sample])
    after = _anomaly_counter_value("heart_rate", "RangeValidator")
    assert after - before == 1
