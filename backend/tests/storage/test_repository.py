from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.core.models import IngestPayload, Sample
from src.storage.repository import SampleRepository


@pytest.fixture
def repo() -> SampleRepository:
    """Unit test with mock - integration tests go in tests/integration/."""
    return SampleRepository()


def test_samples_to_insert_params() -> None:
    """Test that payload is converted to insert-ready dicts."""
    device_id = uuid4()
    payload = IngestPayload(
        device_id=device_id,
        batch=[
            Sample(
                metric="heart_rate",
                value=72.0,
                unit="bpm",
                timestamp=datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
                source="apple_watch",
            ),
        ],
    )
    rows = SampleRepository.payload_to_rows(payload)
    assert len(rows) == 1
    assert rows[0]["device_id"] == device_id
    assert rows[0]["metric"] == "heart_rate"
    assert rows[0]["value"] == 72.0
