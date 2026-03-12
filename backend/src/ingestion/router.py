import logging
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.events import Event, EventBus
from src.core.models import IngestPayload
from src.ingestion.service import IngestionService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DataReceived(Event):
    """Emitted when validated data is ready for processing."""
    payload: IngestPayload


class IngestResponse(BaseModel):
    accepted: int


def create_ingest_router(service: IngestionService, event_bus: EventBus) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["ingestion"])

    @router.post("/ingest", response_model=IngestResponse, status_code=202)
    async def ingest(payload: IngestPayload) -> IngestResponse:
        errors = service.validate(payload)
        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})

        published = await event_bus.publish(DataReceived(payload=payload))
        if not published:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")

        logger.info(
            "Accepted %d samples from device %s",
            len(payload.batch),
            payload.device_id,
        )
        return IngestResponse(accepted=len(payload.batch))

    return router
