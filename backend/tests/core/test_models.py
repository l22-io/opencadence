from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.core.models import IngestPayload, Sample


def test_valid_sample() -> None:
    sample = Sample(
        metric="heart_rate",
        value=72.0,
        unit="bpm",
        timestamp=datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
        source="apple_watch_series_9",
    )
    assert sample.metric == "heart_rate"
    assert sample.value == 72.0


def test_valid_ingest_payload() -> None:
    payload = IngestPayload(
        device_id=uuid4(),
        batch=[
            Sample(
                metric="heart_rate",
                value=72.0,
                unit="bpm",
                timestamp=datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
                source="apple_watch_series_9",
            )
        ],
    )
    assert len(payload.batch) == 1


def test_empty_batch_rejected() -> None:
    with pytest.raises(ValidationError):
        IngestPayload(device_id=uuid4(), batch=[])


def test_batch_over_limit_rejected() -> None:
    samples = [
        Sample(
            metric="heart_rate",
            value=72.0,
            unit="bpm",
            timestamp=datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
            source="test",
        )
        for _ in range(1001)
    ]
    with pytest.raises(ValidationError):
        IngestPayload(device_id=uuid4(), batch=samples)
