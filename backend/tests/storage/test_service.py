from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.models import IngestPayload, Sample
from src.core.registry import MetricRegistry
from src.storage.service import StorageService


def _make_payload() -> IngestPayload:
    from datetime import UTC, datetime

    return IngestPayload(
        device_id=uuid4(),
        batch=[
            Sample(
                metric="heart_rate",
                value=72.0,
                unit="bpm",
                timestamp=datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                source="healthkit",
            ),
        ],
    )


def _make_service(session_factory=None, processing_side_effect=None):
    if session_factory is None:
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        session_factory = MagicMock(return_value=session)

    registry = MagicMock(spec=MetricRegistry)
    service = StorageService(session_factory=session_factory, registry=registry)

    if processing_side_effect is not None:
        service._processing = MagicMock()
        service._processing.process.side_effect = processing_side_effect

    return service, session_factory


def test_storage_service_creates_without_error() -> None:
    service, _ = _make_service()
    assert service is not None


@pytest.mark.asyncio
async def test_dead_letter_persisted_on_failure():
    service, session_factory = _make_service(
        processing_side_effect=ValueError("processing exploded"),
    )
    payload = _make_payload()

    # Should not raise -- dead letter swallows the exception
    await service.handle_data_received(payload)

    # Processing fails before any session is opened, so the only
    # session_factory call is for the dead letter insert
    assert session_factory.call_count == 1
    dl_session = session_factory.return_value
    dl_session.execute.assert_called()
    dl_session.commit.assert_called()


@pytest.mark.asyncio
async def test_dead_letter_does_not_reraise():
    service, _ = _make_service(
        processing_side_effect=RuntimeError("db connection lost"),
    )
    payload = _make_payload()

    # Must not raise
    await service.handle_data_received(payload)


@pytest.mark.asyncio
async def test_dead_letter_insert_failure_propagates():
    """If the dead letter insert itself fails, the exception should propagate."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute.side_effect = RuntimeError("db completely down")

    session_factory = MagicMock(return_value=session)
    service, _ = _make_service(
        session_factory=session_factory,
        processing_side_effect=ValueError("processing failed"),
    )
    payload = _make_payload()

    with pytest.raises(RuntimeError, match="db completely down"):
        await service.handle_data_received(payload)
