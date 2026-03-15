from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.metrics.router import create_metrics_router


@pytest.fixture
def mock_app_state():
    engine = MagicMock()
    pool = MagicMock()
    pool.size.return_value = 10
    pool.checkedout.return_value = 2
    engine.pool = pool

    redis = AsyncMock()
    redis.ping.return_value = True

    event_bus = MagicMock()
    event_bus.queue_depth = 5

    return engine, redis, event_bus


def _make_app(engine, redis, event_bus, metrics_token=None):
    app = FastAPI()
    app.include_router(
        create_metrics_router(
            engine=engine, redis=redis, event_bus=event_bus,
            metrics_token=metrics_token,
        )
    )
    return app


def test_metrics_returns_prometheus_format(mock_app_state):
    engine, redis, event_bus = mock_app_state
    app = _make_app(engine, redis, event_bus)
    client = TestClient(app)

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "oc_http_requests_total" in response.text
    assert "oc_db_pool_size" in response.text


def test_metrics_no_auth_when_token_not_set(mock_app_state):
    engine, redis, event_bus = mock_app_state
    app = _make_app(engine, redis, event_bus, metrics_token=None)
    client = TestClient(app)

    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_auth_required_when_token_set(mock_app_state):
    engine, redis, event_bus = mock_app_state
    app = _make_app(engine, redis, event_bus, metrics_token="secret-token")  # noqa: S106
    client = TestClient(app)

    # No auth header
    response = client.get("/metrics")
    assert response.status_code == 401

    # Wrong token
    response = client.get("/metrics", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401

    # Correct token
    response = client.get(
        "/metrics", headers={"Authorization": "Bearer secret-token"}
    )
    assert response.status_code == 200
    assert "oc_http_requests_total" in response.text
