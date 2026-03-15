import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.models import IngestPayload, Sample
from src.ingestion.router import DataReceived
from src.streaming.broadcaster import SubscriptionFilter, WebSocketBroadcaster


def test_empty_filter_matches_nothing():
    f = SubscriptionFilter()
    device_id = uuid4()
    assert not f.matches(device_id, "heart_rate")


def test_subscribe_all_metrics():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics=None)
    assert f.matches(device_id, "heart_rate")
    assert f.matches(device_id, "spo2")
    assert not f.matches(uuid4(), "heart_rate")


def test_subscribe_specific_metrics():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics={"heart_rate"})
    assert f.matches(device_id, "heart_rate")
    assert not f.matches(device_id, "spo2")


def test_subscribe_additive():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics={"heart_rate"})
    f.add(device_id, metrics={"spo2"})
    assert f.matches(device_id, "heart_rate")
    assert f.matches(device_id, "spo2")


def test_subscribe_all_replaces_specific():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics={"heart_rate"})
    f.add(device_id, metrics=None)
    assert f.matches(device_id, "spo2")


def test_unsubscribe_device():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics=None)
    f.remove(device_id, metrics=None)
    assert not f.matches(device_id, "heart_rate")


def test_unsubscribe_specific_metric():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics={"heart_rate", "spo2"})
    f.remove(device_id, metrics={"heart_rate"})
    assert not f.matches(device_id, "heart_rate")
    assert f.matches(device_id, "spo2")


def test_device_ids_property():
    f = SubscriptionFilter()
    d1, d2 = uuid4(), uuid4()
    f.add(d1, metrics=None)
    f.add(d2, metrics={"heart_rate"})
    assert set(f.device_ids) == {d1, d2}


def test_metrics_for_device():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics={"heart_rate", "spo2"})
    assert f.metrics_for(device_id) == {"heart_rate", "spo2"}


def test_metrics_for_device_all():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics=None)
    assert f.metrics_for(device_id) is None


# --- WebSocketBroadcaster tests ---


@pytest.fixture
def broadcaster():
    return WebSocketBroadcaster()


def _mock_ws():
    ws = AsyncMock(spec=["send_json", "close"])
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_register_and_unregister(broadcaster):
    ws = _mock_ws()
    filter_ = SubscriptionFilter()
    broadcaster.register(ws, filter_)
    assert broadcaster.connection_count == 1
    broadcaster.unregister(ws)
    assert broadcaster.connection_count == 0


@pytest.mark.asyncio
async def test_broadcast_sends_to_matching_client(broadcaster):
    ws = _mock_ws()
    device_id = uuid4()
    filter_ = SubscriptionFilter()
    filter_.add(device_id, metrics={"heart_rate"})
    broadcaster.register(ws, filter_)

    await broadcaster.broadcast(
        device_id,
        "heart_rate",
        {
            "device_id": str(device_id),
            "metric": "heart_rate",
            "time": "2026-03-13T12:00:00Z",
            "value": 72.0,
            "unit": "bpm",
            "source": "healthkit",
        },
    )

    ws.send_json.assert_called_once()
    msg = ws.send_json.call_args[0][0]
    assert msg["type"] == "sample"
    assert msg["data"]["value"] == 72.0


@pytest.mark.asyncio
async def test_broadcast_skips_non_matching_client(broadcaster):
    ws = _mock_ws()
    device_id = uuid4()
    filter_ = SubscriptionFilter()
    filter_.add(device_id, metrics={"spo2"})
    broadcaster.register(ws, filter_)

    await broadcaster.broadcast(
        device_id,
        "heart_rate",
        {
            "device_id": str(device_id),
            "metric": "heart_rate",
            "time": "2026-03-13T12:00:00Z",
            "value": 72.0,
            "unit": "bpm",
            "source": "healthkit",
        },
    )

    ws.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_disconnects_slow_client(broadcaster):
    ws = _mock_ws()
    ws.send_json = AsyncMock(side_effect=asyncio.TimeoutError)
    device_id = uuid4()
    filter_ = SubscriptionFilter()
    filter_.add(device_id, metrics=None)
    broadcaster.register(ws, filter_)

    await broadcaster.broadcast(
        device_id,
        "heart_rate",
        {
            "device_id": str(device_id),
            "metric": "heart_rate",
            "time": "2026-03-13T12:00:00Z",
            "value": 72.0,
            "unit": "bpm",
            "source": "healthkit",
        },
    )

    ws.close.assert_called_once()
    assert broadcaster.connection_count == 0


@pytest.mark.asyncio
async def test_stop_closes_all_connections(broadcaster):
    ws1, ws2 = _mock_ws(), _mock_ws()
    broadcaster.register(ws1, SubscriptionFilter())
    broadcaster.register(ws2, SubscriptionFilter())

    await broadcaster.stop()

    ws1.close.assert_called_once_with(code=1001, reason="Server shutting down")
    ws2.close.assert_called_once_with(code=1001, reason="Server shutting down")
    assert broadcaster.connection_count == 0


@pytest.mark.asyncio
async def test_handle_data_received_broadcasts_samples(broadcaster):
    ws = _mock_ws()
    device_id = uuid4()
    filter_ = SubscriptionFilter()
    filter_.add(device_id, metrics={"heart_rate"})
    broadcaster.register(ws, filter_)

    payload = IngestPayload(
        device_id=device_id,
        batch=[
            Sample(
                metric="heart_rate",
                value=72.0,
                unit="bpm",
                timestamp=datetime(2026, 3, 13, 12, 0, tzinfo=UTC),
                source="healthkit",
            ),
        ],
    )
    event = DataReceived(payload=payload)
    await broadcaster.handle_data_received(event)

    assert ws.send_json.call_count == 1
    msg = ws.send_json.call_args[0][0]
    assert msg["type"] == "sample"
    assert msg["data"]["metric"] == "heart_rate"
    assert msg["data"]["device_id"] == str(device_id)
