import logging
from dataclasses import dataclass

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.dependencies import require_api_key
from src.core.events import Event, EventBus
from src.core.models import IngestPayload
from src.core.rate_limiter import RateLimiter
from src.ingestion.service import IngestionService
from src.metrics.instruments import SAMPLES_INGESTED
from src.storage.models import Device

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DataReceived(Event):
    """Emitted when validated data is ready for processing."""
    payload: IngestPayload


class IngestResponse(BaseModel):
    accepted: int


def create_ingest_router(
    service: IngestionService,
    event_bus: EventBus,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    rate_limiter: RateLimiter | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["ingestion"])

    async def get_authenticated_device(
        api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> Device:
        if session_factory is None:
            raise HTTPException(status_code=500, detail="Auth not configured")
        async with session_factory() as session:
            return await require_api_key(api_key=api_key, session=session)

    @router.post("/ingest", response_model=IngestResponse, status_code=202)
    async def ingest(
        payload: IngestPayload,
        device: Device = Depends(get_authenticated_device),
    ) -> IngestResponse:
        if payload.device_id != device.id:
            raise HTTPException(
                status_code=403, detail="Device ID does not match API key"
            )

        if rate_limiter is not None:
            allowed, remaining, reset = await rate_limiter.check(device.id)
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={
                        "Retry-After": str(reset),
                        "X-RateLimit-Remaining": "0",
                    },
                )

        errors = service.validate(payload)
        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})

        published = await event_bus.publish(DataReceived(payload=payload))
        if not published:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")

        for sample in payload.batch:
            SAMPLES_INGESTED.labels(metric_type=sample.metric).inc()

        logger.info(
            "Accepted %d samples from device %s",
            len(payload.batch),
            payload.device_id,
        )
        return IngestResponse(accepted=len(payload.batch))

    return router
