from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.config import Settings


@pytest.fixture
def healthy_session_factory():
    session = AsyncMock()
    result = MagicMock()
    result.scalar.return_value = 1
    session.execute.return_value = result

    @asynccontextmanager
    async def factory():
        yield session

    return factory


@pytest.fixture
def unhealthy_session_factory():
    session = AsyncMock()
    session.execute.side_effect = Exception("Connection refused")

    @asynccontextmanager
    async def factory():
        yield session

    return factory


def _make_app(session_factory) -> FastAPI:
    from src.main import create_app

    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        redis_url="redis://localhost",
        jwt_secret="test-secret",  # noqa: S106
    )  # type: ignore[call-arg]
    app = create_app(settings=settings)
    # Override the session factory used by probes
    app.state.session_factory = session_factory
    return app


def test_liveness_always_ok():
    app = _make_app(AsyncMock())
    client = TestClient(app)
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_healthy(healthy_session_factory):
    app = _make_app(healthy_session_factory)
    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_unhealthy(unhealthy_session_factory):
    app = _make_app(unhealthy_session_factory)
    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
