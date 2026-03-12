from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.events import InProcessEventBus
from src.core.models import IngestPayload, Sample
from src.core.registry import MetricRegistry
from src.ingestion.router import DataReceived
from src.processing.base import AnomalyFlag
from src.storage.service import StorageService


@pytest.fixture
def mock_session_factory() -> AsyncMock:
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=session)
    return factory


def test_storage_service_creates_without_error(mock_session_factory: AsyncMock) -> None:
    """Basic construction test - integration tests cover actual DB writes."""
    registry_mock = MagicMock(spec=MetricRegistry)
    service = StorageService(
        session_factory=mock_session_factory,
        registry=registry_mock,
    )
    assert service is not None
