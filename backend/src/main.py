import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI

from src.core.config import Settings
from src.core.events import InProcessEventBus
from src.core.logging import setup_logging
from src.core.registry import MetricRegistry
from src.ingestion.router import DataReceived, create_ingest_router
from src.ingestion.service import IngestionService
from src.api.router import create_api_router
from src.fhir.router import create_fhir_router
from src.storage.database import create_session_factory
from src.storage.repository import SampleRepository
from src.storage.service import StorageService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()  # type: ignore[call-arg]

    setup_logging(level=settings.log_level)

    # Core components
    metrics_path = Path(__file__).parent / "core" / "metrics"
    registry = MetricRegistry.from_directory(metrics_path)
    event_bus = InProcessEventBus(max_queue_depth=settings.event_bus_queue_depth)

    # Database
    session_factory = create_session_factory(settings)
    repo = SampleRepository()

    # Services
    ingestion_service = IngestionService(registry=registry)
    storage_service = StorageService(
        session_factory=session_factory, registry=registry
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Wire event handlers
        async def on_data_received(event: DataReceived) -> None:
            await storage_service.handle_data_received(event.payload)

        event_bus.subscribe(DataReceived, on_data_received)
        await event_bus.start()
        logger.info("OpenCadence started with %d metrics", len(registry.list_metrics()))
        yield
        await event_bus.stop()
        logger.info("OpenCadence stopped")

    app = FastAPI(
        title="OpenCadence",
        description="Self-hostable health data pipeline",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Mount routers
    app.include_router(create_ingest_router(service=ingestion_service, event_bus=event_bus, session_factory=session_factory))
    app.include_router(create_api_router(
        session_factory=session_factory, repo=repo,
        jwt_secret=settings.jwt_secret, jwt_algorithm=settings.jwt_algorithm,
    ))
    app.include_router(create_fhir_router(
        session_factory=session_factory, repo=repo, registry=registry,
        jwt_secret=settings.jwt_secret, jwt_algorithm=settings.jwt_algorithm,
    ))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
