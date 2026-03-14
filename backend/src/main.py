import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.api.anomalies import create_anomalies_router
from src.api.devices import create_devices_router
from src.api.router import create_api_router
from src.core.config import Settings
from src.core.events import InProcessEventBus
from src.core.logging import setup_logging
from src.core.rate_limiter import RateLimiter
from src.core.registry import MetricRegistry
from src.deadletter.router import create_dead_letter_router
from src.fhir.router import create_fhir_router
from src.ingestion.router import DataReceived, create_ingest_router
from src.ingestion.service import IngestionService
from src.metrics.middleware import PrometheusMiddleware
from src.metrics.router import create_metrics_router
from src.storage.database import create_engine
from src.storage.repository import SampleRepository
from src.storage.service import StorageService
from src.streaming.broadcaster import WebSocketBroadcaster
from src.streaming.router import create_stream_router

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()  # type: ignore[call-arg]

    setup_logging(level=settings.log_level)

    # Core components
    metrics_path = Path(__file__).parent / "core" / "metrics"
    registry = MetricRegistry.from_directory(metrics_path)
    event_bus = InProcessEventBus(max_queue_depth=settings.event_bus_queue_depth)

    # Database -- create engine directly to retain reference for metrics
    engine = create_engine(settings)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = SampleRepository()

    # Rate limiting
    redis = Redis.from_url(settings.redis_url)
    rate_limiter = RateLimiter(
        redis=redis, max_requests=settings.api_rate_limit, window_seconds=60
    )

    # Services
    ingestion_service = IngestionService(registry=registry)
    storage_service = StorageService(
        session_factory=session_factory, registry=registry
    )
    broadcaster = WebSocketBroadcaster()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Wire event handlers
        async def on_data_received(event: DataReceived) -> None:
            await storage_service.handle_data_received(event.payload)

        event_bus.subscribe(DataReceived, on_data_received)
        event_bus.subscribe(DataReceived, broadcaster.handle_data_received)
        await event_bus.start()
        logger.info("OpenCadence started with %d metrics", len(registry.list_metrics()))
        yield
        await broadcaster.stop()
        await event_bus.stop()
        await redis.aclose()
        logger.info("OpenCadence stopped")

    app = FastAPI(
        title="OpenCadence",
        description="Self-hostable health data pipeline",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Mount routers
    app.include_router(create_ingest_router(
        service=ingestion_service, event_bus=event_bus,
        session_factory=session_factory, rate_limiter=rate_limiter,
    ))
    app.include_router(create_api_router(
        session_factory=session_factory, repo=repo,
        jwt_secret=settings.jwt_secret, jwt_algorithm=settings.jwt_algorithm,
    ))
    app.include_router(create_fhir_router(
        session_factory=session_factory, repo=repo, registry=registry,
        jwt_secret=settings.jwt_secret, jwt_algorithm=settings.jwt_algorithm,
    ))
    app.include_router(create_devices_router(
        session_factory=session_factory,
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
    ))
    app.include_router(create_anomalies_router(
        session_factory=session_factory,
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
    ))

    app.include_router(create_stream_router(
        broadcaster=broadcaster,
        session_factory=session_factory,
        repo=repo,
        registry=registry,
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
    ))

    app.include_router(create_dead_letter_router(
        session_factory=session_factory,
        event_bus=event_bus,
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
    ))

    app.include_router(create_metrics_router(
        engine=engine.sync_engine,
        redis=redis,
        event_bus=event_bus,
        metrics_token=settings.metrics_token,
    ))

    # Store references for probes and metrics access
    app.state.session_factory = session_factory
    app.state.engine = engine
    app.state.redis = redis
    app.state.event_bus = event_bus
    app.state.broadcaster = broadcaster

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/live")
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def readiness() -> JSONResponse:
        try:
            async with app.state.session_factory() as session:
                await session.execute(text("SELECT 1"))
            return JSONResponse({"status": "ok"})
        except Exception:
            logger.warning("Readiness check failed", exc_info=True)
            return JSONResponse({"status": "unavailable"}, status_code=503)

    app.add_middleware(PrometheusMiddleware)

    return app
