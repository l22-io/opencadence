from unittest.mock import AsyncMock, MagicMock

import pytest

from src.metrics.instruments import (
    ANOMALIES_FLAGGED,
    DB_POOL_CHECKED_OUT,
    DB_POOL_SIZE,
    EVENT_BUS_QUEUE_DEPTH,
    HTTP_REQUESTS_TOTAL,
    RATE_LIMIT_REJECTIONS,
    REDIS_CONNECTED,
    SAMPLES_INGESTED,
    collect_infra_metrics,
)


def _counter_value(counter, labels=None):
    """Read the current value of a counter (with optional labels)."""
    if labels:
        return counter.labels(**labels)._value.get()
    return counter._value.get()


def _gauge_value(gauge, labels=None):
    """Read the current value of a gauge."""
    if labels:
        return gauge.labels(**labels)._value.get()
    return gauge._value.get()


def test_samples_ingested_counter():
    before = _counter_value(SAMPLES_INGESTED, {"metric_type": "heart_rate"})
    SAMPLES_INGESTED.labels(metric_type="heart_rate").inc(3)
    after = _counter_value(SAMPLES_INGESTED, {"metric_type": "heart_rate"})
    assert after - before == 3


def test_anomalies_flagged_counter():
    before = _counter_value(
        ANOMALIES_FLAGGED, {"metric_type": "heart_rate", "validator": "RangeValidator"}
    )
    ANOMALIES_FLAGGED.labels(
        metric_type="heart_rate", validator="RangeValidator"
    ).inc()
    after = _counter_value(
        ANOMALIES_FLAGGED, {"metric_type": "heart_rate", "validator": "RangeValidator"}
    )
    assert after - before == 1


def test_rate_limit_rejections_counter():
    before = _counter_value(RATE_LIMIT_REJECTIONS)
    RATE_LIMIT_REJECTIONS.inc()
    after = _counter_value(RATE_LIMIT_REJECTIONS)
    assert after - before == 1


@pytest.mark.asyncio
async def test_collect_infra_metrics_healthy():
    engine = MagicMock()
    pool = MagicMock()
    pool.size.return_value = 10
    pool.checkedout.return_value = 3
    engine.pool = pool

    redis = AsyncMock()
    redis.ping.return_value = True

    event_bus = MagicMock()
    event_bus.queue_depth = 42

    await collect_infra_metrics(engine=engine, redis=redis, event_bus=event_bus)

    assert _gauge_value(DB_POOL_SIZE) == 10
    assert _gauge_value(DB_POOL_CHECKED_OUT) == 3
    assert _gauge_value(REDIS_CONNECTED) == 1
    assert _gauge_value(EVENT_BUS_QUEUE_DEPTH) == 42


@pytest.mark.asyncio
async def test_collect_infra_metrics_redis_down():
    engine = MagicMock()
    pool = MagicMock()
    pool.size.return_value = 5
    pool.checkedout.return_value = 0
    engine.pool = pool

    redis = AsyncMock()
    redis.ping.side_effect = ConnectionError("Redis down")

    event_bus = MagicMock()
    event_bus.queue_depth = 0

    await collect_infra_metrics(engine=engine, redis=redis, event_bus=event_bus)

    assert _gauge_value(REDIS_CONNECTED) == 0
